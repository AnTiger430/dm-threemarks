# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .formatters import BasePayloadPresenter, fmt_int


class HangarPayloadPresenter(BasePayloadPresenter):
    """Builds the hangar HUD payload dictionary (clean 2x2 thresholds without tilde)."""

    def build_payload(self, rating, ema, marks, has_rating, thresholds=None):
        t65, t85, t95, t100, t_next_pct, t_next = self.resolve_thresholds(thresholds, rating)
        if not has_rating:
            t65 = t85 = t95 = t100 = t_next = 0
        return {
            'min': False,
            'nodata': not has_rating,
            'pct': (u'%.2f%%' % rating) if rating > 0 else u'--.--%',
            'bar': round(max(0.0, min(100.0, rating)), 2),
            'marks': int(marks),
            'ema': fmt_int(ema) if ema > 0 else u'—',
            't65': fmt_int(t65) if (has_rating and 0 < t65 < 30000) else u'—',
            't85': fmt_int(t85) if (has_rating and 0 < t85 < 30000) else u'—',
            't95': fmt_int(t95) if (has_rating and 0 < t95 < 30000) else u'—',
            't100': fmt_int(t100) if (has_rating and 0 < t100 < 30000) else u'—',
            'v3d': {
                'isHangar': True,
                'mini': False,
                'pct': round(rating, 2) if has_rating else 0.0,
                'bar': round(max(0.0, min(100.0, rating)), 2) if has_rating else 0.0,
                'delta': None,
                'sDelta': None,
                'dmg': int(round(ema)) if has_rating else 0,
                'tHold': 0,
                'tMark': 0,
                'tPlus1': 0,
                't65': int(t65),
                't85': int(t85),
                't95': int(t95),
                't100': int(t100),
                'tNextPct': int(t_next_pct) if has_rating else 65,
                'tNext': int(t_next),
                'own': 0,
                'spot': 0,
                'track': 0,
                'stun': 0,
                'marks': int(marks),
                'big': False,
                'isSpg': False,
                'alt': False,
                'hasRating': bool(has_rating),
            },
        }
