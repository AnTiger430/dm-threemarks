# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.config.defaults import DEFAULT_CONFIG
from ...domain.value_objects.color import hex_of_rgb
from ..v3.samples import PREVIEW_ORDER

MENU_LINKAGE = 'dm.threemarks'

MENU_NUM = (
    ('uiScale', 0.5, 2.5),
    ('panelOpacity', 0.0, 1.0),
    ('zeroBand', 0.0, 1.0),
    ('bigFrom', 0.0, 10.0),
    ('bigDamageFactor', 1.0, 10.0),
)
MENU_BOOL = ('dmgFollowsSign', 'bigByDamage', 'hideInIntro', 'hideInKillcam', 'hideAfterDeath')
MENU_COLORS = ('colorPlus', 'colorMinus', 'colorZero', 'colorBig', 'pctColor', 'colorDmg', 'colorProj')

MENU_V3_INT = (
    ('v3Font', 0, 7), ('v3Density', 0, 2), ('v3MinWidth', 0, 200), ('v3Anchor', 0, 5),
    ('v3FrameStyle', 0, 3), ('v3Radius', 0, 14), ('v3StarsPos', 0, 5),
    ('v3StarsStyle', 0, 2), ('v3StarsSize', 10, 22), ('v3StarsGap', 2, 14),
    ('v3HeaderOrder', 0, 2), ('v3PctDecimals', 0, 1), ('v3DeltaIcon', 0, 3),
    ('v3DeltaColorMode', 0, 1), ('v3BarStyle', 0, 3), ('v3BarScale', 0, 1),
    ('v3BarHeight', 2, 10), ('v3BarTrackHeight', 1, 10), ('v3BarTextSize', 10, 26),
    ('v3BarColorMode', 0, 2), ('v3DamageLabel', 0, 3), ('v3ThousandsSep', 0, 2),
    ('v3AssistShow', 0, 3), ('v3AssistMode', 0, 1), ('v3AssistPlace', 0, 1), ('v3AssistSize', 0, 24),
    ('v3TempoShow', 0, 3), ('v3TempoMode', 0, 2), ('v3TempoPlace', 0, 1), ('v3TempoSize', 0, 24),
)
MENU_V3_FLOAT = (('v3CornerAlpha', 0.0, 1.0), ('v3BorderAlpha', 0.0, 1.0), ('v3BgOpacity', 0.0, 1.0))
MENU_V3_BOOL = (
    'v3StarsDivider', 'v3StarsGlow',
    'v3BarEndTicks', 'v3BarCursor', 'v3BarMarks',
    'v3ShowDamage', 'v3DamageDynColor', 'v3AssistHideZero',
)
MENU_V3_STR = ('v3DamageCustomLabel', 'v3BarCustomText', 'vhBarCustomText')
MENU_V3_COLORS = (
    'v3CornerColor', 'v3BgColor', 'v3StarOnColor', 'v3StarOffColor',
    'v3BarCustomColor', 'v3AccentPlus', 'v3AccentMinus', 'v3AccentZero',
    'v3AccentBig', 'v3TextMain', 'v3TextMuted',
)

MENU_VH_INT = (
    ('vhFont', 0, 7), ('vhDensity', 0, 2), ('vhFrameStyle', 0, 3), ('vhRadius', 0, 14),
    ('vhStarsPos', 0, 5), ('vhStarsStyle', 0, 2), ('vhStarsSize', 10, 22),
    ('vhStarsGap', 2, 14), ('vhPctDecimals', 0, 1), ('vhBarStyle', 0, 3),
    ('vhBarScale', 0, 1), ('vhBarHeight', 2, 10), ('vhBarTrackHeight', 1, 10),
    ('vhBarTextSize', 10, 26), ('vhThousandsSep', 0, 2),
)
MENU_VH_FLOAT = (
    ('vhScale', 0.5, 2.5), ('vhCornerAlpha', 0.0, 1.0),
    ('vhBorderAlpha', 0.0, 1.0), ('vhBgOpacity', 0.0, 1.0),
)
MENU_VH_BOOL = (
    'hangarPanel', 'vhStarsDivider', 'vhStarsGlow',
    'vhBarEndTicks', 'vhBarCursor', 'vhBarMarks',
    'vhShowEma', 'vhShowThresholds',
)
MENU_VH_COLORS = (
    'vhBarColor', 'vhTextMain', 'vhTextMuted',
    'vhCornerColor', 'vhBgColor', 'vhStarOnColor', 'vhStarOffColor',
)

MENU_CONFIG_KEYS = (
    MENU_BOOL + MENU_V3_BOOL + MENU_VH_BOOL + MENU_V3_STR +
    MENU_COLORS + MENU_V3_COLORS + MENU_VH_COLORS +
    tuple(n for n, _l, _h in (MENU_NUM + MENU_V3_INT + MENU_V3_FLOAT + MENU_VH_INT + MENU_VH_FLOAT))
)

MENU_ALL_KEYS = (
    ('battleSection', 'hangarSection', 'previewTarget', 'previewState', 'previewStateHangar', 'previewAlt', 'battlePanelVariant') +
    MENU_CONFIG_KEYS
)


class MenuValueConverter(object):
    """Translates between ConfigStore values and Aslain ModsSettingsAPI control types."""

    def __init__(self, config_store):
        self._config = config_store

    @staticmethod
    def color_value(raw):
        try:
            if isinstance(raw, basestring):
                text = raw.strip().lstrip('#')
                if len(text) >= 6:
                    int(text[:6], 16)
                    return '#' + text[:6].upper()
            elif isinstance(raw, bool):
                return None
            elif isinstance(raw, (int, long)):
                return '#%06X' % (raw & 0xFFFFFF)
            elif isinstance(raw, (list, tuple)) and len(raw) >= 3:
                return hex_of_rgb([float(v) for v in raw[:3]])
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def convert(key, raw):
        if key in MENU_BOOL or key in MENU_V3_BOOL or key in MENU_VH_BOOL:
            return bool(raw)
        if key in MENU_V3_STR:
            if isinstance(raw, basestring):
                text = raw.decode('utf-8', 'replace') if isinstance(raw, str) else raw
                return text.replace(u'\r', u' ').replace(u'\n', u' ')[:24]
            return None
        if key in MENU_COLORS or key in MENU_V3_COLORS or key in MENU_VH_COLORS:
            return MenuValueConverter.color_value(raw)
        for name, low, high in MENU_V3_INT + MENU_VH_INT:
            if name == key:
                try:
                    return int(round(max(low, min(high, float(raw)))))
                except (TypeError, ValueError):
                    return None
        for name, low, high in MENU_NUM + MENU_V3_FLOAT + MENU_VH_FLOAT:
            if name == key:
                try:
                    return round(max(low, min(high, float(raw))), 4)
                except (TypeError, ValueError):
                    return None
        return None

    def current_values(self, preview_state=None):
        c = self._config
        values = {}
        for name, low, high in MENU_NUM + MENU_V3_FLOAT + MENU_VH_FLOAT:
            values[name] = round(c.number(name, low, high), 4)
        for name, low, high in MENU_V3_INT + MENU_VH_INT:
            values[name] = c.integer(name, low, high)
        for name in MENU_BOOL + MENU_V3_BOOL + MENU_VH_BOOL:
            values[name] = bool(c.get(name, DEFAULT_CONFIG.get(name)))
        for name in MENU_V3_STR:
            values[name] = c.string(name, DEFAULT_CONFIG.get(name, u''), 24)
        for name in MENU_COLORS + MENU_V3_COLORS + MENU_VH_COLORS:
            values[name] = c.color(name)
        values['battlePanelVariant'] = c.integer('battlePreset', 0, 1)
        ps = preview_state or {}
        state = ps.get('state', 'plus')
        values['battleSection'] = int(ps.get('battleSection', 0) or 0)
        values['hangarSection'] = int(ps.get('hangarSection', 0) or 0)
        p_idx = PREVIEW_ORDER.index(state) if state in PREVIEW_ORDER else 0
        values['previewState'] = p_idx
        values['previewStateHangar'] = p_idx
        values['previewAlt'] = 1 if ps.get('alt', False) else 0
        values['previewTarget'] = 1 if int(ps.get('target', 0) or 0) == 1 else 0
        return values

    @staticmethod
    def default_values():
        values = {}
        for name, _l, _h in MENU_NUM + MENU_V3_FLOAT + MENU_VH_FLOAT:
            values[name] = float(DEFAULT_CONFIG[name])
        for name, _l, _h in MENU_V3_INT + MENU_VH_INT:
            values[name] = int(DEFAULT_CONFIG[name])
        for name in MENU_BOOL + MENU_V3_BOOL + MENU_VH_BOOL:
            values[name] = bool(DEFAULT_CONFIG[name])
        for name in MENU_V3_STR:
            values[name] = unicode(DEFAULT_CONFIG[name])
        for name in MENU_COLORS + MENU_V3_COLORS + MENU_VH_COLORS:
            values[name] = str(DEFAULT_CONFIG[name]).upper()
        values['battlePanelVariant'] = int(DEFAULT_CONFIG.get('battlePreset', 0))
        values['battleSection'] = 0
        values['hangarSection'] = 0
        values['previewState'] = 0
        values['previewStateHangar'] = 0
        values['previewAlt'] = 0
        values['previewTarget'] = 0
        return values

    @staticmethod
    def preview_state_for(key):
        low = str(key).lower()
        for word, state in (('minus', 'minus'), ('zero', 'zero'), ('big', 'big'), ('plus', 'plus')):
            if word in low:
                return state
        return None
