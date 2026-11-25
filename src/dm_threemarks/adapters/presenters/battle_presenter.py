# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .formatters import BasePayloadPresenter, fmt_int


class BattlePayloadPresenter(BasePayloadPresenter):
    """Builds the battle HUD payload dictionary identically to v10.12.7."""

    def __init__(self, config_store):
        self._config = config_store

    def build_payload(self, shown_pct, bar_pct, delta, dmg, proj_ema, marks,
                      glowing, has_rating, big=False, report=None, thresholds=None,
                      is_spg=False, alt_down=False, session_base=0.0, hold_dmg=None):
        if has_rating:
            pct_txt = u'%.2f%%' % shown_pct
            if delta is None:
                delta_txt = u''
            else:
                sign = u'+' if delta >= 0 else u''
                delta_txt = u'%s%.2f%%' % (sign, delta)
        else:
            pct_txt = u'--.--%'
            delta_txt = u''

        target_hold = int(round(hold_dmg)) if hold_dmg is not None else int(round(proj_ema))
        data = {
            'min': False,
            'pct': pct_txt,
            'delta': delta_txt,
            'bar': round(max(0.0, min(100.0, bar_pct)), 2),
            'glow': bool(glowing),
            'big': bool(big),
            'dmg': fmt_int(dmg),
            'proj': fmt_int(target_hold) if target_hold > 0 else u'—',
            'marks': int(marks),
            'dmgTitle': self._config.get('textDamageTitle', u'Сум. урон:'),
        }

        preset = self._config.integer('battlePreset', 0, 1)
        parts = report.to_parts_dict() if report is not None else {}
        if preset == 0:
            t65, t85, t95, _t100, t_next_pct, t_next = self.resolve_thresholds(thresholds, shown_pct)
            if not has_rating:
                t65 = t85 = t95 = t_next = 0
            if parts.get('src') == 'feedback':
                own = int(parts.get('damage', 0) or 0)
                spot = int(parts.get('radio', 0) or 0)
                track = int(parts.get('track', 0) or 0)
                stun = int(parts.get('stun', 0) or 0)
            else:
                own = int(parts.get('effDamage', 0) or 0)
                spot = int(parts.get('effAssist', 0) or 0)
                track = 0
                stun = int(parts.get('effStun', 0) or 0)
            s_delta = (shown_pct - session_base) if has_rating else None
            data['v3d'] = {
                'pct': round(shown_pct, 2),
                'bar': round(bar_pct, 2),
                'delta': round(delta, 2) if delta is not None else None,
                'sDelta': round(s_delta, 2) if s_delta is not None else None,
                'dmg': int(dmg),
                'tHold': max(0, target_hold),
                'tMark': 0,
                'tPlus1': 0,
                'tNextPct': int(t_next_pct),
                'tNext': int(t_next),
                't95': int(t95),
                'own': max(0, own),
                'spot': max(0, spot),
                'track': max(0, track),
                'stun': max(0, stun),
                'marks': int(marks),
                'big': bool(big),
                'isSpg': bool(is_spg),
                'alt': bool(alt_down),
                'hasRating': bool(has_rating),
            }
        else:
            show_spot = bool(self._config.get('showSpot', True))
            show_track = bool(self._config.get('showTrack', True))
            if show_spot or show_track:
                assist = (
                    parts.get('radio', 0) if show_spot else None,
                    parts.get('track', 0) if show_track else None,
                )
                if assist[0] is not None or assist[1] is not None:
                    data['ast'] = [None if v is None else int(v) for v in assist]
        return data
