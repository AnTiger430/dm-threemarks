# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .defaults import DEFAULT_CONFIG


def _normalize_color_str(raw):
    value = str(raw or '').strip()
    if len(value) == 6:
        value = '#' + value
    if len(value) == 7 and value[0] == '#':
        try:
            int(value[1:], 16)
            return value.upper()
        except ValueError:
            pass
    return None


def _remap_bar_style(val, legacy):
    try:
        idx = int(round(float(val)))
    except (TypeError, ValueError):
        idx = 0
    if legacy:
        idx = {0: 0, 1: 1, 2: 0, 3: 2, 4: 3}.get(idx, idx)
    return max(0, min(3, idx))


class ConfigStore(object):
    """Encapsulated runtime configuration container replacing global g_config."""

    def __init__(self, initial=None, logger=None):
        self._data = dict(DEFAULT_CONFIG)
        self._logger = logger
        self.settings_open = False
        if isinstance(initial, dict):
            self.replace_normalized(initial)

    def raw_dict(self):
        return self._data

    def snapshot(self):
        return dict(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def update(self, mapping):
        if isinstance(mapping, dict):
            self._data.update(mapping)

    def replace_normalized(self, stored):
        cfg = self.normalize_loaded(stored)
        self._data = cfg
        return cfg

    @staticmethod
    def normalize_loaded(stored):
        cfg = dict(DEFAULT_CONFIG)
        legacy_bar = True
        if isinstance(stored, dict):
            for key in DEFAULT_CONFIG:
                if key in stored:
                    cfg[key] = stored[key]
            if 'battlePreset' not in stored:
                cfg['battlePreset'] = 1 if bool(cfg.get('battlePercentOnly', False)) else 0
            try:
                legacy_bar = int(stored.get('barStyleVersion', 1) or 1) < 2
            except (TypeError, ValueError):
                legacy_bar = True
            for bar_key in ('v3BarStyle', 'vhBarStyle'):
                if bar_key in stored:
                    cfg[bar_key] = _remap_bar_style(stored[bar_key], legacy_bar)
        try:
            raw_preset = int(round(float(cfg.get('battlePreset', 0))))
            preset = 1 if raw_preset == 1 else 0
        except (TypeError, ValueError):
            preset = 0
        cfg['v3BarStyle'] = _remap_bar_style(cfg.get('v3BarStyle', 0), False)
        cfg['vhBarStyle'] = _remap_bar_style(cfg.get('vhBarStyle', 0), False)
        cfg['barStyleVersion'] = 2
        cfg['battlePreset'] = preset
        cfg['battlePercentOnly'] = (preset == 1)
        cfg['hangarOnlyRandom'] = True
        cfg['hideUnderWindows'] = False
        return cfg

    def color(self, key, cfg=None):
        src = self._data if cfg is None else cfg
        raw = src.get(key, DEFAULT_CONFIG.get(key, '#FFFFFF'))
        parsed = _normalize_color_str(raw)
        if parsed is not None:
            return parsed
        if cfg is None and self._logger is not None:
            self._logger.once(
                ('badcolor', key, str(raw or '').strip()),
                'config: "%s" is not a #RRGGBB colour (%r), using the default' % (key, raw),
            )
        return str(DEFAULT_CONFIG.get(key, '#FFFFFF')).upper()

    def number(self, key, low, high, cfg=None):
        src = self._data if cfg is None else cfg
        try:
            value = float(src.get(key, DEFAULT_CONFIG.get(key, low)))
        except (TypeError, ValueError):
            if cfg is None and self._logger is not None:
                self._logger.once(('badnum', key), 'config: "%s" is not a number, using the default' % key)
            value = float(DEFAULT_CONFIG.get(key, low))
        return max(low, min(high, value))

    def integer(self, key, low, high, cfg=None):
        src = self._data if cfg is None else cfg
        try:
            raw = src.get(key, DEFAULT_CONFIG.get(key, low))
            if isinstance(raw, bool):
                value = int(raw)
            else:
                value = int(round(float(raw)))
        except (TypeError, ValueError):
            value = int(DEFAULT_CONFIG.get(key, low))
        return max(low, min(high, value))

    def string(self, key, default=u'', max_len=24, cfg=None):
        src = self._data if cfg is None else cfg
        raw = src.get(key, DEFAULT_CONFIG.get(key, default))
        try:
            if raw is None:
                txt = default
            elif isinstance(raw, unicode):
                txt = raw
            elif isinstance(raw, str):
                txt = raw.decode('utf-8', 'replace')
            else:
                txt = unicode(raw)
            txt = txt.strip()
            if max_len > 0 and len(txt) > max_len:
                txt = txt[:max_len]
            return txt
        except Exception:
            return default

    def ui_scale(self):
        return self.number('uiScale', 0.5, 2.5)

    def vh_scale(self):
        return self.number('vhScale', 0.5, 2.5)

    def to_v3_from_hangar(self, cfg=None):
        src = self._data if cfg is None else cfg
        return {
            'panelOpacity': src.get('panelOpacity', 1.0),
            'v3Font': src.get('vhFont', 2),
            'v3Density': src.get('vhDensity', 0),
            'v3MinWidth': 0,
            'v3Anchor': 1,
            'v3FrameStyle': src.get('vhFrameStyle', 2),
            'v3Radius': src.get('vhRadius', 5),
            'v3CornerColor': src.get('vhCornerColor', '#FFFFFF'),
            'v3CornerAlpha': src.get('vhCornerAlpha', 0.0),
            'v3BorderAlpha': src.get('vhBorderAlpha', 0.20),
            'v3BgColor': src.get('vhBgColor', '#131313'),
            'v3BgOpacity': src.get('vhBgOpacity', 0.60),
            'v3StarsPos': src.get('vhStarsPos', 0),
            'v3StarsStyle': src.get('vhStarsStyle', 0),
            'v3StarsDivider': src.get('vhStarsDivider', False),
            'v3StarsSize': src.get('vhStarsSize', 22),
            'v3StarsGap': src.get('vhStarsGap', 7),
            'v3StarsGlow': src.get('vhStarsGlow', True),
            'v3StarOnColor': src.get('vhStarOnColor', '#FFFFFF'),
            'v3StarOffColor': src.get('vhStarOffColor', '#9AA3AE'),
            'v3HeaderOrder': 0,
            'v3PctDecimals': src.get('vhPctDecimals', 1),
            'v3DeltaIcon': 3,
            'v3DeltaColorMode': 0,
            'v3BarStyle': src.get('vhBarStyle', 0),
            'v3BarScale': src.get('vhBarScale', 0),
            'v3BarHeight': src.get('vhBarHeight', 4),
            'v3BarTrackHeight': src.get('vhBarTrackHeight', 2),
            'v3BarCustomText': src.get('vhBarCustomText', u'KIBERSPORT'),
            'v3BarTextSize': src.get('vhBarTextSize', 15),
            'v3BarEndTicks': src.get('vhBarEndTicks', True),
            'v3BarCursor': src.get('vhBarCursor', True),
            'v3BarMarks': src.get('vhBarMarks', True),
            'v3BarColorMode': 2,
            'v3BarCustomColor': src.get('vhBarColor', '#A7D080'),
            'v3ShowDamage': src.get('vhShowEma', True),
            'v3DamageLabel': 0,
            'v3DamageCustomLabel': u'Суммарный урон',
            'v3ThousandsSep': src.get('vhThousandsSep', 2),
            'v3DamageDynColor': True,
            'v3AssistShow': 3,
            'v3AssistMode': 0,
            'v3AssistPlace': 0,
            'v3AssistHideZero': False,
            'v3AssistSize': 0,
            'v3TempoShow': 3,
            'v3TempoMode': 0,
            'v3TempoPlace': 0,
            'v3TempoSize': 0,
            'v3AccentPlus': src.get('v3AccentPlus', '#A7D080'),
            'v3AccentMinus': '#E57373',
            'v3AccentZero': '#9AA3AE',
            'v3AccentBig': '#B07CFF',
            'v3TextMain': src.get('vhTextMain', '#FFFFFF'),
            'v3TextMuted': src.get('vhTextMuted', '#B8BDC4'),
            'vhShowThresholds': src.get('vhShowThresholds', True),
            'vhShow100': True,
        }
