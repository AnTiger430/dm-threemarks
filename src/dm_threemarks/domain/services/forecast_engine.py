# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math

from ..constants import EMA_K, PCT_CELL, STALE_GAP
from ..entities.curve import day_of
from ..value_objects.forecast_result import ForecastResult


def floor_pct(value):
    """Floor percentage to hundredths exactly matching the WoT server."""
    return math.floor(float(value) * 100.0 + 1e-6) / 100.0


def next_average(avg, combined):
    """Return (rounded_integer_avg_after_battle, unrounded_float_projected)."""
    avg = float(avg)
    projected = avg + (float(combined) - avg) * EMA_K
    return (float(int(projected + 0.5)) if projected > 0.0 else 0.0, projected)


class ForecastEngine(object):
    """Pure domain service implementing server curve selection and MoE prediction."""

    def __init__(self, epoch):
        self._epoch = epoch

    @staticmethod
    def written_at(seen, percent, avg, battles, last_battle):
        if not seen:
            return 0
        try:
            same = (
                abs(float(seen.get('p', 0.0) or 0.0) - percent) < 0.005 and
                float(seen.get('a', 0.0) or 0.0) == float(avg or 0.0) and
                int(seen.get('b', battles)) == int(battles)
            )
            if same:
                return int(seen.get('w', 0) or 0)
            return int(last_battle or 0)
        except (TypeError, ValueError):
            return 0

    def server_curve(self, mark, curve, now, day_curve_fn):
        key = str(mark.int_cd)
        pick, days = curve, [curve]
        if curve.day is not None:
            today = day_of(now)
            by_day = {}
            for day in range(today, today - 4, -1):
                found = day_curve_fn(key, day, curve)
                if found:
                    by_day[day] = found
            by_day.setdefault(curve.day, curve)
            want = self._epoch.day(now)
            nearest = min(by_day, key=lambda d: (abs(d - want), -d))
            pick = by_day[nearest]
            days = [by_day[d] for d in sorted(by_day, reverse=True)]
        avg, percent = mark.avg, mark.percent
        if not (avg > 0.0 and percent > 0.0):
            return (pick, 0.0, False)

        def onto(c):
            if c.exact:
                return 0.0
            return percent + PCT_CELL / 2.0 - c.percent_of(avg)

        if pick.explains(avg, percent):
            return (pick, onto(pick), True)
        last = mark.written
        fresh = self._epoch.holds(last, now)
        later = self._epoch.seen_day if self._epoch.seen_at > last else 0
        for other in days:
            if other is not pick and other.explains(avg, percent):
                if fresh and later <= other.day:
                    return (other, onto(other), True)
                return (pick, 0.0, False)
        if later and pick.exact and pick.day is not None and later >= pick.day:
            return (pick, 0.0, False)
        if fresh or (last > 0 and self._epoch.by_clock(last) == self._epoch.by_clock(now)):
            return (pick, percent + PCT_CELL / 2.0 - pick.percent_of(avg), True)
        return (pick, 0.0, False)

    def current_percent(self, mark, curve, now, day_curve_fn):
        if mark.avg > 0.0 and curve:
            server, _shift, anchored = self.server_curve(mark, curve, now, day_curve_fn)
            if not anchored and server.exact:
                live = server.cell(mark.avg) / 100.0
                if abs(live - mark.percent) >= STALE_GAP:
                    return (max(0.0, min(100.0, live)), True)
        return (mark.percent, False)

    def forecast(self, mark, combined, curve, now, day_curve_fn):
        base, _recomputed = self.current_percent(mark, curve, now, day_curve_fn)
        server, shift, _anchored = self.server_curve(mark, curve, now, day_curve_fn)
        if mark.avg > 0.0 or mark.percent <= 0.0:
            avg = float(mark.avg)
            whole, projected = next_average(avg, combined)
            if not shift:
                after = server.cell(whole) / 100.0
                return ForecastResult(after, after - base, whole, projected)
            pct = server.percent_of(whole)
            first = server.points[0][1]
            if 0.0 < avg <= first and whole <= first:
                pct *= 1.0 + shift / server.percent_of(avg)
            else:
                pct += shift
        else:
            avg = server.whole_damage(mark.percent)
            whole, projected = next_average(avg, combined)
            if server.explains(avg, mark.percent):
                after = server.cell(whole) / 100.0
                return ForecastResult(after, after - base, whole, projected)
            pct = mark.percent + PCT_CELL / 2.0 + server.percent_of(whole) - server.percent_of(avg)
        after = floor_pct(max(0.0, min(100.0, pct)))
        return ForecastResult(after, after - base, whole, projected)

    def hold_damage(self, mark, curve, now, day_curve_fn):
        """Return fixed battle combined damage needed to hold current mark percentage."""
        if mark is None or (mark.avg <= 0.0 and mark.percent <= 0.0):
            return 0
        hold = float(mark.avg or 0.0)
        if curve:
            base = self.current_percent(mark, curve, now, day_curve_fn)[0]
            server, shift, _anchored = self.server_curve(mark, curve, now, day_curve_fn)
            if base > 0.0 and not shift:
                req = float(server.whole_damage(base))
                if req > hold:
                    hold = req
        return int(math.ceil(hold - 1e-6)) if hold > 0.0 else 0
