# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.config.defaults import DEFAULT_CONFIG, V3_DEFAULTS, VH_DEFAULTS
from ...application.ports.settings_menu import ISettingsMenu
from ..v3.samples import PREVIEW_ORDER
from .schema import MENU_ALL_KEYS, MENU_CONFIG_KEYS, MENU_LINKAGE, MENU_V3_STR, MenuValueConverter


def _menu_import():
    try:
        from gui.aslainMenu import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except Exception:
        pass
    try:
        from gui.modsSettingsApi import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except Exception:
        return None, None


def _menu_args(args):
    linkage = settings = None
    for arg in args:
        if isinstance(arg, basestring) and linkage is None:
            linkage = arg
        elif isinstance(arg, dict) and settings is None:
            settings = arg
    return linkage, settings


class AslainMenuAdapter(ISettingsMenu):
    """Adapter implementing ISettingsMenu over Aslain Mod Menu / ModsSettingsAPI."""

    PREVIEW_MIN_INTERVAL = 0.09

    def __init__(self, config_store, config_sync, preview_renderer, template_builder, logger, clock=None, scheduler=None):
        self._config = config_store
        self._config_sync = config_sync
        self._preview = preview_renderer
        self._builder = template_builder
        self._logger = logger
        self._clock = clock
        self._scheduler = scheduler
        self._last_preview_t = -1.0
        self._preview_cb = None
        self._api = None
        self._tpl = None
        self._ver = (1, 0, 0)
        self._ok = False
        self._tries = 0
        self._template = None
        self._full_template = None
        self._tpl_v3 = True
        self._committed = None
        self._dirty_live = False
        self._need_tpl_resync = False
        self._on_refresh = None
        self._get_battle_panel = None
        self._get_hangar_panel = None

    def bind_runtime(self, on_refresh=None, get_battle_panel=None, get_hangar_panel=None):
        self._on_refresh = on_refresh
        self._get_battle_panel = get_battle_panel
        self._get_hangar_panel = get_hangar_panel

    def is_registered(self):
        return self._ok

    def set_hardware_alt(self, active):
        self._preview.state['hwAlt'] = bool(active)

    def swap_settings_page(self, panel):
        try:
            if panel is not None and panel.settings_controller is not None:
                panel.close_settings()
                panel.settings_controller_clear()
                self._notify_refresh()
        except Exception:
            self._logger.error('menu swap')

    def _register_hooks(self, api):
        defaults = MenuValueConverter.default_values()
        for fn_name, args in (('setModDefaults', (MENU_LINKAGE, defaults)), ('setModTemplateDefault', (MENU_LINKAGE, defaults, self._on_applied))):
            if hasattr(api, fn_name):
                try:
                    getattr(api, fn_name)(*args)
                except Exception:
                    self._logger.error('menu defaults')
                break
        try:
            if hasattr(api, 'registerLiveSettingsChange'):
                api.registerLiveSettingsChange(MENU_LINKAGE, self._on_live, True)
            else:
                live = getattr(api, 'onSettingsChanged', None) or getattr(api, 'onModSettingsChanged', None)
                if live is not None:
                    live += self._on_live
        except Exception:
            self._logger.error('menu live register')
        try:
            api.onWindowClosed += self._on_closed
        except Exception:
            self._logger.error('menu closed register')
        try:
            api.onWindowOpened += self._on_opened
        except Exception:
            self._logger.once('noopened', 'Mod Menu has no onWindowOpened: the preview starts with the first change')

    def register(self):
        if self._ok:
            return True
        api, tpl = _menu_import()
        if api is None or tpl is None:
            self._tries += 1
            if self._tries == 1:
                self._logger.info('Mod Menu not found, using the panel settings page')
            return False
        try:
            ver = tuple(api.getVersionTuple())
        except Exception:
            ver = tuple(getattr(api, 'version', None) or (1, 0, 0))
        self._ver, self._api, self._tpl = ver, api, tpl
        try:
            template = self._builder.build(tpl, ver, show_v3=True)
            try:
                saved = api.setModTemplate(MENU_LINKAGE, template, self._on_applied, self._on_button)
            except TypeError:
                saved = api.setModTemplate(MENU_LINKAGE, template, self._on_applied)
                try:
                    ev_btn = getattr(api, 'onButtonClicked', None)
                    if ev_btn is not None:
                        ev_btn += self._on_button
                except Exception:
                    self._logger.error('menu button register')
            self._template = self._full_template = template
            self._tpl_v3 = self._ok = True
            self._register_hooks(api)
            self._logger.info('registered in Mod Menu %s (%s)' % ('.'.join(str(x) for x in ver), type(api).__module__))
            self._apply_settings(saved, True)
            self._snapshot_committed()
            self.sync_tabs()
            self._clear_preview_keys()
            self.refresh_preview()
            if self._get_hangar_panel is not None:
                self.swap_settings_page(self._get_hangar_panel())
            return True
        except Exception:
            self._logger.error('menu register')
            self._ok = False
            return False

    def unregister(self):
        self._cancel_preview_timer()
        api = self._api
        if not self._ok or api is None:
            return
        self._ok = False
        self._safe(getattr(api, 'unregisterLiveSettingsChange', None), MENU_LINKAGE, self._on_live)
        for attr, handler in (('onSettingsChanged', self._on_live), ('onModSettingsChanged', self._on_live), ('onButtonClicked', self._on_button), ('onWindowClosed', self._on_closed), ('onWindowOpened', self._on_opened)):
            ev = getattr(api, attr, None)
            if ev is not None:
                self._safe(ev.__isub__, handler)

    def push_values(self):
        if not self._ok or self._api is None:
            return
        try:
            self._snapshot_committed()
            self._api.updateModSettings(MENU_LINKAGE, MenuValueConverter(self._config).current_values(self._preview.state))
        except Exception:
            self._logger.error('menu push')

    def _snapshot_committed(self):
        self._committed = self._config.snapshot()
        self._dirty_live = False

    def _revert_unsaved(self):
        if not self._committed:
            self._dirty_live = False
            return
        before = self._config.snapshot()
        cfg = self._config.replace_normalized(self._committed)
        for key in ('x', 'y', 'hx', 'hy'):
            cfg[key] = before.get(key, cfg.get(key))
        self._dirty_live = False

    def _cancel_preview_timer(self):
        if self._preview_cb is not None and self._scheduler is not None:
            self._safe(self._scheduler.cancel, self._preview_cb)
        self._preview_cb = None

    def _flush_preview(self):
        self._cancel_preview_timer()
        self.refresh_preview()
        if self._clock is not None:
            self._last_preview_t = self._clock.now()

    def _schedule_preview(self, immediate=False):
        if immediate or self._clock is None or self._scheduler is None:
            self._flush_preview()
            return
        now = self._clock.now()
        elapsed = now - self._last_preview_t
        if self._last_preview_t < 0.0 or elapsed >= self.PREVIEW_MIN_INTERVAL:
            self._flush_preview()
        elif self._preview_cb is None:
            wait = max(0.02, self.PREVIEW_MIN_INTERVAL - elapsed)
            self._preview_cb = self._scheduler.schedule(wait, self._flush_preview)

    def _clear_preview_keys(self):
        ps = self._preview.state
        ps['source'] = ps['key'] = ps['keyBattle'] = ps['keyHangar'] = None

    def _iter_comps(self, template):
        for col_key in ('column1', 'column2', 'column3', 'column4'):
            for comp in (template.get(col_key, ()) or ()):
                yield comp
                for sub in (comp.get('items') or ()):
                    yield sub

    def refresh_preview(self):
        api, template = self._api, self._template
        if api is None or template is None:
            return
        try:
            ps = self._preview.state
            has_split = any(c.get('varName') == 'marksLivePreviewHangar' for c in self._iter_comps(template))
            targets = (('marksLivePreview', 'keyBattle', 0), ('marksLivePreviewHangar', 'keyHangar', 1)) if has_split else (('marksLivePreview', 'key', None),)
            upd_img = getattr(api, 'updateImage', None)
            need_reload = False
            for var_name, key_name, tgt in targets:
                source, _bw, _bh, width, height = self._preview.render(target=tgt)
                key = (source, width, height)
                if key == ps.get(key_name):
                    continue
                found = False
                for comp in self._iter_comps(template):
                    if comp.get('varName') == var_name:
                        comp['source'], comp['width'], comp['height'] = source, width, height
                        found = True
                if not found:
                    continue
                ps[key_name] = key
                if tgt in (None, int(ps.get('target', 0) or 0)):
                    ps['source'], ps['key'] = source, key
                if upd_img is not None:
                    try:
                        upd_img(MENU_LINKAGE, var_name, source, width, height)
                        continue
                    except Exception:
                        pass
                need_reload = True
            if need_reload:
                api.setModTemplate(MENU_LINKAGE, template, self._on_applied)
        except Exception:
            self._logger.error('menu preview refresh')

    def sync_tabs(self, force=False):
        if self._api is None or self._tpl is None:
            return False
        reload_fn = getattr(self._api, 'reloadModTemplate', None)
        want_v3 = (self._config.integer('battlePreset', 0, 1) == 0)
        if not force and self._tpl_v3 == want_v3:
            return False
        if reload_fn is None:
            return False
        try:
            cur_bsec = int(self._preview.state.get('battleSection', 0) or 0)
            if self._tpl_v3 != want_v3:
                mapped_bsec = (4 if cur_bsec == 1 else 0) if want_v3 else (1 if cur_bsec == 4 else 0)
                self._preview.state['battleSection'] = mapped_bsec
            else:
                mapped_bsec = cur_bsec
            new_tpl = self._builder.build(self._tpl, self._ver, show_v3=want_v3)
            self._template = new_tpl
            self._tpl_v3 = want_v3
            self._preview.state['syncing'] = True
            try:
                reload_fn(MENU_LINKAGE, new_tpl)
                set_val = getattr(self._api, 'setControlValue', None)
                if set_val is not None:
                    self._safe(set_val, MENU_LINKAGE, 'battleSection', mapped_bsec)
            finally:
                self._preview.state['syncing'] = False
            self._clear_preview_keys()
            return True
        except Exception:
            self._logger.error('menu sync tabs')
            return False

    def _notify_refresh(self):
        if self._on_refresh is not None:
            self._on_refresh()

    def _set_ctl(self, key, value):
        fn = getattr(self._api, 'setControlValue', None) if self._api is not None else None
        if fn is None or self._preview.state.get('syncing'):
            return False
        self._preview.state['syncing'] = True
        try:
            return fn(MENU_LINKAGE, key, value)
        except Exception:
            return False
        finally:
            self._preview.state['syncing'] = False

    def _apply_settings(self, settings, save):
        if not isinstance(settings, dict):
            return False
        changed = False
        ps = self._preview.state
        target_explicit = self._preview.apply_ui_controls(settings)
        if not save and ps.get('stateChangedBy'):
            twin = 'previewStateHangar' if ps['stateChangedBy'] == 'previewState' else 'previewState'
            self._set_ctl(twin, ps['uiState'])
        if 'battlePanelVariant' in settings:
            try:
                raw_var = int(settings['battlePanelVariant'])
                preset = 1 if raw_var == 1 else 0
            except (TypeError, ValueError):
                preset, raw_var = None, None
            if preset is not None:
                if self._config.get('battlePreset') != preset:
                    self._config.set('battlePreset', preset)
                    changed = True
                only_pct = (preset == 1)
                if self._config.get('battlePercentOnly') != only_pct:
                    self._config.set('battlePercentOnly', only_pct)
                    changed = True
                if raw_var == 2:
                    self._set_ctl('battlePanelVariant', 0)

        vh_touch = b_touch = False
        ps['textChanged'] = False
        for key in MENU_CONFIG_KEYS:
            if key not in settings:
                continue
            value = MenuValueConverter.convert(key, settings[key])
            if value is None:
                self._logger.once(('menubad', key), 'Mod Menu sent an unreadable value for "%s": %r' % (key, settings[key]))
                continue
            if self._config.get(key) != value:
                self._config.set(key, value)
                changed = True
                if key in MENU_V3_STR:
                    ps['textChanged'] = True
                if key.startswith('vh') or key in ('hangarPanel', 'hangarOnlyRandom', 'hideUnderWindows'):
                    vh_touch = True
                elif key.startswith('v3') or key.startswith('color') or key in ('uiScale', 'dmgFollowsSign', 'pctColor'):
                    b_touch = True
                st = MenuValueConverter.preview_state_for(key)
                if st:
                    ps['state'] = st
                    new_idx = PREVIEW_ORDER.index(st)
                    ps['uiState'] = new_idx
                    if not save:
                        self._set_ctl('previewState', new_idx)
                        self._set_ctl('previewStateHangar', new_idx)
        if not save and not target_explicit:
            h_act = bool(vh_touch or ps.get('hangarSectionChanged'))
            b_act = bool(b_touch or ps.get('battleSectionChanged'))
            want_target = 1 if (h_act and not b_act) else (0 if (b_act and not h_act) else None)
            if want_target is not None and ps.get('target') != want_target:
                ps['target'] = want_target
                self._set_ctl('previewTarget', want_target)
        if changed:
            if save:
                self._config_sync.save_current()
            self._notify_refresh()
        return changed

    def _safe(self, fn, *args, **kwargs):
        if fn is None:
            return
        try:
            fn(*args, **kwargs)
        except Exception:
            pass

    def _reset_preset(self, defaults_dict):
        self._config.update(defaults_dict)
        self._config_sync.save_current()
        self._snapshot_committed()
        if self._api is not None:
            vals = MenuValueConverter(self._config).current_values(self._preview.state)
            self._preview.state['syncing'] = True
            try:
                self._safe(getattr(self._api, 'updateModSettings', None), MENU_LINKAGE, vals)
                set_val = getattr(self._api, 'setControlValue', None)
                if set_val is not None:
                    for key in defaults_dict:
                        if key in vals:
                            self._safe(set_val, MENU_LINKAGE, key, vals[key])
            finally:
                self._preview.state['syncing'] = False
        self._cancel_preview_timer()
        self._notify_refresh()
        self._clear_preview_keys()
        self.refresh_preview()

    def _reset_position(self, key_x, key_y, get_panel):
        self._config.set(key_x, DEFAULT_CONFIG[key_x])
        self._config.set(key_y, DEFAULT_CONFIG[key_y])
        self._config_sync.save_current()
        self._snapshot_committed()
        panel = get_panel() if get_panel is not None else None
        if panel is not None:
            self._safe(panel.move_to, self._config.get(key_x), self._config.get(key_y))
        self._notify_refresh()

    def _on_button(self, *args, **kwargs):
        try:
            strs = [a for a in args if isinstance(a, basestring)]
            linkage = kwargs.get('linkage') or (strs[0] if strs else None)
            if linkage != MENU_LINKAGE:
                return
            var_name = kwargs.get('varName') or (strs[1] if len(strs) >= 2 else None)
            btn_name = kwargs.get('buttonName') or kwargs.get('button') or kwargs.get('name') or (strs[2] if len(strs) >= 3 else None)
            action = btn_name or var_name
            if action in ('v3ResetPreset', 'resetPreset'):
                self._reset_preset(dict(V3_DEFAULTS, uiScale=DEFAULT_CONFIG['uiScale']))
            elif action == 'vhResetPreset':
                self._reset_preset(VH_DEFAULTS)
            elif action in ('resetPosition', 'v3ResetPosition'):
                self._reset_position('x', 'y', self._get_battle_panel)
            elif action == 'resetHangarPosition':
                self._reset_position('hx', 'hy', self._get_hangar_panel)
        except Exception:
            self._logger.error('menu button')

    def _on_applied(self, *args):
        try:
            linkage, settings = _menu_args(args)
            if linkage == MENU_LINKAGE:
                self._cancel_preview_timer()
                self._apply_settings(settings, True)
                self._snapshot_committed()
                self._need_tpl_resync = False
                self.sync_tabs()
                self._clear_preview_keys()
                self.refresh_preview()
        except Exception:
            self._logger.error('menu apply')

    def _on_opened(self, *args):
        try:
            self._cancel_preview_timer()
            if self._dirty_live:
                self._revert_unsaved()
                self._need_tpl_resync = True
            self.sync_tabs(force=self._need_tpl_resync)
            self._need_tpl_resync = False
            self._clear_preview_keys()
            self.refresh_preview()
        except Exception:
            self._logger.error('menu opened')

    def _on_live(self, *args):
        try:
            if self._preview.state.get('syncing'):
                return
            linkage, settings = _menu_args(args)
            if linkage == MENU_LINKAGE or (isinstance(settings, dict) and any(k in settings for k in MENU_ALL_KEYS)):
                self._dirty_live = True
                changed = self._apply_settings(settings, False)
                swapped = self.sync_tabs()
                if swapped and not changed:
                    self._notify_refresh()
                self._schedule_preview(immediate=bool(swapped or self._preview.state.get('textChanged')))
        except Exception:
            self._logger.error('menu live')

    def _on_closed(self, *args):
        try:
            self._cancel_preview_timer()
            ps = self._preview.state
            ps['state'], ps['uiState'], ps['battleSection'], ps['hangarSection'] = 'plus', 0, 0, 0
            self._clear_preview_keys()
            if self._dirty_live:
                self._revert_unsaved()
            src_tpl = self._full_template or self._template
            if self._api is not None and src_tpl is not None:
                saved = self._api.getModSettings(MENU_LINKAGE, src_tpl)
                if isinstance(saved, dict) and saved:
                    self._apply_settings(saved, False)
            if self.sync_tabs():
                self._need_tpl_resync = True
            self._notify_refresh()
            self.refresh_preview()
        except Exception:
            self._logger.error('menu closed')
