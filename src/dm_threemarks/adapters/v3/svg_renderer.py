# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import math

from ...application.config.validator import ConfigStore
from ..presenters.formatters import fmt_int, svg_advance, svg_escape
from .samples import SVG_SPOT_RUNS, SVG_TRACK_RUNS
from .svg_primitives import (
    SVG_FONT,
    font_spec,
    svg_arrow,
    svg_bitmap_icon,
    svg_star,
    svg_text,
    v3_assist_icon_svg,
    v3_corners_paths,
    v3_delta_icon_svg,
    v3_frame_path,
    v3_star_svg,
)


class V3SvgRenderer(object):
    """Renders tactical V3/Hangar SVG and Classic/Korben SVG previews (1-to-1 with 10.12.7)."""

    def __init__(self, metrics_calc, config_store=None):
        self._metrics = metrics_calc
        self._cfg_store = config_store or ConfigStore()

    def render_bar_svg(self, cfg, m, ratio, bar_col):
        c = self._cfg_store
        fspec = font_spec(c.integer('v3Font', 0, 7, cfg))
        nfam, nw = fspec['num_family'], fspec['num_weight']
        f_scale = fspec['width_scale']
        bx = float(m['cx'])
        bw = float(m['cw'])
        bar_style = c.integer('v3BarStyle', 0, 3, cfg)
        if bar_style == 2 or m['barY'] is None:
            return u''
        if bar_style == 3:
            b_txt = m.get('barText') or c.string('v3BarCustomText', u'KIBERSPORT', 24, cfg) or u'KIBERSPORT'
            b_sz = int(m.get('barTextSize', c.integer('v3BarTextSize', 10, 26, cfg)))
            tw = min(bw, max(1.0, float(m.get('barTextW') or svg_advance(b_txt, b_sz, f_scale))))
            tx_mid = bx + bw * 0.5
            tx0 = bx + (bw - tw) * 0.5
            ty = float(m['barY']) + float(m['barBlockH']) * 0.5 + float(b_sz) * 0.34
            fill_w = max(0.0, min(tw, tw * ratio))
            win_w = float(m.get('winW') or (bx * 2.0 + bw))
            clip_top = float(int(math.floor(float(m['barY']) - 2.0)))
            clip_h = float(int(math.ceil(float(m['barBlockH']) + 6.0)))
            clip_bx = float(int(math.floor(bx)))
            clip_bw = float(int(math.ceil(bw)))
            clip_x = float(int(math.floor(tx0)))
            clip_w = 0.0
            if fill_w > 0.2:
                clip_x1 = min(
                    clip_bx + clip_bw,
                    float(int(math.ceil(tx0 + fill_w))) if ratio >= 0.999 else float(int(round(tx0 + fill_w))),
                )
                clip_w = max(1.0, clip_x1 - clip_x)
            pad_r = max(clip_bx + clip_bw + 1.0, win_w - 1.0)
            pad_anchors = (
                u'<rect x="0.0" y="%.1f" width="1.0" height="%.1f" fill="#000000" fill-opacity="0.01"/>'
                u'<rect x="%.1f" y="%.1f" width="1.0" height="%.1f" fill="#000000" fill-opacity="0.01"/>'
            ) % (clip_top, clip_h, pad_r, clip_top, clip_h)
            defs = [
                u'<clipPath id="v3tb" shape-rendering="optimizeSpeed"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath>' % (
                    clip_bx, clip_top, clip_bw, clip_h,
                )
            ]
            if clip_w > 0.0:
                defs.append(
                    u'<clipPath id="v3tc" shape-rendering="optimizeSpeed"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath>' % (
                        clip_x, clip_top, clip_w, clip_h,
                    )
                )
            out = [
                u'<defs>%s</defs>' % u''.join(defs),
                u'<g clip-path="url(#v3tb)">%s<text x="%.1f" y="%.1f" text-anchor="middle" font-family="%s" font-size="%d" font-weight="%d" fill="#FFFFFF" fill-opacity="0.25">%s</text></g>' % (
                    pad_anchors, tx_mid, ty, nfam, b_sz, nw, svg_escape(b_txt),
                ),
            ]
            if clip_w > 0.0:
                out.append(
                    u'<g clip-path="url(#v3tc)">%s%s</g>' % (
                        pad_anchors,
                        svg_text(tx_mid, ty, b_txt, bar_col, b_sz, anchor=u'middle', shadow=True, shadow_op=0.85, family=nfam, weight=nw),
                    )
                )
            return u''.join(out)

        bh = float(m['barH'])
        track_h = float(m.get('trackH', c.integer('v3BarTrackHeight', 1, 10, cfg)))
        by = float(m['barY']) + (float(m['barBlockH']) - bh) * 0.5
        track_y = by + (bh - track_h) * 0.5
        out = []
        if bar_style == 1:
            gap = 2.0
            spans = [(0.0, 65.0), (65.0, 85.0), (85.0, 95.0), (95.0, 100.0)]
            weights = [0.65, 0.20, 0.10, 0.05]
            usable_w = bw - gap * (len(spans) - 1)
            cur_x = bx
            cur_pct = max(0.0, min(100.0, ratio * 100.0))
            cursor_tip_x = bx
            for idx, (s0, s1) in enumerate(spans):
                sw = usable_w * weights[idx]
                seg_fill = max(0.0, min(1.0, (cur_pct - s0) / max(1e-6, s1 - s0)))
                out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>' % (
                    cur_x, track_y, sw, track_h,
                ))
                if seg_fill > 0.005:
                    fw = max(1.0, sw * seg_fill)
                    out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="%s" stroke="#000000" stroke-width="0.6" stroke-opacity="0.60"/>' % (
                        cur_x, by, fw, bh, bar_col,
                    ))
                    cursor_tip_x = cur_x + fw
                cur_x += sw + gap
            if bool(cfg.get('v3BarCursor', True)):
                cur_h = max(10.0, max(bh, track_h) + 6.0)
                cur_y = by + (bh - cur_h) * 0.5
                tip_x = max(bx, min(bx + bw - 2.5, cursor_tip_x - 1.25))
                out.append(u'<rect x="%.1f" y="%.1f" width="2.5" height="%.1f" rx="0.8" fill="#FFFFFF" fill-opacity="0.95"/>' % (
                    tip_x, cur_y, cur_h,
                ))
            return u''.join(out)

        out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>' % (
            bx, track_y, bw, track_h,
        ))
        if bool(cfg.get('v3BarEndTicks', True)):
            tick_h = max(8.0, max(bh, track_h) + 4.0)
            tick_top = by + (bh - tick_h) * 0.5
            out.append(u'<rect x="%.1f" y="%.1f" width="1.2" height="%.1f" fill="#FFFFFF" fill-opacity="0.45"/>' % (bx, tick_top, tick_h))
            out.append(u'<rect x="%.1f" y="%.1f" width="1.2" height="%.1f" fill="#FFFFFF" fill-opacity="0.45"/>' % (bx + bw - 1.2, tick_top, tick_h))
        if bool(cfg.get('v3BarMarks', False)) and c.integer('v3BarScale', 0, 1, cfg) == 0:
            mark_h = max(bh, track_h) + 3.0
            mark_top = by + (bh - mark_h) * 0.5
            for th in (65.0, 85.0, 95.0):
                tx = bx + bw * (th / 100.0)
                out.append(u'<rect x="%.1f" y="%.1f" width="1.0" height="%.1f" fill="#FFFFFF" fill-opacity="0.40"/>' % (tx - 0.5, mark_top, mark_h))
        fill_w = max(0.0, min(bw, bw * ratio))
        if fill_w > 0.5:
            out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="%s"/>' % (bx, by, fill_w, bh, bar_col))
        if bool(cfg.get('v3BarCursor', True)):
            cur_h = max(10.0, max(bh, track_h) + 6.0)
            cur_y = by + (bh - cur_h) * 0.5
            cur_x = max(bx, min(bx + bw - 2.5, bx + fill_w - 1.25))
            out.append(u'<rect x="%.1f" y="%.1f" width="2.5" height="%.1f" rx="0.8" fill="#FFFFFF" fill-opacity="0.95"/>' % (
                cur_x, cur_y, cur_h,
            ))
        return u''.join(out)

    def render_v3_svg(self, cfg, sample, alt=False):
        c = self._cfg_store
        fspec = font_spec(c.integer('v3Font', 0, 7, cfg))
        nfam, nw = fspec['num_family'], fspec['num_weight']
        lfam, lw = fspec['lbl_family'], fspec['lbl_weight']
        f_scale = fspec['width_scale']
        m = self._metrics.compute(cfg, sample, alt=alt)
        win_w, win_h = m['winW'], m['winH']
        fx, fy, fw, fh = float(m['fx']), float(m['fy']), float(m['fw']), float(m['fh'])
        cx, cw = float(m['cx']), float(m['cw'])

        panel_op = c.number('panelOpacity', 0.0, 1.0, cfg)
        text_main = c.color('v3TextMain', cfg)
        text_muted = c.color('v3TextMuted', cfg)
        frame_style = c.integer('v3FrameStyle', 0, 3, cfg)
        rad = c.integer('v3Radius', 0, 14, cfg)
        bg_col = c.color('v3BgColor', cfg)
        bg_op = c.number('v3BgOpacity', 0.0, 1.0, cfg)
        shadow_op = 0.85 if frame_style == 3 else ((0.85 * (1.0 - bg_op / 0.55)) if bg_op < 0.55 else 0.0)
        corner_col = c.color('v3CornerColor', cfg)
        corner_op = c.number('v3CornerAlpha', 0.0, 1.0, cfg)
        border_op = c.number('v3BorderAlpha', 0.0, 1.0, cfg)

        parts = []
        if frame_style != 3:
            if bg_op > 0.01:
                parts.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" fill-opacity="%.3f"/>' % (
                    fx, fy, fw, fh, rad, bg_col, bg_op,
                ))
            if frame_style in (0, 2) and border_op > 0.01:
                gap_side, g0, g1 = None, 0.0, 0.0
                sp = m['starsPos']
                half_gap = m['starsSpan'] * 0.5 + 6.0
                if sp == 0:
                    gap_side, g0, g1 = 'top', fx + fw * 0.5 - half_gap, fx + fw * 0.5 + half_gap
                elif sp == 1:
                    gap_side, g0, g1 = 'bottom', fx + fw * 0.5 - half_gap, fx + fw * 0.5 + half_gap
                elif sp == 2 and m['sideBorderStars']:
                    gap_side, g0, g1 = 'left', fy + fh * 0.5 - half_gap, fy + fh * 0.5 + half_gap
                elif sp == 3 and m['sideBorderStars']:
                    gap_side, g0, g1 = 'right', fy + fh * 0.5 - half_gap, fy + fh * 0.5 + half_gap
                parts.append(u'<path d="%s" fill="none" stroke="%s" stroke-width="1.0" stroke-opacity="%.3f"/>' % (
                    v3_frame_path(fx, fy, fw, fh, rad, gap_side, g0, g1), corner_col, border_op,
                ))
            if frame_style in (0, 1) and corner_op > 0.01:
                for cp in v3_corners_paths(fx, fy, fw, fh, rad):
                    parts.append(u'<path d="%s" fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-opacity="%.3f"/>' % (
                        cp, corner_col, corner_op,
                    ))
        if m['divLine'] is not None:
            x1, y1, x2, y2 = m['divLine']
            parts.append(u'<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2" stroke-opacity="0.45"/>' % (
                x1, y1, x2, y2, corner_col,
            ))

        marks = int(sample.get('marks', 0) or 0)
        star_style = c.integer('v3StarsStyle', 0, 2, cfg)
        star_on = c.color('v3StarOnColor', cfg)
        star_off = c.color('v3StarOffColor', cfg)
        star_glow = bool(cfg.get('v3StarsGlow', True))
        star_r = float(m['starSize']) * 0.5
        for idx, (scx, scy) in enumerate(m['starsCoords']):
            parts.append(v3_star_svg(scx, scy, star_r, idx < marks, star_style, star_on, star_off, star_glow))

        hy = float(m['headerY'])
        pct_base_y = hy + float(m['pctSize']) * 0.90
        del_base_y = hy + float(m['pctSize']) * 0.84
        ho = c.integer('v3HeaderOrder', 0, 2, cfg)
        di = c.integer('v3DeltaIcon', 0, 3, cfg)
        dc = c.integer('v3DeltaColorMode', 0, 1, cfg)
        del_col = m['deltaAccent'] if dc == 0 else text_muted
        delta_dir = 'down' if m['kind'] == 'minus' else ('zero' if m['kind'] == 'zero' else 'up')

        def draw_delta(x_left):
            cur = x_left
            if m['deltaIconW'] > 0:
                parts.append(v3_delta_icon_svg(cur, del_base_y - 10.0, di, delta_dir, del_col))
                cur += m['deltaIconW'] + 4.0
            parts.append(svg_text(cur, del_base_y, m['deltaText'], del_col, m['deltaSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))

        if ho == 0:
            parts.append(svg_text(cx, pct_base_y, m['pctText'], text_main, m['pctSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
            if m['showDelta']:
                draw_delta(cx + cw - m['deltaW'] - (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0))
        elif ho == 1:
            if m['showDelta']:
                draw_delta(cx)
            parts.append(svg_text(cx + cw - (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0), pct_base_y, m['pctText'], text_main, m['pctSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
        else:
            total_hw = m['pctW'] + (10.0 + m['deltaW'] if m['showDelta'] else 0.0) + (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0.0)
            hx = cx + (cw - total_hw) * 0.5
            parts.append(svg_text(hx, pct_base_y, m['pctText'], text_main, m['pctSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
            if m['showDelta']:
                draw_delta(hx + m['pctW'] + 10.0)
        if m['starsPos'] == 4:
            sx0 = cx + cw - m['starsSpan'] + star_r
            scy = hy + m['headerH'] * 0.5
            for idx in range(3):
                parts.append(v3_star_svg(sx0 + idx * (m['starSize'] + m['starGap']), scy, star_r, idx < marks, star_style, star_on, star_off, star_glow))

        ratio = self._metrics.bar_ratio(cfg, sample, m['dmg'], m['tgt'])
        bar_col = self._metrics.bar_color(cfg, float(sample.get('pct', 0.0) or 0.0), m['kind'], m['deltaAccent'])
        parts.append(self.render_bar_svg(cfg, m, ratio, bar_col))

        if m['dmgY'] is not None:
            dy = float(m['dmgY']) + float(m['dmgSize']) * 0.92
            if m['dmgLblText']:
                lbl_sz = int(m.get('dmgLblSize', m['dmgSize']))
                parts.append(svg_text(cx, dy, m['dmgLblText'], text_muted, lbl_sz, anchor=u'start', shadow=True, shadow_op=shadow_op, family=lfam, weight=lw))
            if m.get('isHangar'):
                has_rating = bool(sample.get('hasRating', True))
                ema_col = c.color('v3AccentPlus', cfg) if (has_rating and m['dmg'] > 0) else text_muted
                parts.append(svg_text(cx + cw, dy, m['dmgStr'], ema_col, m['dmgSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
            else:
                need_part = u'/ ' + m['tgtStr']
                need_w = svg_advance(need_part, m['dmgSize'], f_scale)
                if bool(cfg.get('v3DamageDynColor', True)):
                    dmg_col = m['deltaAccent']
                else:
                    dmg_col = text_main
                if m.get('dmgLblMode') == 3:
                    dmg_w = svg_advance(m['dmgStr'], m['dmgSize'], f_scale)
                    split_x = cx + cw * 0.5 - (dmg_w + 4.0 + need_w) * 0.5 + dmg_w
                    parts.append(svg_text(split_x, dy, m['dmgStr'], dmg_col, m['dmgSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                    parts.append(svg_text(split_x + 4.0, dy, need_part, text_muted, m['dmgSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                else:
                    parts.append(svg_text(cx + cw - need_w - 4.0, dy, m['dmgStr'], dmg_col, m['dmgSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                    parts.append(svg_text(cx + cw, dy, need_part, text_muted, m['dmgSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))

        if m['astItems'] and m['astY'] is not None:
            ay = float(m['astY'])
            baseline_y = ay + float(m['astSize']) * 0.92
            base_x = cx if m['astInside'] else (win_w - max(cw, m['astRowMinW'])) * 0.5
            base_w = cw if m['astInside'] else max(cw, m['astRowMinW'])
            total_w = sum(m['astWidths']) + max(0, len(m['astWidths']) - 1) * m['astItemGap']
            cur_x = base_x + (base_w - total_w) * 0.5
            for idx, it in enumerate(m['astItems']):
                col = c.color('v3AccentPlus', cfg) if it['active'] else text_muted
                iop = 1.0 if it['active'] else 0.82
                parts.append(v3_assist_icon_svg(it['ch'], cur_x, ay + (m['astH'] - m['astIconSize']) * 0.5, m['astIconSize'], col, iop))
                parts.append(svg_text(cur_x + m['astIconSize'] + 5.0, baseline_y, it['text'], col, m['astSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                cur_x += m['astWidths'][idx] + m['astItemGap']

        if m.get('thrItems') and m.get('thrY') is not None:
            ty = float(m['thrY'])
            baseline_y = ty + float(m['thrSize']) * 0.92
            total_w = sum(m['thrWidths']) + max(0, len(m['thrWidths']) - 1) * m['thrItemGap']
            cur_x = cx + (cw - total_w) * 0.5
            for idx, it in enumerate(m['thrItems']):
                l_col = text_muted
                v_col = text_main
                parts.append(svg_text(cur_x, baseline_y, it['lbl'], l_col, m['thrSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                lbl_adv = svg_advance(it['lbl'] + u' ', m['thrSize'], f_scale)
                parts.append(svg_text(cur_x + lbl_adv, baseline_y, it['valStr'], v_col, m['thrSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                cur_x += m['thrWidths'][idx] + m['thrItemGap']

        if m.get('hRows'):
            h_rows = m['hRows']
            if m.get('hSepY') is not None:
                parts.append(u'<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.0" stroke-opacity="0.18"/>' % (
                    cx, float(m['hSepY']), cx + cw, float(m['hSepY']), corner_col,
                ))
            col0_w = float(m.get('hCol0W') or 68.0)
            col1_w = float(m.get('hCol1W') or 72.0)
            col_gap = float(m.get('hColGap') or 16.0)
            total_grid_w = col0_w + col_gap + col1_w
            gx0 = cx + (cw - total_grid_w) * 0.5
            gx1 = gx0 + col0_w + col_gap
            for row_y, row_items in ((m.get('hRow1Y'), h_rows[0]), (m.get('hRow2Y'), h_rows[1] if len(h_rows) > 1 else [])):
                if row_y is None or not row_items or len(row_items) < 2:
                    continue
                tb_y = float(row_y) + float(m['thrSize']) * 0.92
                it0, it1 = row_items[0], row_items[1]
                l_col0 = c.color('v3AccentPlus', cfg) if it0['done'] else text_muted
                v_col0 = c.color('v3AccentPlus', cfg) if it0['done'] else text_main
                parts.append(svg_text(gx0, tb_y, it0['lbl'], l_col0, m['thrSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                parts.append(svg_text(gx0 + col0_w, tb_y, it0['valStr'], v_col0, m['thrSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                l_col1 = c.color('v3AccentPlus', cfg) if it1['done'] else text_muted
                v_col1 = c.color('v3AccentPlus', cfg) if it1['done'] else text_main
                parts.append(svg_text(gx1, tb_y, it1['lbl'], l_col1, m['thrSize'], anchor=u'start', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))
                parts.append(svg_text(gx1 + col1_w, tb_y, it1['valStr'], v_col1, m['thrSize'], anchor=u'end', shadow=True, shadow_op=shadow_op, family=nfam, weight=nw))

        body = u'<g opacity="%.3f">%s</g>' % (panel_op, u''.join(parts))
        svg = u'<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (
            win_w, win_h, win_w, win_h, body,
        )
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')), win_w, win_h

    def render_classic_svg(self, cfg_store, sample, preset):
        fspec = font_spec(cfg_store.integer('v3Font', 0, 7))
        nfam, nw = fspec['num_family'], fspec['num_weight']
        lfam, lw = fspec['lbl_family'], fspec['lbl_weight']
        f_scale = fspec['width_scale']
        delta = float(sample['delta'])
        zero_band = cfg_store.number('zeroBand', 0.0, 1.0)
        big_by_dmg = bool(cfg_store.get('bigByDamage', True))
        if sample['big'] and big_by_dmg:
            kind = 'big'
        elif abs(delta) <= zero_band:
            kind = 'zero'
        elif delta < 0:
            kind = 'minus'
        elif not big_by_dmg and delta >= cfg_store.number('bigFrom', 0.0, 10.0):
            kind = 'big'
        else:
            kind = 'plus'
        delta_color = {
            'plus': cfg_store.color('colorPlus'), 'minus': cfg_store.color('colorMinus'),
            'zero': cfg_store.color('colorZero'), 'big': cfg_store.color('colorBig'),
        }[kind]
        only_pct = (preset == 1 or bool(cfg_store.get('battlePercentOnly', False)))
        pct_color = delta_color if (only_pct or cfg_store.get('pctFollowsSign', False)) else cfg_store.color('pctColor')
        dmg_color = delta_color if cfg_store.get('dmgFollowsSign', True) else cfg_store.color('colorDmg')
        proj_color = cfg_store.color('colorProj')
        bg_opacity = cfg_store.number('bgOpacity', 0.0, 1.0)
        panel_opacity = cfg_store.number('panelOpacity', 0.0, 1.0)
        track_opacity = cfg_store.number('trackOpacity', 0.0, 1.0)
        tick_color = cfg_store.color('tickColor')
        glow_on = bool(sample['glow'] and cfg_store.get('glow', True))
        pct_text = u'%.2f%%' % sample['pct']
        delta_text = u'%+.2f%%' % sample['delta']
        dmg_text = fmt_int(sample['dmg'])
        proj_text = fmt_int(sample['proj'])
        need_text = u'/ ' + proj_text
        bar_key = {'plus': 'barColorPlus', 'minus': 'barColorMinus', 'zero': 'barColorZero', 'big': 'barColorBig'}[kind]
        bar_color = cfg_store.color(bar_key) if cfg_store.get('barBySign', True) else cfg_store.color('barColorStandard')

        if only_pct:
            width, height = 220, 72
            w_dmg = svg_advance(dmg_text, 15, f_scale)
            w_need = svg_advance(need_text, 15, f_scale)
            split_x = 110.0 - (w_dmg + 4.0 + w_need) * 0.5 + w_dmg
            items = [
                svg_text(110.0, 31.0, pct_text, pct_color, 22, anchor=u'middle', family=nfam, weight=nw),
                svg_text(split_x, 57.0, dmg_text, dmg_color, 15, anchor=u'end', family=nfam, weight=nw),
                svg_text(split_x + 4.0, 57.0, need_text, proj_color, 15, anchor=u'start', family=nfam, weight=nw),
            ]
        else:
            show_spot = bool(cfg_store.get('showSpot', False))
            show_track = bool(cfg_store.get('showTrack', False))
            ast_on = show_spot or show_track
            width, height = 244, (118 if ast_on else 96)
            panel_h = 94 if ast_on else 72
            stroke_k = min(1.0, bg_opacity / 0.8) if bg_opacity > 0.0 else 0.0
            fill_width = max(0.0, min(200.0, float(sample['pct']) * 2.0))
            pct_w = svg_advance(pct_text, 22, f_scale)
            arrow_x = 12.0 + (220.0 - pct_w) * 0.5 + pct_w + 9.0
            delta_x = arrow_x + 16.0
            marks = 3 if sample['pct'] >= 95.0 else (2 if sample['pct'] >= 85.0 else (1 if sample['pct'] >= 65.0 else 0))
            items = [
                u'<rect x="12" y="12" width="220" height="%d" rx="9" fill="#0C1219" fill-opacity="%.3f" stroke="#BAD2E5" stroke-opacity="%.3f"/>' % (
                    panel_h, bg_opacity, 0.20 * stroke_k,
                ),
                svg_text(122.0, 33.0, pct_text, pct_color, 22, anchor=u'middle', family=nfam, weight=nw),
                svg_arrow(arrow_x, 22.0, delta_color, down=(delta < 0.0)),
                svg_text(delta_x, 32.0, delta_text, delta_color, 15, anchor=u'start', family=nfam, weight=nw),
                u'<rect x="22" y="45" width="200" height="8" rx="4" fill="#E2EBF4" fill-opacity="%.3f"/>' % track_opacity,
            ]
            if glow_on and fill_width > 0.0:
                items.append(u'<rect x="20" y="43" width="%.1f" height="12" rx="6" fill="%s" fill-opacity="0.32"/>' % (fill_width + 4.0, bar_color))
            if fill_width > 0.0:
                items.append(u'<rect x="22" y="45" width="%.1f" height="8" rx="4" fill="%s"/>' % (fill_width, bar_color))
                items.append(u'<rect x="%.1f" y="41" width="2" height="16" rx="1" fill="%s"/>' % (22.0 + fill_width - 1.0, tick_color))
            need_x = 85.0 + svg_advance(dmg_text, 15, f_scale) + 4.0
            items.extend([
                svg_text(18.0, 75.0, u'Сум. урон:', '#C8D0D8', 13, anchor=u'start', family=lfam, weight=lw),
                svg_text(85.0, 75.0, dmg_text, dmg_color, 15, anchor=u'start', family=nfam, weight=nw),
                svg_text(need_x, 75.0, need_text, proj_color, 15, anchor=u'start', family=nfam, weight=nw),
                svg_star(187.0, 70.0, 6.5, '#FFD23C' if marks >= 1 else '#6E7884', 1.0 if marks >= 1 else 0.45),
                svg_star(204.0, 70.0, 6.5, '#FFD23C' if marks >= 2 else '#6E7884', 1.0 if marks >= 2 else 0.45),
                svg_star(221.0, 70.0, 6.5, '#FFD23C' if marks >= 3 else '#6E7884', 1.0 if marks >= 3 else 0.45),
            ])
            if ast_on:
                r_val = int(sample['assist'][0]) if show_spot else 0
                t_val = int(sample['assist'][1]) if show_track else 0
                main_color = delta_color if cfg_store.get('pctFollowsSign', False) else cfg_store.color('pctColor')
                r_item_w = 22.0 + svg_advance(fmt_int(r_val), 15, f_scale)
                t_item_w = 22.0 + svg_advance(fmt_int(t_val), 15, f_scale)
                total_w = (r_item_w if show_spot else 0.0) + (28.0 if (show_spot and show_track) else 0.0) + (t_item_w if show_track else 0.0)
                cur_x = 122.0 - total_w * 0.5
                if show_spot:
                    r_col = delta_color if r_val > t_val else main_color
                    r_op = 1.0 if r_val > t_val else 0.6
                    items.append(svg_bitmap_icon(cur_x, 87.0, SVG_SPOT_RUNS, r_op))
                    items.append(svg_text(cur_x + 22.0, 100.0, fmt_int(r_val), r_col, 15, anchor=u'start', family=nfam, weight=nw))
                    cur_x += r_item_w + 28.0
                if show_track:
                    t_col = delta_color if t_val > r_val else main_color
                    t_op = 1.0 if t_val > r_val else 0.6
                    items.append(svg_bitmap_icon(cur_x, 87.0, SVG_TRACK_RUNS, t_op))
                    items.append(svg_text(cur_x + 22.0, 100.0, fmt_int(t_val), t_col, 15, anchor=u'start', family=nfam, weight=nw))
        body = u'<g opacity="%.3f">%s</g>' % (panel_opacity, u''.join(items))
        svg = u'<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (width, height, width, height, body)
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')), width, height
