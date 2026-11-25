# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...domain.value_objects.thresholds import Thresholds


def fmt_int(n):
    try:
        return u'{:,}'.format(int(round(n))).replace(',', u' ')
    except Exception:
        return unicode(n)


def v3_fmt_num(n, sep_mode):
    try:
        val = int(round(float(n)))
    except Exception:
        val = 0
    neg = val < 0
    s = str(abs(val))
    if sep_mode == 2:
        res = unicode(s)
    else:
        sep = u' ' if sep_mode == 0 else u','
        out = []
        while len(s) > 3:
            out.append(unicode(s[-3:]))
            s = s[:-3]
        out.append(unicode(s))
        res = sep.join(reversed(out))
    return (u'-' + res) if neg else res


def svg_escape(text):
    if isinstance(text, unicode):
        u = text
    elif isinstance(text, str):
        u = unicode(text, 'utf-8', 'replace')
    else:
        u = unicode(text)
    return (
        u.replace(u'&', u'&amp;')
        .replace(u'<', u'&lt;')
        .replace(u'>', u'&gt;')
        .replace(u'"', u'&quot;')
    )


_EXTRA_WIDE_UPPER = u'ЖШЩЮЫФДMW'
_EXTRA_WIDE_LOWER = u'жшщюыфдмmw'
_NARROW_GLYPHS = u'Iiljtf!|ІіЇї'


def svg_advance(text, size, scale=1.0):
    """Approximate horizontal width for SVG/DOM placement with optional font scale."""
    if not isinstance(text, unicode):
        text = unicode(text, 'utf-8', 'replace') if isinstance(text, str) else unicode(text)
    w = 0.0
    s = float(size)
    for ch in text:
        if u'0' <= ch <= u'9':
            w += 0.50 * s
        elif ch == u' ':
            w += 0.24 * s
        elif ch == u'/':
            w += 0.38 * s
        elif ch in (u'.', u',', u':'):
            w += 0.26 * s
        elif ch in (u'+', u'-', u'\u2212'):
            w += 0.48 * s
        elif ch == u'%':
            w += 0.78 * s
        elif ch == u'\u2014':
            w += 0.62 * s
        elif ch in _EXTRA_WIDE_UPPER:
            w += 0.90 * s
        elif ch in _EXTRA_WIDE_LOWER:
            w += 0.78 * s
        elif ch in _NARROW_GLYPHS:
            w += 0.34 * s
        elif ch.isupper():
            w += 0.64 * s
        else:
            w += 0.54 * s
    try:
        sc = float(scale)
    except (TypeError, ValueError):
        sc = 1.0
    return w * (sc if sc > 0.0 else 1.0)


class BasePayloadPresenter(object):
    """Shared helper projecting Thresholds into V3 next-mark fields."""

    @staticmethod
    def resolve_thresholds(thresholds, pct):
        thr = thresholds if thresholds is not None else Thresholds()
        t65, t85, t95, t100 = thr.as_tuple()
        t_next_pct, t_next = thr.next_for(pct)
        return t65, t85, t95, t100, t_next_pct, t_next
