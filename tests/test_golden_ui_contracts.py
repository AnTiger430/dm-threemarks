# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from dm_threemarks.adapters.menu.aslain_adapter import AslainMenuAdapter
from dm_threemarks.adapters.menu.preview_renderer import MenuPreviewRenderer
from dm_threemarks.adapters.menu.schema import MenuValueConverter
from dm_threemarks.adapters.menu.template_builder import MenuTemplateBuilder
from dm_threemarks.adapters.presenters.ui_config_serializer import UiConfigSerializer
from dm_threemarks.adapters.v3.metrics import V3MetricsCalculator
from dm_threemarks.adapters.v3.samples import PREVIEW_SAMPLES, PREVIEW_SAMPLES_V3
from dm_threemarks.adapters.v3.svg_renderer import V3SvgRenderer
from dm_threemarks.application.config.defaults import DEFAULT_CONFIG
from dm_threemarks.application.config.validator import ConfigStore


def _load_golden():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'golden_v10_12_7.json')
    with open(path, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


def _decode_svg(uri):
    return base64.b64decode(uri.split(',', 1)[1]).decode('utf-8')


def _norm_json(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


class _FakeTpl(object):
    def createSlider(self, text, key, val, lo, hi, step, **kw):
        return {'type': 'Slider', 'text': text, 'varName': key, 'value': val}

    def createCheckbox(self, text, key, val, **kw):
        return {'type': 'CheckBox', 'text': text, 'varName': key, 'value': val}

    def createColorChoice(self, text, key, val, **kw):
        return {'type': 'ColorChoice', 'text': text, 'varName': key, 'value': val}

    def createLabel(self, text):
        return {'type': 'Label', 'text': text}

    def createDropdown(self, text, key, opts, val, **kw):
        return {'type': 'Dropdown', 'text': text, 'varName': key, 'options': opts, 'value': val}

    def createRadioButtonGroup(self, text, key, opts, val, **kw):
        return {'type': 'RadioButtonGroup', 'text': text, 'varName': key, 'options': opts, 'value': val}

    def generateOptions(self, labels):
        return [{'label': s} for s in labels]


class TestGoldenAdapterContracts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.golden = _load_golden()

    def test_config_and_payloads(self):
        store = ConfigStore()
        ser = UiConfigSerializer(store)
        self.assertEqual(_norm_json(ser.ui_payload()), self.golden['payloads']['ui'])
        self.assertEqual(_norm_json(ser.v3_ui_payload()), self.golden['payloads']['v3'])
        self.assertEqual(_norm_json(ser.vh_ui_payload()), self.golden['payloads']['vh'])
        self.assertEqual(_norm_json(store.to_v3_from_hangar()), self.golden['payloads']['vh_to_v3'])

    def test_menu_values_converts_and_template(self):
        store = ConfigStore()
        conv = MenuValueConverter(store)
        self.assertEqual(_norm_json(conv.default_values()), self.golden['menu']['defaults'])
        self.assertEqual(_norm_json(conv.current_values()), self.golden['menu']['values'])
        exp = self.golden['menu']['converts']
        self.assertEqual(conv.convert('v3BarStyle', 99), exp['v3BarStyle_clamp'])
        self.assertEqual(conv.convert('v3BarTextSize', 17.6), exp['v3BarTextSize_float'])
        self.assertEqual(conv.convert('v3BarCustomText', u'ABC\nDEF\r12345678901234567890'), exp['v3BarCustomText_nl'])
        self.assertEqual(conv.convert('v3BgOpacity', 1.75), exp['v3BgOpacity_clamp'])
        self.assertEqual(conv.convert('v3CornerColor', 0x12AB34), exp['v3CornerColor_int'])
        self.assertEqual(conv.convert('v3CornerColor', [255, 128, 0]), exp['v3CornerColor_list'])
        self.assertEqual(conv.convert('v3ShowDamage', 0), exp['v3ShowDamage_bool'])

        metrics = V3MetricsCalculator(store)
        svg = V3SvgRenderer(metrics, store)
        preview = MenuPreviewRenderer(store, svg)
        builder = MenuTemplateBuilder(conv, preview)
        tpl = builder.build(_FakeTpl(), (2, 1, 0), show_v3=True)
        flat = json.dumps(tpl, ensure_ascii=False)
        self.assertNotIn('hangarOnlyRandom', flat)
        self.assertNotIn('hideUnderWindows', flat)
        self.assertNotIn('vhShow100', flat)
        self.assertNotIn('v3HideInSniper', flat)
        self.assertNotIn('v3Anchor', flat)
        self.assertNotIn(u'Тактическая (трек + курсор)', flat)
        for key in ('v3Font', 'vhFont', 'v3BarCustomText', 'v3BarTextSize', 'vhBarCustomText', 'vhBarTextSize', 'v3AssistSize', 'v3TempoSize', 'hideInIntro', 'hideInKillcam', 'hideAfterDeath'):
            self.assertIn(key, flat)

        lesta_tpl = MenuTemplateBuilder(conv, preview, is_lesta=True).build(_FakeTpl(), (2, 1, 0), show_v3=True)
        lesta_flat = json.dumps(lesta_tpl, ensure_ascii=False)
        self.assertNotIn('hideInIntro', lesta_flat)
        self.assertNotIn('hideInKillcam', lesta_flat)
        self.assertIn('hideAfterDeath', lesta_flat)

    def test_v3_metrics_and_svg_parity(self):
        configs = [
            ('battle_default_plus_noalt', {}, 'plus', False, False),
            ('battle_default_minus_alt', {'v3AssistShow': 1, 'v3TempoShow': 1}, 'minus', True, False),
            ('battle_barstyle4_customtext', {'v3BarStyle': 3, 'v3BarCustomText': u'CYBER PRO', 'v3BarTextSize': 18, 'v3BarColorMode': 1}, 'big', True, False),
            ('battle_hud_noframe_side_stars', {'v3FrameStyle': 3, 'v3StarsPos': 2, 'v3StarsDivider': True, 'v3HeaderOrder': 2, 'v3BarStyle': 1}, 'zero', False, False),
            ('hangar_default', {}, 'plus', False, True),
            ('hangar_barstyle4_customtext', {'vhBarStyle': 3, 'vhBarCustomText': u'THREE MARKS', 'vhBarTextSize': 16}, 'zero', False, True),
        ]
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        for label, patch, state, alt, is_hangar in configs:
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(patch)
            sample = dict(PREVIEW_SAMPLES_V3[state])
            if is_hangar:
                sample['isHangar'] = True
                sample['delta'] = None
                m_cfg = store.to_v3_from_hangar(cfg)
            else:
                m_cfg = cfg
            met = _norm_json(metrics.compute(m_cfg, sample, alt=alt))
            uri, bw, bh = renderer.render_v3_svg(m_cfg, sample, alt=alt)
            exp = self.golden['v3_cases'][label]
            self.assertEqual(met, exp['metrics'])
            self.assertEqual(bw, exp['bw'])
            self.assertEqual(bh, exp['bh'])
            self.assertEqual(_decode_svg(uri), exp['svg'])

    def test_classic_and_korben_previews(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        preview = MenuPreviewRenderer(store, renderer)
        for target, preset, state in ((0, 0, 'plus'), (0, 1, 'minus'), (1, 0, 'zero')):
            store.replace_normalized({'battlePreset': preset})
            preview.state['target'] = target
            preview.state['state'] = state
            preview.state['alt'] = False
            preview.state['hwAlt'] = False
            uri, bw, bh, dw, dh = preview.render()
            exp = self.golden['preview_cases']['%d_%d_%s' % (target, preset, state)]
            self.assertEqual((bw, bh, dw, dh), (exp['bw'], exp['bh'], exp['dw'], exp['dh']))
            self.assertEqual(_decode_svg(uri), exp['svg'])

    def test_aslain_menu_adapter_v2_registration_and_lifecycle(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from in_memory_adapters import FakeClock, MemoryConfigRepository, MemoryLogger
        from dm_threemarks.application.use_cases.config_sync import ConfigSyncService

        class _Ev(object):
            def __init__(self):
                self.handlers = []

            def __iadd__(self, fn):
                self.handlers.append(fn)
                return self

            def __isub__(self, fn):
                if fn in self.handlers:
                    self.handlers.remove(fn)
                return self

        class _FakeAslainApi(object):
            def __init__(self):
                self.onWindowOpened = _Ev()
                self.onWindowClosed = _Ev()
                self.templates = []
                self.defaults = None
                self.live_cb = None
                self.button_cb = None
                self.images = []
                self.reloaded = []
                self.controls = []
                self.unregistered_live = False
                self.reg_order = []
                self.input_previews = {}
                self.preview_replies = []
                self.unregistered_previews = []

            def getVersionTuple(self):
                return (2, 1, 15)

            def setModTemplate(self, linkage, template, apply_cb, button_cb=None):
                self.reg_order.append('setModTemplate')
                self.templates.append((linkage, template))
                self.button_cb = button_cb
                return {'v3BarStyle': 1}

            def setModDefaults(self, linkage, defaults):
                self.defaults = (linkage, defaults)

            def registerLiveSettingsChange(self, linkage, cb, include_all=False):
                self.live_cb = cb

            def unregisterLiveSettingsChange(self, linkage, cb):
                self.unregistered_live = (self.live_cb == cb)

            def registerInputPreview(self, linkage, var_name, handler):
                self.reg_order.append('registerInputPreview:' + var_name)
                self.input_previews[var_name] = handler

            def unregisterInputPreview(self, linkage, var_name):
                self.unregistered_previews.append((linkage, var_name))
                self.input_previews.pop(var_name, None)

            def setInputPreview(self, linkage, var_name, content, token=None):
                self.preview_replies.append((linkage, var_name, content, token))

            def setControlValue(self, linkage, key, val):
                self.controls.append((linkage, key, val))
                return True

            def updateImage(self, linkage, var_name, src, w, h):
                self.images.append((linkage, var_name, src, w, h))

            def reloadModTemplate(self, linkage, tpl):
                self.reloaded.append((linkage, tpl))

            def getModSettings(self, linkage, tpl):
                return {}

        class _FakeTplV2(_FakeTpl):
            def __init__(self):
                self.tabs_created = []

            def createTab(self, title, items):
                self.tabs_created.append(title)
                return [{'type': 'Tab', 'title': title, 'items': items}]

            def createInput(self, text, key, val, **kw):
                return {'type': 'TextInput', 'text': text, 'varName': key, 'value': val}

            def createRadioButtonGroup(self, text, key, opts, val, **kw):
                return {'type': 'RadioButtonGroup', 'text': text, 'varName': key, 'options': opts, 'value': val, 'inline': bool(kw.get('inline', False))}

            def createActionButton(self, var_name, btn_text, label=None, **kw):
                return {'type': 'Button', 'varName': var_name, 'text': label, 'btnText': btn_text}

            def visibleWhen(self, ctl, master, val, indent=False, condition='=='):
                ctl['masterVarName'] = master
                ctl['masterValue'] = val
                ctl['gateHides'] = True
                ctl['masterIndent'] = bool(indent)
                if condition != '==':
                    ctl['condition'] = condition
                return ctl

        fake_api = _FakeAslainApi()
        fake_tpl = _FakeTplV2()
        aslain_mod = type(sys)('gui.aslainMenu')
        aslain_mod.g_modsSettingsApi = fake_api
        aslain_mod.templates = fake_tpl
        prev_gui = sys.modules.get('gui')
        prev_aslain = sys.modules.get('gui.aslainMenu')
        if prev_gui is None:
            sys.modules['gui'] = type(sys)('gui')
        sys.modules['gui.aslainMenu'] = aslain_mod
        try:
            logger = MemoryLogger()
            store = ConfigStore(logger=logger)
            sync = ConfigSyncService(MemoryConfigRepository(), store, FakeClock(), logger)
            metrics = V3MetricsCalculator(store)
            svg = V3SvgRenderer(metrics, store)
            preview = MenuPreviewRenderer(store, svg)
            builder = MenuTemplateBuilder(MenuValueConverter(store), preview)
            adapter = AslainMenuAdapter(store, sync, preview, builder, logger)
            refreshes = [0]
            adapter.bind_runtime(on_refresh=lambda: refreshes.__setitem__(0, refreshes[0] + 1))

            ok = adapter.register()
            self.assertTrue(ok)
            self.assertEqual(adapter._ver, (2, 1, 15))
            # Only 2 top tabs ('Боевая панель' and 'Ангар'), each with inline section buttons and tab-scoped column2 preview
            self.assertEqual(fake_tpl.tabs_created, [u'Боевая панель', u'Ангар', u'Боевая панель', u'Ангар'])
            self.assertEqual(len(fake_api.input_previews), 0)
            tabs_by_title = dict((t['title'], t['items']) for t in fake_api.templates[0][1]['column1'] if t.get('type') == 'Tab')
            col2_by_title = dict((t['title'], t['items']) for t in fake_api.templates[0][1]['column2'] if t.get('type') == 'Tab')
            self.assertEqual(set(col2_by_title.keys()), set([u'Боевая панель', u'Ангар']))
            self.assertTrue(any(c.get('varName') == 'marksLivePreview' for c in col2_by_title[u'Боевая панель']))
            self.assertTrue(any(c.get('varName') == 'marksLivePreviewHangar' for c in col2_by_title[u'Ангар']))
            self.assertFalse(any(c.get('varName') == 'previewTarget' for c in col2_by_title[u'Боевая панель']))
            b_nav = [c for c in tabs_by_title[u'Боевая панель'] if c.get('varName') == 'battleSection'][0]
            h_nav = [c for c in tabs_by_title[u'Ангар'] if c.get('varName') == 'hangarSection'][0]
            self.assertEqual(b_nav['type'], 'RadioButtonGroup')
            self.assertTrue(b_nav['inline'])
            self.assertNotIn('span', b_nav)
            self.assertEqual([o['label'] for o in b_nav['options']], [u'Основное', u'Рамка и звёзды', u'Шапка и полоска', u'Урон и ассист', u'Цвета'])
            self.assertEqual(h_nav['type'], 'RadioButtonGroup')
            self.assertTrue(h_nav['inline'])
            self.assertNotIn('span', h_nav)
            self.assertEqual([o['label'] for o in h_nav['options']], [u'Основное', u'Рамка и звёзды', u'Полоска', u'Цвета'])
            self.assertEqual(fake_api.defaults[0], 'dm.threemarks')
            self.assertEqual(fake_api.defaults[1]['battleSection'], 0)
            self.assertEqual(fake_api.defaults[1]['hangarSection'], 0)
            self.assertIsNotNone(fake_api.live_cb)
            self.assertIsNotNone(fake_api.button_cb)
            self.assertEqual(store.get('v3BarStyle'), 1)
            self.assertEqual(len(fake_api.onWindowOpened.handlers), 1)
            self.assertEqual(len(fake_api.onWindowClosed.handlers), 1)

            # Live change should update config, trigger refresh, and updateImage
            before_imgs = len(fake_api.images)
            fake_api.live_cb('dm.threemarks', {'v3Density': 2})
            self.assertEqual(store.get('v3Density'), 2)
            self.assertGreater(len(fake_api.images), before_imgs)
            self.assertGreaterEqual(refreshes[0], 1)

            # Clicking Hangar sub-section button 1 auto-switches previewTarget -> 1; Battle sub-section button 2 -> 0
            fake_api.live_cb('dm.threemarks', {'hangarSection': 1})
            self.assertEqual(preview.state['hangarSection'], 1)
            self.assertEqual(preview.state['target'], 1)
            self.assertIn(('dm.threemarks', 'previewTarget', 1), fake_api.controls)
            fake_api.live_cb('dm.threemarks', {'battleSection': 2})
            self.assertEqual(preview.state['battleSection'], 2)
            self.assertEqual(preview.state['target'], 0)
            self.assertIn(('dm.threemarks', 'previewTarget', 0), fake_api.controls)

            # Full settings dict with unchanged previewTarget still auto-switches Hangar -> Battle on v3* edits
            fake_api.live_cb('dm.threemarks', {'previewTarget': 1, 'vhBarStyle': 3})
            self.assertEqual(preview.state['target'], 1)
            fake_api.live_cb('dm.threemarks', {'previewTarget': 1, 'v3DamageLabel': 1})
            self.assertEqual(preview.state['target'], 0)

            # Committing custom TextInput values updates the corresponding tab's preview image cleanly
            fake_api.live_cb('dm.threemarks', {'v3DamageCustomLabel': u'Тест 22 323'})
            self.assertEqual(store.get('v3DamageCustomLabel'), u'Тест 22 323')
            battle_imgs = [img for img in fake_api.images if img[1] == 'marksLivePreview']
            self.assertIn(u'Тест 22 323', _decode_svg(battle_imgs[-1][2]))

            fake_api.live_cb('dm.threemarks', {'v3BarStyle': 3, 'v3BarCustomText': u'LIVE BAR'})
            battle_imgs = [img for img in fake_api.images if img[1] == 'marksLivePreview']
            self.assertIn(u'LIVE BAR', _decode_svg(battle_imgs[-1][2]))

            ref_before = refreshes[0]
            fake_api.live_cb('dm.threemarks', {'vhBarStyle': 3, 'vhBarCustomText': u'HANGAR LIVE'})
            hangar_imgs = [img for img in fake_api.images if img[1] == 'marksLivePreviewHangar']
            self.assertIn(u'HANGAR LIVE', _decode_svg(hangar_imgs[-1][2]))
            self.assertGreater(refreshes[0], ref_before)

            # TextInput fields rely on instant live typing without an inline button, and flush preview immediately
            text_ctls = dict(
                (c.get('varName'), c)
                for tab in fake_api.templates[0][1]['column1']
                for c in (tab.get('items') if tab.get('type') == 'Tab' else [tab])
                if c.get('type') == 'TextInput'
            )
            for key in ('v3BarCustomText', 'v3DamageCustomLabel', 'vhBarCustomText'):
                self.assertIn(key, text_ctls)
                self.assertFalse(text_ctls[key].get('button'))
            fake_api.live_cb('dm.threemarks', {'v3BarCustomText': u'INSTANT TEXT'})
            self.assertEqual(store.get('v3BarCustomText'), u'INSTANT TEXT')
            self.assertTrue(preview.state.get('textChanged'))
            battle_imgs = [img for img in fake_api.images if img[1] == 'marksLivePreview']
            self.assertIn(u'INSTANT TEXT', _decode_svg(battle_imgs[-1][2]))
            fake_api.live_cb('dm.threemarks', {'v3BarHeight': 6})
            self.assertFalse(preview.state.get('textChanged'))

            # Hangar previewStateHangar syncs twin Battle previewState and updates both previews
            fake_api.live_cb('dm.threemarks', {'previewStateHangar': 1})
            self.assertEqual(preview.state['uiState'], 1)
            self.assertEqual(preview.state['state'], 'minus')
            self.assertIn(('dm.threemarks', 'previewState', 1), fake_api.controls)

            # Resetting Battle Preset 1 also restores uiScale to built-in default (0.9)
            fake_api.live_cb('dm.threemarks', {'uiScale': 1.4})
            self.assertEqual(store.get('uiScale'), 1.4)
            fake_api.button_cb('dm.threemarks', 'v3ResetPreset')
            self.assertAlmostEqual(store.get('uiScale'), 0.9, places=3)
            self.assertTrue(any(k == 'uiScale' and abs(v - 0.9) < 1e-3 for _, k, v in fake_api.controls))

            # Variant switch 0 -> 1 -> 0 maps battleSection (4 <-> 1) and keeps 2 top tabs
            fake_api.live_cb('dm.threemarks', {'battleSection': 4})
            fake_api.live_cb('dm.threemarks', {'battlePanelVariant': 1})
            self.assertEqual(preview.state['battleSection'], 1)
            self.assertIn(('dm.threemarks', 'battleSection', 1), fake_api.controls)
            reloaded_leg = dict((t['title'], t['items']) for t in fake_api.reloaded[-1][1]['column1'] if t.get('type') == 'Tab')
            self.assertEqual(set(reloaded_leg.keys()), set([u'Боевая панель', u'Ангар']))
            self.assertEqual(len([c for c in reloaded_leg[u'Боевая панель'] if c.get('varName') == 'battleSection'][0]['options']), 2)
            fake_api.live_cb('dm.threemarks', {'battlePanelVariant': 0})
            self.assertEqual(preview.state['battleSection'], 4)
            self.assertIn(('dm.threemarks', 'battleSection', 4), fake_api.controls)
            reloaded_v3 = dict((t['title'], t['items']) for t in fake_api.reloaded[-1][1]['column1'] if t.get('type') == 'Tab')
            self.assertEqual(set(reloaded_v3.keys()), set([u'Боевая панель', u'Ангар']))
            self.assertEqual(len([c for c in reloaded_v3[u'Боевая панель'] if c.get('varName') == 'battleSection'][0]['options']), 5)

            # Cancel/close-without-saving after live switch Киберспорт (0) -> Корбен (1) reverts config & resyncs template on reopen
            for h_fn in list(fake_api.onWindowOpened.handlers):
                h_fn()
            fake_api.live_cb('dm.threemarks', {'battlePanelVariant': 1})
            self.assertEqual(store.get('battlePreset'), 1)
            self.assertFalse(adapter._tpl_v3)
            for h_fn in list(fake_api.onWindowClosed.handlers):
                h_fn()
            self.assertEqual(store.get('battlePreset'), 0)
            self.assertFalse(store.get('battlePercentOnly'))
            self.assertTrue(adapter._tpl_v3)
            self.assertTrue(adapter._need_tpl_resync)
            reloads_before_reopen = len(fake_api.reloaded)
            for h_fn in list(fake_api.onWindowOpened.handlers):
                h_fn()
            self.assertEqual(len(fake_api.reloaded), reloads_before_reopen + 1)
            self.assertFalse(adapter._need_tpl_resync)
            reopened_v3 = dict((t['title'], t['items']) for t in fake_api.reloaded[-1][1]['column1'] if t.get('type') == 'Tab')
            self.assertEqual(len([c for c in reopened_v3[u'Боевая панель'] if c.get('varName') == 'battleSection'][0]['options']), 5)
            battle_imgs = [img for img in fake_api.images if img[1] == 'marksLivePreview']
            self.assertIn(u'<svg ', _decode_svg(battle_imgs[-1][2]))

            adapter.unregister()
            self.assertTrue(fake_api.unregistered_live)
            self.assertEqual(len(fake_api.input_previews), 0)
            self.assertEqual(len(fake_api.onWindowOpened.handlers), 0)
            self.assertEqual(len(fake_api.onWindowClosed.handlers), 0)
        finally:
            if prev_aslain is None:
                sys.modules.pop('gui.aslainMenu', None)
            else:
                sys.modules['gui.aslainMenu'] = prev_aslain
            if prev_gui is None:
                sys.modules.pop('gui', None)

    def test_assist_and_tempo_auto_and_manual_sizing(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        sample = dict(PREVIEW_SAMPLES_V3['plus'])

        # Additive panel width (10..200) scales content width and auto font/icon sizes
        base_cfg = dict(DEFAULT_CONFIG)
        base_cfg.update({'v3MinWidth': 0, 'v3AssistSize': 0, 'v3TempoSize': 0})
        base_m = metrics.compute(base_cfg, sample, alt=False)
        for extra in (10, 50, 200):
            cfg_w = dict(base_cfg, v3MinWidth=extra)
            m_w = metrics.compute(cfg_w, sample, alt=False)
            self.assertEqual(m_w['winW'], base_m['winW'] + extra)

        wide_cfg = dict(base_cfg, v3MinWidth=120)
        wide_m = metrics.compute(wide_cfg, sample, alt=False)
        self.assertGreater(wide_m['astSize'], 14)
        self.assertGreater(wide_m['astIconSize'], 15)
        self.assertGreater(wide_m['thrSize'], 13)

        # Manual sizes override auto scaling cleanly
        man_cfg = dict(DEFAULT_CONFIG)
        man_cfg.update({'v3AssistSize': 20, 'v3TempoSize': 18})
        man_m = metrics.compute(man_cfg, sample, alt=False)
        self.assertEqual(man_m['astSize'], 20)
        self.assertEqual(man_m['astIconSize'], 21)
        self.assertEqual(man_m['thrSize'], 18)

    def test_equal_assist_channels_are_both_inactive(self):
        from dm_threemarks.domain.services.assist_resolver import AssistResolver
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        self.assertEqual(AssistResolver.resolve_channels(480, 480), (480, 480, 480, None))
        items_eq, active_eq, _, _ = metrics.resolve_assist(DEFAULT_CONFIG, {'spot': 480, 'track': 480})
        self.assertIsNone(active_eq)
        self.assertEqual([it['active'] for it in items_eq], [False, False])
        items_s, active_s, _, _ = metrics.resolve_assist(DEFAULT_CONFIG, {'spot': 480, 'track': 300})
        self.assertEqual(active_s, 'spot')
        self.assertEqual([it['active'] for it in items_s], [True, False])
        items_t, active_t, _, _ = metrics.resolve_assist(DEFAULT_CONFIG, {'spot': 300, 'track': 480})
        self.assertEqual(active_t, 'track')
        self.assertEqual([it['active'] for it in items_t], [False, True])

    def test_font_presets_all_8_metrics_svg_and_menu(self):
        self.assertEqual(DEFAULT_CONFIG['v3Font'], 2)
        self.assertEqual(DEFAULT_CONFIG['vhFont'], 2)
        self.assertEqual(DEFAULT_CONFIG['v3Density'], 0)
        self.assertEqual(DEFAULT_CONFIG['uiScale'], 0.9)
        self.assertEqual(DEFAULT_CONFIG['vhScale'], 1.1)
        self.assertEqual(DEFAULT_CONFIG['vhDensity'], 0)
        self.assertEqual(DEFAULT_CONFIG['vhFrameStyle'], 2)
        self.assertEqual(DEFAULT_CONFIG['vhRadius'], 5)
        self.assertEqual(DEFAULT_CONFIG['vhBgColor'], '#131313')
        self.assertEqual(DEFAULT_CONFIG['vhBgOpacity'], 0.60)
        self.assertEqual(DEFAULT_CONFIG['vhStarsSize'], 22)
        self.assertEqual(DEFAULT_CONFIG['v3Anchor'], 1)
        self.assertNotIn('v3HideInSniper', DEFAULT_CONFIG)
        store = ConfigStore()
        conv = MenuValueConverter(store)
        self.assertEqual(conv.convert('v3Font', 99), 7)
        self.assertEqual(conv.convert('vhFont', -3), 0)
        self.assertEqual(store.to_v3_from_hangar({'vhFont': 5})['v3Font'], 5)

        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        sample = dict(PREVIEW_SAMPLES_V3['plus'])

        expected_svg_families = (
            u'ThreeMarksPFDINMax', u'Warhelios', u'ThreeMarksDINRound', u'ThreeMarksJura',
            u'ThreeMarksExo2', u'ThreeMarksRubik', u'ThreeMarksFiraCond', u'ThreeMarksTektur',
        )
        base_m = metrics.compute(dict(DEFAULT_CONFIG, v3Font=0), sample, alt=False)
        for idx in range(8):
            cfg = dict(DEFAULT_CONFIG, v3Font=idx)
            m = metrics.compute(cfg, sample, alt=False)
            uri, bw, bh = renderer.render_v3_svg(cfg, sample, alt=False)
            svg = _decode_svg(uri)
            self.assertGreater(bw, 0)
            self.assertGreater(bh, 0)
            self.assertIn(u'<svg ', svg)
            self.assertIn(expected_svg_families[idx], svg)
            self.assertNotIn(u'@font-face', svg)
            self.assertNotIn(u'Arial', svg)
            self.assertNotIn(u'sans-serif', svg)
            if idx == 0:
                self.assertEqual(m['winW'], base_m['winW'])
            else:
                self.assertGreaterEqual(m['winW'], base_m['winW'])
        classic_uri, _cw, _ch = renderer.render_classic_svg(store, PREVIEW_SAMPLES['plus'], 1)
        classic_svg = _decode_svg(classic_uri)
        self.assertNotIn(u'@font-face', classic_svg)
        self.assertNotIn(u'Arial', classic_svg)
        self.assertNotIn(u'sans-serif', classic_svg)

    def test_aslain_live_preview_throttled_and_deduplicated(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from in_memory_adapters import FakeClock, FakeScheduler, MemoryConfigRepository, MemoryLogger
        from dm_threemarks.application.use_cases.config_sync import ConfigSyncService

        class _Api(object):
            def __init__(self):
                self.images = []
                self.live_cb = None

            def getVersionTuple(self):
                return (2, 1, 15)

            def setModTemplate(self, linkage, template, apply_cb, button_cb=None):
                return {}

            def registerLiveSettingsChange(self, linkage, cb, include_all=False):
                self.live_cb = cb

            def updateImage(self, linkage, var_name, src, w, h):
                self.images.append((linkage, var_name, src, w, h))

        class _Tpl(_FakeTpl):
            def createTab(self, title, items):
                return [{'type': 'Tab', 'title': title, 'items': items}]

            def createInput(self, text, key, val, **kw):
                return {'type': 'TextInput', 'text': text, 'varName': key, 'value': val}

            def createActionButton(self, var_name, btn_text, label=None, **kw):
                return {'type': 'Button', 'varName': var_name, 'text': label, 'btnText': btn_text}

            def visibleWhen(self, ctl, master, val, indent=False, condition='=='):
                return ctl

        api = _Api()
        tpl = _Tpl()
        aslain_mod = type(sys)('gui.aslainMenu')
        aslain_mod.g_modsSettingsApi = api
        aslain_mod.templates = tpl
        prev_gui = sys.modules.get('gui')
        prev_aslain = sys.modules.get('gui.aslainMenu')
        if prev_gui is None:
            sys.modules['gui'] = type(sys)('gui')
        sys.modules['gui.aslainMenu'] = aslain_mod
        try:
            logger = MemoryLogger()
            clock = FakeClock(now=100.0)
            sched = FakeScheduler()
            store = ConfigStore(logger=logger)
            sync = ConfigSyncService(MemoryConfigRepository(), store, clock, logger)
            metrics = V3MetricsCalculator(store)
            svg = V3SvgRenderer(metrics, store)
            preview = MenuPreviewRenderer(store, svg)
            builder = MenuTemplateBuilder(MenuValueConverter(store), preview)
            adapter = AslainMenuAdapter(store, sync, preview, builder, logger, clock=clock, scheduler=sched)
            adapter.register()
            base_imgs = len(api.images)

            # 10 rapid slider ticks within 1ms -> only 1 immediate update + 1 coalesced update on timer flush
            for step in range(10):
                clock.advance(0.001)
                api.live_cb('dm.threemarks', {'v3MinWidth': (step + 1) * 10})
            self.assertEqual(len(api.images) - base_imgs, 1)
            self.assertEqual(len(sched.scheduled), 1)
            clock.advance(0.1)
            for hid, cb in list(sched.scheduled.items()):
                sched.scheduled.pop(hid)
                cb()
            self.assertEqual(len(api.images) - base_imgs, 2)

            # Identical value after interval produces 0 extra updateImage calls
            clock.advance(0.2)
            api.live_cb('dm.threemarks', {'v3MinWidth': 100})
            self.assertEqual(len(api.images) - base_imgs, 2)
        finally:
            if prev_aslain is None:
                sys.modules.pop('gui.aslainMenu', None)
            else:
                sys.modules['gui.aslainMenu'] = prev_aslain
            if prev_gui is None:
                sys.modules.pop('gui', None)

    def test_long_wide_custom_text_auto_fits_inside_panel(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        sample = dict(PREVIEW_SAMPLES_V3['plus'])
        wide_text = u'Ж' * 24

        for font_idx in range(8):
            cfg = dict(DEFAULT_CONFIG)
            cfg.update({
                'v3Font': font_idx,
                'v3BarStyle': 3,
                'v3BarCustomText': wide_text,
                'v3BarTextSize': 18,
                'v3DamageLabel': 1,
                'v3DamageCustomLabel': wide_text,
            })
            m = metrics.compute(cfg, sample, alt=False)
            self.assertLessEqual(m['cw'], 178 + 80)
            self.assertGreaterEqual(m['barTextSize'], 8)
            self.assertLess(m['barTextSize'], 18)
            self.assertLessEqual(m['barTextW'], m['cw'])
            self.assertGreaterEqual(m['dmgLblSize'], 8)
            self.assertLess(m['dmgLblSize'], m['dmgSize'])

            uri, _bw, _bh = renderer.render_v3_svg(cfg, sample, alt=False)
            svg = _decode_svg(uri)
            self.assertIn(u'text-anchor="middle"', svg)
            self.assertIn(u'clipPath id="v3tb"', svg)

        # Adding extra panel width via v3MinWidth=120 lets the fitted font grow back toward 18px
        m_narrow = metrics.compute(dict(DEFAULT_CONFIG, v3BarStyle=3, v3BarCustomText=wide_text, v3BarTextSize=18, v3MinWidth=0), sample, alt=False)
        m_wide = metrics.compute(dict(DEFAULT_CONFIG, v3BarStyle=3, v3BarCustomText=wide_text, v3BarTextSize=18, v3MinWidth=120), sample, alt=False)
        self.assertGreater(m_wide['winW'], m_narrow['winW'])
        self.assertGreater(m_wide['barTextSize'], m_narrow['barTextSize'])

    def test_custom_bar_text_svg_clip_prevents_edge_bleed(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        phrase = u'СИМВОЛ ЕБАНЫЙ ПИДАРАС'
        anchor_re = re.compile(r'<rect x="([0-9.]+)" y="([0-9.]+)" width="([0-9.]+)" height="([0-9.]+)" fill="#000000" fill-opacity="0\.01"/>')
        v3tb_re = re.compile(r'<clipPath id="v3tb" shape-rendering="optimizeSpeed"><rect x="([0-9.]+)" y="([0-9.]+)" width="([0-9.]+)" height="([0-9.]+)"/></clipPath>')
        v3tc_re = re.compile(r'<clipPath id="v3tc" shape-rendering="optimizeSpeed"><rect x="([0-9.]+)" y="([0-9.]+)" width="([0-9.]+)" height="([0-9.]+)"/></clipPath>')

        for font_idx in (0, 2, 3, 7):
            for pct in (15.0, 43.28, 85.0, 100.0):
                cfg = dict(DEFAULT_CONFIG, v3Font=font_idx, v3BarStyle=3, v3BarCustomText=phrase, v3BarTextSize=15)
                sample = dict(PREVIEW_SAMPLES_V3['plus'], pct=pct)
                uri, win_w, _win_h = renderer.render_v3_svg(cfg, sample, alt=False)
                svg = _decode_svg(uri)

                m_tb = v3tb_re.search(svg)
                m_tc = v3tc_re.search(svg)
                self.assertIsNotNone(m_tb)
                self.assertIsNotNone(m_tc)
                bx, _by, bw, _bh = [float(v) for v in m_tb.groups()]
                cx, cy, cw, ch = [float(v) for v in m_tc.groups()]
                for coord in (cx, cy, cw, ch):
                    self.assertEqual(coord, float(int(coord)))

                g_tc_pos = svg.find(u'<g clip-path="url(#v3tc)">')
                self.assertNotEqual(g_tc_pos, -1)
                g_tc_seg = svg[g_tc_pos:]
                anchors = anchor_re.findall(g_tc_seg)
                self.assertEqual(len(anchors), 2)
                left_x = float(anchors[0][0])
                right_x = float(anchors[1][0])
                self.assertEqual(left_x, 0.0)
                self.assertGreater(right_x, bx + bw)
                self.assertEqual(right_x, max(bx + bw + 1.0, float(win_w) - 1.0))
                self.assertLess(left_x + 1.0, cx)
                self.assertLessEqual(cx + cw, bx + bw)
                self.assertLess(cx + cw, right_x)

        cfg_zero = dict(DEFAULT_CONFIG, v3Font=2, v3BarStyle=3, v3BarCustomText=phrase, v3BarTextSize=15)
        sample_zero = dict(PREVIEW_SAMPLES_V3['plus'], pct=0.0, dmg=0)
        uri_zero, _w0, _h0 = renderer.render_v3_svg(cfg_zero, sample_zero, alt=False)
        svg_zero = _decode_svg(uri_zero)
        self.assertIn(u'<clipPath id="v3tb" shape-rendering="optimizeSpeed">', svg_zero)
        self.assertNotIn(u'id="v3tc"', svg_zero)
        self.assertNotIn(u'clip-path="url(#v3tc)"', svg_zero)

    def test_v3_damage_row_centered_without_label(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        sample = dict(PREVIEW_SAMPLES_V3['plus'])

        cfg_right = dict(DEFAULT_CONFIG, v3DamageLabel=2)
        cfg_center = dict(DEFAULT_CONFIG, v3DamageLabel=3)
        m_right = metrics.compute(cfg_right, sample, alt=False)
        m_center = metrics.compute(cfg_center, sample, alt=False)
        self.assertEqual(m_center['dmgLblText'], u'')
        self.assertEqual(m_center['dmgLblMode'], 3)
        self.assertEqual(m_right['winW'], m_center['winW'])

        svg_right = _decode_svg(renderer.render_v3_svg(cfg_right, sample, alt=False)[0])
        svg_center = _decode_svg(renderer.render_v3_svg(cfg_center, sample, alt=False)[0])
        m_r = re.search(r'<text x="([0-9.]+)"[^>]*text-anchor="(end|start)"[^>]*>/ 1480</text>', svg_right)
        m_c = re.search(r'<text x="([0-9.]+)"[^>]*text-anchor="(end|start)"[^>]*>/ 1480</text>', svg_center)
        self.assertIsNotNone(m_r)
        self.assertIsNotNone(m_c)
        self.assertEqual(m_r.group(2), u'end')
        self.assertEqual(m_c.group(2), u'start')
        self.assertLess(float(m_c.group(1)), m_center['cx'] + m_center['cw'])
        self.assertAlmostEqual(float(m_r.group(1)), m_right['cx'] + m_right['cw'], places=1)

    def test_smart_contextual_colors_placement_and_uniqueness(self):
        from dm_threemarks.adapters.menu.schema import MENU_COLORS, MENU_VH_COLORS, MENU_V3_COLORS

        class _GateTpl(_FakeTpl):
            def createTab(self, title, items):
                return [{'type': 'Tab', 'title': title, 'items': items}]

            def createInput(self, text, key, val, **kw):
                return {'type': 'TextInput', 'text': text, 'varName': key, 'value': val}

            def visibleWhen(self, ctl, master, val, indent=False, condition='=='):
                ctl['masterVarName'] = master
                ctl['masterValue'] = val
                ctl['gateHides'] = True
                ctl['masterIndent'] = bool(indent)
                if condition != '==':
                    ctl['condition'] = condition
                return ctl

        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)
        preview = MenuPreviewRenderer(store, renderer)
        builder = MenuTemplateBuilder(MenuValueConverter(store), preview)
        tpl = builder.build(_GateTpl(), (2, 1, 15), show_v3=True)

        tabs = dict((t['title'], t['items']) for t in tpl['column1'] if t.get('type') == 'Tab')
        self.assertEqual(set(tabs.keys()), set([u'Боевая панель', u'Ангар']))
        by_key = {}
        tab_of = {}
        dups = []
        for title, items in tabs.items():
            for comp in items:
                vn = comp.get('varName')
                if not vn:
                    continue
                if vn in by_key:
                    dups.append(vn)
                by_key[vn] = comp
                tab_of[vn] = title
        self.assertEqual(dups, [])
        self.assertNotIn('v3Anchor', by_key)
        self.assertEqual(tab_of['battleSection'], u'Боевая панель')
        self.assertEqual(tab_of['hangarSection'], u'Ангар')
        self.assertNotIn('span', by_key['battleSection'])
        self.assertNotIn('span', by_key['hangarSection'])

        def _bsec(comp):
            if comp.get('masterVarName') == 'battleSection':
                return comp.get('masterValue')
            ms = [c['masterValue'] for c in comp.get('conditions', ()) if c.get('masterVarName') == 'battleSection']
            return ms[0] if len(ms) == 1 else None

        expected_colors = MENU_V3_COLORS + MENU_VH_COLORS + MENU_COLORS
        for ck in expected_colors:
            self.assertIn(ck, by_key)

        # v3BarCustomColor placed directly after v3BarColorMode in 'Боевая панель' (battleSection == 2) with smart gates + indent
        b_keys = [c.get('varName') for c in tabs[u'Боевая панель'] if c.get('varName')]
        self.assertEqual(tab_of['v3BarCustomColor'], u'Боевая панель')
        self.assertEqual(b_keys.index('v3BarCustomColor'), b_keys.index('v3BarColorMode') + 1)
        self.assertTrue(by_key['v3BarCustomColor'].get('masterIndent'))
        self.assertEqual(
            {(c['masterVarName'], c.get('condition', '==')): c['masterValue'] for c in by_key['v3BarCustomColor']['conditions']},
            {('battleSection', '=='): 2, ('battlePanelVariant', '=='): 0, ('v3BarStyle', '!='): 2, ('v3BarColorMode', '=='): 2},
        )

        # Frame & star colors placed in battleSection == 1 with smart visibility + indent
        for fk in ('v3BgColor', 'v3CornerColor', 'v3StarOnColor', 'v3StarOffColor'):
            self.assertEqual(tab_of[fk], u'Боевая панель')
            self.assertEqual(_bsec(by_key[fk]), 1)
            self.assertTrue(by_key[fk].get('masterIndent'))
        self.assertIn(
            {'masterVarName': 'v3BgOpacity', 'masterValue': 0.01, 'condition': '>'},
            by_key['v3BgColor']['conditions'],
        )
        self.assertIn(
            {'masterVarName': 'v3StarsStyle', 'masterValue': [0, 1]},
            by_key['v3StarOnColor']['conditions'],
        )

        # Hangar colors placed under their respective sections in 'Ангар' with smart gates
        for hk in MENU_VH_COLORS:
            self.assertEqual(tab_of[hk], u'Ангар')
        for h_ind in ('vhBgColor', 'vhCornerColor', 'vhStarOnColor', 'vhStarOffColor'):
            self.assertTrue(by_key[h_ind].get('masterIndent'))
            self.assertIn({'masterVarName': 'hangarSection', 'masterValue': 1}, by_key[h_ind]['conditions'])
        for h_col in ('vhBarColor', 'vhTextMain', 'vhTextMuted'):
            self.assertIn({'masterVarName': 'hangarSection', 'masterValue': 3}, by_key[h_col]['conditions'])
        self.assertIn(
            {'masterVarName': 'vhBgOpacity', 'masterValue': 0.01, 'condition': '>'},
            by_key['vhBgColor']['conditions'],
        )
        self.assertIn(
            {'masterVarName': 'vhStarsStyle', 'masterValue': [0, 1]},
            by_key['vhStarOnColor']['conditions'],
        )

        # 'Цвета' subsection (battleSection == 4) contains clean labels and only the 4 accents + text colors
        colors_sec_items = [c for c in tabs[u'Боевая панель'] if c.get('varName') and _bsec(c) == 4]
        colors_by_vn = dict((c['varName'], c) for c in colors_sec_items)
        self.assertEqual(
            set(colors_by_vn.keys()),
            set(('v3AccentPlus', 'v3AccentMinus', 'v3AccentZero', 'v3AccentBig', 'v3TextMain', 'v3TextMuted') + MENU_COLORS + ('dmgFollowsSign',)),
        )
        self.assertEqual(colors_by_vn['v3AccentPlus']['text'], u'Плюс')
        self.assertEqual(colors_by_vn['v3AccentMinus']['text'], u'Минус')
        self.assertEqual(colors_by_vn['v3AccentZero']['text'], u'Ноль')
        self.assertEqual(colors_by_vn['v3AccentBig']['text'], u'Большой плюс')

    def test_damage_big_color_tempo_neutral_hangar_plus_and_zero_delta_icon(self):
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        renderer = V3SvgRenderer(metrics, store)

        # 1. Battle 'big' state colors damage number with v3AccentBig (NOT green), and keeps achieved tempo neutral
        cfg_big = dict(DEFAULT_CONFIG, v3DamageDynColor=True, v3TempoShow=0, v3AccentPlus='#11AA22', v3AccentBig='#BB55FF')
        sample_big = dict(PREVIEW_SAMPLES_V3['big'], dmg=6820, tHold=3750, tNext=2150, t95=3450, tNextPct=85)
        svg_big = _decode_svg(renderer.render_v3_svg(cfg_big, sample_big, alt=False)[0])
        self.assertIn(u'fill="#BB55FF">6820</text>', svg_big)
        self.assertNotIn(u'fill="#11AA22">6820</text>', svg_big)
        self.assertIn(u'fill="#FFFFFF">2150</text>', svg_big)
        self.assertIn(u'fill="#FFFFFF">3450</text>', svg_big)
        self.assertNotIn(u'fill="#11AA22">85%</text>', svg_big)
        self.assertNotIn(u'fill="#11AA22">2150</text>', svg_big)

        # 2. Hangar thresholds highlight using v3AccentPlus ('Плюс') permanently by marks, never highlighting 100%, while bar uses vhBarColor
        cfg_h = dict(DEFAULT_CONFIG, v3AccentPlus='#22CC44', vhBarColor='#FFAA00')
        v3_h = store.to_v3_from_hangar(cfg_h)
        sample_h = dict(PREVIEW_SAMPLES_V3['zero'], isHangar=True, delta=None, pct=84.02, marks=2, dmg=4367)
        svg_h = _decode_svg(renderer.render_v3_svg(v3_h, sample_h, alt=False)[0])
        self.assertIn(u'fill="#FFAA00"', svg_h)
        self.assertIn(u'fill="#22CC44">65%</text>', svg_h)
        self.assertIn(u'fill="#22CC44">85%</text>', svg_h)
        self.assertNotIn(u'fill="#22CC44">95%</text>', svg_h)
        self.assertNotIn(u'fill="#22CC44">100%</text>', svg_h)
        self.assertNotIn(u'fill="#FFAA00">65%</text>', svg_h)

        sample_h3 = dict(PREVIEW_SAMPLES_V3['big'], isHangar=True, delta=None, pct=100.0, marks=3, dmg=6200)
        svg_h3 = _decode_svg(renderer.render_v3_svg(v3_h, sample_h3, alt=False)[0])
        self.assertIn(u'fill="#22CC44">65%</text>', svg_h3)
        self.assertIn(u'fill="#22CC44">85%</text>', svg_h3)
        self.assertIn(u'fill="#22CC44">95%</text>', svg_h3)
        self.assertNotIn(u'fill="#22CC44">100%</text>', svg_h3)

        # 3. Zero delta state displays '0.00%' (no '+') and neutral icon for both triangle (diamond) & arrow (right)
        sample_z = dict(PREVIEW_SAMPLES_V3['zero'], delta=0.004)
        svg_z_tri = _decode_svg(renderer.render_v3_svg(dict(DEFAULT_CONFIG, v3DeltaIcon=0), sample_z, alt=False)[0])
        svg_z_arr = _decode_svg(renderer.render_v3_svg(dict(DEFAULT_CONFIG, v3DeltaIcon=1), sample_z, alt=False)[0])
        self.assertIn(u'>0.00%</text>', svg_z_tri)
        self.assertNotIn(u'>+0.00%</text>', svg_z_tri)
        self.assertIn(u'<polygon points="', svg_z_tri)
        self.assertIsNotNone(re.search(r'M ([0-9.]+) ([0-9.]+) L ([0-9.]+) \2 M', svg_z_arr))

    def test_tektur_jura_width_scale_lesta_curve_and_pending_thresholds(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from in_memory_adapters import FakeClock, MemoryConfigRepository, MemoryLogger
        from dm_threemarks.adapters.presenters.hangar_presenter import HangarPayloadPresenter
        from dm_threemarks.adapters.v3.svg_primitives import font_spec
        from dm_threemarks.application.use_cases.config_sync import ConfigSyncService
        from dm_threemarks.application.use_cases.hangar_session import HangarSessionService
        from dm_threemarks.domain.entities.curve import Curve
        from dm_threemarks.domain.entities.mark_snapshot import MarkSnapshot
        from dm_threemarks.domain.entities.server_epoch import ServerEpoch
        from dm_threemarks.domain.services.forecast_engine import ForecastEngine
        from dm_threemarks.domain.services.threshold_calculator import ThresholdCalculator

        self.assertAlmostEqual(font_spec(3)['width_scale'], 1.30, places=2)
        self.assertAlmostEqual(font_spec(7)['width_scale'], 1.30, places=2)
        store = ConfigStore()
        metrics = V3MetricsCalculator(store)
        h_pfd = metrics.compute(
            store.to_v3_from_hangar(dict(DEFAULT_CONFIG, vhFont=0)),
            dict(PREVIEW_SAMPLES_V3['zero'], isHangar=True),
        )
        h_tektur = metrics.compute(
            store.to_v3_from_hangar(dict(DEFAULT_CONFIG, vhFont=7)),
            dict(PREVIEW_SAMPLES_V3['zero'], isHangar=True),
        )
        self.assertGreaterEqual(h_tektur['hCol0W'], 65)
        self.assertGreater(h_tektur['hCol0W'], h_pfd['hCol0W'])

        # Non-exact 14-point Lesta/Poliroid curve must NOT overwrite dossier percentage
        raw_14 = {'20': 900, '40': 1400, '55': 1900, '65': 2300, '85': 3400, '95': 4300, '100': 5100}
        non_exact = Curve(raw_14, day=739000)
        self.assertFalse(non_exact.exact)
        fe = ForecastEngine(ServerEpoch())
        now_ts = 1795500000.0
        mark = MarkSnapshot(14881, 81.31, 3100.0, 200, 1, 0)
        pct_out, recomp = fe.current_percent(mark, non_exact, now_ts, lambda *a: None)
        self.assertFalse(recomp)
        self.assertAlmostEqual(pct_out, 81.31, places=2)

        # HangarSessionService waits while curve is pending instead of flashing fallback thresholds
        class _FakeCurves(object):
            def __init__(self):
                self.pending = True
                self.curve = None
                self.version = 1

            def is_pending(self, _cd):
                return self.pending

            def request_calc(self, _cd):
                pass

            def curve_for(self, _cd):
                return self.curve

            def day_curve(self, *a):
                return None

            def pump(self):
                return False

        class _FakeDossier(object):
            def get_current_vehicle_info(self):
                return (14881, 10)

        class _FakeSnapUc(object):
            def mark_for(self, cd):
                return MarkSnapshot(cd, 87.93, 3829.0, 504, 3, 0)

            def witness_epoch(self, *a):
                pass

        class _FakePanel(object):
            def __init__(self):
                self.window = None
                self.settings_controller = None
                self.pushes = []

            def is_settings_open(self):
                return False

            def build(self):
                pass

            def set_mini(self, _v):
                pass

            def push(self, p):
                self.pushes.append(p)

        curves = _FakeCurves()
        panel = _FakePanel()
        logger = MemoryLogger()
        svc = HangarSessionService(
            store, ConfigSyncService(MemoryConfigRepository(), store, FakeClock(), logger),
            _FakeDossier(), curves, _FakeSnapUc(), fe, ThresholdCalculator(fe),
            FakeClock(), None, None, None, None, logger, HangarPayloadPresenter(), lambda: panel,
        )
        svc._panel = panel
        svc._update()
        p_wait = panel.pushes[-1]
        self.assertEqual(p_wait['pct'], u'--.--%')
        self.assertEqual(p_wait['ema'], u'—')
        self.assertEqual(p_wait['t65'], u'—')
        self.assertEqual(p_wait['bar'], 0.0)
        self.assertFalse(p_wait['v3d']['hasRating'])
        self.assertEqual(p_wait['marks'], 3)
        curves.pending = False
        curves.curve = non_exact
        svc._update()
        p_ready = panel.pushes[-1]
        self.assertEqual(p_ready['pct'], u'87.93%')
        self.assertEqual(p_ready['ema'], u'3 829')
        self.assertEqual(p_ready['v3d']['t65'], 2300)
        self.assertTrue(p_ready['v3d']['hasRating'])


if __name__ == '__main__':
    unittest.main()
