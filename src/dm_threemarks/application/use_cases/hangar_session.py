# -*- coding: utf-8 -*-
from __future__ import absolute_import


_HIDE_VIEW_KEYWORDS = (
    'techtree', 'research', 'vehiclehub', 'upgrade',
    'moduleset', 'blueprint', 'shop', 'barracks',
    'profile', 'exchange', 'personalmissions',
)
_SETUP_VIEW_KEYWORDS = ('tank_setup', 'tanksetup', 'ammunition_setup', 'ammunitionsetup')
_SETUP_VIEW_EXCLUDES = ('ammunition_panel', 'ammunitionpanel', 'hangar_view', 'tooltip')
_POPUP_VIEW_EXCLUDES = ('window', 'popover', 'dialog', 'tooltip')


def _is_setup_view(name):
    """Return True for fullscreen tank/ammunition setup screens, ignoring persistent hangar widgets."""
    low = str(name or '').lower()
    if not low:
        return False
    if any(ex in low for ex in _SETUP_VIEW_EXCLUDES):
        return False
    return any(k in low for k in _SETUP_VIEW_KEYWORDS)


class HangarSessionService(object):
    """Application use case managing hangar overlay lifecycle, visibility, and vehicle refresh."""

    TICK = 0.05
    DRAG_TICK = 0.0

    def __init__(self, config_store, config_sync, dossier_provider, curve_sync,
                 snapshot_uc, forecast_engine, threshold_calc, clock, scheduler,
                 input_provider, hangar_env, menu_port, logger,
                 hangar_presenter, panel_factory, drag_controller=None):
        self._config = config_store
        self._config_sync = config_sync
        self._dossier = dossier_provider
        self._curves = curve_sync
        self._snapshot_uc = snapshot_uc
        self._forecast = forecast_engine
        self._threshold_calc = threshold_calc
        self._clock = clock
        self._scheduler = scheduler
        self._input = input_provider
        self._env = hangar_env
        self._menu = menu_port
        self._logger = logger
        self._presenter = hangar_presenter
        self._panel_factory = panel_factory
        self._drag = drag_controller

        self._panel = None
        self._cb_id = None
        self._watch_id = None
        self._in_lobby = False
        self._blocked = False
        self._setup_open = False
        self._need_refresh = False
        self._last_payload = None
        self._last_int_cd = None
        self._last_update_t = 0.0
        self._state_id = None
        self._mode_desc = None
        self._view_names = set()
        self._view_log_lines = 0
        self._hw_alt = False

    @property
    def panel(self):
        return self._panel

    def on_lobby(self):
        self._in_lobby = True
        self._blocked = False
        self._reconcile_pending()
        self._scan_views()
        self._ensure()
        if self._watch_id is None:
            self._watch_tick()

    def on_leave_lobby(self):
        self._in_lobby = False
        if self._watch_id is not None:
            self._scheduler.cancel(self._watch_id)
            self._watch_id = None
        self._hide()

    def set_blocked(self, blocked):
        self._blocked = bool(blocked)
        if self._blocked:
            self._hide()
        else:
            self._ensure()

    def on_view_loaded(self, alias):
        text = str(alias or '').lower()
        if not text:
            return
        self._logger.once(('alias', text), 'lobby view alias: %s' % text)
        if any(ex in text for ex in _POPUP_VIEW_EXCLUDES):
            return
        if any(k in text for k in _HIDE_VIEW_KEYWORDS) or _is_setup_view(text):
            self._blocked = True
            self._hide()
        elif 'hangar' in text:
            self._blocked = False
            self._ensure()

    def refresh(self):
        self._last_payload = None
        if self._panel is not None:
            self._update()
        else:
            self._ensure()

    def _reconcile_pending(self):
        fn = getattr(self._snapshot_uc, 'reconcile_pending', None)
        if fn is not None:
            fn()

    def on_vehicle_changed(self, *args, **kwargs):
        info = self._dossier.get_current_vehicle_info()
        if info is not None:
            self._snapshot_uc.snapshot_vehicle(info[0])
        self._reconcile_pending()
        self.refresh()

    def _watch_tick(self):
        if not self._in_lobby:
            self._watch_id = None
            return
        try:
            if not self._menu.is_registered():
                self._menu.register()
            else:
                hw_alt = self._input.is_alt_down()
                if hw_alt != self._hw_alt:
                    self._hw_alt = hw_alt
                    self._menu.set_hardware_alt(hw_alt)
                    self._menu.refresh_preview()
            self._scan_views()
            if self._panel is None and not self._blocked:
                self._ensure()
        except Exception:
            self._logger.error('hangar watch')
        self._watch_id = self._scheduler.schedule(0.3, self._watch_tick)

    def _scan_views(self):
        reason = ''
        shown, state_id = self._env.hangar_state()
        if state_id != self._state_id:
            self._state_id = state_id
            self._logger.info('lobby state: %s (hangar=%s)' % (state_id, shown))
        if shown is False:
            reason = 'state %s' % state_id
        elif self._config.get('hideUnderWindows', False):
            own_win = getattr(self._panel, 'window', None)
            if self._env.is_covered(own_win):
                reason = 'big window'
        random, mode_desc = self._env.hangar_mode()
        if mode_desc != self._mode_desc:
            self._mode_desc = mode_desc
            self._logger.info('hangar mode: %s random=%s' % (mode_desc, random))
        if not reason and random is False and self._config.get('hangarOnlyRandom', True):
            reason = 'not a random battle'
        names = self._env.view_class_names()
        if names is not None:
            if names != self._view_names and self._view_log_lines < 400:
                added = sorted(names - self._view_names)
                removed = sorted(self._view_names - names)
                self._view_log_lines += 1
                self._logger.info('hangar views +%s -%s' % (added, removed))
            self._view_names = names
            if not reason and any(_is_setup_view(n) for n in names):
                reason = 'setup view'
        cover = bool(reason)
        if cover != self._setup_open:
            self._setup_open = cover
            self._logger.info('hangar panel %s (%s)' % ('hidden' if cover else 'shown', reason or 'ok'))
            if cover:
                self._hide()
            else:
                self._ensure()
        if shown is True and not cover and self._blocked:
            self._blocked = False
            self._logger.info('hangar unblocked (state %s)' % state_id)
            if self._panel is None:
                self._ensure()

    def _ensure(self):
        if not self._config.get('hangarPanel', True):
            return
        if not self._in_lobby or self._blocked or self._setup_open:
            return
        info = self._dossier.get_current_vehicle_info()
        if info is not None and info[1] < int(self._config.get('minVehicleLevel', 5)):
            return
        try:
            if self._panel is None:
                self._panel = self._panel_factory()
                if self._panel is None:
                    return
                self._last_payload = None
                self._update()
                if self._panel is None:
                    return
                self._panel.build()
                self._menu.swap_settings_page(self._panel)
            else:
                self._update()
            if self._cb_id is None:
                self._tick()
        except Exception:
            self._logger.error('hangar init')

    def _hide(self):
        if self._cb_id is not None:
            self._scheduler.cancel(self._cb_id)
            self._cb_id = None
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        if self._drag is not None:
            self._drag.reset()

    def _update(self):
        if self._panel is None:
            return
        if not self._config.get('hangarPanel', True):
            self._hide()
            return
        self._last_update_t = self._clock.now()
        try:
            if self._panel.is_settings_open():
                self._panel.push({})
                return
            info = self._dossier.get_current_vehicle_info()
            if info is None:
                return
            int_cd, level = info
            self._last_int_cd = int_cd
            if level < int(self._config.get('minVehicleLevel', 5)):
                self._hide()
                return
            mark = self._snapshot_uc.mark_for(int_cd)
            if mark is None:
                return
            self._curves.request_calc(int_cd)
            rating, ema, marks = mark.percent, mark.avg, mark.marks
            curve = self._curves.curve_for(int_cd)
            server_now = self._clock.server_now()
            if curve and rating > 0 and ema > 0:
                try:
                    self._snapshot_uc.witness_epoch(str(int_cd), mark.avg, mark.percent, mark.written)
                    rating = self._forecast.current_percent(mark, curve, server_now, self._curves.day_curve)[0]
                except Exception:
                    self._logger.error('hangar curve')
            if curve is None and self._curves.is_pending(int_cd):
                rating = 0.0
                ema = 0.0
            has_rating = bool(rating > 0 and ema > 0)
            thresholds = None
            if has_rating:
                thresholds = self._threshold_calc.compute_thresholds(
                    mark, rating, ema, curve, server_now,
                    self._curves.day_curve, self._curves.version,
                )
            payload = self._presenter.build_payload(rating, ema, marks, has_rating, thresholds)
            if getattr(self._panel, 'set_mini', None) is not None:
                self._panel.set_mini(False)
            if payload != self._last_payload:
                self._last_payload = payload
                self._panel.push(payload)
        except Exception:
            self._logger.error('hangar update')

    def _tick(self):
        if self._panel is None:
            self._cb_id = None
            return
        dragging = False
        try:
            self._need_refresh = False
            if self._drag is not None:
                drag_changed = self._drag.poll(self._panel, min_key='minHangar')
                if drag_changed:
                    self._need_refresh = True
                dragging = self._drag.is_dragging()
            if not dragging:
                info = self._dossier.get_current_vehicle_info()
                if info is not None and info[0] != self._last_int_cd:
                    self._last_int_cd = info[0]
                    self._snapshot_uc.snapshot_vehicle(info[0])
                    self._last_payload = None
                    self._need_refresh = True
                settings_ctrl = self._panel.settings_controller
                if settings_ctrl is not None and settings_ctrl.poll(self, self._panel):
                    self._need_refresh = True
                pumped = self._curves.pump()
                cfg_changed = self._config_sync.poll()
                due_periodic = (self._clock.now() - self._last_update_t >= 0.5)
                if pumped or cfg_changed or self._need_refresh:
                    self._last_payload = None
                    self._update()
                elif due_periodic:
                    self._reconcile_pending()
                    self._update()
        except Exception:
            self._logger.error('hangar tick')
        self._cb_id = self._scheduler.schedule(self.DRAG_TICK if dragging else self.TICK, self._tick)
