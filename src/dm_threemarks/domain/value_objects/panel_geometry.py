# -*- coding: utf-8 -*-
from __future__ import absolute_import


class PanelGeometry(object):
    """Window pixel geometry and anchor compensation math."""

    __slots__ = ('win_w', 'win_h')

    def __init__(self, win_w, win_h):
        self.win_w = int(win_w)
        self.win_h = int(win_h)

    @staticmethod
    def anchor_offset(anchor, old_w, old_h, new_w, new_h, px_w_fn, px_h_fn):
        if old_w == new_w and old_h == new_h:
            return (0.0, 0.0)
        dw = px_w_fn(new_w - old_w)
        dh = px_h_fn(new_h - old_h)
        if anchor in (0, 3):
            dx = 0.0
        elif anchor in (1, 4):
            dx = -0.5 * dw
        else:
            dx = -dw
        dy = 0.0 if anchor in (0, 1, 2) else dh
        return (dx, dy)
