# -*- coding: utf-8 -*-
from __future__ import absolute_import


class ForecastResult(object):
    """Result of projecting MoE percentage and EMA after the current battle."""

    __slots__ = ('after', 'delta', 'whole_avg', 'projected_avg')

    def __init__(self, after, delta, whole_avg, projected_avg):
        self.after = float(after)
        self.delta = float(delta)
        self.whole_avg = float(whole_avg)
        self.projected_avg = float(projected_avg)

    def as_tuple(self):
        return (self.after, self.delta, self.whole_avg, self.projected_avg)


class BattlePlan(object):
    """Cached battle forecast plan including curve day and purple threshold."""

    __slots__ = ('after', 'delta', 'whole_avg', 'curve_day', 'big_at', 'hold_dmg')

    def __init__(self, after, delta, whole_avg, curve_day, big_at, hold_dmg=0):
        self.after = float(after)
        self.delta = delta
        self.whole_avg = int(whole_avg)
        self.curve_day = curve_day
        self.big_at = float(big_at)
        self.hold_dmg = int(hold_dmg)

    def as_tuple(self):
        return (self.after, self.delta, self.whole_avg, self.curve_day, self.big_at)
