# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math

from ..constants import LEVELS
from ..entities.curve import Curve
from ..value_objects.thresholds import Thresholds


def calc_percent(ema, start, end, d, p):
    """Analytic equivalent of spoter threshold estimator (step 0.1 up to 30000)."""
    if not (start <= end < 100.001) or ema >= 30000:
        return ema
    need = end * d / p
    result = max(ema, need) + 0.1
    return min(result, 30000.0)


def calc_statistics(p, d):
    """Return {65: ema, 85: ema, 95: ema} fallback threshold estimates."""
    pc = math.floor(p) + 1
    dc = calc_percent(d, p, pc, d, p)
    data = [
        2,
        calc_percent(0, 0.0, 20.0, d, p),
        calc_percent(0, 0.0, 40.0, d, p),
        calc_percent(0, 0.0, 55.0, d, p),
        calc_percent(0, 0.0, 65.0, d, p),
        calc_percent(0, 0.0, 85.0, d, p),
        calc_percent(0, 0.0, 95.0, d, p),
        calc_percent(0, 0.0, 100.0, d, p),
    ]
    idx = [x for x in LEVELS if x >= p][0]
    check = LEVELS.index(idx)
    limit1 = dc
    limit2 = data[check]
    delta = limit2 - limit1
    for value in xrange(len(data)):
        if data[value] == limit1 or data[value] == limit2:
            continue
        if value > check:
            data[value] = int(math.ceil(math.ceil((data[value] + delta) / 10.0)) * 10)
    return {65: data[4], 85: data[5], 95: data[6]}


def build_fallback_curve(percent, avg):
    """Build a monotonic approximate Curve anchored at (percent, avg) when API data is absent."""
    try:
        p = float(percent or 0.0)
        d = float(avg or 0.0)
    except (TypeError, ValueError):
        return None
    if not (0.0 < p <= 100.0 and d > 0.0):
        return None
    stats = calc_statistics(p, d)
    t65 = float(stats[65])
    t85 = float(stats[85])
    t95 = float(stats[95])
    t100 = max(t95 + 10.0, float(int(math.ceil(t95 * (100.0 / 95.0) / 10.0) * 10)))
    candidates = []
    for q in (20.0, 40.0, 55.0):
        if q < p:
            val = float(calc_percent(0, 0.0, q, d, p))
        elif p < 65.0 and t65 > d:
            val = d + (t65 - d) * ((q - p) / (65.0 - p))
        else:
            val = d * (q / p)
        candidates.append((q, max(1.0, val)))
    candidates.extend([(65.0, t65), (85.0, t85), (95.0, t95), (100.0, t100)])

    below = []
    cur_d = d
    for q, val in sorted(candidates, reverse=True):
        if q <= p - 0.5 and 0.0 < val < cur_d:
            below.append((q, val))
            cur_d = val
    below.reverse()

    above = []
    cur_d = d
    for q, val in sorted(candidates):
        if q >= p + 0.5 and val > cur_d:
            above.append((q, val))
            cur_d = val

    raw = dict((str(q), float(val)) for q, val in (below + [(p, d)] + above))
    curve = Curve(raw, day=None)
    return curve if curve else None


class ThresholdCalculator(object):
    """Domain service computing 65/85/95/100% EMA damage thresholds with caching."""

    def __init__(self, forecast_engine):
        self._forecast = forecast_engine
        self._cache_key = None
        self._cache_val = Thresholds()

    def compute_thresholds(self, mark, rating, ema, curve, now, day_curve_fn, calc_version):
        if mark is None or (not curve and (rating <= 0 or ema <= 0)):
            return Thresholds()
        key = (
            int(mark.int_cd or 0),
            int(round(float(mark.avg))),
            int(round(float(mark.percent) * 100)),
            int(round(float(rating) * 100)),
            int(round(float(ema))),
            int(calc_version),
        )
        if self._cache_key == key:
            return self._cache_val
        res = [0, 0, 0, 0]
        if curve:
            limits = self._forecast.server_curve(mark, curve, now, day_curve_fn)[0].thresholds()
            if limits:
                for i in range(min(4, len(limits))):
                    v = limits[i]
                    if v is not None and 0 < v < 30000:
                        res[i] = int(math.ceil(v))
        if not any(res) and rating > 0 and ema > 0:
            stats = calc_statistics(float(rating), float(ema))
            for i, k in enumerate((65, 85, 95)):
                v = stats.get(k)
                if v and 0 < v < 30000:
                    res[i] = int(math.ceil(v))
            if res[2] > 0:
                res[3] = min(30000, int(math.ceil(res[2] * (100.0 / 95.0) / 10.0) * 10))
        out = Thresholds(res[0], res[1], res[2], res[3])
        self._cache_key = key
        self._cache_val = out
        return out
