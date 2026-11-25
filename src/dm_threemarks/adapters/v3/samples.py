# -*- coding: utf-8 -*-
from __future__ import absolute_import

PREVIEW_ORDER = ('plus', 'minus', 'zero', 'big')

PREVIEW_SAMPLES = {
    'plus': dict(pct=43.28, delta=1.63, dmg=2266, proj=1480, big=False, glow=False, assist=(577, 120)),
    'minus': dict(pct=70.64, delta=-0.70, dmg=1120, proj=2320, big=False, glow=False, assist=(0, 0)),
    'zero': dict(pct=85.47, delta=0.0, dmg=2890, proj=2890, big=False, glow=False, assist=(12, 12)),
    'big': dict(pct=97.83, delta=4.52, dmg=6820, proj=3750, big=True, glow=True, assist=(210, 1830)),
}

PREVIEW_SAMPLES_V3 = {
    'plus': dict(
        pct=43.28, delta=1.25, sDelta=1.85, dmg=1850, tHold=1480, tMark=2150, tPlus1=1480,
        tNextPct=65, tNext=2150, t65=2150, t85=2890, t95=3450, t100=3920,
        own=1100, spot=750, track=0, stun=0, marks=0, big=False, isSpg=False, hasRating=True,
    ),
    'minus': dict(
        pct=70.64, delta=-1.15, sDelta=-1.15, dmg=1420, tHold=2320, tMark=2890, tPlus1=2320,
        tNextPct=85, tNext=2890, t65=2150, t85=2890, t95=3450, t100=3920,
        own=900, spot=0, track=520, stun=0, marks=1, big=False, isSpg=False, hasRating=True,
    ),
    'zero': dict(
        pct=85.47, delta=0.0, sDelta=0.0, dmg=2890, tHold=2890, tMark=3450, tPlus1=2890,
        tNextPct=95, tNext=3450, t65=2150, t85=2890, t95=3450, t100=3920,
        own=2410, spot=480, track=480, stun=0, marks=2, big=False, isSpg=False, hasRating=True,
    ),
    'big': dict(
        pct=97.83, delta=4.65, sDelta=5.20, dmg=6820, tHold=3750, tMark=3920, tPlus1=3750,
        tNextPct=100, tNext=3920, t65=2150, t85=2890, t95=3450, t100=3920,
        own=4120, spot=1200, track=2700, stun=850, marks=3, big=True, isSpg=True, hasRating=True,
    ),
}

PREVIEW_CONTAINER_W = 280
PREVIEW_CONTAINER_H = 176

SVG_SPOT_RUNS = (
    (3, 2, 3, 2), (6, 2, 1, 1), (3, 3, 1, 1), (4, 3, 4, 2), (8, 3, 1, 1),
    (6, 4, 1, 1), (7, 4, 3, 2), (3, 5, 3, 2), (8, 5, 1, 1), (9, 5, 2, 2),
    (3, 6, 1, 1), (4, 6, 4, 2), (9, 6, 1, 1), (10, 6, 2, 2), (6, 7, 3, 2),
    (10, 7, 1, 1), (11, 7, 2, 2), (3, 8, 2, 2), (5, 8, 1, 1), (7, 8, 1, 1),
    (8, 8, 2, 2), (11, 8, 2, 2), (3, 9, 4, 2), (8, 9, 2, 2), (11, 9, 1, 1),
    (12, 9, 1, 2), (13, 9, 1, 1), (5, 10, 2, 2), (7, 10, 1, 1), (9, 10, 2, 2),
    (12, 10, 2, 2), (1, 11, 1, 1), (2, 11, 2, 2), (4, 11, 1, 1), (6, 11, 2, 2),
    (9, 11, 2, 2), (12, 11, 2, 2), (1, 12, 4, 2), (6, 12, 2, 2), (9, 12, 1, 1),
    (10, 12, 1, 2), (12, 12, 1, 1), (13, 12, 1, 2), (1, 13, 4, 2),
    (1, 14, 1, 1), (2, 14, 2, 2), (4, 14, 1, 1),
)

SVG_TRACK_RUNS = (
    (6, 1, 2, 2), (8, 1, 1, 1), (10, 1, 1, 1), (6, 2, 6, 2), (4, 3, 1, 1),
    (7, 3, 6, 2), (3, 4, 3, 2), (7, 4, 1, 2), (8, 4, 1, 1), (10, 4, 1, 1),
    (11, 4, 3, 2), (3, 5, 1, 1), (4, 5, 5, 2), (11, 5, 1, 1), (12, 5, 2, 2),
    (0, 6, 2, 1), (4, 6, 1, 1), (5, 6, 5, 2), (11, 6, 3, 2), (0, 7, 3, 2),
    (3, 7, 1, 1), (4, 7, 2, 2), (7, 7, 1, 1), (8, 7, 7, 2), (0, 8, 1, 1),
    (1, 8, 5, 2), (6, 8, 1, 1), (8, 8, 1, 1), (9, 8, 2, 2), (12, 8, 1, 1),
    (13, 8, 2, 2), (1, 9, 1, 1), (2, 9, 5, 2), (7, 9, 1, 1), (8, 9, 3, 2),
    (13, 9, 1, 1), (5, 10, 7, 2), (6, 11, 2, 2), (9, 11, 1, 1), (10, 11, 2, 2),
    (5, 12, 1, 1), (6, 12, 2, 2), (10, 12, 1, 1), (5, 13, 1, 1), (6, 13, 3, 2),
    (7, 14, 2, 2),
)
