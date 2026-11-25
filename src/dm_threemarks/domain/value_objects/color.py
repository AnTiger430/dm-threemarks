# -*- coding: utf-8 -*-
from __future__ import absolute_import


class ColorRgb(object):
    """Immutable 3-channel RGB color value object (0..255 per channel)."""

    __slots__ = ('r', 'g', 'b')

    def __init__(self, r, g, b):
        self.r = float(r)
        self.g = float(g)
        self.b = float(b)

    def as_tuple(self):
        return (self.r, self.g, self.b)

    def to_hex(self):
        return hex_of_rgb(self.as_tuple())

    def to_css(self):
        return rgb_css(self.as_tuple())

    def mix(self, other, t):
        return ColorRgb(*mix_rgb(self.as_tuple(), other.as_tuple(), t))


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def rgb_of_hex(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def hex_of_rgb(rgb):
    return '#%02X%02X%02X' % tuple(int(round(max(0.0, min(255.0, v)))) for v in rgb)


def mix_rgb(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def rgb_css(rgb):
    return 'rgb(%d,%d,%d)' % tuple(int(round(v)) for v in rgb)


def normalize_hex_color(raw, default='#FFFFFF'):
    text = str(raw or '').strip()
    if len(text) == 6:
        text = '#' + text
    if len(text) == 7 and text[0] == '#':
        try:
            int(text[1:], 16)
            return text.upper()
        except ValueError:
            pass
    return str(default).upper()
