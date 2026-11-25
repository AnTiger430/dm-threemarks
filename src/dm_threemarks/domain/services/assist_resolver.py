# -*- coding: utf-8 -*-
from __future__ import absolute_import


class AssistResolver(object):
    """Domain rules for assist channel selection and battle delta evaluation."""

    @staticmethod
    def resolve_channels(spot, track):
        s_val = max(0, int(round(float(spot or 0))))
        t_val = max(0, int(round(float(track or 0))))
        max_ast = max(s_val, t_val)
        active = None
        if s_val > t_val:
            active = 'spot'
        elif t_val > s_val:
            active = 'track'
        return s_val, t_val, max_ast, active

    @staticmethod
    def classify_delta(delta, zero_band, big_by_dmg, is_big_dmg, big_from):
        if delta is None:
            return 'zero'
        val = float(delta)
        if big_by_dmg and is_big_dmg and val >= 0.0:
            return 'big'
        if not big_by_dmg and big_from > 0.0 and val >= big_from:
            return 'big'
        if abs(val) <= zero_band:
            return 'zero'
        return 'minus' if val < 0.0 else 'plus'
