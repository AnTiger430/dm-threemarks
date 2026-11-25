# -*- coding: utf-8 -*-
from __future__ import absolute_import


class Thresholds(object):
    """Moving-average total damage thresholds for 65% / 85% / 95% / 100%."""

    __slots__ = ('t65', 't85', 't95', 't100')

    def __init__(self, t65=0, t85=0, t95=0, t100=0):
        self.t65 = int(t65 or 0)
        self.t85 = int(t85 or 0)
        self.t95 = int(t95 or 0)
        self.t100 = int(t100 or 0)

    def as_tuple(self):
        return (self.t65, self.t85, self.t95, self.t100)

    def next_for(self, pct):
        val = float(pct)
        if val < 65.0:
            return (65, self.t65)
        if val < 85.0:
            return (85, self.t85)
        if val < 95.0:
            return (95, self.t95)
        return (100, self.t100)
