# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dm_threemarks.adapters.presenters.battle_presenter import BattlePayloadPresenter
from dm_threemarks.adapters.presenters.hangar_presenter import HangarPayloadPresenter
from dm_threemarks.adapters.presenters.ui_config_serializer import UiConfigSerializer
from dm_threemarks.adapters.settings.in_game_settings import InGameSettingsController, SET_H
from dm_threemarks.adapters.v3.metrics import V3MetricsCalculator
from dm_threemarks.adapters.v3.svg_primitives import v3_assist_icon_svg
from dm_threemarks.application.config.validator import ConfigStore
from dm_threemarks.application.use_cases.config_sync import ConfigSyncService
from dm_threemarks.domain.value_objects.damage_report import DamageReport
from dm_threemarks.domain.value_objects.thresholds import Thresholds
from in_memory_adapters import FakeClock, FakeInputProvider, MemoryConfigRepository, MemoryLogger

NODE_PATHS = [
    r'C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe',
]


def _find_node():
    for candidate in NODE_PATHS:
        if os.path.isfile(candidate):
            return candidate
    return 'node'


class TestFrontendContract(unittest.TestCase):

    def test_python_payload_to_modular_js_dom_parity(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_dir = os.path.join(repo_root, 'package', 'res', 'gui', 'gameface', 'mods', 'dm', 'ThreeMarks')

        logger = MemoryLogger()
        clock = FakeClock()
        cfg_repo = MemoryConfigRepository()
        store = ConfigStore(logger=logger)
        cfg_sync = ConfigSyncService(cfg_repo, store, clock, logger)
        metrics = V3MetricsCalculator(store)
        ser = UiConfigSerializer(store)
        b_pres = BattlePayloadPresenter(store)
        h_pres = HangarPayloadPresenter()
        thr = Thresholds(2150, 2890, 3450, 3920)
        rep = DamageReport(damage=1100, radio=750, track=520, source='feedback')

        # 1. Battle V3 custom text fill (barStyle=3), without and with Alt
        store.replace_normalized({'barStyleVersion': 2, 'v3BarStyle': 3, 'v3BarCustomText': u'CYBER PRO', 'v3BarTextSize': 18, 'v3AssistShow': 1, 'v3TempoShow': 1, 'v3BgOpacity': 0.0})
        b_no_alt = b_pres.build_payload(70.64, 70.64, -1.15, 1620, 2320, 1, False, True, report=rep, thresholds=thr, alt_down=False)
        b_no_alt['mode'] = 'b'
        b_no_alt['ui'] = ser.ui_payload()
        b_no_alt_m = metrics.compute(store.raw_dict(), b_no_alt['v3d'], alt=False)
        b_no_alt['v3m'] = [b_no_alt_m['winW'], b_no_alt_m['winH']]

        b_alt = b_pres.build_payload(70.64, 70.64, -1.15, 1620, 2320, 1, False, True, report=rep, thresholds=thr, alt_down=True)
        b_alt['mode'] = 'b'
        b_alt['ui'] = ser.ui_payload()
        b_alt_m = metrics.compute(store.raw_dict(), b_alt['v3d'], alt=True)
        b_alt['v3m'] = [b_alt_m['winW'], b_alt_m['winH']]

        # 2. Korben preset (battlePreset=1, v3Font=4 Exo 2)
        store.replace_normalized({'battlePreset': 1, 'v3Font': 4})
        korben = b_pres.build_payload(64.12, 64.12, -1.15, 1120, 1980, 0, False, True, report=rep)
        korben['mode'] = 'b'
        korben['ui'] = ser.ui_payload()
        self.assertEqual(korben['ui']['v3'], {'fnt': 4})

        # 3. Hangar custom text fill (vhBarStyle=3) + compact 2x2 thresholds without '~'
        store.replace_normalized({'barStyleVersion': 2, 'vhBarStyle': 3, 'vhBarCustomText': u'THREE MARKS', 'vhBarTextSize': 16})
        hangar = h_pres.build_payload(43.28, 1850.0, 0, True, thr)
        hangar['mode'] = 'h'
        hangar['ui'] = ser.ui_payload()
        hangar_m = metrics.compute(store.to_v3_from_hangar(), hangar['v3d'], alt=False)
        hangar['v3m'] = [hangar_m['winW'], hangar_m['winH']]

        # 3b. Hangar scaled (vhScale=1.15, vhBgOpacity=0.26, fs=0)
        store.replace_normalized({'barStyleVersion': 2, 'vhScale': 1.15, 'vhBgOpacity': 0.26, 'vhFrameStyle': 0, 'vhBarStyle': 1})
        hangar_scaled = h_pres.build_payload(43.28, 1850.0, 0, True, thr)
        hangar_scaled['mode'] = 'h'
        hangar_scaled['ui'] = ser.ui_payload()
        hangar_scaled_m = metrics.compute(store.to_v3_from_hangar(), hangar_scaled['v3d'], alt=False)
        hangar_scaled['v3m'] = [hangar_scaled_m['winW'], hangar_scaled_m['winH']]

        # 3c. Font presets (v3Font=4 Exo 2, vhFont=5 Rubik) + equal assist tie + additive width without v3m
        store.replace_normalized({'barStyleVersion': 2, 'v3Font': 4, 'vhFont': 5, 'v3MinWidth': 40})
        rep_eq = DamageReport(damage=1100, radio=480, track=480, source='feedback')
        b_exo = b_pres.build_payload(70.64, 70.64, -1.15, 1620, 2320, 1, False, True, report=rep_eq, thresholds=thr, alt_down=False)
        b_exo['mode'] = 'b'
        b_exo['ui'] = ser.ui_payload()
        b_exo_m = metrics.compute(store.raw_dict(), b_exo['v3d'], alt=False)

        store.replace_normalized({'barStyleVersion': 2, 'v3Font': 4, 'vhFont': 5, 'v3MinWidth': 0})
        b_exo0_m = metrics.compute(store.raw_dict(), b_exo['v3d'], alt=False)

        h_rubik = h_pres.build_payload(43.28, 1850.0, 0, True, thr)
        h_rubik['mode'] = 'h'
        h_rubik['ui'] = ser.ui_payload()
        h_rubik_m = metrics.compute(store.to_v3_from_hangar(), h_rubik['v3d'], alt=False)

        # 3d. Long wide custom bar text auto-fits in both Python & JS without v3m
        store.replace_normalized({'barStyleVersion': 2, 'v3BarStyle': 3, 'v3BarCustomText': u'Ж' * 24, 'v3BarTextSize': 18, 'v3Font': 2})
        b_long = b_pres.build_payload(70.64, 70.64, 1.25, 1850, 1480, 0, False, True, report=rep, thresholds=thr, alt_down=False)
        b_long['mode'] = 'b'
        b_long['ui'] = ser.ui_payload()
        b_long_m = metrics.compute(store.raw_dict(), b_long['v3d'], alt=False)

        # 3e. Hangar no-rating vs 4-digit thresholds must share identical winW/winH
        store.replace_normalized({'barStyleVersion': 2, 'vhBarStyle': 0})
        h_nodata = h_pres.build_payload(0.0, 0.0, 0, False, None)
        h_nodata['mode'] = 'h'
        h_nodata['ui'] = ser.ui_payload()
        h_nodata_m = metrics.compute(store.to_v3_from_hangar(), h_nodata['v3d'], alt=False)
        h_nodata['v3m'] = [h_nodata_m['winW'], h_nodata_m['winH']]

        h_fourdigit = h_pres.build_payload(72.5, 2400.0, 1, True, thr)
        h_fourdigit['mode'] = 'h'
        h_fourdigit['ui'] = ser.ui_payload()
        h_fourdigit_m = metrics.compute(store.to_v3_from_hangar(), h_fourdigit['v3d'], alt=False)
        h_fourdigit['v3m'] = [h_fourdigit_m['winW'], h_fourdigit_m['winH']]

        # 3f. Battle damage row without label: right-aligned (dl=2) vs centered (dl=3)
        store.replace_normalized({'barStyleVersion': 2, 'v3DamageLabel': 2})
        b_dmg_right = b_pres.build_payload(70.64, 70.64, 1.25, 1850, 1480, 0, False, True, report=rep, thresholds=thr, alt_down=False)
        b_dmg_right['mode'] = 'b'
        b_dmg_right['ui'] = ser.ui_payload()
        b_dmg_right_m = metrics.compute(store.raw_dict(), b_dmg_right['v3d'], alt=False)
        b_dmg_right['v3m'] = [b_dmg_right_m['winW'], b_dmg_right_m['winH']]

        store.replace_normalized({'barStyleVersion': 2, 'v3DamageLabel': 3})
        b_dmg_center = b_pres.build_payload(70.64, 70.64, 1.25, 1850, 1480, 0, False, True, report=rep, thresholds=thr, alt_down=False)
        b_dmg_center['mode'] = 'b'
        b_dmg_center['ui'] = ser.ui_payload()
        b_dmg_center_m = metrics.compute(store.raw_dict(), b_dmg_center['v3d'], alt=False)
        b_dmg_center['v3m'] = [b_dmg_center_m['winW'], b_dmg_center_m['winH']]

        # 3g. Battle big damage color + neutral tempo thresholds + neutral zero delta icon
        store.replace_normalized({'barStyleVersion': 2, 'v3DamageDynColor': True, 'v3TempoShow': 0, 'v3DeltaIcon': 1})
        b_big_t = b_pres.build_payload(97.83, 97.83, 4.65, 6820, 3750, 3, True, True, big=True, report=rep, thresholds=thr, alt_down=False)
        b_big_t['mode'] = 'b'
        b_big_t['ui'] = ser.ui_payload()
        b_big_t_m = metrics.compute(store.raw_dict(), b_big_t['v3d'], alt=False)
        b_big_t['v3m'] = [b_big_t_m['winW'], b_big_t_m['winH']]

        b_zero = b_pres.build_payload(84.02, 84.02, 0.004, 2400, 2400, 1, False, True, report=rep, thresholds=thr, alt_down=False)
        b_zero['mode'] = 'b'
        b_zero['ui'] = ser.ui_payload()
        b_zero_m = metrics.compute(store.raw_dict(), b_zero['v3d'], alt=False)
        b_zero['v3m'] = [b_zero_m['winW'], b_zero_m['winH']]

        # 3h. Hangar permanent marks highlight (marks=2 with pct=84.02 highlights 65 & 85; marks=3 with pct=100 never highlights 100%)
        store.replace_normalized({'barStyleVersion': 2})
        h_marks2 = h_pres.build_payload(84.02, 4367.0, 2, True, thr)
        h_marks2['mode'] = 'h'
        h_marks2['ui'] = ser.ui_payload()
        h_marks2_m = metrics.compute(store.to_v3_from_hangar(), h_marks2['v3d'], alt=False)
        h_marks2['v3m'] = [h_marks2_m['winW'], h_marks2_m['winH']]

        store.replace_normalized({'barStyleVersion': 2, 'vhFont': 7})
        h_marks3 = h_pres.build_payload(100.0, 6200.0, 3, True, thr)
        h_marks3['mode'] = 'h'
        h_marks3['ui'] = ser.ui_payload()
        h_marks3_m = metrics.compute(store.to_v3_from_hangar(), h_marks3['v3d'], alt=False)
        h_marks3['v3m'] = [h_marks3_m['winW'], h_marks3_m['winH']]

        # 4. In-game settings payload
        set_ctrl = InGameSettingsController(store, cfg_sync, FakeInputProvider(), clock)
        settings_payload = {'mode': 's', 'set': set_ctrl.items, 'setH': SET_H, 'cfg': True, 'ui': ser.ui_payload()}

        fixture_bundle = {
            'uiDir': ui_dir,
            'battleNoAlt': b_no_alt,
            'battleAlt': b_alt,
            'korben': korben,
            'hangar': hangar,
            'hangarScaled': hangar_scaled,
            'battleFontExo': b_exo,
            'hangarFontRubik': h_rubik,
            'battleLongText': b_long,
            'hangarNoData': h_nodata,
            'hangarFourDigit': h_fourdigit,
            'battleDmgRight': b_dmg_right,
            'battleDmgCenter': b_dmg_center,
            'battleBigTempoDone': b_big_t,
            'battleZero': b_zero,
            'hangarMarks2': h_marks2,
            'hangarMarks3': h_marks3,
            'settings': settings_payload,
            'expected': {
                'battleWinW': b_no_alt_m['winW'],
                'hangarWinW': hangar_m['winW'],
                'hangarWinH': hangar_m['winH'],
                'hangarScaledWinW': hangar_scaled_m['winW'],
                'hangarScaledWinH': hangar_scaled_m['winH'],
                'exoWinW': b_exo_m['winW'],
                'exo0WinW': b_exo0_m['winW'],
                'rubikWinW': h_rubik_m['winW'],
                'longWinW': b_long_m['winW'],
                'longBarTextSize': b_long_m['barTextSize'],
                'hangarStableW': h_fourdigit_m['winW'],
                'hangarStableH': h_fourdigit_m['winH'],
                'trackSvgTag': v3_assist_icon_svg('track', 0, 0, 16, '#FFFFFF', 1.0),
            },
        }

        node_script = """
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const uiDir = data.uiDir;

function makeEl(id) {
    return {
        id: id || '', tag: id || '', className: '', textContent: '', src: '', attrs: {}, style: {},
        children: [], firstChild: null,
        setAttribute(k, v) { this.attrs[k] = String(v); },
        appendChild(c) { this.children.push(c); this.firstChild = this.children[0] || null; return c; },
        removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); this.firstChild = this.children[0] || null; },
        replaceChild(n, o) { const i = this.children.indexOf(o); if (i >= 0) this.children[i] = n; this.firstChild = this.children[0] || null; },
        getBoundingClientRect() { return { width: 80, height: 18 }; }
    };
}
const els = {};
const intervals = [];
let resizeCalls = 0;
const sandbox = {
    viewEnv: { getScale: () => 1, resizeViewPx: () => { resizeCalls += 1; } },
    document: {
        getElementById(id) { if (!els[id]) els[id] = makeEl(id); return els[id]; },
        createElement(tag) { return makeEl(tag); },
        createElementNS(ns, tag) { const el = makeEl(tag); el.namespaceURI = ns; return el; },
        documentElement: makeEl('html'),
        body: makeEl('body')
    },
    Math, Number, String, Boolean, Array, Object, JSON, parseInt, parseFloat, isFinite
};
sandbox.window = sandbox;
sandbox.model = { payload: '{}', onReady: () => {} };
sandbox.requestAnimationFrame = (cb) => cb();
sandbox.setInterval = (cb, ms) => { intervals.push(cb); return intervals.length; };
sandbox.clearInterval = () => {};
sandbox.btoa = (s) => Buffer.from(s, 'binary').toString('base64');

vm.createContext(sandbox);
const scripts = [
    'js/defaults.js', 'js/utils.js', 'js/v3_metrics.js', 'js/v3_svg.js', 'js/renderer_v3.js',
    'js/renderer_classic.js', 'js/renderer_settings.js', 'js/gameface_bridge.js', 'ThreeMarks.js'
];
for (const rel of scripts) {
    vm.runInContext(fs.readFileSync(path.join(uiDir, rel), 'utf8'), sandbox, { filename: rel });
}
if (!sandbox.DmThreeMarks || !sandbox.DmThreeMarks.app) throw new Error('Missing DmThreeMarks.app');

// 0. Booting with empty '{}' payload must keep all panels hidden and avoid resizing
if (els['tm-v3'] && els['tm-v3'].style.display && els['tm-v3'].style.display !== 'none') {
    throw new Error('tm-v3 shown on initial empty payload');
}
if (els['tm-panel'] && els['tm-panel'].style.display && els['tm-panel'].style.display !== 'none') {
    throw new Error('tm-panel shown on initial empty payload');
}
if (els['tm-btoggle'] && els['tm-btoggle'].style.display && els['tm-btoggle'].style.display !== 'none') {
    throw new Error('tm-btoggle shown on initial empty payload');
}
if (resizeCalls !== 0) {
    throw new Error('Expected 0 resizeViewPx calls on empty payload, got ' + resizeCalls);
}

function push(obj) {
    sandbox.model.payload = JSON.stringify(obj);
    sandbox.DmThreeMarks.app.refresh();
}

push({});
if (els['tm-v3'].style.display !== 'none' || els['tm-panel'].style.display !== 'none' || els['tm-btoggle'].style.display !== 'none') {
    throw new Error('Explicit empty {} payload must hide all panels');
}

// 1. Battle V3 custom text & Alt width lock
function pxS(v, ui, isH) { return Math.max(1, Math.round(v * (isH ? ui.hs : ui.s))); }
push(data.battleNoAlt);
const elV3 = els['tm-v3'];
if (elV3.style.display !== 'block') throw new Error('tm-v3 not shown');
const wNoAlt = elV3.style.width;
if (wNoAlt !== pxS(data.expected.battleWinW, data.battleNoAlt.ui, false) + 'px') throw new Error('Battle width mismatch: ' + wNoAlt);
const barTxtWrap = elV3.children.find(c => c.className === 'v3-bartxt-wrap');
if (!barTxtWrap || barTxtWrap.style.display !== 'flex') throw new Error('barTxtWrap not shown');
const clip = barTxtWrap.children[0].children[1];
if (clip.style.width !== '70.64%') throw new Error('clip width mismatch: ' + clip.style.width);
if (barTxtWrap.children[0].children[0].textContent !== 'CYBER PRO') throw new Error('custom text mismatch');
const bgEl = elV3.children.find(c => c.className === 'v3-bgimg');
if (!bgEl || !bgEl.firstChild || bgEl.firstChild.tag !== 'svg' || bgEl.firstChild.children.length === 0) {
    throw new Error('Expected inline <svg> with primitives inside .v3-bgimg');
}
const expVb = '0 0 ' + parseInt(elV3.style.width, 10) + ' ' + parseInt(elV3.style.height, 10);
if (bgEl.firstChild.attrs.viewBox !== expVb) {
    throw new Error('Expected physical SVG viewBox ' + expVb + ', got ' + bgEl.firstChild.attrs.viewBox);
}
const hasRoundStar = bgEl.firstChild.children.some(ch => ch.tag === 'polygon' && ch.attrs['stroke-linejoin'] === 'round');
if (!hasRoundStar) throw new Error('Expected stroke-linejoin=round on V3 SVG star fallback');
const bgFillEl = elV3.children.find(c => c.className === 'v3-bgfill');
if (!bgFillEl || bgFillEl.style.display !== 'none') {
    throw new Error('Expected .v3-bgfill hidden when bgo=0.0, got: ' + (bgFillEl && bgFillEl.style.display));
}
const hdrEl = elV3.children.find(c => c.className === 'v3-hdr');
const pctEl = hdrEl && hdrEl.children[0];
if (!pctEl || pctEl.textContent !== '70.64%' || (pctEl.children && pctEl.children.length !== 0)) {
    throw new Error('Expected single-span .v3-pct textContent 70.64%, got: ' + (pctEl && pctEl.textContent));
}
const delIcoEl = hdrEl && hdrEl.children[1] && hdrEl.children[1].children[0];
if (!delIcoEl || !delIcoEl.firstChild || delIcoEl.firstChild.tag !== 'svg' || delIcoEl.firstChild.children.length === 0) {
    throw new Error('Expected inline <svg> inside delta icon');
}
function checkNoDataSvg(node) {
    if (!node) return;
    if (node.src && String(node.src).indexOf('data:image/svg') === 0) {
        throw new Error('Forbidden data:image/svg src found on ' + node.className);
    }
    for (const ch of (node.children || [])) checkNoDataSvg(ch);
}
checkNoDataSvg(elV3);

push(data.battleAlt);
if (elV3.style.width !== wNoAlt) throw new Error('Width shifted on Alt: ' + wNoAlt + ' -> ' + elV3.style.width);
if (barTxtWrap.children[0].children[1].firstChild.style.textShadow !== '0 1px 0 rgba(0,0,0,0.85)') {
    throw new Error('Unexpected transparent textShadow: ' + barTxtWrap.children[0].children[1].firstChild.style.textShadow);
}
const astRow0 = elV3.children.find(c => c.className === 'v3-astwrap');
const astIco0 = astRow0 && astRow0.children[0] && astRow0.children[0].children[0];
if (!astIco0 || !astIco0.firstChild || astIco0.firstChild.tag !== 'svg' || astIco0.firstChild.children.length === 0) {
    throw new Error('Expected inline <svg> inside assist icon');
}
const trackNode = astRow0 && astRow0.children[1] && astRow0.children[1].children[0];
if (!trackNode || !trackNode.firstChild || trackNode.firstChild.children.length !== 1 || !trackNode.firstChild.children[0].attrs.fill) {
    throw new Error('Expected single solid-fill path for track assist icon');
}
const jsTrackUri = sandbox.DmThreeMarks.v3Svg.assistIconUri({}, 'track', 16, '#FFFFFF', 1.0);
const jsTrackSvg = Buffer.from(jsTrackUri.split(',')[1], 'base64').toString('utf8');
if (jsTrackSvg.indexOf(data.expected.trackSvgTag) < 0) {
    throw new Error('Python/JS track icon SVG mismatch: ' + jsTrackSvg + ' vs ' + data.expected.trackSvgTag);
}
checkNoDataSvg(elV3);

// 2. Korben mode (native pixel sizing without CSS body transform)
push(data.korben);
if (els['tm-panel'].style.display !== 'block') throw new Error('tm-panel not shown in Korben mode');
if (els['tm-panel'].className.indexOf('percent-only') < 0) throw new Error('missing percent-only class');
if (sandbox.document.body.style.transform !== 'none') {
    throw new Error('Expected body transform none in Korben mode, got: ' + sandbox.document.body.style.transform);
}
if (els['tm-panel'].style.width !== Math.round(220 * data.korben.ui.s) + 'px') {
    throw new Error('Korben native panel width mismatch: ' + els['tm-panel'].style.width);
}
if (els['tm-pct'].style.fontSize !== Math.round(22 * data.korben.ui.s) + 'px') {
    throw new Error('Korben native pct fontSize mismatch: ' + els['tm-pct'].style.fontSize);
}
if (String(els['tm-pct'].style.fontFamily || '').indexOf('ThreeMarksExo2') < 0) {
    throw new Error('Korben mode did not apply v3Font to #tm-pct: ' + els['tm-pct'].style.fontFamily);
}

// 3. Hangar compact 2x2 grid & custom text
push(data.hangar);
if (elV3.style.width !== pxS(data.expected.hangarWinW, data.hangar.ui, true) + 'px' || elV3.style.height !== pxS(data.expected.hangarWinH, data.hangar.ui, true) + 'px') {
    throw new Error('Hangar size mismatch: ' + elV3.style.width + 'x' + elV3.style.height);
}
const thr1 = elV3.children.find(c => c.className === 'v3-astwrap v3-thrwrap');
const thr2 = elV3.children.find(c => c.className === 'v3-astwrap v3-thrwrap v3-thrwrap2');
if (thr1.style.justifyContent !== 'center' || thr2.style.justifyContent !== 'center') throw new Error('Hangar grid not centered');
if (thr1.children[0].children[2].textContent !== '2150') throw new Error('Unexpected 65 cell text: ' + thr1.children[0].children[2].textContent);
if (thr2.children[1].children[1].textContent !== '100%' || thr2.children[1].children[2].textContent !== '3920') throw new Error('Unexpected 100 cell: ' + thr2.children[1].children[2].textContent);
if (thr1.children[0].children[2].style.textShadow !== 'none') throw new Error('Expected no textShadow on opaque hangar panel: ' + thr1.children[0].children[2].style.textShadow);

// 3b. Hangar scaled natively without CSS body transform and with adaptive crisp textShadow on translucent bg
push(data.hangarScaled);
if (sandbox.document.body.style.transform !== 'none') throw new Error('Expected body transform none in V3: ' + sandbox.document.body.style.transform);
const expScaledW = Math.round(data.expected.hangarScaledWinW * 1.15) + 'px';
if (elV3.style.width !== expScaledW) throw new Error('Scaled width mismatch: ' + elV3.style.width + ' vs ' + expScaledW);
if (thr1.children[0].children[2].style.textShadow !== '0 1px 0 rgba(0,0,0,0.45)') throw new Error('Expected adaptive translucent textShadow: ' + thr1.children[0].children[2].style.textShadow);

// 3c. Font presets class, additive width (+40), equal assist tie -> both muted, and Python-JS width parity
push(data.battleFontExo);
if (elV3.className !== 'tm-font-4') throw new Error('Expected tm-font-4, got: ' + elV3.className);
if (data.expected.exoWinW !== data.expected.exo0WinW + 40) throw new Error('Additive width failed in Python: ' + data.expected.exoWinW);
if (elV3.style.width !== pxS(data.expected.exoWinW, data.battleFontExo.ui, false) + 'px') throw new Error('Exo width mismatch: ' + elV3.style.width + ' vs ' + pxS(data.expected.exoWinW, data.battleFontExo.ui, false));
const astRow = elV3.children.find(c => c.className === 'v3-astwrap');
if (!astRow || astRow.children[0].children[1].style.color !== data.battleFontExo.ui.v3.tmu || astRow.children[1].children[1].style.color !== data.battleFontExo.ui.v3.tmu) {
    throw new Error('Equal assist channels must both be muted/gray');
}
push(data.hangarFontRubik);
if (elV3.className !== 'tm-font-5') throw new Error('Expected tm-font-5, got: ' + elV3.className);
if (elV3.style.width !== pxS(data.expected.rubikWinW, data.hangarFontRubik.ui, true) + 'px') throw new Error('Rubik width mismatch: ' + elV3.style.width + ' vs ' + pxS(data.expected.rubikWinW, data.hangarFontRubik.ui, true));

// 3d. Long wide custom bar text auto-fits in JS matching Python width & fontSize
push(data.battleLongText);
if (elV3.style.width !== pxS(data.expected.longWinW, data.battleLongText.ui, false) + 'px') throw new Error('Long text width mismatch: ' + elV3.style.width + ' vs ' + pxS(data.expected.longWinW, data.battleLongText.ui, false));
if (barTxtWrap.children[0].children[0].style.fontSize !== pxS(data.expected.longBarTextSize, data.battleLongText.ui, false) + 'px') {
    throw new Error('Long text fitted fontSize mismatch: ' + barTxtWrap.children[0].children[0].style.fontSize + ' vs ' + pxS(data.expected.longBarTextSize, data.battleLongText.ui, false));
}

// 3e. Hangar no-rating vs 4-digit thresholds keep identical width/height and trigger 0 extra resizes
push(data.hangarNoData);
if (elV3.style.width !== pxS(data.expected.hangarStableW, data.hangarNoData.ui, true) + 'px' || elV3.style.height !== pxS(data.expected.hangarStableH, data.hangarNoData.ui, true) + 'px') {
    throw new Error('Hangar noData size mismatch: ' + elV3.style.width + 'x' + elV3.style.height);
}
const resizesBeforeSwitch = resizeCalls;
push(data.hangarFourDigit);
if (elV3.style.width !== pxS(data.expected.hangarStableW, data.hangarFourDigit.ui, true) + 'px' || elV3.style.height !== pxS(data.expected.hangarStableH, data.hangarFourDigit.ui, true) + 'px') {
    throw new Error('Hangar fourDigit size mismatch: ' + elV3.style.width + 'x' + elV3.style.height);
}
if (resizeCalls !== resizesBeforeSwitch) {
    throw new Error('Expected 0 extra resizeViewPx calls on tank switch, got ' + (resizeCalls - resizesBeforeSwitch));
}

// 3f. Battle damage row without label: right (dl=2) vs centered (dl=3)
push(data.battleDmgCenter);
const dmgRowEl = elV3.children.find(c => c.className === 'v3-dmg');
const dmgLblEl = dmgRowEl.children[0];
const dmgValsEl = dmgRowEl.children[1];
if (dmgLblEl.style.display !== 'none' || dmgRowEl.style.justifyContent !== 'center' || dmgValsEl.style.marginLeft !== '0px') {
    throw new Error('Expected centered dmg row for dl=3, got: ' + dmgLblEl.style.display + '/' + dmgRowEl.style.justifyContent + '/' + dmgValsEl.style.marginLeft);
}
push(data.battleDmgRight);
if (dmgLblEl.style.display !== 'none' || dmgRowEl.style.justifyContent !== 'space-between' || dmgValsEl.style.marginLeft !== 'auto') {
    throw new Error('Expected right-aligned dmg row for dl=2, got: ' + dmgLblEl.style.display + '/' + dmgRowEl.style.justifyContent + '/' + dmgValsEl.style.marginLeft);
}

// 3g. Battle big damage uses big color, tempo stays neutral even when dmg>=target, and zero delta uses neutral glyph + '0.00%'
push(data.battleBigTempoDone);
if (dmgValsEl.children[0].style.color !== data.battleBigTempoDone.ui.v3.big) {
    throw new Error('Expected big damage color ' + data.battleBigTempoDone.ui.v3.big + ', got ' + dmgValsEl.children[0].style.color);
}
if (thr1.children[0].children[1].style.color !== data.battleBigTempoDone.ui.v3.tmu || thr1.children[0].children[2].style.color !== data.battleBigTempoDone.ui.v3.tm) {
    throw new Error('Battle tempo row must remain neutral textMain/textMuted color when achieved');
}
push(data.battleZero);
if (hdrEl.children[1].children[1].textContent !== '0.00%') {
    throw new Error('Expected clean 0.00% delta text, got: ' + hdrEl.children[1].children[1].textContent);
}
if (delIcoEl.firstChild.children[0].attrs.d.indexOf('M 1.5 5.5 L 9.5 5.5') < 0) {
    throw new Error('Expected neutral horizontal arrow for zero delta: ' + delIcoEl.firstChild.children[0].attrs.d);
}

// 3h. Hangar permanent marks highlight (marks=2/84.02% highlights 65 & 85; marks=3/100% never highlights 100%)
push(data.hangarMarks2);
const vh2 = data.hangarMarks2.ui.vh;
if (thr1.children[0].children[1].style.color !== vh2.up || thr1.children[1].children[1].style.color !== vh2.up) {
    throw new Error('Expected 65% and 85% highlighted for marks=2 even when pct=84.02%');
}
if (thr2.children[0].children[1].style.color !== vh2.tmu || thr2.children[1].children[1].style.color !== vh2.tmu) {
    throw new Error('Expected 95% and 100% unhighlighted for marks=2');
}
push(data.hangarMarks3);
const vh3 = data.hangarMarks3.ui.vh;
if (thr2.children[0].children[1].style.color !== vh3.up) {
    throw new Error('Expected 95% highlighted for marks=3');
}
if (thr2.children[1].children[1].style.color !== vh3.tmu || thr2.children[1].children[2].style.color !== vh3.tm) {
    throw new Error('Expected 100% never highlighted even at 100.0%');
}
if (thr1.children[0].style.width !== thr2.children[0].style.width || thr1.children[1].style.width !== thr2.children[1].style.width) {
    throw new Error('Expected aligned fixed column widths across hangar rows, got row1=' + thr1.children[0].style.width + '/' + thr1.children[1].style.width + ' row2=' + thr2.children[0].style.width + '/' + thr2.children[1].style.width);
}
if (parseInt(thr2.children[1].style.width, 10) < 75 || thr2.children[1].children[2].style.marginLeft !== Math.round(4 * data.hangarMarks3.ui.hs) + 'px') {
    throw new Error('Expected widened width & gap for Tektur hangar thresholds, got width=' + thr2.children[1].style.width + ' marginLeft=' + thr2.children[1].children[2].style.marginLeft);
}
if (bgFillEl.style.display !== 'block' || String(bgFillEl.style.backgroundColor).indexOf('rgba(') !== 0) {
    throw new Error('Expected native CSS rgba .v3-bgfill on framed hangar panel, got: ' + bgFillEl.style.backgroundColor);
}
const bNoFrame = JSON.parse(JSON.stringify(data.battleNoAlt));
bNoFrame.ui.v3.fs = 3;
bNoFrame.v3m = null;
push(bNoFrame);
if (bgFillEl.style.display !== 'none') {
    throw new Error('Expected .v3-bgfill hidden when fs=3 (frameless HUD), got: ' + bgFillEl.style.display);
}

// 4. In-battle collapse/expand toggle ('minus' on Ctrl, 'plus' only on Ctrl when bmin=true, 0 extra resizes)
const bMinus = Object.assign({}, data.battleNoAlt, { ctrl: true, bmin: false });
push(bMinus);
if (els['tm-btoggle'].style.display !== 'block' || els['tm-btoggle'].className !== 'minus') {
    throw new Error('Expected minus toggle in battle with Ctrl: ' + els['tm-btoggle'].style.display + '/' + els['tm-btoggle'].className);
}
if (els['tm-bt-v'].style.display !== 'none') throw new Error('Minus icon must hide vertical bar');
const bToggleBox = Math.max(16, Math.round(22 * data.battleNoAlt.ui.s));
const minusLeft = els['tm-btoggle'].style.left;
if (minusLeft !== (pxS(data.expected.battleWinW, data.battleNoAlt.ui, false) - bToggleBox) + 'px') {
    throw new Error('Expected right-aligned minus left=' + (pxS(data.expected.battleWinW, data.battleNoAlt.ui, false) - bToggleBox) + 'px, got ' + minusLeft);
}

const resizesBeforeCollapse = resizeCalls;
const bPlusNoCtrl = Object.assign({}, data.battleNoAlt, { ctrl: false, bmin: true });
push(bPlusNoCtrl);
if (els['tm-v3'].style.display !== 'none' || els['tm-panel'].style.display !== 'none') {
    throw new Error('Collapsed battle mode must hide V3 and classic panels');
}
if (els['tm-btoggle'].style.display !== 'none') {
    throw new Error('Collapsed plus toggle must stay hidden when Ctrl is not pressed');
}
if (resizeCalls !== resizesBeforeCollapse) {
    throw new Error('Collapsing battle panel must trigger 0 resizeViewPx calls');
}

const bPlusCtrl = Object.assign({}, data.battleNoAlt, { ctrl: true, bmin: true });
push(bPlusCtrl);
if (els['tm-btoggle'].style.display !== 'block' || els['tm-btoggle'].className !== 'plus' || els['tm-bt-v'].style.display !== 'block') {
    throw new Error('Expected plus toggle when collapsed with Ctrl: ' + els['tm-btoggle'].className);
}
if (els['tm-btoggle'].style.left !== minusLeft) {
    throw new Error('Plus toggle must share exact right-aligned X with minus toggle');
}
if (resizeCalls !== resizesBeforeCollapse) {
    throw new Error('Showing plus toggle must trigger 0 resizeViewPx calls');
}

// 5. Settings mode hides battle toggle
push(data.settings);
if (els['tm-btoggle'].style.display !== 'none') throw new Error('Battle toggle must hide in settings');
if (els['tm-panel'].className !== 'settings') throw new Error('settings class missing');
if (els['tm-set'].children.length === 0) throw new Error('settings DOM empty');

console.log('FRONTEND_CONTRACT_OK');
"""
        fd_in, in_path = tempfile.mkstemp(prefix='tm_fe_in_', suffix='.json')
        os.close(fd_in)
        fd_js, js_path = tempfile.mkstemp(prefix='tm_fe_test_', suffix='.js')
        os.close(fd_js)
        try:
            with open(in_path, 'wb') as f:
                f.write(json.dumps(fixture_bundle, ensure_ascii=False).encode('utf-8'))
            with open(js_path, 'wb') as f:
                f.write(node_script.encode('utf-8'))
            proc = subprocess.Popen([_find_node(), js_path, in_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
            self.assertEqual(proc.returncode, 0, 'Node contract test failed:\n%s\n%s' % (out, err))
            self.assertIn('FRONTEND_CONTRACT_OK', out)
        finally:
            for p in (in_path, js_path):
                if os.path.exists(p):
                    os.remove(p)

    def test_css_keeps_sdf_enabled_and_prevents_glyph_clipping(self):
        import re
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        css_path = os.path.join(repo_root, 'package', 'res', 'gui', 'gameface', 'mods', 'dm', 'ThreeMarks', 'ThreeMarks.css')
        css_txt = open(css_path, 'rb').read().decode('utf-8')
        self.assertNotIn('coh-font-sdf: off', css_txt)
        self.assertNotIn('-coherent-font-sdf: off', css_txt)
        self.assertNotIn('0 1px 2px', css_txt)
        self.assertNotIn('0 1px 3px', css_txt)
        dmg_m = re.search(r'#tm-v3\s+\.v3-dmg\s*\{([^}]*)\}', css_txt)
        self.assertIsNotNone(dmg_m)
        self.assertNotIn('overflow: hidden', dmg_m.group(1))
        pct_m = re.search(r'#tm-v3\s+\.v3-pct\s*\{([^}]*)\}', css_txt)
        self.assertIsNotNone(pct_m)
        self.assertIn('display: block', pct_m.group(1))
        self.assertNotIn('.v3-pct-sign', css_txt)


if __name__ == '__main__':
    unittest.main()
