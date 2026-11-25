# -*- coding: utf-8 -*-
from __future__ import absolute_import

import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import base64
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
SRC_DIR = os.path.join(REPO_ROOT, 'src')
UI_DIR = os.path.join(REPO_ROOT, 'package', 'res', 'gui', 'gameface', 'mods', 'dm', 'ThreeMarks')
MAPS_DIR = os.path.join(REPO_ROOT, 'package', 'res', 'gui', 'maps', 'three_marks')
OUT_DIR = os.path.join(REPO_ROOT, 'dist', 'ui_audit')

for p in (SRC_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from dm_threemarks.application.config.defaults import DEFAULT_CONFIG, MOD_VERSION
from dm_threemarks.application.config.validator import ConfigStore
from dm_threemarks.adapters.menu.aslain_adapter import AslainMenuAdapter
from dm_threemarks.adapters.menu.preview_renderer import MenuPreviewRenderer
from dm_threemarks.adapters.menu.schema import MENU_LINKAGE, MenuValueConverter
from dm_threemarks.adapters.menu.template_builder import BATTLE_SECTIONS_LEGACY, BATTLE_SECTIONS_V3, MenuTemplateBuilder
from dm_threemarks.adapters.presenters.battle_presenter import BattlePayloadPresenter
from dm_threemarks.adapters.presenters.hangar_presenter import HangarPayloadPresenter
from dm_threemarks.adapters.presenters.ui_config_serializer import UiConfigSerializer
from dm_threemarks.adapters.v3.samples import PREVIEW_ORDER, PREVIEW_SAMPLES, PREVIEW_SAMPLES_V3
from dm_threemarks.adapters.v3.metrics import V3MetricsCalculator
from dm_threemarks.adapters.v3.svg_renderer import V3SvgRenderer
from dm_threemarks.domain.value_objects.thresholds import Thresholds
from wot_stubs import StrictAslainApiV2, StrictAslainTemplatesV2


def _make_svg(cfg):
    return V3SvgRenderer(V3MetricsCalculator(cfg), cfg)


FONT_NAMES = [
    u'0: PFDINMax',
    u'1: Warhelios',
    u'2: DINRoundPro',
    u'3: Jura',
    u'4: Exo 2',
    u'5: Rubik',
    u'6: Fira Cond',
    u'7: Tektur',
]

HANGAR_SECTIONS = [u'Основное', u'Рамка и звёзды', u'Полоска и пороги', u'Цвета']


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def _u(val):
    if isinstance(val, unicode):
        return val
    if isinstance(val, str):
        return val.decode('utf-8', 'replace')
    return unicode(val)


def _esc(val):
    s = _u(val)
    return (
        s.replace(u'&', u'&amp;')
         .replace(u'<', u'&lt;')
         .replace(u'>', u'&gt;')
         .replace(u'"', u'&quot;')
    )


def _find_browser():
    candidates = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    for name in ('chrome', 'msedge'):
        for d in os.environ.get('PATH', '').split(os.pathsep):
            cand = os.path.join(d.strip('"'), name + '.exe')
            if os.path.isfile(cand):
                return cand
    raise RuntimeError('Neither Chrome nor Edge binary found on host')


def _build_audit_css():
    css_path = os.path.join(UI_DIR, 'ThreeMarks.css')
    with open(css_path, 'rb') as f:
        css = f.read().decode('utf-8')
    css = css.replace('coui://gui/gameface/mods/dm/ThreeMarks/', '../../package/res/gui/gameface/mods/dm/ThreeMarks/')
    css = css.replace('img://gui/maps/three_marks/', '../../package/res/gui/maps/three_marks/')
    css = re.sub(r'#tm-v3(?=[\s.,:{#\[])', '[data-v3-host="1"]', css)
    if css.rstrip().endswith('#tm-v3'):
        css = css + ', [data-v3-host="1"]'
    css = re.sub(r'#tm-panel(?=[\s.,:{#\[])', '[data-panel-host="1"]', css)
    css += u"""
/* Audit page layout overrides */
html, body {
  background: #0e131a !important;
  color: #e6ebf2;
  overflow: visible !important;
  font-family: "Segoe UI", Tahoma, Arial, sans-serif;
  margin: 0;
  padding: 0;
}
.audit-sheet {
  padding: 16px 20px 24px 20px;
  max-width: 1360px;
}
.audit-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  padding-bottom: 8px;
  margin-bottom: 14px;
}
.audit-head h1 {
  font-size: 16px;
  font-weight: 700;
  color: #f4f7fb;
  letter-spacing: 0.3px;
}
.audit-head .meta {
  font-size: 12px;
  color: #93a1b3;
}
.audit-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
}
.audit-card {
  background: linear-gradient(155deg, rgba(28,36,48,0.92), rgba(16,21,29,0.96));
  border: 1px solid rgba(160,185,215,0.18);
  border-radius: 8px;
  padding: 10px 12px;
  min-width: 248px;
}
.audit-card.bad {
  border-color: #ff6060;
  box-shadow: 0 0 0 1px rgba(255,96,96,0.45);
}
.audit-title {
  font-size: 12px;
  font-weight: 700;
  color: #dce6f2;
  margin-bottom: 6px;
}
.audit-stage {
  position: relative;
  display: inline-block;
  padding: 10px 14px;
  border-radius: 6px;
  background:
    radial-gradient(circle at 20% 20%, rgba(74,92,110,0.38), rgba(20,27,36,0.92)),
    linear-gradient(135deg, #2b3542 0%, #192029 100%);
  border: 1px solid rgba(255,255,255,0.08);
  min-width: 210px;
}
.audit-stage [data-panel-host="1"] {
  position: relative !important;
  left: 0 !important;
  top: 0 !important;
}
.audit-stage [data-v3-host="1"] {
  position: relative;
}
.audit-note {
  margin-top: 6px;
  font-size: 11px;
  color: #93a1b3;
  font-family: Consolas, monospace;
}
.audit-note.err {
  color: #ff8080;
}
.audit-pair {
  display: flex;
  gap: 14px;
  align-items: center;
}
.audit-pair-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.audit-sublbl {
  font-size: 10px;
  text-transform: uppercase;
  color: #8ea0b5;
  letter-spacing: 0.5px;
}
/* Font matrix rows */
.font-row {
  display: flex;
  align-items: center;
  gap: 14px;
  background: rgba(22,29,39,0.92);
  border: 1px solid rgba(160,185,215,0.16);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.font-row.bad { border-color: #ff6060; }
.font-name {
  width: 120px;
  flex: 0 0 120px;
  font-size: 12px;
  font-weight: 700;
  color: #e2eaf4;
}
.font-zoom {
  flex: 1 1 auto;
  background: linear-gradient(180deg, rgba(16,22,30,0.95), rgba(11,15,21,0.98));
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 6px;
  padding: 8px 12px;
}
.font-zoom-line {
  display: inline-block;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.22;
  color: #ffffff;
  border-top: 1px dashed rgba(255,255,255,0.15);
  border-bottom: 1px dashed rgba(255,255,255,0.15);
  padding: 0 4px;
  white-space: nowrap;
}
.font-zoom-meta {
  font-size: 10px;
  color: #93a1b3;
  margin-top: 4px;
  font-family: Consolas, monospace;
}
"""
    out_css = os.path.join(OUT_DIR, 'ThreeMarks_audit.css')
    with open(out_css, 'wb') as f:
        f.write(css.encode('utf-8'))
    return out_css


class _FeedbackMock(object):
    def __init__(self, damage=0, radio=0, track=0, stun=0, src='feedback'):
        self._d = {'damage': damage, 'radio': radio, 'track': track, 'stun': stun, 'src': src}

    def to_parts_dict(self):
        return dict(self._d)


def _make_battle_case(title, cfg_overrides=None, sample=None, scale=None, bmin=False, ctrl=False):
    cfg_data = dict(DEFAULT_CONFIG)
    if cfg_overrides:
        cfg_data.update(cfg_overrides)
    cfg = ConfigStore(cfg_data)
    presenter = BattlePayloadPresenter(cfg)
    ser = UiConfigSerializer(cfg)

    s = {
        'shown_pct': 85.50, 'bar_pct': 85.50, 'delta': 0.34, 'dmg': 4233,
        'proj_ema': 3537, 'hold_dmg': 3537, 'marks': 2, 'glowing': False,
        'has_rating': True, 'big': False, 'damage': 3561, 'radio': 672,
        'track': 0, 'stun': 0, 't65': 2100, 't85': 2950, 't95': 3680, 't100': 4150,
        'is_spg': False, 'alt_down': False, 'session_base': 85.16,
    }
    if sample:
        s.update(sample)
    report = _FeedbackMock(s['damage'], s['radio'], s['track'], s['stun'])
    thrs = Thresholds(s['t65'], s['t85'], s['t95'], s['t100'])
    payload = presenter.build_payload(
        s['shown_pct'], s['bar_pct'], s['delta'], s['dmg'], s['proj_ema'],
        s['marks'], s['glowing'], s['has_rating'], big=s['big'], report=report,
        thresholds=thrs, is_spg=s['is_spg'], alt_down=s['alt_down'],
        session_base=s['session_base'], hold_dmg=s['hold_dmg'],
    )
    payload['mode'] = 'b'
    payload['ui'] = ser.ui_payload()
    if bmin:
        payload['bmin'] = True
    if ctrl:
        payload['ctrl'] = True
    eff_scale = cfg.ui_scale() if scale is None else scale

    # Optional Python SVG comparison sample for preset 0 or classic
    svg_info = None
    if cfg.integer('battlePreset', 0, 1) == 0:
        svg_sample = {
            'pct': s['shown_pct'], 'bar': s['bar_pct'], 'delta': s['delta'],
            'sDelta': s['shown_pct'] - s['session_base'] if s['has_rating'] else None,
            'dmg': s['dmg'], 'tHold': s['hold_dmg'],
            't65': s['t65'], 't85': s['t85'], 't95': s['t95'], 't100': s['t100'],
            'tNextPct': 65 if s['shown_pct'] < 65 else (85 if s['shown_pct'] < 85 else (95 if s['shown_pct'] < 95 else 100)),
            'tNext': s['t85'] if s['shown_pct'] < 85 else (s['t95'] if s['shown_pct'] < 95 else s['t100']),
            'own': s['damage'], 'spot': s['radio'], 'track': s['track'], 'stun': s['stun'],
            'marks': s['marks'], 'big': s['big'], 'isSpg': s['is_spg'], 'hasRating': s['has_rating'],
        }
        uri, sw, sh = _make_svg(cfg).render_v3_svg(cfg.snapshot(), svg_sample, alt=s['alt_down'])
        svg_info = {'uri': uri, 'w': sw, 'h': sh}

    return {'title': title, 'payload': payload, 'scale': eff_scale, 'svg': svg_info}


def _make_hangar_case(title, cfg_overrides=None, sample=None, scale=None):
    cfg_data = dict(DEFAULT_CONFIG)
    if cfg_overrides:
        cfg_data.update(cfg_overrides)
    cfg = ConfigStore(cfg_data)
    presenter = HangarPayloadPresenter()
    ser = UiConfigSerializer(cfg)

    s = {
        'rating': 84.02, 'ema': 2480, 'marks': 2, 'has_rating': True,
        't65': 1850, 't85': 2590, 't95': 3210, 't100': 3680,
    }
    if sample:
        s.update(sample)
    payload = presenter.build_payload(
        s['rating'], s['ema'], s['marks'], s['has_rating'],
        thresholds=Thresholds(s['t65'], s['t85'], s['t95'], s['t100']),
    )
    payload['mode'] = 'h'
    payload['ui'] = ser.ui_payload()
    eff_scale = cfg.vh_scale() if scale is None else scale

    h_sample = {
        'isHangar': True, 'pct': s['rating'], 'bar': s['rating'],
        'delta': None, 'sDelta': None, 'dmg': s['ema'], 'tHold': s['ema'],
        't65': s['t65'], 't85': s['t85'], 't95': s['t95'], 't100': s['t100'],
        'own': 0, 'spot': 0, 'track': 0, 'stun': 0,
        'marks': s['marks'], 'big': False, 'isSpg': False, 'hasRating': s['has_rating'],
    }
    uri, sw, sh = _make_svg(cfg).render_v3_svg(cfg.to_v3_from_hangar(), h_sample, alt=False)
    return {
        'title': title, 'payload': payload, 'scale': eff_scale,
        'svg': {'uri': uri, 'w': sw, 'h': sh},
    }


def _js_scripts_block():
    return u"""
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/defaults.js"></script>
  <script>
    window.DmThreeMarks.CONST.FONT_URL = '../../package/res/gui/maps/three_marks/font_';
    window.DmThreeMarks.CONST.SET_IMG = '../../package/res/gui/maps/three_marks/set_';
  </script>
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/utils.js"></script>
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/v3_metrics.js"></script>
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/v3_svg.js"></script>
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/renderer_v3.js"></script>
  <script src="../../package/res/gui/gameface/mods/dm/ThreeMarks/js/renderer_classic.js"></script>
"""


def _panel_render_and_audit_js():
    return u"""
  <script>
  (function () {
    var ns = window.DmThreeMarks;
    var U = ns.utils;

    function makePanelDom(host) {
      host.innerHTML =
        '<span class="p-pct" id="tm-pct">--.--%</span>' +
        '<div id="tm-arrow"></div>' +
        '<div class="tm-run" id="tm-delta"></div>' +
        '<div id="tm-cap0"></div><div id="tm-cap100"></div>' +
        '<div id="tm-track"><div id="tm-fill"></div></div>' +
        '<div id="tm-tick"></div><div id="tm-title"></div>' +
        '<div id="tm-valwrap"><div class="tm-run" id="tm-val"></div><div class="tm-run" id="tm-need"></div></div>' +
        '<span class="tm-star" id="tm-star1"></span><span class="tm-star" id="tm-star2"></span><span class="tm-star" id="tm-star3"></span>' +
        '<div id="tm-ast"><div class="tm-ag" id="tm-ast-r"><div class="tm-ai" id="tm-ast-ri"></div><div class="tm-live" id="tm-ast-rv"></div></div>' +
        '<div class="tm-ag" id="tm-ast-t"><div class="tm-ai" id="tm-ast-ti"></div><div class="tm-live" id="tm-ast-tv"></div></div></div>' +
        '<div id="tm-hsep"></div><div id="tm-hema-l"></div><div class="tm-run" id="tm-hema-v"></div>' +
        '<div class="tm-run tm-hthr" id="tm-h65l"></div><div class="tm-run tm-hthr" id="tm-h65v"></div>' +
        '<div class="tm-run tm-hthr" id="tm-h85l"></div><div class="tm-run tm-hthr" id="tm-h85v"></div>' +
        '<div class="tm-run tm-hthr" id="tm-h95l"></div><div class="tm-run tm-hthr" id="tm-h95v"></div>' +
        '<div id="tm-nodata"></div><div id="tm-btn"></div><div id="tm-cfg"></div><div id="tm-set"></div>';
      var q = function (sel) { return host.querySelector(sel); };
      return {
        panel: host,
        pct: q('#tm-pct'), arrow: q('#tm-arrow'), delta: q('#tm-delta'),
        fill: q('#tm-fill'), tick: q('#tm-tick'), val: q('#tm-val'), need: q('#tm-need'), valWrap: q('#tm-valwrap'),
        stars: [q('#tm-star1'), q('#tm-star2'), q('#tm-star3')],
        emaV: q('#tm-hema-v'),
        thr: {
          l65: q('#tm-h65l'), v65: q('#tm-h65v'),
          l85: q('#tm-h85l'), v85: q('#tm-h85v'),
          l95: q('#tm-h95l'), v95: q('#tm-h95v')
        },
        btn: q('#tm-btn'), track: q('#tm-track'), set: q('#tm-set'), cfg: q('#tm-cfg'),
        ast: q('#tm-ast'), astR: q('#tm-ast-r'), astT: q('#tm-ast-t'),
        astRv: q('#tm-ast-rv'), astTv: q('#tm-ast-tv'), astRi: q('#tm-ast-ri'), astTi: q('#tm-ast-ti')
      };
    }

    function visRect(el) {
      if (!el) return null;
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return null;
      var r = el.getBoundingClientRect();
      if (r.width <= 0.2 || r.height <= 0.2) return null;
      return r;
    }

    function overlaps(a, b, tol) {
      if (!a || !b) return false;
      return !(a.right <= b.left + tol || b.right <= a.left + tol || a.bottom <= b.top + tol || b.bottom <= a.top + tol);
    }

    function auditV3Card(card, host, caseObj, errors, warnings) {
      var p = caseObj.payload;
      var hostRect = host.getBoundingClientRect();
      var title = caseObj.title;

      // 1. Sibling overlap checks
      var pairs = [
        ['hdr pct vs delta', host.querySelector('.v3-pct'), host.querySelector('.v3-delwrap')],
        ['dmg lbl vs vals', host.querySelector('.v3-dmglbl'), host.querySelector('.v3-dmgvals')]
      ];
      var astItems = host.querySelectorAll('.v3-astwrap:not(.v3-thrwrap) .v3-astitem');
      var visAst = [];
      for (var i = 0; i < astItems.length; i += 1) {
        if (visRect(astItems[i])) visAst.push(astItems[i]);
      }
      for (var ai = 0; ai + 1 < visAst.length; ai += 1) {
        pairs.push(['ast item ' + ai + ' vs ' + (ai + 1), visAst[ai], visAst[ai + 1]]);
      }
      var thrRows = host.querySelectorAll('.v3-thrwrap');
      for (var tr = 0; tr < thrRows.length; tr += 1) {
        var cells = thrRows[tr].querySelectorAll('.v3-thritem');
        var visCells = [];
        for (var c = 0; c < cells.length; c += 1) {
          if (visRect(cells[c])) {
            visCells.push(cells[c]);
            pairs.push(['thr cell lbl vs val', cells[c].querySelector('.v3-thrlbl'), cells[c].querySelector('.v3-thrval')]);
          }
        }
        if (visCells.length >= 2) {
          pairs.push(['thr row ' + tr + ' col0 vs col1', visCells[0], visCells[1]]);
        }
      }
      for (var k = 0; k < pairs.length; k += 1) {
        var ra = visRect(pairs[k][1]), rb = visRect(pairs[k][2]);
        if (overlaps(ra, rb, 1.0)) {
          errors.push(title + ': OVERLAP ' + pairs[k][0] + ' (' + ra.right.toFixed(1) + ' > ' + rb.left.toFixed(1) + ')');
        }
      }

      // 2. Bounds and scrollWidth clipping check
      var innerSels = ['.v3-pct', '.v3-delwrap', '.v3-dmglbl', '.v3-dmgvals', '.v3-thrlbl', '.v3-thrval'];
      for (var si = 0; si < innerSels.length; si += 1) {
        var els = host.querySelectorAll(innerSels[si]);
        for (var ei = 0; ei < els.length; ei += 1) {
          var el = els[ei];
          var rr = visRect(el);
          if (!rr) continue;
          if (rr.left < hostRect.left - 2.0 || rr.right > hostRect.right + 2.0) {
            errors.push(title + ': HORIZ CLIP/OVERFLOW ' + innerSels[si] + ' [' + rr.left.toFixed(1) + '..' + rr.right.toFixed(1) + '] outside [' + hostRect.left.toFixed(1) + '..' + hostRect.right.toFixed(1) + ']');
          }
          if (rr.top < hostRect.top - 2.0 || rr.bottom > hostRect.bottom + 2.0) {
            errors.push(title + ': VERT CLIP/OVERFLOW ' + innerSels[si]);
          }
        }
      }

      // 3. Python SVG vs JS DOM size parity
      if (caseObj.svg) {
        var jsW = Math.round(hostRect.width / (caseObj.scale || 1));
        var jsH = Math.round(hostRect.height / (caseObj.scale || 1));
        if (Math.abs(jsW - caseObj.svg.w) > 4 || Math.abs(jsH - caseObj.svg.h) > 4) {
          warnings.push(title + ': JS(' + jsW + 'x' + jsH + ') vs SVG(' + caseObj.svg.w + 'x' + caseObj.svg.h + ') size delta');
        }
      }
    }

    window.renderAuditCards = function (cases) {
      var cards = document.querySelectorAll('.audit-card[data-idx]');
      for (var i = 0; i < cards.length; i += 1) {
        var idx = parseInt(cards[i].getAttribute('data-idx'), 10);
        var c = cases[idx];
        var host = cards[i].querySelector('.tm-render-target');
        var p = c.payload;
        var u = U.readUi(p.ui);
        if (p.mode === 'h' || Number(u.preset) === 0 || Number(u.preset) === 2) {
          host.setAttribute('data-v3-host', '1');
          host.style.display = 'block';
          var r = new ns.V3Renderer(host);
          var dims = r.render(p, u, p.mode === 'h', c.scale);
          var noteEl = cards[i].querySelector('.audit-note');
          if (noteEl && !noteEl.textContent) {
            noteEl.textContent = dims[0] + 'x' + dims[1] + ' @' + Number(c.scale).toFixed(2) + (c.svg ? (' | svg ' + c.svg.w + 'x' + c.svg.h) : '');
          }
        } else {
          host.setAttribute('data-panel-host', '1');
          host.style.display = 'block';
          var cdom = makePanelDom(host);
          var cr = new ns.ClassicRenderer(cdom, function () { return c.scale || 1; });
          cr.render(p, u, function () {}, c.scale);
          cr.layoutAll();
          var cNote = cards[i].querySelector('.audit-note');
          if (cNote && !cNote.textContent) {
            cNote.textContent = (cdom.panel.style.width || '220px') + 'x' + (cdom.panel.style.height || '72px') + ' @' + Number(c.scale || 1).toFixed(2) + ' (native px)';
          }
        }
      }

      var finalized = false;
      function finalizeAudit() {
        if (finalized) return;
        finalized = true;
        var errors = [], warnings = [], loadedFonts = [];
        if (document.fonts && document.fonts.forEach) {
          document.fonts.forEach(function (f) {
            if (f.status === 'loaded' && loadedFonts.indexOf(f.family) < 0) {
              loadedFonts.push(f.family);
            } else if (f.status === 'error') {
              errors.push('Font load error: ' + f.family);
            }
          });
        }
        var v3Cards = document.querySelectorAll('.audit-card[data-idx]');
        for (var k = 0; k < v3Cards.length; k += 1) {
          var ci = parseInt(v3Cards[k].getAttribute('data-idx'), 10);
          var host = v3Cards[k].querySelector('[data-v3-host="1"]');
          if (host) {
            var prevErrs = errors.length;
            auditV3Card(v3Cards[k], host, cases[ci], errors, warnings);
            if (errors.length > prevErrs) {
              v3Cards[k].classList.add('bad');
              var n = v3Cards[k].querySelector('.audit-note');
              if (n) {
                n.classList.add('err');
                n.textContent += ' | ' + errors[errors.length - 1];
              }
            }
          }
        }
        var res = document.getElementById('audit-result');
        if (res) {
          res.textContent = JSON.stringify({
            errors: errors,
            warnings: warnings,
            loadedFonts: loadedFonts,
            scrollHeight: Math.ceil(document.documentElement.scrollHeight),
            scrollWidth: Math.ceil(document.documentElement.scrollWidth)
          });
        }
        window.__AUDIT_DONE__ = true;
      }

      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function () {
          setTimeout(finalizeAudit, 80);
        });
      }
      setTimeout(finalizeAudit, 600);
    };
  }());
  </script>
"""


def _write_panel_sheet(filename, title, cases, has_svg_compare=False):
    cards_html = []
    for idx, c in enumerate(cases):
        if has_svg_compare and c.get('svg') and idx >= len(cases) - 2:
            s = c['svg']
            stage_inner = (
                u'<div class="audit-pair">'
                u'<div class="audit-pair-col"><div class="audit-sublbl">Gameface DOM (JS)</div><div class="tm-render-target"></div></div>'
                u'<div class="audit-pair-col"><div class="audit-sublbl">Mod Menu Preview (Python SVG)</div>'
                u'<img src="%s" width="%d" height="%d" style="display:block;" /></div>'
                u'</div>'
            ) % (_esc(s['uri']), s['w'], s['h'])
        else:
            stage_inner = u'<div class="tm-render-target"></div>'
        cards_html.append(
            u'<div class="audit-card" data-idx="%d">'
            u'<div class="audit-title">%s</div>'
            u'<div class="audit-stage">%s</div>'
            u'<div class="audit-note"></div>'
            u'</div>' % (idx, _esc(c['title']), stage_inner)
        )

    html = u"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>%s</title>
  <link rel="stylesheet" href="ThreeMarks_audit.css">
</head>
<body>
  <div class="audit-sheet">
    <div class="audit-head">
      <h1>%s</h1>
      <div class="meta">dm.threemarks %s | %d scenarios</div>
    </div>
    <div class="audit-grid">%s</div>
  </div>
  <script id="audit-result" type="application/json">{}</script>
  %s
  %s
  <script>
    window.renderAuditCards(%s);
  </script>
</body>
</html>""" % (
        _esc(title), _esc(title), _esc(MOD_VERSION), len(cases),
        u'\n'.join(cards_html),
        _js_scripts_block(),
        _panel_render_and_audit_js(),
        json.dumps([{'title': c['title'], 'payload': c['payload'], 'scale': c['scale'], 'svg': c.get('svg')} for c in cases], ensure_ascii=False),
    )
    out_path = os.path.join(OUT_DIR, filename)
    with open(out_path, 'wb') as f:
        f.write(html.encode('utf-8'))
    return out_path


def _write_fonts_sheet():
    cases = []
    rows_html = []
    for fnt in range(8):
        b_idx = len(cases)
        cases.append(_make_battle_case(
            u'Battle %s' % FONT_NAMES[fnt],
            cfg_overrides={'v3Font': fnt, 'v3TempoShow': 0},
            sample={'shown_pct': 84.95, 'bar_pct': 84.95, 'delta': -0.18, 'dmg': 3120, 'hold_dmg': 2950, 'radio': 672, 'track': 140, 'alt_down': True},
            scale=1.0,
        ))
        h_idx = len(cases)
        cases.append(_make_hangar_case(
            u'Hangar %s' % FONT_NAMES[fnt],
            cfg_overrides={'vhFont': fnt, 'vhScale': 1.0},
            sample={'rating': 84.02, 'ema': 3450, 'marks': 2, 't65': 1950, 't85': 2850, 't95': 4150, 't100': 10450},
            scale=1.0,
        ))
        zoom_cls = u'tm-font-%d' % fnt
        rows_html.append(
            u'<div class="font-row">'
            u'<div class="font-name">%s<div class="font-zoom-meta">v3Font=%d</div></div>'
            u'<div class="audit-card" data-idx="%d"><div class="audit-stage"><div class="tm-render-target"></div></div><div class="audit-note"></div></div>'
            u'<div class="audit-card" data-idx="%d"><div class="audit-stage"><div class="tm-render-target"></div></div><div class="audit-note"></div></div>'
            u'<div class="font-zoom">'
            u'<div class="%s" data-v3-host="1" style="display:block;position:relative;width:auto;height:auto;">'
            u'<span class="font-zoom-line" style="font-family:inherit;">84.95%% &nbsp; 3.07%% &nbsp; 100.00%% &nbsp; --.--%%</span>'
            u'</div>'
            u'<div class="font-zoom-meta">Glyph clip check (font-size: 32px, line-height: 1.22)</div>'
            u'</div>'
            u'</div>' % (_esc(FONT_NAMES[fnt]), fnt, b_idx, h_idx, zoom_cls)
        )

    html = u"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Fonts Matrix (0..7) + Clipping Check</title>
  <link rel="stylesheet" href="ThreeMarks_audit.css">
</head>
<body>
  <div class="audit-sheet">
    <div class="audit-head">
      <h1>Fonts Matrix (v3Font 0..7) — Battle + Hangar + 2.5x Glyph Clip Check</h1>
      <div class="meta">dm.threemarks %s | 8 font families</div>
    </div>
    %s
  </div>
  <script id="audit-result" type="application/json">{}</script>
  %s
  %s
  <script>
    window.renderAuditCards(%s);
  </script>
</body>
</html>""" % (
        _esc(MOD_VERSION),
        u'\n'.join(rows_html),
        _js_scripts_block(),
        _panel_render_and_audit_js(),
        json.dumps([{'title': c['title'], 'payload': c['payload'], 'scale': c['scale'], 'svg': c.get('svg')} for c in cases], ensure_ascii=False),
    )
    out_path = os.path.join(OUT_DIR, '02_fonts_matrix.html')
    with open(out_path, 'wb') as f:
        f.write(html.encode('utf-8'))
    return out_path


def _eval_cond(values, master_key, master_val, cond='=='):
    cur = values.get(master_key)
    if isinstance(master_val, (list, tuple)):
        if cond == '!=':
            return cur not in master_val
        return cur in master_val
    if cond == '==':
        return cur == master_val
    if cond == '!=':
        return cur != master_val
    try:
        a, b = float(cur), float(master_val)
        if cond == '>':
            return a > b
        if cond == '>=':
            return a >= b
        if cond == '<':
            return a < b
        if cond == '<=':
            return a <= b
    except Exception:
        pass
    return False


def _is_control_visible(ctl, values, override_section=None):
    v = dict(values)
    if override_section:
        v.update(override_section)
    if 'conditions' in ctl:
        logic = ctl.get('conditionsLogic', 'AND')
        results = [_eval_cond(v, c['masterVarName'], c['masterValue'], c.get('condition', '==')) for c in ctl['conditions']]
        return any(results) if logic == 'OR' else all(results)
    if 'masterVarName' in ctl:
        return _eval_cond(v, ctl['masterVarName'], ctl['masterValue'], ctl.get('condition', '=='))
    return True


def _control_section_index(ctl, sec_key):
    if 'conditions' in ctl:
        for c in ctl['conditions']:
            if c.get('masterVarName') == sec_key:
                return c.get('masterValue')
    if ctl.get('masterVarName') == sec_key:
        return ctl.get('masterValue')
    return None


def _render_ctl_html(ctl, values, visible=True):
    ctype = ctl.get('type', 'Label')
    var = ctl.get('varName', '')
    text = _u(ctl.get('text', ''))
    val = values.get(var, ctl.get('value'))
    indent = ' indent' if ctl.get('masterIndent') else ''
    cls = 'mm-ctl' + indent + ('' if visible else ' gated-hidden')
    if ctype == 'Label':
        return u'<div class="%s mm-lbl">%s</div>' % (cls, text)
    if ctype == 'CheckBox':
        on = ' checked' if bool(val) else ''
        return u'<div class="%s"><span class="mm-chk%s"></span><span class="mm-txt">%s</span></div>' % (cls, on, text)
    if ctype == 'Slider':
        try:
            disp = u'%.2f' % float(val)
        except Exception:
            disp = _u(val)
        return u'<div class="%s"><span class="mm-txt">%s</span><span class="mm-pill">%s</span></div>' % (cls, text, _esc(disp))
    if ctype == 'Dropdown':
        opts = ctl.get('options') or []
        try:
            idx = int(val)
        except Exception:
            idx = 0
        lbl = _u(opts[idx].get('label', idx)) if 0 <= idx < len(opts) else _u(val)
        return u'<div class="%s"><span class="mm-txt">%s</span><span class="mm-dd">%s &#9662;</span></div>' % (cls, text, _esc(lbl))
    if ctype == 'RadioButtonGroup':
        opts = ctl.get('options') or []
        try:
            cur_idx = int(val)
        except Exception:
            cur_idx = 0
        btns = []
        for idx, o in enumerate(opts):
            act = ' active' if idx == cur_idx else ''
            raw_lbl = _u(o.get('label', idx))
            if '<img' in raw_lbl:
                lbl_html = re.sub(r"img://gui/", u"../../package/res/gui/", raw_lbl)
            else:
                lbl_html = _esc(raw_lbl)
            btns.append(u'<span class="mm-rbtn%s" style="display:inline-flex;align-items:center;gap:4px;">%s</span>' % (act, lbl_html))
        inline_cls = ' inline' if ctl.get('inline') else ' stack'
        return u'<div class="%s mm-radio-wrap"><div class="mm-txt">%s</div><div class="mm-radios%s">%s</div></div>' % (cls, text, inline_cls, u''.join(btns))
    if ctype == 'ColorChoice':
        cval = _u(val or '#FFFFFF')
        return u'<div class="%s"><span class="mm-txt">%s</span><span class="mm-col"><span class="mm-swatch" style="background:%s;"></span>%s</span></div>' % (cls, text, _esc(cval), _esc(cval))
    if ctype == 'TextInput':
        return u'<div class="%s"><span class="mm-txt">%s</span><span class="mm-inp">%s</span></div>' % (cls, text, _esc(val or u''))
    if ctype == 'Button':
        btn = ctl.get('button') or {}
        btxt = ctl.get('btnText') or btn.get('text') or var
        return u'<div class="%s"><span class="mm-txt">%s</span><span class="mm-btn">%s</span></div>' % (cls, text, _esc(btxt))
    if ctype == 'Image':
        src = ctl.get('source', '')
        w = ctl.get('width', 240)
        h = ctl.get('height', 120)
        return u'<div class="%s mm-imgbox"><div class="mm-txt">%s (%dx%d)</div><div class="mm-preview-frame"><img src="%s" width="%d" height="%d"/></div></div>' % (cls, text, w, h, _esc(src), w, h)
    return u'<div class="%s"><span class="mm-txt">%s (%s)</span></div>' % (cls, _esc(ctype), _esc(text))


def _menu_css():
    return u"""
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0d1117;
  color: #dfe6ee;
  font-family: "Segoe UI", Tahoma, Arial, sans-serif;
  font-size: 12px;
  padding: 16px 20px 24px 20px;
}
.mm-shell {
  width: 1320px;
  background: linear-gradient(180deg, #1b1e23 0%, #14171b 100%);
  border: 1px solid #353b44;
  border-radius: 6px;
  padding: 14px 18px;
}
.mm-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid #2d333b;
  padding-bottom: 8px;
  margin-bottom: 10px;
}
.mm-title { font-size: 16px; font-weight: 700; color: #f2f5f8; }
.mm-ver { font-size: 11px; color: #9aa3ae; }
.mm-tabs { display: flex; gap: 16px; margin-bottom: 12px; border-bottom: 1px solid #2d333b; padding-bottom: 6px; }
.mm-tab { font-size: 13px; color: #8c95a0; padding: 2px 4px; }
.mm-tab.active { color: #f5a623; font-weight: 700; border-bottom: 2px solid #f5a623; }
.mm-cols { display: flex; gap: 20px; align-items: flex-start; }
.mm-col1 { flex: 1 1 680px; }
.mm-col2 { flex: 0 0 580px; background: rgba(0,0,0,0.22); border: 1px solid #2b3038; border-radius: 6px; padding: 12px; }
.mm-sec {
  background: rgba(255,255,255,0.025);
  border: 1px solid #2c313a;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.mm-sec-h {
  font-size: 12px; font-weight: 700; color: #f5a623;
  margin-bottom: 8px; display: flex; justify-content: space-between;
}
.mm-sec-h .cnt { font-weight: 400; color: #8c95a0; font-size: 11px; }
.mm-ctl {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  gap: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.mm-ctl.indent { padding-left: 18px; }
.mm-ctl.gated-hidden { opacity: 0.42; }
.mm-ctl.gated-hidden .mm-txt::after { content: " [gated]"; color: #8c95a0; font-size: 10px; }
.mm-lbl { color: #d5dce4; padding-top: 4px; border-bottom: none; display: block; }
.mm-txt { color: #cfd6df; flex: 1 1 auto; }
.mm-chk {
  width: 14px; height: 14px; border: 1px solid #6b7480; border-radius: 2px;
  background: #20242a; display: inline-block; flex: 0 0 14px;
}
.mm-chk.checked { background: #f5a623; border-color: #f5a623; }
.mm-pill, .mm-dd, .mm-inp, .mm-btn, .mm-col {
  background: #22272e; border: 1px solid #3c434d; border-radius: 3px;
  padding: 2px 8px; color: #eef2f6; font-size: 11px; white-space: nowrap;
}
.mm-btn { background: #2d333c; font-weight: 600; }
.mm-col { display: inline-flex; align-items: center; gap: 6px; font-family: Consolas, monospace; }
.mm-swatch { width: 12px; height: 12px; border-radius: 2px; border: 1px solid rgba(255,255,255,0.3); display: inline-block; }
.mm-radio-wrap { display: block; }
.mm-radios.inline { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; }
.mm-radios.stack { display: flex; flex-direction: column; gap: 4px; margin-top: 5px; }
.mm-rbtn {
  background: #20252c; border: 1px solid #39404a; border-radius: 3px;
  padding: 3px 8px; font-size: 11px; color: #b7c0cb;
}
.mm-rbtn.active { background: #4b391a; border-color: #f5a623; color: #fff; font-weight: 600; }
.mm-imgbox { display: block; border-bottom: none; margin-bottom: 8px; }
.mm-preview-frame {
  margin-top: 6px;
  background: radial-gradient(circle at 50% 45%, #2b3440, #161b22);
  border: 1px solid #363d47;
  border-radius: 4px;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
}
.mm-gallery {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 12px;
  border-top: 1px solid #2d333b;
  padding-top: 10px;
}
.mm-gal-item {
  background: #171c23; border: 1px solid #2e343e; border-radius: 4px; padding: 6px; text-align: center;
}
.mm-gal-lbl { font-size: 10px; color: #9aa3ae; margin-bottom: 4px; }
"""


def _write_menu_sheet(filename, active_tab_title, cfg_overrides=None, show_v3=True, target=0):
    cfg = ConfigStore(dict(DEFAULT_CONFIG, **(cfg_overrides or {})))
    svg = _make_svg(cfg)
    preview = MenuPreviewRenderer(cfg, svg)
    preview.state['target'] = target
    converter = MenuValueConverter(cfg)
    builder = MenuTemplateBuilder(converter, preview)
    tpl_api = StrictAslainTemplatesV2()
    tpl = builder.build(tpl_api, (2, 1, 15), show_v3=show_v3)
    values = converter.current_values(preview.state)

    col1_tabs = dict((t['title'], t['items']) for t in tpl['column1'])
    col2_tabs = dict((t['title'], t['items']) for t in tpl['column2'])
    items1 = col1_tabs[active_tab_title]
    items2 = col2_tabs[active_tab_title]

    sec_key = 'hangarSection' if active_tab_title == u'Ангар' else 'battleSection'
    sec_names = HANGAR_SECTIONS if active_tab_title == u'Ангар' else (BATTLE_SECTIONS_V3 if show_v3 else BATTLE_SECTIONS_LEGACY)

    nav_html = []
    sec_groups = dict((i, []) for i in range(len(sec_names)))
    for ctl in items1:
        sidx = _control_section_index(ctl, sec_key)
        if sidx is None:
            nav_html.append(_render_ctl_html(ctl, values, _is_control_visible(ctl, values)))
        else:
            sec_groups.setdefault(int(sidx), []).append(ctl)

    secs_html = []
    for sidx, sname in enumerate(sec_names):
        sec_vals = dict(values)
        sec_vals[sec_key] = sidx
        group = sec_groups.get(sidx, [])
        vis_count = 0
        ctl_rows = []
        for ctl in group:
            vis = _is_control_visible(ctl, sec_vals)
            if vis:
                vis_count += 1
            ctl_rows.append(_render_ctl_html(ctl, sec_vals, visible=vis))
        secs_html.append(
            u'<div class="mm-sec"><div class="mm-sec-h"><span>%s</span><span class="cnt">%d/%d visible</span></div>%s</div>'
            % (_esc(sname), vis_count, len(group), u''.join(ctl_rows))
        )

    col2_html = []
    for ctl in items2:
        col2_html.append(_render_ctl_html(ctl, values, visible=_is_control_visible(ctl, values)))

    # Add 4-state preview SVG gallery on column 2 so we verify plus/minus/zero/big SVGs together
    gal_html = []
    old_st = preview.state['state']
    for st in PREVIEW_ORDER:
        preview.state['state'] = st
        uri, _sw, _sh, pw, ph = preview.render(target=target)
        gal_html.append(
            u'<div class="mm-gal-item"><div class="mm-gal-lbl">%s (%dx%d)</div><img src="%s" width="%d" height="%d"/></div>'
            % (_esc(st), pw, ph, _esc(uri), pw, ph)
        )
    preview.state['state'] = old_st

    tabs_bar = u''.join(
        u'<span class="mm-tab%s">%s</span>' % (' active' if t['title'] == active_tab_title else '', _esc(t['title']))
        for t in tpl['column1']
    )
    html = u"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Mod Menu — %s (%s)</title>
  <style>%s</style>
</head>
<body>
  <div class="mm-shell">
    <div class="mm-top">
      <div class="mm-title">%s</div>
      <div class="mm-ver">v%s | preset=%s</div>
    </div>
    <div class="mm-tabs">%s</div>
    <div class="mm-cols">
      <div class="mm-col1">%s%s</div>
      <div class="mm-col2">%s<div class="mm-gallery">%s</div></div>
    </div>
  </div>
  <script id="audit-result" type="application/json">{}</script>
  <script>
    setTimeout(function () {
      var res = document.getElementById('audit-result');
      if (res) {
        res.textContent = JSON.stringify({
          errors: [], warnings: [], loadedFonts: [],
          scrollHeight: Math.ceil(document.documentElement.scrollHeight),
          scrollWidth: Math.ceil(document.documentElement.scrollWidth)
        });
      }
    }, 50);
  </script>
</body>
</html>""" % (
        _esc(active_tab_title), 'V3' if show_v3 else 'Korben',
        _menu_css(),
        _esc(tpl['modDisplayName']), _esc(MOD_VERSION), 'KiBeRsPoRt' if show_v3 else 'Korben',
        tabs_bar,
        u''.join(nav_html), u''.join(secs_html),
        u''.join(col2_html), u''.join(gal_html),
    )
    out_path = os.path.join(OUT_DIR, filename)
    with open(out_path, 'wb') as f:
        f.write(html.encode('utf-8'))
    return out_path, tpl, values


class _MemConfigSync(object):
    def __init__(self):
        self.saves = 0

    def save_current(self):
        self.saves += 1


class _MemLogger(object):
    def __init__(self):
        self.errors = []

    def info(self, _msg):
        pass

    def once(self, _key, _msg):
        pass

    def error(self, msg):
        self.errors.append(msg)


def _audit_mod_menu():
    errors = []
    warnings = []
    checks = []

    for label, preset, show_v3 in (('V3 KiBeRsPoRt', 0, True), ('Korben Classic', 1, False)):
        cfg = ConfigStore(dict(DEFAULT_CONFIG, battlePreset=preset))
        svg = _make_svg(cfg)
        preview = MenuPreviewRenderer(cfg, svg)
        conv = MenuValueConverter(cfg)
        builder = MenuTemplateBuilder(conv, preview)
        tpl = builder.build(StrictAslainTemplatesV2(), (2, 1, 15), show_v3=show_v3)
        values = conv.current_values(preview.state)

        # Collect all varNames
        col1_tabs = dict((t['title'], t['items']) for t in tpl['column1'])
        col2_tabs = dict((t['title'], t['items']) for t in tpl['column2'])
        all_vars = set()
        for tname, items in list(col1_tabs.items()) + list(col2_tabs.items()):
            seen_tab = set()
            for ctl in items:
                vn = ctl.get('varName')
                if vn:
                    if vn in seen_tab:
                        errors.append('[%s/%s] duplicate varName=%s' % (label, tname, vn))
                    seen_tab.add(vn)
                    all_vars.add(vn)

        # Validate masterVarName targets & non-empty subsections
        for tname, items in list(col1_tabs.items()) + list(col2_tabs.items()):
            for ctl in items:
                if 'masterVarName' in ctl and ctl['masterVarName'] not in all_vars:
                    errors.append('[%s/%s] broken masterVarName=%s' % (label, tname, ctl['masterVarName']))
                for c in ctl.get('conditions', ()):
                    if c.get('masterVarName') not in all_vars:
                        errors.append('[%s/%s] broken condition masterVarName=%s' % (label, tname, c.get('masterVarName')))
                for opt in ctl.get('options', ()):
                    for img_ref in re.findall(r"img://([^'\"\s>]+)", _u(opt.get('label', u''))):
                        asset_path = os.path.join(REPO_ROOT, 'package', 'res', img_ref.replace('/', os.sep))
                        if not os.path.isfile(asset_path):
                            errors.append('[%s/%s] missing menu option asset: %s' % (label, tname, asset_path))

        sec_specs = [
            (u'Боевая панель', 'battleSection', BATTLE_SECTIONS_V3 if show_v3 else BATTLE_SECTIONS_LEGACY),
            (u'Ангар', 'hangarSection', HANGAR_SECTIONS),
        ]
        for tname, sec_key, sec_names in sec_specs:
            items = col1_tabs.get(tname, ())
            for sidx, sname in enumerate(sec_names):
                sv = dict(values)
                sv[sec_key] = sidx
                vis_items = [c for c in items if _control_section_index(c, sec_key) == sidx and _is_control_visible(c, sv)]
                if not vis_items:
                    errors.append('[%s/%s] empty subsection "%s" (%d)' % (label, tname, sname, sidx))
                else:
                    checks.append('%s | %s > %s: %d visible controls' % (label, tname, sname, len(vis_items)))

        # Validate SVG preview images
        for tname, var_name in ((u'Боевая панель', 'marksLivePreview'), (u'Ангар', 'marksLivePreviewHangar')):
            imgs = [c for c in col2_tabs.get(tname, ()) if c.get('varName') == var_name]
            if not imgs:
                errors.append('[%s/%s] missing preview Image %s' % (label, tname, var_name))
            else:
                src = imgs[0].get('source', '')
                if not src.startswith('data:image/svg+xml;base64,'):
                    errors.append('[%s/%s] invalid SVG URI on %s' % (label, tname, var_name))
                else:
                    xml = base64.b64decode(src.split(',', 1)[1]).decode('utf-8')
                    if '<svg' not in xml or imgs[0].get('width', 0) <= 0 or imgs[0].get('height', 0) <= 0:
                        errors.append('[%s/%s] invalid decoded SVG content on %s' % (label, tname, var_name))

    # Cancel-without-saving desync simulation (Киберспорт -> Корбен -> Close without Save -> Reopen)
    cfg = ConfigStore(dict(DEFAULT_CONFIG, battlePreset=0))
    sync = _MemConfigSync()
    logger = _MemLogger()
    svg = _make_svg(cfg)
    preview = MenuPreviewRenderer(cfg, svg)
    conv = MenuValueConverter(cfg)
    builder = MenuTemplateBuilder(conv, preview)
    adapter = AslainMenuAdapter(cfg, sync, preview, builder, logger)

    class _CancelSimApi(StrictAslainApiV2):
        def getModSettings(self, _linkage, _template):
            return dict(MenuValueConverter.default_values(), battlePanelVariant=0, battlePreset=0)

    api = _CancelSimApi()
    tpl = StrictAslainTemplatesV2()
    # Wire minimal sys.modules stub for gui.aslainMenu inside this check only
    prev_gui = sys.modules.get('gui')
    prev_aslain = sys.modules.get('gui.aslainMenu')

    class _FakePkg(object):
        pass

    gui_mod = _FakePkg()
    aslain_mod = _FakePkg()
    aslain_mod.g_modsSettingsApi = api
    aslain_mod.templates = tpl
    gui_mod.aslainMenu = aslain_mod
    sys.modules['gui'] = gui_mod
    sys.modules['gui.aslainMenu'] = aslain_mod
    try:
        if not adapter.register():
            errors.append('AslainMenuAdapter.register() failed during cancel simulation')
        else:
            api.onWindowOpened.emit()
            api.live_cb(MENU_LINKAGE, {'battlePanelVariant': 1})
            if adapter._tpl_v3:
                errors.append('Live switch to Korben did not switch _tpl_v3 to False')
            api.onWindowClosed.emit()
            api.onWindowOpened.emit()
            if cfg.integer('battlePreset', 0, 1) != 0:
                errors.append('Cancel without saving did not revert battlePreset to 0')
            if not adapter._tpl_v3:
                errors.append('Cancel without saving did not restore V3 template (_tpl_v3=False after reopen)')
            reg_col1 = dict((t['title'], t['items']) for t in api.templates[MENU_LINKAGE]['column1'])
            b_nav = [c for c in reg_col1[u'Боевая панель'] if c.get('varName') == 'battleSection']
            if not b_nav or len(b_nav[0].get('options', ())) != 5:
                errors.append('After cancel & reopen, battleSection does not have 5 V3 sections')
            if logger.errors:
                errors.extend([u'Adapter error: %s' % _u(e) for e in logger.errors])
            checks.append(u'Cancel-without-saving state machine: Киберспорт -> Корбен -> Close -> Reopen OK')
    finally:
        if prev_gui is not None:
            sys.modules['gui'] = prev_gui
        else:
            sys.modules.pop('gui', None)
        if prev_aslain is not None:
            sys.modules['gui.aslainMenu'] = prev_aslain
        else:
            sys.modules.pop('gui.aslainMenu', None)

    return {'errors': errors, 'warnings': warnings, 'checks': checks}


class _QuietHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class _AuditHttpServer(object):
    def __init__(self, root_dir):
        self._root = root_dir
        self._server = None
        self._thread = None
        self.port = None

    def __enter__(self):
        root = self._root

        class _RootedHandler(_QuietHandler):
            def translate_path(self, path):
                path = path.split('?', 1)[0].split('#', 1)[0]
                parts = [p for p in path.split('/') if p and p not in ('.', '..')]
                return os.path.join(root, *parts)

        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        self._server = SocketServer.ThreadingTCPServer(('127.0.0.1', 0), _RootedHandler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        return self

    def __exit__(self, *args):
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass


def _run_chrome(args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError('Browser exited with %d: %s' % (proc.returncode, err))
    return out


def _capture_page(browser_exe, base_url, html_rel, png_name, width, min_height=760):
    url = base_url + html_rel
    user_data = tempfile.mkdtemp(prefix='tm_chrome_')
    try:
        common = [
            browser_exe,
            '--headless=new',
            '--disable-gpu',
            '--no-first-run',
            '--no-default-browser-check',
            '--user-data-dir=' + user_data,
            '--force-device-scale-factor=1',
            '--hide-scrollbars',
            '--virtual-time-budget=3500',
        ]
        # Pass 1: inspect DOM geometry + full scrollHeight
        dom_out = _run_chrome(common + ['--window-size=%d,%d' % (width, min_height), '--dump-dom', url])
        m = re.search(r'<script id="audit-result" type="application/json">(.*?)</script>', dom_out, re.DOTALL)
        audit_data = {}
        if m:
            try:
                audit_data = json.loads(m.group(1).strip() or '{}')
            except Exception:
                audit_data = {'errors': ['Failed to parse audit-result JSON']}

        scroll_h = int(audit_data.get('scrollHeight', 0) or 0)
        cap_h = max(min_height, min(4200, scroll_h + 24 if scroll_h > 0 else 1800))

        # Pass 2: crisp screenshot at exact computed height
        png_path = os.path.join(OUT_DIR, png_name)
        _run_chrome(common + ['--window-size=%d,%d' % (width, cap_h), '--screenshot=' + png_path, url])
        return png_path, cap_h, audit_data
    finally:
        shutil.rmtree(user_data, ignore_errors=True)


def _write_index_html(sheets, menu_audit, panel_errors, panel_warnings):
    cards = []
    for rel_html, png_name, caption in sheets:
        cards.append(
            u'<div class="idx-card">'
            u'<div class="idx-bar"><a href="%s">%s</a><span>%s</span></div>'
            u'<a href="%s"><img src="%s" alt="%s"/></a>'
            u'</div>' % (_esc(rel_html), _esc(caption), _esc(png_name), _esc(rel_html), _esc(png_name), _esc(caption))
        )
    all_err = panel_errors + menu_audit['errors']
    status_cls = 'ok' if not all_err else 'fail'
    status_txt = 'PASS (0 errors)' if not all_err else ('FAIL (%d errors)' % len(all_err))
    diag_items = (
        u''.join(u'<li class="e">%s</li>' % _esc(e) for e in all_err) +
        u''.join(u'<li class="w">%s</li>' % _esc(w) for w in (panel_warnings + menu_audit['warnings'])) +
        u''.join(u'<li class="c">%s</li>' % _esc(c) for c in menu_audit['checks'])
    )
    html = u"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>dm.threemarks Visual Render & Audit Dashboard</title>
  <style>
    body { background:#0d1117; color:#e6edf3; font-family:"Segoe UI",Tahoma,Arial,sans-serif; margin:0; padding:20px 26px; }
    h1 { font-size:20px; margin:0 0 6px 0; }
    .sub { color:#8b949e; font-size:13px; margin-bottom:16px; }
    .badge { display:inline-block; padding:3px 10px; border-radius:4px; font-weight:700; font-size:12px; margin-left:10px; }
    .badge.ok { background:#1f4d2e; color:#86ef6a; border:1px solid #3c8c53; }
    .badge.fail { background:#541d22; color:#ff8080; border:1px solid #b53d44; }
    .diag { background:#161b22; border:1px solid #30363d; border-radius:6px; padding:12px 16px; margin-bottom:20px; }
    .diag ul { margin:6px 0 0 18px; padding:0; font-size:12px; line-height:1.55; }
    .diag li.e { color:#ff8080; font-weight:600; }
    .diag li.w { color:#f0c674; }
    .diag li.c { color:#9ecbff; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(560px, 1fr)); gap:16px; }
    .idx-card { background:#161b22; border:1px solid #30363d; border-radius:8px; overflow:hidden; }
    .idx-bar { display:flex; justify-content:space-between; padding:10px 14px; border-bottom:1px solid #30363d; font-size:13px; }
    .idx-bar a { color:#58a6ff; font-weight:700; text-decoration:none; }
    .idx-bar span { color:#8b949e; font-family:Consolas,monospace; font-size:11px; }
    .idx-card img { width:100%%; display:block; }
  </style>
</head>
<body>
  <h1>dm.threemarks Visual UI & Mod Menu Audit <span class="badge %s">%s</span></h1>
  <div class="sub">Version: %s | Generated in dist/ui_audit/ | Real Gameface CSS/JS + Python V3SvgRenderer + Aslain Menu Simulator</div>
  <div class="diag">
    <strong>Automated Audit Checks</strong>
    <ul>%s</ul>
  </div>
  <div class="grid">%s</div>
</body>
</html>""" % (status_cls, status_txt, _esc(MOD_VERSION), diag_items, u'\n'.join(cards))
    idx_path = os.path.join(OUT_DIR, 'index.html')
    with open(idx_path, 'wb') as f:
        f.write(html.encode('utf-8'))
    return idx_path


def _build_battle_cases():
    return [
        _make_battle_case(u'1. Default Plus (85.50%)', sample={'shown_pct': 85.50, 'bar_pct': 85.50, 'delta': 0.34, 'dmg': 4233, 'hold_dmg': 3537, 'marks': 2}),
        _make_battle_case(u'2. Minus (84.95%)', sample={'shown_pct': 84.95, 'bar_pct': 84.95, 'delta': -0.18, 'dmg': 1420, 'hold_dmg': 2320, 'marks': 1}),
        _make_battle_case(u'3. Zero Band (85.01%)', sample={'shown_pct': 85.01, 'bar_pct': 85.01, 'delta': 0.01, 'dmg': 2890, 'hold_dmg': 2890, 'marks': 2}),
        _make_battle_case(u'4. Big Plus (95.12%)', sample={'shown_pct': 95.12, 'bar_pct': 95.12, 'delta': 1.42, 'dmg': 6820, 'hold_dmg': 3750, 'marks': 3, 'big': True}),
        _make_battle_case(u'5. First Battle (0 -> 3.24%)', sample={'shown_pct': 3.24, 'bar_pct': 3.24, 'delta': 3.24, 'dmg': 51, 'hold_dmg': 1220, 'marks': 0}),
        _make_battle_case(u'6. No Rating (--.--%)', sample={'shown_pct': 0.0, 'bar_pct': 0.0, 'delta': None, 'dmg': 0, 'hold_dmg': 0, 'marks': 0, 'has_rating': False}),
        _make_battle_case(u'7. 100.00% Three Marks', sample={'shown_pct': 100.0, 'bar_pct': 100.0, 'delta': 0.45, 'dmg': 7210, 'hold_dmg': 4150, 'marks': 3}),
        _make_battle_case(u'8. Alt Pressed (Tempo + Assist)', cfg_overrides={'v3TempoShow': 1}, sample={'alt_down': True, 'radio': 672, 'track': 410}),
        _make_battle_case(u'9. Bar Style 1 (Segmented)', cfg_overrides={'v3BarStyle': 1}),
        _make_battle_case(u'10. Bar Style 3 (Wide Cyrillic Stress)', cfg_overrides={'v3BarStyle': 3, 'v3BarCustomText': u'ЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖЖ'}),
        _make_battle_case(u'11. Frame 3 (HUD) + Right Stars', cfg_overrides={'v3FrameStyle': 3, 'v3StarsPos': 3, 'v3StarsDivider': True}),
        _make_battle_case(u'12. Inline Header Stars (pos=4)', cfg_overrides={'v3StarsPos': 4, 'v3DamageLabel': 1, 'v3DamageCustomLabel': u'Мой очень длинный текст'}),
        _make_battle_case(u'13. Classic / Korben Preset', cfg_overrides={'battlePreset': 1, 'showSpot': True, 'showTrack': True}),
        _make_battle_case(u'14. JS DOM vs Python SVG (Plus)', sample={'shown_pct': 43.28, 'bar_pct': 43.28, 'delta': 1.25, 'dmg': 1850, 'hold_dmg': 1480, 'marks': 0, 't65': 2150, 't85': 2890, 't95': 3450, 't100': 3920, 'radio': 750, 'track': 0}),
        _make_battle_case(u'15. JS DOM vs Python SVG (Alt Big)', cfg_overrides={'v3TempoShow': 1}, sample={'shown_pct': 97.83, 'bar_pct': 97.83, 'delta': 4.65, 'dmg': 6820, 'hold_dmg': 3750, 'marks': 3, 'big': True, 'alt_down': True, 't65': 2150, 't85': 2890, 't95': 3450, 't100': 3920, 'radio': 1200, 'track': 2700, 'stun': 850, 'is_spg': True}),
    ]


def _build_hangar_cases():
    return [
        _make_hangar_case(u'1. Default Hangar (84.02%, m=2)'),
        _make_hangar_case(u'2. Zero Marks (30.20%, m=0)', sample={'rating': 30.20, 'ema': 307, 'marks': 0}),
        _make_hangar_case(u'3. One Mark (72.14%, m=1)', sample={'rating': 72.14, 'ema': 2150, 'marks': 1}),
        _make_hangar_case(u'4. Three Marks (96.40%, m=3)', sample={'rating': 96.40, 'ema': 3510, 'marks': 3}),
        _make_hangar_case(u'5. 100.00% Peak', sample={'rating': 100.00, 'ema': 4250, 'marks': 3}),
        _make_hangar_case(u'6. Pending / Loading (--.--%)', sample={'rating': 0.0, 'ema': 0, 'marks': 0, 'has_rating': False, 't65': 0, 't85': 0, 't95': 0, 't100': 0}),
        _make_hangar_case(u'7. 5-Digit Thresholds (12345)', sample={'rating': 91.20, 'ema': 10450, 'marks': 2, 't65': 6850, 't85': 9240, 't95': 10980, 't100': 12345}),
        _make_hangar_case(u'8. Bar Style 1 (Segmented)', cfg_overrides={'vhBarStyle': 1}),
        _make_hangar_case(u'9. Bar Style 3 (Custom Text)', cfg_overrides={'vhBarStyle': 3, 'vhBarCustomText': u'KIBERSPORT PRO'}),
        _make_hangar_case(u'10. Tektur Font + HUD Frame', cfg_overrides={'vhFont': 7, 'vhFrameStyle': 3}),
        _make_hangar_case(u'11. JS DOM vs Python SVG (Default)', sample={'rating': 70.64, 'ema': 2320, 'marks': 1, 't65': 2150, 't85': 2890, 't95': 3450, 't100': 3920}),
        _make_hangar_case(u'12. JS DOM vs Python SVG (Jura m=3)', cfg_overrides={'vhFont': 3, 'vhBarStyle': 1}, sample={'rating': 97.83, 'ema': 3750, 'marks': 3, 't65': 2150, 't85': 2890, 't95': 3450, 't100': 3920}),
    ]


def main():
    _ensure_dir(OUT_DIR)
    browser_exe = _find_browser()
    _build_audit_css()

    battle_cases = _build_battle_cases()
    hangar_cases = _build_hangar_cases()
    _write_panel_sheet('01_battle_states.html', u'Battle Panel States + Classic + JS vs SVG', battle_cases, has_svg_compare=True)
    _write_fonts_sheet()
    _write_panel_sheet('03_hangar_states.html', u'Hangar Panel States + JS vs SVG', hangar_cases, has_svg_compare=True)
    _write_menu_sheet('04_menu_battle_v3.html', u'Боевая панель', show_v3=True, target=0)
    _write_menu_sheet('05_menu_hangar.html', u'Ангар', show_v3=True, target=1)
    _write_menu_sheet('06_menu_korben.html', u'Боевая панель', cfg_overrides={'battlePreset': 1}, show_v3=False, target=0)

    menu_audit = _audit_mod_menu()

    capture_specs = [
        ('01_battle_states.html', '01_battle_states.png', 1360, u'Battle Panel States'),
        ('02_fonts_matrix.html', '02_fonts_matrix.png', 1360, u'Fonts Matrix (0..7)'),
        ('03_hangar_states.html', '03_hangar_states.png', 1360, u'Hangar Panel States'),
        ('04_menu_battle_v3.html', '04_menu_battle_v3.png', 1380, u'Mod Menu: Battle V3'),
        ('05_menu_hangar.html', '05_menu_hangar.png', 1380, u'Mod Menu: Hangar'),
        ('06_menu_korben.html', '06_menu_korben.png', 1380, u'Mod Menu: Korben'),
    ]

    panel_errors = []
    panel_warnings = []
    page_reports = {}
    with _AuditHttpServer(REPO_ROOT) as srv:
        base_url = 'http://127.0.0.1:%d/dist/ui_audit/' % srv.port
        for html_name, png_name, width, _cap in capture_specs:
            png_path, cap_h, data = _capture_page(browser_exe, base_url, html_name, png_name, width)
            errs = list(data.get('errors') or [])
            warns = list(data.get('warnings') or [])
            panel_errors.extend(errs)
            panel_warnings.extend(warns)
            page_reports[png_name] = {
                'png': png_path,
                'width': width,
                'height': cap_h,
                'loadedFonts': data.get('loadedFonts', []),
                'errors': errs,
                'warnings': warns,
            }

    idx_path = _write_index_html([(h, p, c) for h, p, _w, c in capture_specs], menu_audit, panel_errors, panel_warnings)

    report = {
        'version': MOD_VERSION,
        'browser': browser_exe,
        'index': idx_path,
        'pages': page_reports,
        'menuAudit': menu_audit,
        'totalErrors': len(panel_errors) + len(menu_audit['errors']),
        'totalWarnings': len(panel_warnings) + len(menu_audit['warnings']),
    }
    def _norm_json(obj):
        if isinstance(obj, str):
            return obj.decode('utf-8', 'replace')
        if isinstance(obj, list):
            return [_norm_json(x) for x in obj]
        if isinstance(obj, dict):
            return dict((_norm_json(k), _norm_json(v)) for k, v in obj.items())
        return obj

    report_path = os.path.join(OUT_DIR, 'report.json')
    with open(report_path, 'wb') as f:
        f.write(json.dumps(_norm_json(report), indent=2, ensure_ascii=False).encode('utf-8'))

    print('============================================================')
    print('  dm.threemarks Visual Render & Audit (%s)' % MOD_VERSION)
    print('  Browser : %s' % browser_exe)
    print('  Dashboard: %s' % idx_path)
    print('  Report   : %s' % report_path)
    print('============================================================')
    for _h, png_name, _w, cap in capture_specs:
        pr = page_reports[png_name]
        st = 'PASS' if not pr['errors'] else 'FAIL'
        print('  [%s] %s (%dx%d) | fonts=%d | err=%d warn=%d' % (
            st, png_name, pr['width'], pr['height'], len(pr['loadedFonts']), len(pr['errors']), len(pr['warnings'])
        ))
    m_st = 'PASS' if not menu_audit['errors'] else 'FAIL'
    print('  [%s] Mod Menu Structure & Cancel State Machine (%d checks, err=%d)' % (
        m_st, len(menu_audit['checks']), len(menu_audit['errors'])
    ))
    for e in panel_errors + menu_audit['errors']:
        print('  [ERROR] %s' % _u(e).encode('utf-8'))
    for w in panel_warnings + menu_audit['warnings']:
        print('  [WARN]  %s' % _u(w).encode('utf-8'))

    return 1 if report['totalErrors'] > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
