# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
import math
import time

from ..constants import ANCHORS, API_DAY_LAG, EPOCH_DAY, KNOTS


def day_of(ts):
    """Ordinal day number (date.toordinal) for UTC timestamp."""
    return EPOCH_DAY + int(float(ts) // 86400)


def utc_day_text(ts=None):
    return time.strftime('%Y-%m-%d', time.gmtime(time.time() if ts is None else ts))


def day_number(text):
    year, month, dom = [int(part) for part in str(text).split('-')]
    return datetime.date(year, month, dom).toordinal()


def day_text(number):
    return datetime.date.fromordinal(int(number)).isoformat()


def api_day(updated, now=None):
    """Ordinal day for which API serves the curve, from updated_at (or None)."""
    try:
        updated = float(updated or 0)
    except (TypeError, ValueError):
        return None
    if updated <= 0.0:
        return None
    ref = time.time() if now is None else float(now)
    day = day_of(updated) + API_DAY_LAG
    return day if abs(day - day_of(ref)) <= 60 else None


def served_on_knots(served):
    """Return True if all API percentiles lie linearly between the 8 server knots."""
    for i in range(len(KNOTS) - 1):
        p0, p1 = KNOTS[i], KNOTS[i + 1]
        d0, d1 = int(served[float(p0)]), int(served[float(p1)])
        for q in range(p0 + 1, p1):
            value = served.get(float(q))
            if value is not None and \
                    int(value) != d0 + (d1 - d0) * (q - p0) // (p1 - p0):
                return False
    return True


class Curve(object):
    """Tank damage distribution curve: (percent, damage) points."""

    __slots__ = ('points', 'exact', 'day')

    def __init__(self, raw, day=None):
        pts = []
        for key, value in raw.items():
            try:
                p, d = float(key), float(value)
            except (TypeError, ValueError):
                continue
            if 0.0 < p <= 100.0 and d > 0.0:
                pts.append((p, d))
        pts.sort()
        served = dict(pts)
        self.exact = False
        if all(float(k) in served for k in KNOTS):
            knots = [(float(k), float(int(served[float(k)]))) for k in KNOTS]
            rising = all(a[1] < b[1] for a, b in zip(knots, knots[1:]))
            if rising and served_on_knots(served):
                pts, self.exact = knots, True
            elif all(float(a) in served for a in ANCHORS):
                pts = [(float(a), served[float(a)]) for a in ANCHORS]
        clean = []
        for p, d in pts:
            if len(clean) == 1 and d == clean[0][1]:
                clean[0] = (p, d)
                continue
            if clean and d <= clean[-1][1]:
                continue
            clean.append((p, d))
        self.points = clean
        self.day = day

    def __nonzero__(self):
        return len(self.points) >= 2

    __bool__ = __nonzero__

    @classmethod
    def from_row(cls, values, day=None):
        if not isinstance(values, list) or len(values) != len(ANCHORS):
            return None
        try:
            raw = dict((str(p), float(v)) for p, v in zip(ANCHORS, values))
        except (TypeError, ValueError):
            return None
        if min(raw.values()) <= 0.0:
            return None
        curve = cls(raw, day)
        return curve if curve else None

    def damage_of(self, percent):
        pts = self.points
        if not pts:
            return 0.0
        if percent <= pts[0][0]:
            return pts[0][1] * (percent / pts[0][0]) if pts[0][0] > 0 else pts[0][1]
        for i in range(1, len(pts)):
            p0, d0 = pts[i - 1]
            p1, d1 = pts[i]
            if percent <= p1:
                return d0 + (percent - p0) * (d1 - d0) / (p1 - p0)
        return pts[-1][1]

    def percent_of(self, damage):
        pts = self.points
        if not pts:
            return 0.0
        if damage <= pts[0][1]:
            return pts[0][0] * (damage / pts[0][1]) if pts[0][1] > 0 else 0.0
        for i in range(1, len(pts)):
            p0, d0 = pts[i - 1]
            p1, d1 = pts[i]
            if damage <= d1:
                return p0 + (damage - d0) * (p1 - p0) / (d1 - d0)
        return 100.0

    def cell(self, damage):
        """Integer hundredths of a percent floored identically to the server."""
        if not self.exact or damage != int(damage):
            return int(math.floor(self.percent_of(damage) * 100.0 + 1e-6))
        damage = int(damage)
        pts = self.points
        p0, d0 = int(pts[0][0]), int(pts[0][1])
        if damage <= d0:
            return p0 * 100 * damage // d0 if damage > 0 else 0
        for i in range(1, len(pts)):
            p1, d1 = int(pts[i][0]), int(pts[i][1])
            if damage <= d1:
                return p0 * 100 + (damage - d0) * (p1 - p0) * 100 // (d1 - d0)
            p0, d0 = p1, d1
        return 10000

    def explains(self, damage, percent):
        shown = int(round(percent * 100.0))
        if self.exact:
            return self.cell(damage) == shown
        return abs(self.percent_of(damage) * 100.0 - (shown + 0.5)) <= 1.25

    def whole_damage(self, percent):
        if percent > 0.0:
            return math.ceil(self.damage_of(percent) - 1e-6)
        return 0.0

    def thresholds(self):
        return (
            self.damage_of(65.0),
            self.damage_of(85.0),
            self.damage_of(95.0),
            self.damage_of(100.0),
        )
