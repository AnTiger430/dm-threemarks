# -*- coding: utf-8 -*-
from __future__ import absolute_import

import math

from ...application.config.validator import ConfigStore
from ...domain.services.assist_resolver import AssistResolver
from ..presenters.formatters import svg_advance, v3_fmt_num
from .svg_primitives import font_spec


class V3MetricsCalculator(object):
    """Computes exact tactical layout metrics shared between Python SVG and Gameface DOM."""

    def __init__(self, config_store=None):
        self._cfg_store = config_store or ConfigStore()

    def resolve_assist(self, cfg, sample, alt=False):
        spot, track, max_ast, active_ch = AssistResolver.resolve_channels(
            sample.get('spot', 0), sample.get('track', 0)
        )
        show_mode = self._cfg_store.integer('v3AssistShow', 0, 3, cfg)
        raw_mode = self._cfg_store.integer('v3AssistMode', 0, 1, cfg)
        if show_mode == 3 or (show_mode == 1 and not alt) or (show_mode == 2 and alt):
            return [], active_ch, max_ast, False
        rows = [('spot', spot), ('track', track)] if raw_mode == 0 else [(active_ch or 'spot', max_ast)]
        if bool(cfg.get('v3AssistHideZero', False)):
            rows = [(ch, val) for ch, val in rows if val > 0]
        sep = self._cfg_store.integer('v3ThousandsSep', 0, 2, cfg)
        items = []
        for ch, val in rows:
            items.append({
                'ch': ch,
                'val': val,
                'active': (ch == active_ch and val > 0),
                'text': v3_fmt_num(val, sep),
            })
        return items, active_ch, max_ast, False

    def resolve_tempo(self, cfg, sample, alt=False):
        show_mode = self._cfg_store.integer('v3TempoShow', 0, 3, cfg)
        raw_mode = self._cfg_store.integer('v3TempoMode', 0, 2, cfg)
        if show_mode == 3 or (show_mode == 1 and not alt) or (show_mode == 2 and alt):
            return []
        pct = float(sample.get('pct', 0.0) or 0.0)
        t_next_pct = int(sample.get('tNextPct', 0) or 0) or (65 if pct < 65.0 else (85 if pct < 85.0 else (95 if pct < 95.0 else 100)))
        t_next = max(0, int(round(float(sample.get('tNext', 0) or 0))))
        t95 = max(0, int(round(float(sample.get('t95', 0) or 0))))
        dmg = max(0, int(round(float(sample.get('dmg', 0) or 0))))
        if raw_mode == 1:
            pairs = [(t_next_pct, t_next)]
        elif raw_mode == 2:
            pairs = [(95, t95)]
        else:
            if t_next_pct == 95:
                pairs = [(95, t95 if t95 > 0 else t_next)]
            elif t_next_pct < 95:
                pairs = [(t_next_pct, t_next), (95, t95)]
            else:
                pairs = [(95, t95), (100, t_next)]
        sep = self._cfg_store.integer('v3ThousandsSep', 0, 2, cfg)
        items = []
        for p_lbl, val in pairs:
            val_str = v3_fmt_num(val, sep) if val > 0 else u'\u2014'
            lbl = u'%d%%' % p_lbl
            items.append({
                'pct': p_lbl,
                'val': val,
                'done': (val > 0 and dmg >= val),
                'lbl': lbl,
                'valStr': val_str,
                'text': lbl + u' ' + val_str,
            })
        return items

    def resolve_hangar_rows(self, cfg, sample):
        if not bool(sample.get('isHangar')) or bool(sample.get('mini')) or not bool(cfg.get('vhShowThresholds', True)):
            return []
        sep = self._cfg_store.integer('v3ThousandsSep', 0, 2, cfg)
        has_rating = bool(sample.get('hasRating', True))
        pct = float(sample.get('pct', 0.0) or 0.0)
        marks = max(0, int(round(float(sample.get('marks', 0) or 0))))

        def mk_cell(p_lbl, key, req_marks):
            val = max(0, int(round(float(sample.get(key, 0) or 0))))
            val_str = v3_fmt_num(val, sep) if (has_rating and 0 < val < 30000) else u'\u2014'
            lbl = u'%d%%' % p_lbl
            done = False if req_marks is None else (has_rating and val > 0 and (marks >= req_marks or pct >= float(p_lbl)))
            return {'pct': p_lbl, 'val': val, 'done': done, 'lbl': lbl, 'valStr': val_str, 'text': lbl + u' ' + val_str}

        return [
            [mk_cell(65, 't65', 1), mk_cell(85, 't85', 2)],
            [mk_cell(95, 't95', 3), mk_cell(100, 't100', None)],
        ]

    def delta_info(self, cfg, sample):
        c = self._cfg_store
        has_rating = bool(sample.get('hasRating', True))
        pct = float(sample.get('pct', 0.0) or 0.0)
        dec_idx = c.integer('v3PctDecimals', 0, 1, cfg)
        dec = 0 if dec_idx == 0 else 2
        if not has_rating:
            return (u'--%' if dec == 0 else u'--.--%'), u'', 'zero', c.color('v3AccentZero', cfg), False
        pct_text = (u'%%.%df%%%%' % dec) % pct
        raw_delta = sample.get('delta')
        if raw_delta is None:
            return pct_text, u'', 'zero', c.color('v3AccentZero', cfg), False
        val = float(raw_delta)
        kind = AssistResolver.classify_delta(
            val,
            c.number('zeroBand', 0.0, 1.0, cfg),
            bool(cfg.get('bigByDamage', True)),
            bool(sample.get('big', False)),
            c.number('bigFrom', 0.0, 10.0, cfg),
        )
        accents = {
            'plus': c.color('v3AccentPlus', cfg),
            'minus': c.color('v3AccentMinus', cfg),
            'zero': c.color('v3AccentZero', cfg),
            'big': c.color('v3AccentBig', cfg),
        }
        near_zero = (abs(val) < (0.5 if dec == 0 else 0.005))
        disp_val = 0.0 if near_zero else val
        sign = u'' if (near_zero or val < 0) else u'+'
        delta_text = (u'%s%%.%df%%%%' % (sign, dec)) % disp_val
        show_delta = (c.integer('v3DeltaIcon', 0, 3, cfg) != 3)
        return pct_text, delta_text, kind, accents[kind], show_delta

    def target_info(self, cfg, sample):
        dmg = max(0, int(round(float(sample.get('dmg', 0) or 0))))
        tgt = max(0, int(round(float(sample.get('tHold', 0) or 0))))
        sep = self._cfg_store.integer('v3ThousandsSep', 0, 2, cfg)
        dmg_str = v3_fmt_num(dmg, sep)
        tgt_str = v3_fmt_num(tgt, sep) if tgt > 0 else u'\u2014'
        rem_str = v3_fmt_num(max(0, tgt - dmg), sep) if tgt > 0 else u'\u2014'
        return dmg, tgt, dmg_str, tgt_str, rem_str

    def bar_ratio(self, cfg, sample, dmg, tgt):
        pct = max(0.0, min(100.0, float(sample.get('bar', sample.get('pct', 0.0)) or 0.0)))
        scale = self._cfg_store.integer('v3BarScale', 0, 1, cfg)
        if scale == 1:
            if pct < 65.0:
                return pct / 65.0
            if pct < 85.0:
                return (pct - 65.0) / 20.0
            if pct < 95.0:
                return (pct - 85.0) / 10.0
            return (pct - 95.0) / 5.0
        return pct / 100.0

    def bar_color(self, cfg, pct, kind, delta_accent):
        mode = self._cfg_store.integer('v3BarColorMode', 0, 2, cfg)
        if mode == 1:
            return delta_accent
        if mode == 2:
            return self._cfg_store.color('v3BarCustomColor', cfg)
        return self._cfg_store.color('v3AccentPlus', cfg)

    def compute(self, cfg, sample, alt=False):
        c = self._cfg_store
        is_hangar = bool(sample.get('isHangar'))
        f_scale = font_spec(c.integer('v3Font', 0, 7, cfg))['width_scale']
        den = c.integer('v3Density', 0, 2, cfg)
        pad_x, pad_y, gap_row, pct_size, delta_size, dmg_size, ast_size = (
            (10, 7, 4, 24, 14, 13, 13),
            (12, 9, 6, 26, 15, 14, 14),
            (15, 11, 8, 28, 16, 15, 15),
        )[den]

        pct_text, delta_text, kind, delta_accent, show_delta = self.delta_info(cfg, sample)
        if is_hangar:
            show_delta = False
        dmg, tgt, dmg_str, tgt_str, rem_str = self.target_info(cfg, sample)
        if is_hangar and not (bool(sample.get('hasRating', True)) and dmg > 0):
            dmg_str = u'\u2014'
        ast_items, active_ch, max_ast, alt_exp = ([], None, 0, False) if is_hangar else self.resolve_assist(cfg, sample, alt=alt)
        thr_items = [] if is_hangar else self.resolve_tempo(cfg, sample, alt=alt)
        h_rows = self.resolve_hangar_rows(cfg, sample) if is_hangar else []

        frame_style = c.integer('v3FrameStyle', 0, 3, cfg)
        stars_pos = c.integer('v3StarsPos', 0, 5, cfg)
        stars_div = bool(cfg.get('v3StarsDivider', False))
        star_size = c.integer('v3StarsSize', 10, 22, cfg)
        star_gap = c.integer('v3StarsGap', 2, 14, cfg)
        stars_span = 3 * star_size + 2 * star_gap

        di = c.integer('v3DeltaIcon', 0, 3, cfg)
        delta_icon_w = 12 if (show_delta and di in (0, 1)) else 0
        pct_w = svg_advance(pct_text, pct_size, f_scale)
        header_pct_w = pct_w
        if is_hangar:
            pct_dec = 0 if c.integer('v3PctDecimals', 0, 1, cfg) == 0 else 2
            header_pct_w = max(pct_w, svg_advance(u'100%' if pct_dec == 0 else u'100.00%', pct_size, f_scale))
        delta_w = (svg_advance(delta_text, delta_size, f_scale) + (delta_icon_w + 5 if delta_icon_w else 0)) if show_delta else 0
        inline_stars_w = (stars_span + 10) if stars_pos == 4 else 0
        header_min_w = header_pct_w + delta_w + (14 if show_delta and pct_w > 0 else 0) + inline_stars_w

        show_dmg = bool(cfg.get('v3ShowDamage', True))
        dmg_lbl_mode = c.integer('v3DamageLabel', 0, 3, cfg)
        dmg_lbl_text = u''
        if is_hangar:
            dmg_lbl_text = u'Суммарный урон'
            dmg_val_str = dmg_str
        else:
            if dmg_lbl_mode == 0:
                dmg_lbl_text = u'Сум. урон'
            elif dmg_lbl_mode == 1:
                dmg_lbl_text = c.string('v3DamageCustomLabel', u'', 24, cfg)
            dmg_val_str = u'%s / %s' % (dmg_str, tgt_str)
        bar_min_w = (156, 178, 200)[den]
        max_auto_text_w = bar_min_w + 80
        raw_lbl_w = svg_advance(dmg_lbl_text, dmg_size, f_scale) if dmg_lbl_text else 0.0
        h_sep = c.integer('v3ThousandsSep', 0, 2, cfg)
        h_sample_num = v3_fmt_num(9999, h_sep) if is_hangar else u''
        dmg_val_w = svg_advance(dmg_val_str, dmg_size, f_scale) if show_dmg else 0.0
        if is_hangar and show_dmg:
            dmg_val_w = max(dmg_val_w, svg_advance(h_sample_num, dmg_size, f_scale))
        raw_dmg_row_w = (raw_lbl_w + (12 if raw_lbl_w > 0 else 0) + dmg_val_w) if show_dmg else 0.0
        if show_dmg and (not is_hangar) and dmg_lbl_mode == 1:
            dmg_row_min_w = min(raw_dmg_row_w, float(max_auto_text_w))
        else:
            dmg_row_min_w = raw_dmg_row_w

        ast_inside = (c.integer('v3AssistPlace', 0, 1, cfg) == 0)
        ast_item_gap = 18 if len(ast_items) <= 2 else 11
        thr_inside = (c.integer('v3TempoPlace', 0, 1, cfg) == 0)
        thr_item_gap = 14
        base_ast = ast_size
        base_thr = max(11, base_ast - 1)

        bar_style = c.integer('v3BarStyle', 0, 3, cfg)
        bar_h = c.integer('v3BarHeight', 2, 10, cfg)
        track_h = c.integer('v3BarTrackHeight', 1, 10, cfg)
        bar_text = (c.string('v3BarCustomText', u'KIBERSPORT', 24, cfg) or u'KIBERSPORT') if bar_style == 3 else u''
        req_bar_text_size = c.integer('v3BarTextSize', 10, 26, cfg)
        raw_bar_text_w = svg_advance(bar_text, req_bar_text_size, f_scale) if bar_style == 3 else 0.0
        bar_text_min_w = int(math.ceil(min(raw_bar_text_w + 8.0, float(max_auto_text_w)))) if bar_style == 3 else 0

        h_col0_w = h_col1_w = 0
        h_col_gap = 16
        if h_rows and len(h_rows) >= 2:
            h_val_min_w = svg_advance(h_sample_num, base_thr, f_scale)
            h_col0_w = int(math.ceil(svg_advance(u'95%', base_thr, f_scale))) + 8 + int(math.ceil(max(
                h_val_min_w, svg_advance(h_rows[0][0]['valStr'], base_thr, f_scale), svg_advance(h_rows[1][0]['valStr'], base_thr, f_scale)
            )))
            h_col1_w = int(math.ceil(svg_advance(u'100%', base_thr, f_scale))) + 8 + int(math.ceil(max(
                h_val_min_w, svg_advance(h_rows[0][1]['valStr'], base_thr, f_scale), svg_advance(h_rows[1][1]['valStr'], base_thr, f_scale)
            )))
        h_grid_min_w = (h_col0_w + h_col_gap + h_col1_w) if (h_rows and len(h_rows) >= 2) else 0

        extra_w = c.integer('v3MinWidth', 0, 200, cfg)
        radius = c.integer('v3Radius', 0, 14, cfg)
        min_bracket = max(12, radius + 8)
        stars_min_frame_w = (stars_span + 12 + 2 * min_bracket) if (stars_pos in (0, 1) and frame_style != 3) else (stars_span + 8 if stars_pos in (0, 1) else 0)
        base_cw = int(math.ceil(max(bar_min_w, bar_text_min_w, header_min_w, dmg_row_min_w, h_grid_min_w, stars_min_frame_w - 2 * pad_x)))
        cw = base_cw + extra_w

        bar_text_size = req_bar_text_size
        bar_text_w = raw_bar_text_w
        if bar_style == 3:
            avail_bar_w = max(20.0, float(cw) - 6.0)
            if bar_text_w > avail_bar_w:
                bar_text_size = max(8, int(math.floor(req_bar_text_size * (avail_bar_w / bar_text_w))))
                bar_text_w = svg_advance(bar_text, bar_text_size, f_scale)
                while bar_text_size > 8 and bar_text_w > avail_bar_w:
                    bar_text_size -= 1
                    bar_text_w = svg_advance(bar_text, bar_text_size, f_scale)

        dmg_lbl_size = dmg_size
        if show_dmg and dmg_lbl_text:
            avail_lbl_w = max(20.0, float(cw) - dmg_val_w - 10.0)
            if raw_lbl_w > avail_lbl_w:
                dmg_lbl_size = max(8, int(math.floor(dmg_size * (avail_lbl_w / raw_lbl_w))))
                while dmg_lbl_size > 8 and svg_advance(dmg_lbl_text, dmg_lbl_size, f_scale) > avail_lbl_w:
                    dmg_lbl_size -= 1

        width_scale = max(1.0, min(1.65, float(cw) / float(bar_min_w)))
        raw_ast = c.integer('v3AssistSize', 0, 24, cfg)
        if raw_ast > 0:
            ast_size = max(10, min(24, raw_ast))
        else:
            ast_size = int(round(base_ast * width_scale))
            if ast_items and ast_inside:
                while ast_size > base_ast:
                    ico_s = max(12, ast_size + 1)
                    if sum(ico_s + 5 + svg_advance(it['text'], ast_size, f_scale) for it in ast_items) + max(0, len(ast_items) - 1) * ast_item_gap <= cw:
                        break
                    ast_size -= 1
        ast_icon_size = max(12, ast_size + 1)
        ast_widths = [ast_icon_size + 5 + svg_advance(it['text'], ast_size, f_scale) for it in ast_items]
        ast_row_min_w = (sum(ast_widths) + max(0, len(ast_widths) - 1) * ast_item_gap) if ast_widths else 0

        if is_hangar:
            thr_size = base_thr
        else:
            raw_thr = c.integer('v3TempoSize', 0, 24, cfg)
            if raw_thr > 0:
                thr_size = max(10, min(24, raw_thr))
            else:
                thr_size = int(round(base_thr * width_scale))
                if thr_items and thr_inside:
                    while thr_size > base_thr:
                        if sum(svg_advance(it['text'], thr_size, f_scale) for it in thr_items) + max(0, len(thr_items) - 1) * thr_item_gap <= cw:
                            break
                        thr_size -= 1
        thr_widths = [svg_advance(it['text'], thr_size, f_scale) for it in thr_items]
        thr_row_min_w = (sum(thr_widths) + max(0, len(thr_widths) - 1) * thr_item_gap) if thr_widths else 0

        framed = (frame_style != 3)
        side_border_stars = framed and (stars_pos in (2, 3))
        side_outside_stars = (not framed) and (stars_pos in (2, 3))
        half_star = int(math.ceil(star_size * 0.5))

        extra_top = max(0, half_star + 5 - pad_y) if stars_pos == 0 else 0
        extra_bot = max(0, half_star + 5 - pad_y) if stars_pos == 1 else 0
        extra_left = max(0, half_star + 5 - pad_x) if (side_border_stars and stars_pos == 2) else 0
        extra_right = max(0, half_star + 5 - pad_x) if (side_border_stars and stars_pos == 3) else 0

        y = pad_y + extra_top
        header_h = max(int(round(pct_size * 1.15)), star_size + 2) if stars_pos == 4 else int(round(pct_size * 1.15))
        header_y = y
        y += header_h

        eff_bar_h = max(bar_h, track_h)
        bar_y, bar_block_h = None, 0
        if bar_style == 3:
            y += gap_row
            bar_y = y
            bar_block_h = int(round(bar_text_size * 1.18))
            y += bar_block_h
        elif bar_style != 2:
            y += gap_row
            bar_y = y
            bar_block_h = max(
                eff_bar_h,
                10 if bool(cfg.get('v3BarCursor', True)) else eff_bar_h,
                8 if (bar_style == 0 and bool(cfg.get('v3BarEndTicks', True))) else eff_bar_h,
            )
            y += bar_block_h

        dmg_y, dmg_h = None, int(round(dmg_size * 1.25))
        if show_dmg:
            y += gap_row
            dmg_y = y
            y += dmg_h

        ast_y, ast_h = None, max(ast_size + 2, ast_icon_size)
        if ast_items and ast_inside:
            y += gap_row + 1
            ast_y = y
            y += ast_h

        thr_y, thr_h = None, thr_size + 2
        if thr_items and thr_inside:
            y += (gap_row if ast_y is not None else gap_row + 1)
            thr_y = y
            y += thr_h

        h_sep_y = h_row1_y = h_row2_y = None
        if h_rows:
            y += gap_row + 1
            h_sep_y = y
            y += gap_row
            h_row1_y = y
            y += thr_h + 2
            h_row2_y = y
            y += thr_h

        fh = y + pad_y + extra_bot
        if stars_pos in (2, 3):
            min_side_h = stars_span + (2 * (min_bracket + 8) if side_border_stars else 8)
            if fh < min_side_h:
                delta_shift = (min_side_h - fh) // 2
                fh = min_side_h
                header_y += delta_shift
                if bar_y is not None:
                    bar_y += delta_shift
                if dmg_y is not None:
                    dmg_y += delta_shift
                if ast_y is not None:
                    ast_y += delta_shift
                if thr_y is not None:
                    thr_y += delta_shift
                if h_sep_y is not None:
                    h_sep_y += delta_shift
                if h_row1_y is not None:
                    h_row1_y += delta_shift
                if h_row2_y is not None:
                    h_row2_y += delta_shift

        fw = cw + 2 * pad_x + extra_left + extra_right
        margin = 6
        fx = margin + (half_star if (side_border_stars and stars_pos == 2) else (star_size + (14 if stars_div else 8) if (side_outside_stars and stars_pos == 2) else 0))
        fy = margin + (half_star if stars_pos == 0 else 0)
        cx = fx + pad_x + extra_left

        stars_coords, div_line = [], None
        if stars_pos == 0:
            sx0 = fx + fw * 0.5 - stars_span * 0.5 + star_size * 0.5
            stars_coords = [(sx0 + i * (star_size + star_gap), fy) for i in range(3)]
        elif stars_pos == 1:
            sx0 = fx + fw * 0.5 - stars_span * 0.5 + star_size * 0.5
            stars_coords = [(sx0 + i * (star_size + star_gap), fy + fh) for i in range(3)]
        elif stars_pos == 2:
            sy0 = fy + fh * 0.5 - stars_span * 0.5 + star_size * 0.5
            scx = fx if side_border_stars else (margin + star_size * 0.5)
            stars_coords = [(scx, sy0 + i * (star_size + star_gap)) for i in range(3)]
            if side_outside_stars and stars_div:
                div_line = (fx - 7.0, fy + 3.0, fx - 7.0, fy + fh - 3.0)
        elif stars_pos == 3:
            sy0 = fy + fh * 0.5 - stars_span * 0.5 + star_size * 0.5
            scx = (fx + fw) if side_border_stars else (fx + fw + (14 if stars_div else 8) + star_size * 0.5)
            stars_coords = [(scx, sy0 + i * (star_size + star_gap)) for i in range(3)]
            if side_outside_stars and stars_div:
                div_line = (fx + fw + 7.0, fy + 3.0, fx + fw + 7.0, fy + fh - 3.0)

        right_extend = half_star if (side_border_stars and stars_pos == 3) else (((14 if stars_div else 8) + star_size) if (side_outside_stars and stars_pos == 3) else 0)
        win_w = int(math.ceil(fx + fw + right_extend + margin))

        bot_extend = half_star if stars_pos == 1 else 0
        cur_below_y = fy + fh + (half_star + 6 if stars_pos == 1 else 6)
        ast_below_y = thr_below_y = None
        if ast_items and not ast_inside:
            ast_below_y = cur_below_y
            cur_below_y += ast_h + 4
        if thr_items and not thr_inside:
            thr_below_y = cur_below_y
            cur_below_y += thr_h + 4
        win_h = int(math.ceil((cur_below_y - 4 + margin) if (ast_below_y is not None or thr_below_y is not None) else (fy + fh + bot_extend + margin)))

        return {
            'winW': win_w, 'winH': win_h, 'fx': fx, 'fy': fy, 'fw': fw, 'fh': fh,
            'cx': cx, 'cy': fy + header_y, 'cw': cw, 'padX': pad_x, 'padY': pad_y,
            'headerY': fy + header_y, 'headerH': header_h, 'pctSize': pct_size, 'deltaSize': delta_size,
            'pctText': pct_text, 'deltaText': delta_text, 'kind': kind, 'deltaAccent': delta_accent,
            'showDelta': show_delta, 'deltaIconW': delta_icon_w, 'pctW': pct_w, 'deltaW': delta_w,
            'barY': (fy + bar_y) if bar_y is not None else None, 'barH': bar_h, 'trackH': track_h,
            'barBlockH': bar_block_h, 'barStyle': bar_style, 'barText': bar_text,
            'barTextSize': bar_text_size, 'barTextW': bar_text_w,
            'dmgY': (fy + dmg_y) if dmg_y is not None else None, 'dmgH': dmg_h, 'dmgSize': dmg_size,
            'dmg': dmg, 'tgt': tgt, 'dmgStr': dmg_str, 'tgtStr': tgt_str, 'remStr': rem_str,
            'dmgLblText': dmg_lbl_text, 'dmgLblSize': dmg_lbl_size, 'dmgLblMode': dmg_lbl_mode, 'dmgValStr': dmg_val_str,
            'astY': (fy + ast_y) if ast_inside and ast_y is not None else ast_below_y,
            'astH': ast_h, 'astSize': ast_size, 'astIconSize': ast_icon_size,
            'astItemGap': ast_item_gap, 'astItems': ast_items, 'astWidths': ast_widths,
            'astRowMinW': ast_row_min_w, 'astInside': ast_inside,
            'thrY': (fy + thr_y) if thr_inside and thr_y is not None else thr_below_y,
            'thrH': thr_h, 'thrSize': thr_size, 'thrIconSize': 0, 'thrItemGap': thr_item_gap,
            'thrItems': thr_items, 'thrWidths': thr_widths, 'thrRowMinW': thr_row_min_w, 'thrInside': thr_inside,
            'isHangar': is_hangar, 'hRows': h_rows, 'hCol0W': h_col0_w, 'hCol1W': h_col1_w, 'hColGap': h_col_gap,
            'hSepY': (fy + h_sep_y) if h_sep_y is not None else None,
            'hRow1Y': (fy + h_row1_y) if h_row1_y is not None else None,
            'hRow2Y': (fy + h_row2_y) if h_row2_y is not None else None,
            'starsCoords': stars_coords, 'starSize': star_size, 'starGap': star_gap,
            'starsSpan': stars_span, 'starsPos': stars_pos, 'sideBorderStars': side_border_stars,
            'divLine': div_line, 'altExp': alt_exp, 'activeCh': active_ch, 'maxAst': max_ast,
        }
