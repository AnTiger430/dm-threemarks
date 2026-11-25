# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math

from ..presenters.formatters import svg_escape

SVG_FONT = u'PFDINMax'

FONT_PRESETS = (
    {
        'num_family': u'ThreeMarksPFDINMax, PFDINMax',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksPFDINMax, PFDINMax',
        'lbl_weight': 700,
        'width_scale': 1.00,
        'svg_css': u'',
    },
    {
        'num_family': u'Warhelios',
        'num_weight': 700,
        'lbl_family': u'Warhelios',
        'lbl_weight': 400,
        'width_scale': 1.08,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksDINRound, DINRoundPro',
        'num_weight': 700,
        'lbl_family': u'Warhelios',
        'lbl_weight': 400,
        'width_scale': 1.12,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksJura, Jura',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksJura, Jura',
        'lbl_weight': 400,
        'width_scale': 1.30,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksExo2, Warhelios',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksExo2, Warhelios',
        'lbl_weight': 500,
        'width_scale': 1.20,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksRubik, Warhelios',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksRubik, Warhelios',
        'lbl_weight': 500,
        'width_scale': 1.28,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksFiraCond, ThreeMarksPFDINMax, PFDINMax',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksFiraCond, ThreeMarksPFDINMax, PFDINMax',
        'lbl_weight': 500,
        'width_scale': 1.04,
        'svg_css': u'',
    },
    {
        'num_family': u'ThreeMarksTektur, Warhelios',
        'num_weight': 700,
        'lbl_family': u'ThreeMarksTektur, Warhelios',
        'lbl_weight': 500,
        'width_scale': 1.30,
        'svg_css': u'',
    },
)


def font_spec(idx):
    """Return font preset metadata for index 0..7."""
    try:
        i = int(round(float(idx)))
    except (TypeError, ValueError):
        i = 0
    return FONT_PRESETS[max(0, min(len(FONT_PRESETS) - 1, i))]


def svg_text(x, y, text, fill, size, anchor=u'start', shadow=True, shadow_op=0.85, family=SVG_FONT, weight=700):
    """Cohtml-safe SVG text: explicit fill per <text>, no <tspan>, no CSS filter."""
    safe = svg_escape(text)
    w = int(weight)
    parts = []
    if shadow and shadow_op > 0.01:
        parts.append(
            u'<text x="%.1f" y="%.1f" text-anchor="%s" font-family="%s" '
            u'font-size="%d" font-weight="%d" fill="#000000" '
            u'fill-opacity="%.2f">%s</text>' % (
                x, y + 1.0, anchor, family, int(size), w, shadow_op, safe,
            )
        )
    parts.append(
        u'<text x="%.1f" y="%.1f" text-anchor="%s" font-family="%s" '
        u'font-size="%d" font-weight="%d" fill="%s">%s</text>' % (
            x, y, anchor, family, int(size), w, fill, safe,
        )
    )
    return u''.join(parts)


def svg_star(cx, cy, radius, fill, opacity=1.0):
    pts = []
    inner = radius * 0.42
    for i in range(10):
        ang = -math.pi * 0.5 + i * math.pi * 0.2
        rad = radius if (i % 2 == 0) else inner
        pts.append(u'%.1f,%.1f' % (cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return u'<polygon points="%s" fill="%s" fill-opacity="%.2f"/>' % (u' '.join(pts), fill, opacity)


def svg_arrow(x, y, color, down=False):
    if down:
        pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x, y, x + 10.0, y, x + 5.0, y + 9.0)
    else:
        pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x + 5.0, y, x + 10.0, y + 9.0, x, y + 9.0)
    return u'<polygon points="%s" fill="%s"/>' % (pts, color)


def svg_bitmap_icon(ox, oy, runs, opacity):
    rects = []
    for x, y, w, h in runs:
        rects.append(u'<rect x="%.1f" y="%.1f" width="%d" height="%d" fill="#E8E8E8" fill-opacity="%.2f"/>' % (
            ox + x, oy + y, w, h, opacity,
        ))
    return u''.join(rects)


def v3_frame_path(x, y, w, h, r, gap_side=None, g0=0.0, g1=0.0):
    r = max(0.0, min(float(r), min(w, h) * 0.45))
    x0, y0, x1, y1 = float(x), float(y), float(x + w), float(y + h)

    def arc(ax, ay):
        return (u' A %.1f %.1f 0 0 1 %.1f %.1f' % (r, r, ax, ay)) if r > 0.1 else u''

    if gap_side is None:
        if r <= 0.1:
            return u'M %.1f %.1f H %.1f V %.1f H %.1f Z' % (x0, y0, x1, y1, x0)
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s Z') % (
            x0 + r, y0, x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1), x0 + r, arc(x0, y1 - r), y0 + r, arc(x0 + r, y0),
        )
    if gap_side == 'top':
        g0 = max(x0 + r + 2.0, min(x1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(x1 - r - 2.0, g1))
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s H %.1f') % (
            g1, y0, x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1), x0 + r, arc(x0, y1 - r), y0 + r, arc(x0 + r, y0), g0,
        )
    if gap_side == 'bottom':
        g0 = max(x0 + r + 2.0, min(x1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(x1 - r - 2.0, g1))
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s H %.1f') % (
            g0, y1, x0 + r, arc(x0, y1 - r),
            y0 + r, arc(x0 + r, y0), x1 - r, arc(x1, y0 + r), y1 - r, arc(x1 - r, y1), g1,
        )
    if gap_side == 'left':
        g0 = max(y0 + r + 2.0, min(y1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(y1 - r - 2.0, g1))
        return (u'M %.1f %.1f V %.1f%s H %.1f%s V %.1f%s H %.1f%s V %.1f') % (
            x0, g0, y0 + r, arc(x0 + r, y0),
            x1 - r, arc(x1, y0 + r), y1 - r, arc(x1 - r, y1), x0 + r, arc(x0, y1 - r), g1,
        )
    g0 = max(y0 + r + 2.0, min(y1 - r - 4.0, g0))
    g1 = max(g0 + 2.0, min(y1 - r - 2.0, g1))
    return (u'M %.1f %.1f V %.1f%s H %.1f%s V %.1f%s H %.1f%s V %.1f') % (
        x1, g1, y1 - r, arc(x1 - r, y1),
        x0 + r, arc(x0, y1 - r), y0 + r, arc(x0 + r, y0), x1 - r, arc(x1, y0 + r), g0,
    )


def v3_corners_paths(x, y, w, h, r):
    r = max(0.0, min(float(r), min(w, h) * 0.45))
    arm = max(r + 4.0, min(10.0, min(w, h) * 0.22))
    x0, y0, x1, y1 = float(x), float(y), float(x + w), float(y + h)
    if r <= 0.1:
        return [
            u'M %.1f %.1f V %.1f H %.1f' % (x0, y0 + arm, y0, x0 + arm),
            u'M %.1f %.1f H %.1f V %.1f' % (x1 - arm, y0, x1, y0 + arm),
            u'M %.1f %.1f V %.1f H %.1f' % (x1, y1 - arm, y1, x1 - arm),
            u'M %.1f %.1f H %.1f V %.1f' % (x0 + arm, y1, x0, y1 - arm),
        ]
    return [
        u'M %.1f %.1f V %.1f A %.1f %.1f 0 0 1 %.1f %.1f H %.1f' % (x0, y0 + arm, y0 + r, r, r, x0 + r, y0, x0 + arm),
        u'M %.1f %.1f H %.1f A %.1f %.1f 0 0 1 %.1f %.1f V %.1f' % (x1 - arm, y0, x1 - r, r, r, x1, y0 + r, y0 + arm),
        u'M %.1f %.1f V %.1f A %.1f %.1f 0 0 1 %.1f %.1f H %.1f' % (x1, y1 - arm, y1 - r, r, r, x1 - r, y1, x1 - arm),
        u'M %.1f %.1f H %.1f A %.1f %.1f 0 0 1 %.1f %.1f V %.1f' % (x0 + arm, y1, x0 + r, r, r, x0, y1 - r, y1 - arm),
    ]


def v3_star_svg(cx, cy, r, earned, style, on_col, off_col, glow):
    pts = []
    inner = r * 0.43
    for i in range(10):
        ang = -math.pi * 0.5 + i * math.pi * 0.2
        rad = r if (i % 2 == 0) else inner
        pts.append(u'%.2f,%.2f' % (cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pts_str = u' '.join(pts)
    out = []
    if earned:
        fill = u'#FFD23C' if style == 2 else on_col
        if glow:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.24" stroke="%s" stroke-width="2.0" stroke-opacity="0.22"/>' % (pts_str, fill, fill))
        out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.96"/>' % (pts_str, fill))
    else:
        if style == 1:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.50"/>' % (pts_str, off_col))
        else:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.10" stroke="%s" stroke-width="1.15" stroke-opacity="0.55"/>' % (pts_str, off_col, off_col))
    return u''.join(out)


def v3_delta_icon_svg(x, y, kind, state, color):
    mode = 'down' if (state is True or state == 'down') else ('zero' if state == 'zero' else 'up')
    if kind == 0:
        if mode == 'zero':
            pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f' % (
                x + 5.5, y + 1.0, x + 9.5, y + 5.0, x + 5.5, y + 9.0, x + 1.5, y + 5.0,
            )
        elif mode == 'down':
            pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x, y, x + 10.0, y, x + 5.0, y + 9.0)
        else:
            pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x + 5.0, y, x + 10.0, y + 9.0, x, y + 9.0)
        return u'<polygon points="%s" fill="%s"/>' % (pts, color)
    if kind == 1:
        if mode == 'zero':
            return (
                u'<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f L %.1f %.1f" '
                u'fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' % (
                    x + 1.5, y + 5.5, x + 9.5, y + 5.5, x + 6.0, y + 2.0, x + 9.5, y + 5.5, x + 6.0, y + 9.0, color,
                )
            )
        if mode == 'down':
            return (
                u'<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f L %.1f %.1f" '
                u'fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' % (
                    x + 1.5, y + 1.5, x + 9.5, y + 9.5, x + 4.5, y + 9.5, x + 9.5, y + 9.5, x + 9.5, y + 4.5, color,
                )
            )
        return (
            u'<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f L %.1f %.1f" '
            u'fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' % (
                x + 1.5, y + 9.5, x + 9.5, y + 1.5, x + 4.5, y + 1.5, x + 9.5, y + 1.5, x + 9.5, y + 6.5, color,
            )
        )
    return u''


def v3_assist_icon_svg(ch, x, y, size, color, opacity):
    s = float(size) / 16.0
    cx = float(x) + float(size) * 0.5
    cy = float(y) + float(size) * 0.5
    if ch == 'spot':
        r1, dx1, dy1 = 3.5 * s, 2.68 * s, 2.25 * s
        r2, dx2, dy2 = 5.8 * s, 4.31 * s, 3.88 * s
        return (
            u'<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="%.2f"/>'
            u'<path d="M %.2f %.2f A %.2f %.2f 0 0 0 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 0 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 1 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 1 %.2f %.2f" '
            u'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
                cx, cy, 1.45 * s, color, opacity,
                cx - dx1, cy - dy1, r1, r1, cx - dx1, cy + dy1,
                cx - dx2, cy - dy2, r2, r2, cx - dx2, cy + dy2,
                cx + dx1, cy - dy1, r1, r1, cx + dx1, cy + dy1,
                cx + dx2, cy - dy2, r2, r2, cx + dx2, cy + dy2,
                color, 1.25 * s, opacity,
            )
        )
    if ch == 'track':
        ca = math.cos(math.pi * 0.25)
        sa = math.sin(math.pi * 0.25)

        def rot(dx, dy):
            return (cx + (dx * ca - dy * sa) * s, cy + (dx * sa + dy * ca) * s)

        poly = (
            (-2.62, -1.65), (2.62, -1.65), (2.62, -0.36), (5.20, -0.36),
            (5.20, 1.42), (2.15, 1.42), (2.15, 0.05), (-2.15, 0.05),
            (-2.15, 1.42), (-5.20, 1.42), (-5.20, -0.36), (-2.62, -0.36),
        )
        parts = []
        for off in (-4.40, -0.40, 3.60):
            cmds = []
            for vi, (px, py) in enumerate(poly):
                pt = rot(px, py + off)
                cmds.append((u'M %.2f %.2f' if vi == 0 else u'L %.2f %.2f') % pt)
            parts.append(u' '.join(cmds) + u' Z')
        return u'<path d="%s" fill="%s" fill-opacity="%.2f"/>' % (
            u' '.join(parts), color, opacity,
        )
    if ch == 'stun':
        rays = [
            u'M %.1f %.1f L %.1f %.1f' % (
                cx + 2.2 * math.cos(i * math.pi / 3.0), cy + 2.2 * math.sin(i * math.pi / 3.0),
                cx + 5.8 * math.cos(i * math.pi / 3.0), cy + 5.8 * math.sin(i * math.pi / 3.0),
            )
            for i in range(6)
        ]
        return (
            u'<circle cx="%.1f" cy="%.1f" r="2.0" fill="none" stroke="%s" stroke-width="1.4" stroke-opacity="%.2f"/>'
            u'<path d="%s" fill="none" stroke="%s" stroke-width="1.35" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
                cx, cy, color, opacity, u' '.join(rays), color, opacity,
            )
        )
    return (
        u'<circle cx="%.1f" cy="%.1f" r="4.6" fill="none" stroke="%s" stroke-width="1.3" stroke-opacity="%.2f"/>'
        u'<path d="M %.1f %.1f V %.1f M %.1f %.1f V %.1f M %.1f %.1f H %.1f M %.1f %.1f H %.1f" '
        u'fill="none" stroke="%s" stroke-width="1.3" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
            cx, cy, color, opacity,
            cx, cy - 6.5, cy - 2.6, cx, cy + 2.6, cy + 6.5,
            cx - 6.5, cy, cx - 2.6, cx + 2.6, cy, cx + 6.5, color, opacity,
        )
    )
