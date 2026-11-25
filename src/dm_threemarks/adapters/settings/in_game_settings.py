# -*- coding: utf-8 -*-
from __future__ import absolute_import

import colorsys

from ...application.config.defaults import DEFAULT_CONFIG
from ...domain.value_objects.color import clamp01, hex_of_rgb, mix_rgb, rgb_css, rgb_of_hex

SET_H = 500.0
_SET_LABEL_W = {
    'title': 69, 'plus': 36, 'minus': 42, 'zero': 34, 'hangar': 39, 'pct': 39,
    'size': 48, 'bg': 28, 'glow': 61, 'sign': 97, 'reset': 40, 'done': 45,
    'dmg': 91, 'big': 41, 'barsign': 113, 'std': 44, 'spot': 44, 'track': 61,
}
_GEAR = (114.0, 4.0, 134.0, 24.0)
_SWATCHES = (
    '#86EF6A', '#4FD8FF', '#3C8DFF', '#B07CFF', '#FF6FD8',
    '#FF6060', '#FF9A3C', '#FFD23C', '#C8FF3C', '#2FE0A0',
    '#FFFFFF', '#EAEAEA', '#CFCFCF', '#A8A8A8', '#808080',
    '#5A5A5A', '#FF3030', '#00D060', '#00A0FF', '#FFB000',
)
_APPEARANCE_KEYS = (
    'uiScale', 'bgOpacity', 'colorPlus', 'colorMinus',
    'colorZero', 'colorBig', 'barColorPlus', 'barColorMinus',
    'barColorZero', 'barColorBig', 'barColorHangar',
    'barBySign', 'barColorStandard', 'showSpot', 'showTrack', 'bigByDamage',
    'bigDamageFactor', 'bigBasePercent',
    'trackOpacity', 'tickColor', 'pctColor', 'pctFollowsSign',
    'glow', 'zeroBand', 'bigFrom', 'dmgFollowsSign',
    'colorDmg', 'colorProj', 'panelOpacity', 'battlePercentOnly',
)
_HUE_STRIP = 'linear-gradient(90deg,#FF0000,#FFFF00,#00FF00,#00FFFF,#0000FF,#FF00FF,#FF0000)'
_SHADE_STRIP = 'linear-gradient(180deg,#FFFFFF,rgba(255,255,255,0) 50%,rgba(0,0,0,0) 50%,#000000)'


class InGameSettingsController(object):
    """Interactive fallback color/slider configuration overlay rendered inside hangar panel."""

    TARGETS = (
        ('plus', ('colorPlus', 'barColorPlus')),
        ('minus', ('colorMinus', 'barColorMinus')),
        ('zero', ('colorZero', 'barColorZero')),
        ('big', ('colorBig', 'barColorBig')),
        ('hangar', ('barColorHangar',)),
        ('pct', ('pctColor',)),
        ('std', ('barColorStandard',)),
    )
    PICKER = (10.0, 188.0, 200.0, 56.0)
    TRACK = {'size': (72.0, 288.0), 'bg': (72.0, 310.0), 'alpha': (72.0, 332.0)}
    TRACK_W = 100.0
    HOLD_STEP = 0.05

    def __init__(self, config_store, config_sync, input_provider, clock):
        self._config = config_store
        self._config_sync = config_sync
        self._input = input_provider
        self._clock = clock
        self.open = False
        self.target = 0
        self.pick = None
        self.active = None
        self.pressed = False
        self.gearPress = False
        self.changed = False
        self.wantClose = False
        self.dirty = False
        self.items = []
        self._hits = []
        self._held = None
        self._t = 0.0
        self.build()

    def build(self):
        items, hits = [], []

        def box(x, y, w, h, bg=None, bd=None, r=0):
            it = {'t': 'b', 'x': x, 'y': y, 'w': w, 'h': h}
            if bg:
                it['bg'] = bg
            if bd:
                it['bd'] = bd
            if r:
                it['r'] = r
            items.append(it)

        def label(name, x, y, op=1.0):
            items.append({'t': 'i', 'n': name, 'x': x, 'y': y, 'w': _SET_LABEL_W[name], 'op': op})

        def hit(wid, x, y, w, h):
            hits.append((wid, x, y, x + w, y + h))

        label('title', 10, 7)
        track = 'rgba(226,235,244,%.3f)' % self._config.number('trackOpacity', 0.0, 1.0)
        rows = (
            ('colorPlus', 'barColorPlus', '+1.23%', 0),
            ('colorMinus', 'barColorMinus', '-0.85%', 1),
            ('colorZero', 'barColorZero', '0.00%', None),
            ('colorBig', 'barColorBig', '+4.20%', 0),
        )
        for i, (t_key, b_key, text, arrow) in enumerate(rows):
            y0 = 30 + i * 18
            if arrow is not None:
                items.append({'t': 'a', 'x': 12, 'y': y0 + 4, 'c': self._config.color(t_key), 'd': arrow})
            else:
                items.append({'t': 'a', 'x': -30, 'y': -30, 'c': '#000000', 'd': 0})
            items.append({'t': 'x', 'x': 28, 'y': y0 + 1, 's': text, 'c': self._config.color(t_key)})
            box(96, y0 + 5, 114, 8, track, None, 2)
            base = rgb_of_hex(self._config.color(b_key if self._config.get('barBySign', True) else 'barColorStandard'))
            box(96, y0 + 5, 71, 8, 'linear-gradient(90deg,%s,%s)' % (rgb_css(mix_rgb(base, (0, 0, 0), 0.42)), rgb_css(base)), None, 2)

        names = ('plus', 'minus', 'zero', 'big', 'hangar', 'pct', 'std')
        keys = ('colorPlus', 'colorMinus', 'colorZero', 'colorBig', 'barColorHangar', 'pctColor', 'barColorStandard')
        for i, name in enumerate(names):
            x, y = 6 + (i % 3) * 70, 108 + (i // 3) * 26
            on = (i == self.target)
            box(x, y, 66, 22, 'rgba(255,255,255,%s)' % ('0.14' if on else '0.04'),
                'rgba(244,244,244,0.95)' if on else 'rgba(255,255,255,0.14)', 3)
            label(name, x + (66 - _SET_LABEL_W[name]) // 2, y + 1, 1.0 if on else 0.6)
            box(x + 4, y + 19, 58, 2, self._config.color(keys[i]))
            hit('chip:%d' % i, x, y, 66, 22)

        px, py, pw, ph = self.PICKER
        box(px, py, pw, ph, _HUE_STRIP, 'rgba(255,255,255,0.18)', 3)
        box(px, py, pw, ph, _SHADE_STRIP, None, 3)
        if self.pick is not None:
            box(self.pick[0] - 4, self.pick[1] - 4, 8, 8, None, '#FFFFFF', 4)
        else:
            box(-20, -20, 0, 0)
        hit('picker', px, py, pw, ph)
        for k, color in enumerate(_SWATCHES):
            x, y = 11 + (k % 10) * 20, 250 + (k // 10) * 17
            box(x, y, 17, 14, color, 'rgba(255,255,255,0.28)', 2)
            hit('sw:%d' % k, x, y, 17, 14)

        for name, lbl_name, key, lo, span in (
            ('size', 'size', 'uiScale', 0.5, 2.0),
            ('bg', 'bg', 'bgOpacity', 0.0, 1.0),
            ('alpha', None, 'panelOpacity', 0.0, 1.0),
        ):
            tx, ty = self.TRACK[name]
            value = self._config.number(key, lo, lo + span)
            t = clamp01((value - lo) / span)
            if lbl_name is None:
                items.append({'t': 'x', 'x': 10, 'y': ty, 'w': 58, 'h': 17, 's': u'Панель', 'c': '#EAEAEA'})
            else:
                label(lbl_name, 10, ty)
            box(tx, ty + 6, self.TRACK_W, 6, 'rgba(255,255,255,0.16)', None, 3)
            box(tx, ty + 6, t * self.TRACK_W, 6, '#B8C4D0', None, 3)
            box(tx + t * self.TRACK_W - 3, ty + 2, 6, 14, '#F4F4F4', None, 2)
            items.append({'t': 'n', 'x': 180, 'y': ty, 'c': 'white', 's': '%d%%' % int(round(value * 100))})
            hit(name, tx - 4, ty, self.TRACK_W + 8, 18)

        for x, y, key, lbl_name, wid, width in (
            (10, 356, 'glow', 'glow', 'tog:glow', 82),
            (96, 356, 'pctFollowsSign', 'sign', 'tog:sign', 120),
            (10, 378, 'dmgFollowsSign', 'dmg', 'tog:dmg', 120),
            (10, 400, 'barBySign', 'barsign', 'tog:bar', 140),
            (10, 422, 'showSpot', 'spot', 'tog:spot', 90),
            (112, 422, 'showTrack', 'track', 'tog:track', 100),
        ):
            on = bool(self._config.get(key, DEFAULT_CONFIG.get(key)))
            box(x, y + 2, 12, 12, 'rgba(255,255,255,0.06)', 'rgba(244,244,244,0.8)', 2)
            box(x + 3, y + 5, 6, 6, '#F4F4F4', None, 1) if on else box(-20, -20, 0, 0)
            label(lbl_name, x + 17, y - 1)
            hit(wid, x, y, width, 18)

        only_pct = bool(self._config.get('battlePercentOnly', True))
        box(10, 444, 200, 20, 'rgba(134,239,106,0.12)' if only_pct else 'rgba(255,255,255,0.04)',
            'rgba(134,239,106,0.55)' if only_pct else 'rgba(255,255,255,0.18)', 3)
        items.append({'t': 'x', 'x': 16, 'y': 445, 'w': 188, 'h': 18,
                      's': u'Режим 2: % + суммарный урон' if only_pct else u'Режим 1: полная панель', 'c': '#EAEAEA'})
        hit('tog:panel', 10, 444, 200, 20)

        for x, name in ((10, 'reset'), (112, 'done')):
            box(x, 474, 98, 20, 'rgba(255,255,255,0.08)', 'rgba(255,255,255,0.28)', 3)
            label(name, x + (98 - _SET_LABEL_W[name]) // 2, 475)
            hit(name, x, 474, 98, 20)
        self.items = items
        self._hits = hits

    def _hit_test(self, x, y):
        for wid, x1, y1, x2, y2 in reversed(self._hits):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return wid
        return None

    def _set_color(self, color):
        for key in self.TARGETS[self.target][1]:
            self._config.set(key, color)
        self.dirty = True

    def _drag(self, wid, x, y):
        if wid == 'picker':
            px, py, pw, ph = self.PICKER
            rx, ry = clamp01((x - px) / pw), clamp01((y - py) / ph)
            light = clamp01((0.95 - ry) / 0.9)
            r, g, b = colorsys.hls_to_rgb(rx, light, 1.0)
            self._set_color(hex_of_rgb((r * 255, g * 255, b * 255)))
            self.pick = (px + rx * pw, py + ry * ph)
        elif wid in ('size', 'bg', 'alpha'):
            t = clamp01((x - self.TRACK[wid][0]) / self.TRACK_W)
            if wid == 'size':
                self._config.set('uiScale', round((0.5 + 2.0 * t) * 20.0) / 20.0)
            elif wid == 'bg':
                self._config.set('bgOpacity', round(t * 50.0) / 50.0)
            else:
                self._config.set('panelOpacity', round(t * 50.0) / 50.0)
            self.dirty = True

    def on_down(self, x, y):
        wid = self._hit_test(x, y)
        if wid is None:
            return
        toggles = {
            'tog:glow': ('glow', True), 'tog:sign': ('pctFollowsSign', False),
            'tog:dmg': ('dmgFollowsSign', True), 'tog:bar': ('barBySign', True),
            'tog:spot': ('showSpot', True), 'tog:track': ('showTrack', True),
            'tog:panel': ('battlePercentOnly', True),
        }
        if wid in ('picker', 'size', 'bg', 'alpha'):
            self.active = wid
            self._drag(wid, x, y)
        elif wid.startswith('chip:'):
            self.target = int(wid[5:])
            self.pick = None
        elif wid.startswith('sw:'):
            self._set_color(_SWATCHES[int(wid[3:])])
            self.pick = None
        elif wid in toggles:
            key, dval = toggles[wid]
            self._config.set(key, not bool(self._config.get(key, dval)))
            self.dirty = True
        elif wid == 'reset':
            for key in _APPEARANCE_KEYS:
                self._config.set(key, DEFAULT_CONFIG[key])
            self.pick = None
            self.dirty = True
        elif wid == 'done':
            self.wantClose = True
        self.build()
        self.changed = True

    def _sig(self):
        return (tuple(self._config.get(k) for k in _APPEARANCE_KEYS), self.pick, self.target)

    def on_hold(self, x, y):
        if self.active is None:
            return
        now = self._clock.now()
        self._held = (x, y)
        if now - self._t < self.HOLD_STEP:
            return
        self._t = now
        self._apply_held()

    def _apply_held(self):
        if self._held is None or self.active is None:
            return
        x, y = self._held
        self._held = None
        before = self._sig()
        self._drag(self.active, x, y)
        if self._sig() != before:
            self.build()
            self.changed = True

    def on_up(self, x, y):
        self._apply_held()
        self.active = None
        self.save()

    def save(self):
        if self.dirty:
            self.dirty = False
            self._config_sync.save_current()

    def _panel_local(self, panel, px, py):
        ui = getattr(panel, 'ui', 1.0) or 1.0
        return (
            (px - panel.x) / self._input.px_w(1.0) / ui - 12.0,
            (panel.y - py) / self._input.px_h(1.0) / ui - 12.0,
        )

    def poll(self, owner, panel):
        if self._input.is_ctrl_down() or getattr(panel, '_dragging_flag', False):
            return False
        px, py = self._input.cursor_position()
        down = self._input.is_lmb_down()
        lx, ly = self._panel_local(panel, px, py)
        changed = False
        if self.open:
            if down:
                if not self.pressed:
                    self.pressed = True
                    self.on_down(lx, ly)
                else:
                    self.on_hold(lx, ly)
            elif self.pressed:
                self.pressed = False
                self.on_up(lx, ly)
            if self.changed:
                self.changed = False
                changed = True
            if self.wantClose:
                self.wantClose = False
                panel.close_settings()
                changed = True
            return changed or True
        in_gear = (panel.mode == 'h' and _GEAR[0] <= lx <= _GEAR[2] and _GEAR[1] <= ly <= _GEAR[3])
        if down:
            if in_gear and not self.gearPress:
                self.gearPress = True
            return False
        if self.gearPress:
            self.gearPress = False
            if in_gear:
                panel.open_settings()
                return True
        return False
