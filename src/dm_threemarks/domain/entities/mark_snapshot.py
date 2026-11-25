# -*- coding: utf-8 -*-
from __future__ import absolute_import


class MarkSnapshot(object):
    """Server MoE reading from vehicle dossier or persistent cache."""

    __slots__ = ('int_cd', 'percent', 'avg', 'battles', 'marks', 'written')

    def __init__(self, int_cd, percent, avg, battles, marks, written):
        self.int_cd = int_cd
        self.percent = float(percent)
        self.avg = float(avg)
        self.battles = int(battles or 0)
        self.marks = int(marks or 0)
        self.written = int(written or 0)


class VehicleDossier(object):
    """Normalized dossier record for a single vehicle."""

    __slots__ = ('percent', 'avg', 'marks', 'battles', 'last_battle')

    def __init__(self, percent, avg, marks, battles, last_battle):
        self.percent = float(percent)
        self.avg = float(avg)
        self.marks = max(0, min(3, int(marks or 0)))
        self.battles = int(battles or 0)
        self.last_battle = int(last_battle or 0)

    def as_tuple(self):
        return (self.percent, self.avg, self.marks, self.battles, self.last_battle)
