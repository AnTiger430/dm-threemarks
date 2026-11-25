# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

from ...application.config.defaults import PCT_WINDOW_H, PCT_WINDOW_W, WINDOW_H, WINDOW_W
from ...application.ports.panel_view import IPanelView
from ...domain.value_objects.panel_geometry import PanelGeometry
from ..settings.in_game_settings import SET_H
from ..v3.samples import PREVIEW_SAMPLES_V3
from .wulf_views import GF_OK, TmView, TmWindow, WindowStatus, get_main_window, resolve_layout_id, window_alive


class GamefacePanelAdapter(IPanelView):
    """Gameface HUD overlay panel implementing IPanelView."""

    def __init__(self, mode, key_x, key_y, config_store, ui_serializer,
                 metrics_calc, input_provider, scheduler, logger,
                 visibility_guard=None, settings_controller=None,
                 w_px=WINDOW_W, h_px=WINDOW_H):
        self.mode = mode
        self.keyX = key_x
        self.keyY = key_y
        self._config = config_store
        self._ui = ui_serializer
        self._metrics = metrics_calc
        self._input = input_provider
        self._scheduler = scheduler
        self._logger = logger
        self._guard = visibility_guard
        self._settings = settings_controller
        self._dragging_flag = False

        self.x = float(self._config.get(key_x))
        self.y = float(self._config.get(key_y))
        self._base_w = float(w_px)
        self._base_h = float(h_px)
        self.ui = 1.0
        self._geo_key = None
        self._restore_y = None
        self.wPx = float(w_px)
        self.hPx = float(h_px)
        self._bmin_offset_x = 0.0
        self.payload = '{}'
        self.mini = False
        self.model = None
        self.window = None
        self._token = 0
        self._ready = False
        self._win_ready = False
        self._shown = False
        self._last_move = None
        self._destroyed = False
        self._covered = False
        self._visible = False
        self._dim = False

    @property
    def settings_controller(self):
        return self._settings

    def settings_controller_clear(self):
        self._settings = None

    def is_settings_open(self):
        return self._settings is not None and self._settings.open

    def set_mini(self, mini):
        self.mini = bool(mini)

    def build(self):
        self._destroyed = False
        if not GF_OK or self.window is not None:
            return
        self._token += 1
        self._load(self._token)

    def _load(self, token, retry=0):
        if token != self._token or self._destroyed:
            return
        layout_id = resolve_layout_id()
        parent = get_main_window()
        if layout_id is None or parent is None or getattr(parent, 'proxy', None) is None or \
                getattr(parent, 'windowStatus', None) != WindowStatus.LOADED:
            if retry < 100:
                self._scheduler.schedule(0.1, lambda: self._load(token, retry + 1))
            else:
                self._logger.once('nomainwindow', 'panel: main window or Gameface layout never became ready')
            return
        try:
            self.window = TmWindow(TmView(self), parent, owner=self)
            self.window.load()
        except Exception:
            self._logger.error('panel window')

    def on_window_ready(self):
        self._win_ready = True
        self._sync_window_visibility()

    def _sync_window_visibility(self):
        if not window_alive(self.window):
            return
        want_show = bool(self._win_ready and self._ready and (not self._covered) and self.payload != '{}')
        if want_show == self._shown:
            return
        try:
            if want_show:
                self._move(force=True)
                self.window.show(False)
            else:
                self.window.hide()
            self._shown = want_show
            self._visible = want_show
        except Exception:
            if not window_alive(self.window):
                self.window = None

    def on_js_ready(self):
        self._ready = True
        self._publish(force=True)
        self._move(force=True)
        self._sync_window_visibility()

    def push(self, data):
        st = self._settings
        editing = st is not None and st.open
        data = {'set': st.items, 'setH': SET_H, 'mode': 's'} if editing else dict(data, mode=self.mode)
        data['dim'] = bool(self._dim) and not editing
        data['cfg'] = self._settings is not None
        data['ui'] = self._ui.ui_payload()
        if editing:
            data['ui']['s'] = 1.0
        battle_view = not editing and data.get('mode') == 'b'
        hangar_view = not editing and data.get('mode') == 'h'
        bmin = battle_view and bool(data.get('bmin', False))
        preset = int(data['ui'].get('preset', 0)) if battle_view else 0
        self.mini = bool(bmin)
        self._bmin_offset_x = 0.0
        if (battle_view and preset == 0) or hangar_view:
            v3d = data.get('v3d') or PREVIEW_SAMPLES_V3['plus']
            if hangar_view:
                v3d = dict(v3d, isHangar=True)
                m_cfg = self._config.to_v3_from_hangar()
                ui_scale_val = float(data['ui'].get('hs', data['ui']['s']))
                anchor = 0
            else:
                m_cfg = self._config.raw_dict()
                ui_scale_val = float(data['ui']['s'])
                anchor = self._config.integer('v3Anchor', 0, 5)
            m = self._metrics.compute(m_cfg, v3d, alt=bool(v3d.get('alt', False)))
            data['v3m'] = [m['winW'], m['winH']]
            geo = (ui_scale_val, editing, 'vh' if hangar_view else 'v3', m['winW'], m['winH'])
            if geo != self._geo_key:
                prev_geo = self._geo_key
                self._geo_key = geo
                self.ui = ui_scale_val
                exp_w, exp_h = float(m['winW']) * self.ui, float(m['winH']) * self.ui
                dx = dy = 0.0
                if prev_geo is not None and (self.wPx, self.hPx) != (exp_w, exp_h):
                    dx, dy = PanelGeometry.anchor_offset(
                        anchor, self.wPx, self.hPx, exp_w, exp_h,
                        self._input.px_w, self._input.px_h,
                    )
                self.wPx, self.hPx = exp_w, exp_h
                self.move_to(self.x + dx, self.y + dy)
        else:
            pct_only = battle_view and bool(data['ui'].get('onlyPct', True))
            ast = ((not editing) and self.mode == 'b' and ('ast' in data) and not pct_only)
            geo = (data['ui']['s'], editing, ast, pct_only)
            if geo != self._geo_key:
                self._geo_key = geo
                self.ui = data['ui']['s']
                base_h = (SET_H + 24.0) if editing else ((PCT_WINDOW_H if pct_only else self._base_h) + (22.0 if ast else 0.0))
                base_w = PCT_WINDOW_W if pct_only else self._base_w
                self.wPx, self.hPx = base_w * self.ui, base_h * self.ui
                self.move_to(self.x, self.y)
        payload = json.dumps(data, ensure_ascii=True)
        if payload != self.payload:
            self.payload = payload
            self._publish()
        self._move()
        self._sync_window_visibility()

    def _publish(self, force=False):
        if self.model is None or not (self._ready or force):
            return
        try:
            with self.model.transaction() as model:
                model.setPayload(self.payload)
        except Exception:
            pass

    def visual_x(self):
        w = self._input.px_w(self.wPx)
        return max(-1.0, min(1.0 - w, self.x + self._bmin_offset_x))

    def contains(self, pos):
        try:
            px, py = float(pos[0]), float(pos[1])
        except Exception:
            return False
        editing = self.is_settings_open()
        vx = self.visual_x()
        if self.mini and self.mode == 'b' and not editing:
            bx1 = max(0.0, self.wPx - 24.0 * self.ui)
            bx2 = self.wPx
            by1 = 2.0 * self.ui
            by2 = 28.0 * self.ui
            return (
                vx + self._input.px_w(bx1) <= px <= vx + self._input.px_w(bx2) and
                self.y - self._input.px_h(by2) <= py <= self.y - self._input.px_h(by1)
            )
        wp, hp = (self.wPx, 98.0 * self.ui) if (self.mini and self.mode == 'h' and not editing) else (self.wPx, self.hPx)
        w, h = self._input.px_w(wp), self._input.px_h(hp)
        return (vx <= px <= vx + w) and (self.y - h <= py <= self.y)

    def open_settings(self):
        st = self._settings
        if st is None or st.open:
            return
        st.open = True
        st.target = 0
        st.pick = None
        st.active = None
        st.pressed = False
        st.build()
        self._restore_y = self.y
        self._config.settings_open = True
        self._logger.info('settings opened')

    def close_settings(self):
        st = self._settings
        if st is None or not st.open:
            return
        st.save()
        st.open = False
        st.active = None
        st.pressed = False
        self._config.settings_open = False
        if self._restore_y is not None:
            self.y = self._restore_y
            self._restore_y = None
        self._logger.info('settings closed')

    def move_to(self, x, y):
        w, h = self._input.px_w(self.wPx), self._input.px_h(self.hPx)
        self.x = max(-1.0, min(1.0 - w, x))
        self.y = max(-1.0 + h, min(1.0, y))
        self._move()

    def _move(self, force=False):
        if not window_alive(self.window) or not self._ready:
            return
        try:
            sw, sh = self._input.screen_size()
            vx = self.visual_x()
            px = int(round((vx + 1.0) * 0.5 * sw))
            py = int(round((1.0 - self.y) * 0.5 * sh))
            if not force and self._last_move == (px, py):
                return
            self.window.move(px, py)
            self._last_move = (px, py)
        except Exception:
            pass

    def update_visibility(self, hidden=False):
        behaviour = str(self._config.get('battleMenu', 'show')).lower()
        covered = bool(self._guard.is_covered(self.window)) if (self._guard and window_alive(self.window) and behaviour in ('dim', 'hide')) else False
        hidden = bool(hidden) or (behaviour == 'hide' and covered)
        dim = (not hidden) and behaviour == 'dim' and covered
        self._covered = hidden
        if dim != self._dim:
            self._dim = dim
            try:
                data = json.loads(self.payload)
                if isinstance(data, dict) and data.get('mode'):
                    data['dim'] = dim
                    self.payload = json.dumps(data, ensure_ascii=True)
                    self._publish()
            except Exception:
                pass
        self._sync_window_visibility()

    def destroy(self):
        self._destroyed = True
        self._token += 1
        try:
            self.close_settings()
        except Exception:
            self._logger.error('close settings')
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self.model = None
        self._ready = False
        self._win_ready = False
        self._shown = False
        self._bmin_offset_x = 0.0
        self._last_move = None
        self._covered = False
        self._visible = False
        self._dim = False
        self.payload = '{}'
