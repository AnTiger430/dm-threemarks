# -*- coding: utf-8 -*-
from __future__ import absolute_import


class DragController(object):
    """Handles Ctrl+LMB panel dragging and minimize toggle button clicks."""

    def __init__(self, input_provider, config_store, config_sync):
        self._input = input_provider
        self._config = config_store
        self._config_sync = config_sync
        self._drag = None
        self._drag_from = (0.0, 0.0)
        self._drag_moved = False
        self._btn_press = False

    def reset(self):
        self._drag = None
        self._drag_moved = False
        self._btn_press = False

    def is_dragging(self):
        return self._drag is not None

    def _in_button(self, panel, px, py):
        try:
            ui = getattr(panel, 'ui', 1.0)
            if panel.mode == 'b':
                vx = panel.visual_x() if hasattr(panel, 'visual_x') else panel.x
                bx1 = max(0.0, panel.wPx - 24.0 * ui)
                bx2 = panel.wPx
                by1 = 2.0 * ui
                by2 = 28.0 * ui
                return (
                    vx + self._input.px_w(bx1) <= px <= vx + self._input.px_w(bx2) and
                    panel.y - self._input.px_h(by2) <= py <= panel.y - self._input.px_h(by1)
                )
            if panel.mode == 'h':
                vis_w = panel.wPx - 24.0 * ui
                bx1, bx2 = vis_w - 22.0 * ui, vis_w - 2.0 * ui
            else:
                bx1, bx2 = 2.0 * ui, 22.0 * ui
            by1, by2 = 2.0 * ui, 22.0 * ui
            left = panel.x + self._input.px_w(12.0 * ui)
            top = panel.y - self._input.px_h(12.0 * ui)
            return (
                left + self._input.px_w(bx1) <= px <= left + self._input.px_w(bx2) and
                top - self._input.px_h(by2) <= py <= top - self._input.px_h(by1)
            )
        except Exception:
            return False

    def poll(self, panel, min_key=None):
        """Process one input tick; return True if minimize state changed."""
        if panel is None:
            return False
        try:
            px, py = self._input.cursor_position()
            down = self._input.is_lmb_down()
            ctrl = self._input.is_ctrl_down()
            toggled = False
            if down and self._btn_press:
                pass
            elif down and self._drag is not None:
                if not self._drag_moved:
                    fx, fy = self._drag_from
                    if abs(px - fx) > self._input.px_w(2) or abs(py - fy) > self._input.px_h(2):
                        self._drag_moved = True
                if self._drag_moved:
                    panel.move_to(px - self._drag[0], py - self._drag[1])
            elif down and ctrl:
                if min_key is not None and self._in_button(panel, px, py):
                    self._btn_press = True
                elif panel.contains((px, py)):
                    self._drag = (px - panel.x, py - panel.y)
                    self._drag_from = (px, py)
                    self._drag_moved = (min_key is None)
            elif self._btn_press:
                self._btn_press = False
                if min_key is not None and self._in_button(panel, px, py):
                    self._config.set(min_key, not bool(self._config.get(min_key, False)))
                    self._config_sync.save_current()
                    toggled = True
            elif self._drag is not None:
                self._drag = None
                if self._drag_moved:
                    self._config.set(panel.keyX, round(panel.x, 4))
                    self._config.set(panel.keyY, round(panel.y, 4))
                    self._config_sync.save_current()
                elif min_key is not None and self._in_button(panel, *self._drag_from):
                    self._config.set(min_key, not bool(self._config.get(min_key, False)))
                    self._config_sync.save_current()
                    toggled = True
            setattr(panel, '_dragging_flag', self._drag is not None)
            return toggled
        except Exception:
            self._drag = None
            setattr(panel, '_dragging_flag', False)
            return False
