# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dm_threemarks.adapters.presenters.battle_presenter import BattlePayloadPresenter
from dm_threemarks.adapters.presenters.hangar_presenter import HangarPayloadPresenter
from dm_threemarks.application.config.validator import ConfigStore
from dm_threemarks.application.use_cases.battle_session import BattleSessionService
from dm_threemarks.application.use_cases.config_sync import ConfigSyncService
from dm_threemarks.application.use_cases.curve_sync_service import CurveSyncService
from dm_threemarks.application.use_cases.hangar_session import HangarSessionService
from dm_threemarks.application.use_cases.snapshot_vehicle import SnapshotVehicleUseCase
from dm_threemarks.domain.entities.server_epoch import ServerEpoch
from dm_threemarks.domain.entities.mark_snapshot import VehicleDossier
from dm_threemarks.domain.services.forecast_engine import ForecastEngine
from dm_threemarks.domain.services.threshold_calculator import ThresholdCalculator
from dm_threemarks.domain.value_objects.damage_report import DamageReport
from in_memory_adapters import (
    FakeClock,
    FakeHangarEnvironment,
    FakeInputProvider,
    FakeScheduler,
    MemoryCacheRepository,
    MemoryConfigRepository,
    MemoryDossierProvider,
    MemoryLogger,
    MemoryMasteryGateway,
    MemoryPanelView,
    MemorySettingsMenu,
)


class FakeTracker(object):
    def __init__(self, on_changed):
        self.on_changed = on_changed
        self.started = False
        self.stopped = False
        self.current = DamageReport(damage=1800, radio=750, track=200, source='feedback')

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def on_summary(self, summary):
        pass

    def report(self):
        return self.current


class TestApplicationUseCases(unittest.TestCase):

    def _build_deps(self):
        logger = MemoryLogger()
        clock = FakeClock()
        cfg_repo = MemoryConfigRepository({'v3BarStyle': 3, 'barStyleVersion': 2, 'hangarOnlyRandom': False})
        cfg_store = ConfigStore(logger=logger)
        cache_repo = MemoryCacheRepository()
        menu = MemorySettingsMenu()
        cfg_sync = ConfigSyncService(cfg_repo, cfg_store, clock, logger, menu_port=menu)
        cfg_sync.load_initial()

        dossier = MemoryDossierProvider()
        gateway = MemoryMasteryGateway()
        curves = CurveSyncService(cache_repo, gateway, dossier, cfg_store, clock, logger)
        epoch = ServerEpoch()
        forecast = ForecastEngine(epoch)
        thr_calc = ThresholdCalculator(forecast)
        snapshot_uc = SnapshotVehicleUseCase(dossier, cache_repo, curves, forecast, epoch, clock, logger)
        sched = FakeScheduler()
        inp = FakeInputProvider()
        env = FakeHangarEnvironment()
        return {
            'logger': logger, 'clock': clock, 'cfg_repo': cfg_repo, 'cfg_store': cfg_store,
            'cache_repo': cache_repo, 'menu': menu, 'cfg_sync': cfg_sync,
            'dossier': dossier, 'gateway': gateway, 'curves': curves, 'epoch': epoch,
            'forecast': forecast, 'thr_calc': thr_calc, 'snapshot_uc': snapshot_uc,
            'sched': sched, 'inp': inp, 'env': env,
        }

    def test_config_enforces_hangar_random_and_preserves_pos_on_reload(self):
        d = self._build_deps()
        self.assertTrue(d['cfg_store'].get('hangarOnlyRandom'))
        self.assertFalse(d['cfg_store'].get('hideUnderWindows'))
        self.assertEqual(d['cfg_store'].get('v3BarStyle'), 3)

        d['cfg_store'].set('x', -0.25)
        d['cfg_repo'].data = {'x': 0.99, 'v3BarTextSize': 20}
        d['cfg_repo'].mtime = 2.0
        d['clock'].advance(3.0)
        reloaded = d['cfg_sync'].poll()
        self.assertTrue(reloaded)
        self.assertEqual(d['cfg_store'].get('x'), -0.25)
        self.assertEqual(d['cfg_store'].get('v3BarTextSize'), 20)
        self.assertEqual(d['menu'].push_calls, 1)

    def test_curve_sync_and_battle_session_with_in_memory_adapters(self):
        d = self._build_deps()
        d['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)
        d['dossier'].battle_ctx = {'int_cd': 10529, 'is_spg': False, 'is_random': True}

        knots = {20: 600, 40: 1100, 55: 1500, 65: 1850, 75: 2250, 85: 2700, 95: 3300, 100: 3800}
        points = {}
        kkeys = sorted(knots.keys())
        for i in range(len(kkeys) - 1):
            p0, p1 = kkeys[i], kkeys[i + 1]
            d0, d1 = knots[p0], knots[p1]
            for q in range(p0, p1 + 1):
                points[str(q)] = d0 + (d1 - d0) * (q - p0) // (p1 - p0)

        panel = MemoryPanelView()
        tracker_holder = []

        def make_tracker(cb):
            t = FakeTracker(cb)
            tracker_holder.append(t)
            return t

        battle = BattleSessionService(
            d['cfg_store'], d['cfg_sync'], d['cache_repo'], d['dossier'],
            d['curves'], d['snapshot_uc'], d['forecast'], d['thr_calc'],
            d['clock'], d['sched'], d['inp'], d['logger'],
            BattlePayloadPresenter(d['cfg_store']), lambda: panel, make_tracker,
        )
        battle.start()
        self.assertTrue(panel.built)
        self.assertTrue(tracker_holder[0].started)
        self.assertGreaterEqual(len(d['gateway'].curve_requests), 1)
        self.assertEqual(d['gateway'].curve_requests[0][0], '10529')

        d['gateway'].queued.append(('curve', '10529', points, d['clock'].now() - 86400, None))
        d['inp'].alt = True
        d['clock'].advance(1.0)
        battle._tick()

        last_push = panel.pushed[-1]
        self.assertEqual(last_push['v3d']['dmg'], 2550)
        self.assertTrue(last_push['v3d']['alt'])
        self.assertEqual(last_push['v3d']['tHold'], 2400)
        self.assertEqual(last_push['v3d']['tNextPct'], 85)
        self.assertEqual(last_push['v3d']['tNext'], 2700)
        self.assertEqual(last_push['v3d']['t95'], 3300)

        # Item 4: tHold stays fixed across changing battle damage instead of drifting with proj_ema
        tracker_holder[0].current = DamageReport(damage=6000, radio=0, track=0, source='feedback')
        d['clock'].advance(0.1)
        battle._tick()
        self.assertEqual(panel.pushed[-1]['v3d']['dmg'], 6000)
        self.assertEqual(panel.pushed[-1]['v3d']['tHold'], 2400)

        battle.stop()
        self.assertTrue(tracker_holder[0].stopped)
        self.assertTrue(panel.destroyed)
        self.assertIn('pendingForecast', d['cache_repo'].get_entry('10529'))

    def test_hangar_session_with_in_memory_adapters(self):
        d = self._build_deps()
        d['dossier'].current_vehicle = (10529, 10)
        d['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)

        panel = MemoryPanelView()
        hangar = HangarSessionService(
            d['cfg_store'], d['cfg_sync'], d['dossier'], d['curves'],
            d['snapshot_uc'], d['forecast'], d['thr_calc'], d['clock'],
            d['sched'], d['inp'], d['env'], d['menu'], d['logger'],
            HangarPayloadPresenter(), lambda: panel,
        )
        hangar.on_lobby()
        self.assertEqual(d['logger'].errors, [])
        self.assertTrue(panel.built)
        self.assertTrue(d['menu'].registered)
        # While curve request is pending, show clean '-' / '--.--%' loading placeholders
        self.assertEqual(panel.pushed[-1]['pct'], u'--.--%')
        self.assertEqual(panel.pushed[-1]['ema'], u'—')
        self.assertEqual(panel.pushed[-1]['t65'], u'—')

        # Resolve pending request offline -> fallback metrics populate cleanly
        d['gateway'].available = False
        d['curves']._pending.clear()
        d['curves']._hist_pending.clear()
        hangar.refresh()
        last_push = panel.pushed[-1]
        self.assertEqual(last_push['pct'], u'72.50%')
        self.assertFalse(last_push['t65'].startswith(u'~'))
        self.assertIn('t100', last_push['v3d'])

        # Client IItemsCache.onSyncCompleted(reason, diff) passes 2 positional args
        hangar.on_vehicle_changed(1, {'vehicles': {}})

        # UI config change calling refresh() must push updated UI immediately without switching tank
        pushes_before = len(panel.pushed)
        d['cfg_store'].set('vhBgOpacity', 0.90)
        hangar.refresh()
        self.assertGreater(len(panel.pushed), pushes_before)

        # Switching tank in hangar must update via _tick even if onChanged did not fire
        d['dossier'].dossiers[62273] = VehicleDossier(44.11, 1071.0, 0, 28, 1700001000)
        d['dossier'].current_vehicle = (62273, 10)
        d['clock'].advance(0.1)
        hangar._tick()
        self.assertEqual(panel.pushed[-1]['pct'], u'44.11%')

        # Tier < 5 hides panel and _ensure() does not recreate it until Tier >= 5 returns
        d['dossier'].dossiers[111] = VehicleDossier(10.0, 200.0, 0, 5, 1700001000)
        d['dossier'].current_vehicle = (111, 4)
        hangar._tick()
        self.assertIsNone(hangar.panel)
        self.assertTrue(panel.destroyed)
        hangar._ensure()
        self.assertIsNone(hangar.panel)

        d['dossier'].current_vehicle = (10529, 10)
        hangar._watch_tick()
        self.assertIsNotNone(hangar.panel)
        self.assertEqual(panel.pushed[-1]['pct'], u'72.50%')

        # Switching from Tier < 5 to Tier >= 5 pushes initial payload BEFORE build()
        events = []

        class _OrderedPanel(MemoryPanelView):
            def push(self, data):
                events.append(('push', len(events)))
                super(_OrderedPanel, self).push(data)

            def build(self):
                events.append(('build', len(events)))
                super(_OrderedPanel, self).build()

        d2 = self._build_deps()
        d2['dossier'].current_vehicle = (111, 4)
        d2['dossier'].dossiers[111] = VehicleDossier(10.0, 200.0, 0, 5, 1700001000)
        d2['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)
        hangar2 = HangarSessionService(
            d2['cfg_store'], d2['cfg_sync'], d2['dossier'], d2['curves'],
            d2['snapshot_uc'], d2['forecast'], d2['thr_calc'], d2['clock'],
            d2['sched'], d2['inp'], d2['env'], d2['menu'], d2['logger'],
            HangarPayloadPresenter(), _OrderedPanel,
        )
        hangar2.on_lobby()
        self.assertIsNone(hangar2.panel)
        d2['dossier'].current_vehicle = (10529, 10)
        hangar2._watch_tick()
        self.assertIsNotNone(hangar2.panel)
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[0][0], 'push')
        self.assertEqual(events[1][0], 'build')

        # Non-random mode hides hangar panel when hangarOnlyRandom=True
        d['env'].mode = (False, 'event')
        hangar._scan_views()
        self.assertTrue(panel.destroyed)

        hangar.on_leave_lobby()

    def test_legacy_bar_style_migration(self):
        # Legacy configs without barStyleVersion should migrate {0:0, 1:1, 2:0, 3:2, 4:3}
        expected_legacy = {0: 0, 1: 1, 2: 0, 3: 2, 4: 3}
        for old_val, new_val in expected_legacy.items():
            cfg = ConfigStore.normalize_loaded({'v3BarStyle': old_val, 'vhBarStyle': old_val})
            self.assertEqual(cfg['v3BarStyle'], new_val)
            self.assertEqual(cfg['vhBarStyle'], new_val)
            self.assertEqual(cfg['barStyleVersion'], 2)

        # Already migrated configs with barStyleVersion == 2 must keep 0..3 untouched
        for cur_val in (0, 1, 2, 3):
            cfg = ConfigStore.normalize_loaded({'barStyleVersion': 2, 'v3BarStyle': cur_val, 'vhBarStyle': cur_val})
            self.assertEqual(cfg['v3BarStyle'], cur_val)
            self.assertEqual(cfg['vhBarStyle'], cur_val)
            self.assertEqual(cfg['barStyleVersion'], 2)

    def test_smooth_drag_controller_and_hangar_frame_tick(self):
        from dm_threemarks.adapters.settings.drag_controller import DragController

        class _DraggablePanel(MemoryPanelView):
            def __init__(self):
                super(_DraggablePanel, self).__init__()
                self.x = 0.0
                self.y = 0.0
                self.wPx = 220.0
                self.hPx = 140.0
                self.ui = 1.0
                self.keyX = 'hx'
                self.keyY = 'hy'
                self.mode = 'h'

            def contains(self, pos):
                return (self.x <= pos[0] <= self.x + 0.3) and (self.y - 0.3 <= pos[1] <= self.y)

            def move_to(self, x, y):
                self.x = x
                self.y = y

        d = self._build_deps()
        d['dossier'].current_vehicle = (10529, 10)
        d['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)

        panel = _DraggablePanel()
        drag = DragController(d['inp'], d['cfg_store'], d['cfg_sync'])
        cur_pos = [(0.05, -0.05)]
        d['inp'].cursor_position = lambda: cur_pos[0]
        delays = []
        orig_sched = d['sched'].schedule

        def _rec_sched(delay_sec, callback):
            delays.append(delay_sec)
            return orig_sched(delay_sec, callback)

        d['sched'].schedule = _rec_sched

        hangar = HangarSessionService(
            d['cfg_store'], d['cfg_sync'], d['dossier'], d['curves'],
            d['snapshot_uc'], d['forecast'], d['thr_calc'], d['clock'],
            d['sched'], d['inp'], d['env'], d['menu'], d['logger'],
            HangarPayloadPresenter(), lambda: panel, drag_controller=drag,
        )
        hangar.on_lobby()

        # Start Ctrl+LMB drag inside panel
        cur_pos[0] = (0.05, -0.05)
        d['inp'].lmb = True
        d['inp'].ctrl = True
        hangar._tick()
        self.assertTrue(drag.is_dragging())
        self.assertEqual(delays[-1], hangar.DRAG_TICK)

        # Even if Ctrl is released while LMB stays down, dragging continues smoothly
        d['inp'].ctrl = False
        cur_pos[0] = (0.20, -0.15)
        hangar._tick()
        self.assertTrue(drag.is_dragging())
        self.assertGreater(panel.x, 0.1)
        self.assertEqual(delays[-1], hangar.DRAG_TICK)

        # Release LMB: ends drag, saves coordinates, restores normal TICK interval
        d['inp'].lmb = False
        hangar._tick()
        self.assertFalse(drag.is_dragging())
        self.assertEqual(delays[-1], hangar.TICK)

    def test_battle_skips_low_tier_on_fresh_start_and_reconnect(self):
        d = self._build_deps()
        d['dossier'].dossiers[10529] = VehicleDossier(52.0, 450.0, 20, 0, 1699999000)

        panels = []

        def _make_panel():
            p = MemoryPanelView()
            panels.append(p)
            return p

        svc = BattleSessionService(
            d['cfg_store'], d['cfg_sync'], d['cache_repo'], d['dossier'],
            d['curves'], d['snapshot_uc'], d['forecast'], d['thr_calc'],
            d['clock'], d['sched'], d['inp'], d['logger'],
            BattlePayloadPresenter(d['cfg_store']), _make_panel, FakeTracker,
            drag_controller=None,
        )

        # Tier 3 / Tier 4 (level < 5) must NOT build panel
        d['dossier'].battle_ctx = {'int_cd': 10529, 'level': 4, 'is_spg': False, 'is_random': True}
        svc.start()
        self.assertIsNone(svc.panel)
        self.assertEqual(len(panels), 0)

        # Start in Tier 5 -> panel built
        d['dossier'].battle_ctx = {'int_cd': 10529, 'level': 5, 'is_spg': False, 'is_random': True}
        svc.start()
        self.assertIsNotNone(svc.panel)
        self.assertEqual(len(panels), 1)
        first_panel = svc.panel

        # Reconnect straight into a Tier 3 battle -> previous panel stopped and no new panel created
        d['dossier'].battle_ctx = {'int_cd': 10529, 'level': 3, 'is_spg': False, 'is_random': True}
        svc.start()
        self.assertTrue(first_panel.destroyed)
        self.assertIsNone(svc.panel)
        self.assertEqual(len(panels), 1)

    def test_battle_collapse_and_expand_toggle_preserves_anchor_x(self):
        from dm_threemarks.adapters.settings.drag_controller import DragController

        class _BattlePanel(MemoryPanelView):
            def __init__(self, inp):
                super(_BattlePanel, self).__init__()
                self._inp = inp
                self.mode = 'b'
                self.keyX = 'x'
                self.keyY = 'y'
                self.x = 0.2
                self.y = -0.2
                self.wPx = 240.0
                self.hPx = 120.0
                self.ui = 1.0
                self.mini = False
                self._bmin_offset_x = 0.0

            def visual_x(self):
                return self.x + self._bmin_offset_x

            def contains(self, pos):
                w = self._inp.px_w(self.wPx)
                h = self._inp.px_h(self.hPx)
                vx = self.visual_x()
                return (vx <= pos[0] <= vx + w) and (self.y - h <= pos[1] <= self.y)

            def move_to(self, x, y):
                self.x = x
                self.y = y

        d = self._build_deps()
        panel = _BattlePanel(d['inp'])
        drag = DragController(d['inp'], d['cfg_store'], d['cfg_sync'])
        self.assertFalse(bool(d['cfg_store'].get('minBattle', False)))

        # Ctrl + LMB click inside top-right '-' button [wPx-24 .. wPx, 2 .. 28]
        bx = panel.x + d['inp'].px_w(panel.wPx - 12.0)
        by = panel.y - d['inp'].px_h(15.0)
        d['inp'].cursor_position = lambda: (bx, by)
        d['inp'].ctrl = True
        d['inp'].lmb = True
        self.assertFalse(drag.poll(panel, min_key='minBattle'))
        # Holding LMB across ticks (even if cursor jitters slightly inside button) must not drag or prematurely fire
        d['inp'].cursor_position = lambda: (bx + d['inp'].px_w(4.0), by)
        self.assertFalse(drag.poll(panel, min_key='minBattle'))
        self.assertFalse(drag.is_dragging())
        d['inp'].lmb = False
        self.assertTrue(drag.poll(panel, min_key='minBattle'))
        self.assertTrue(bool(d['cfg_store'].get('minBattle', False)))

        # Collapse keeps exact window dimensions and panel.x without shifting or resizing
        orig_x = panel.x
        panel.mini = True
        self.assertEqual(panel.x, orig_x)
        self.assertEqual(panel.wPx, 240.0)
        self.assertEqual(panel.hPx, 120.0)

        # Ctrl + LMB click on '+' button at exact same top-right position expands back cleanly
        d['inp'].cursor_position = lambda: (bx, by)
        d['inp'].ctrl = True
        d['inp'].lmb = True
        self.assertFalse(drag.poll(panel, min_key='minBattle'))
        d['inp'].lmb = False
        self.assertTrue(drag.poll(panel, min_key='minBattle'))
        self.assertFalse(bool(d['cfg_store'].get('minBattle', False)))

    def test_lesta_ru_curves_epoch_and_realm_detection(self):
        from dm_threemarks.domain.constants import LESTA_SERVER_HOUR, LESTA_SERVER_LATE
        from dm_threemarks.domain.entities.curve import Curve, api_day, day_number
        from dm_threemarks.infrastructure.network.mastery_gateway import WgPoliroidMasteryGateway

        # 1. ServerEpoch with Lesta RU hours rolls over at 03:00 UTC (06:00 MSK) instead of 09:00 UTC
        ep_lesta = ServerEpoch(server_hour=LESTA_SERVER_HOUR, server_late=LESTA_SERVER_LATE)
        ep_eu = ServerEpoch()
        ts_0400_utc = 1795320000.0  # 2026-11-22 04:00:00 UTC (07:00 MSK)
        self.assertEqual(ts_0400_utc % 86400.0, 4 * 3600.0)
        self.assertEqual(ep_lesta.by_clock(ts_0400_utc), ep_eu.by_clock(ts_0400_utc) + 1)

        # 2. Gateway on domain='ru' fetches exact 8-knot Poliroid RU curve even with empty app_id,
        # and falls back to Poliroid RU if api.tanki.su fails with an app_id
        class _FakeHttp(object):
            def __init__(self, fail_official=False):
                self.fail_official = fail_official
                self.urls = []

            def is_available(self):
                return True

            def get_json(self, url):
                self.urls.append(url)
                if 'api.tanki.su' in url:
                    if self.fail_official:
                        return {'status': 'error', 'error': {'message': 'INVALID_APPLICATION_ID'}}
                    return {'status': 'ok', 'data': {}}
                return {
                    'status': 'ok',
                    'data': {
                        'data': [{
                            'date': '2026-11-23',
                            'marks': {
                                '20': 666, '30': 1086, '40': 1506, '50': 1856,
                                '55': 2032, '60': 2216, '65': 2401, '70': 2623,
                                '75': 2845, '80': 3122, '85': 3399, '90': 3799,
                                '95': 4200, '100': 4833,
                            },
                        }],
                    },
                }

        class _InlineQueue(object):
            def __init__(self):
                self.items = []

            def spawn(self, fn, args):
                fn(*args)

            def post(self, item):
                self.items.append(item)

            def drain(self):
                out = list(self.items)
                del self.items[:]
                return out

        for fail_off, app_id in ((False, ''), (True, 'bad_lesta_id')):
            d = self._build_deps()
            d['clock']._now = (day_number('2026-11-23') - 719163) * 86400.0 + 43200.0
            d['dossier'].domain = 'ru'
            d['cfg_store'].set('wgApiApplicationId', '')
            d['cfg_store'].set('lestaApiApplicationId', app_id)
            http = _FakeHttp(fail_official=fail_off)
            gw = WgPoliroidMasteryGateway(http, _InlineQueue())
            curves = CurveSyncService(d['cache_repo'], gw, d['dossier'], d['cfg_store'], d['clock'], d['logger'])
            curves.request_curve('7169')
            self.assertTrue(curves.pump())
            c = curves.curve_for(7169)
            self.assertIsNotNone(c)
            self.assertTrue(c.exact)
            self.assertEqual(c.day, day_number('2026-11-23'))
            self.assertEqual(int(c.damage_of(95.0)), 4200)
            self.assertEqual(api_day(gw.drain_results()), None)  # queue drained cleanly
            if fail_off:
                self.assertTrue(any('api.tanki.su' in u for u in http.urls))
            else:
                self.assertTrue(all('poliroid.me/gunmarks/api/v2/data/ru/' in u for u in http.urls))

    def test_hangar_ignores_ammunition_panel_widget_and_hides_on_fullscreen_setup(self):
        d = self._build_deps()
        d['dossier'].vehicle_info = (7169, 10)
        d['dossier'].dossiers[7169] = VehicleDossier(52.0, 2100.0, 50, 0, 1699999000)

        panels = []

        def _make_panel():
            p = MemoryPanelView()
            panels.append(p)
            return p

        hangar = HangarSessionService(
            d['cfg_store'], d['cfg_sync'], d['dossier'], d['curves'],
            d['snapshot_uc'], d['forecast'], d['thr_calc'], d['clock'],
            d['sched'], d['inp'], d['env'], d['menu'], d['logger'],
            HangarPayloadPresenter(), _make_panel,
        )
        d['env'].views = set([
            'gui.impl.pub.main_view.MainView',
            'gui.impl.lobby.tank_setup.ammunition_panel.hangar_view.HangarAmmunitionPanelView',
            'gui.impl.lobby.tank_setup.tooltips.setup_tab_tooltip_view.SetupTabTooltipView',
        ])
        hangar.on_lobby()
        hangar._scan_views()
        self.assertIsNotNone(hangar.panel)
        self.assertFalse(hangar.panel.destroyed)
        hangar.on_view_loaded('tank_setup.ammunition_panel.hangar_view')
        self.assertIsNotNone(hangar.panel)

        # Opening actual fullscreen ammunition setup MUST hide panel
        d['env'].views.add('gui.impl.lobby.tank_setup.ammunition_setup.base_view.AmmunitionSetupView')
        hangar._scan_views()
        self.assertIsNone(hangar.panel)
        self.assertTrue(panels[-1].destroyed)

        # Closing fullscreen setup while persistent HangarAmmunitionPanelView stays mounted restores panel
        d['env'].views.remove('gui.impl.lobby.tank_setup.ammunition_setup.base_view.AmmunitionSetupView')
        hangar._scan_views()
        self.assertIsNotNone(hangar.panel)
        self.assertEqual(len(panels), 2)

        # Legacy Scaleform fullscreen setup view also hides
        d['env'].views.add('gui.Scaleform.daapi.view.lobby.tank_setup.ammunition_setup_view.AmmunitionSetupView')
        hangar._scan_views()
        self.assertIsNone(hangar.panel)

    def test_hangar_monitor_uses_container_view_count_on_multiview_layers(self):
        import types
        from dm_threemarks.infrastructure.wot import hangar_monitor

        class SingleViewContainer(object):
            def __init__(self, view):
                self._view = view

            def getView(self):
                return self._view

        class DefaultContainer(object):
            def __init__(self, count):
                self._count = count

            def getView(self, criteria=None):
                raise AssertionError('getView must not be called on multi-view DefaultContainer')

            def getViewCount(self):
                return self._count

        class _FakeView(object):
            def __init__(self, alias):
                self.alias = alias

        class _FakeCM(object):
            def __init__(self, containers):
                self._containers = containers

            def getContainer(self, layer):
                return self._containers.get(layer)

        class _FakeApp(object):
            def __init__(self, cm):
                self.containerManager = cm

        class _FakeAppLoader(object):
            def __init__(self, cm):
                self._app = _FakeApp(cm)

            def getDefLobbyApp(self):
                return self._app

        class _FakeWindowLayer(object):
            TOP_SUB_VIEW = 3
            LOBBY_TOP_SUB_VIEW = 4
            FULLSCREEN_WINDOW = 5
            SUB_VIEW = 2
            LOBBY_SUB_VIEW = 1

        orig_wl = hangar_monitor.WindowLayer
        orig_dep = hangar_monitor.dependency
        mod_names = (
            'gui', 'gui.Scaleform', 'gui.Scaleform.lobby_entry',
            'skeletons', 'skeletons.gui', 'skeletons.gui.app_loader',
        )
        orig_sys_mods = dict((k, sys.modules.get(k)) for k in mod_names)
        try:
            hangar_monitor.WindowLayer = _FakeWindowLayer
            cm_holder = [None]

            class _FakeDep(object):
                @staticmethod
                def instance(cls):
                    return _FakeAppLoader(cm_holder[0])

            hangar_monitor.dependency = _FakeDep
            for k in mod_names:
                m = types.ModuleType(k)
                if k in ('gui', 'gui.Scaleform', 'skeletons', 'skeletons.gui'):
                    m.__path__ = []
                sys.modules[k] = m
            sys.modules['gui.Scaleform'].lobby_entry = sys.modules['gui.Scaleform.lobby_entry']
            sys.modules['gui'].Scaleform = sys.modules['gui.Scaleform']
            sys.modules['skeletons'].gui = sys.modules['skeletons.gui']
            sys.modules['skeletons.gui'].app_loader = sys.modules['skeletons.gui.app_loader']
            sys.modules['skeletons.gui.app_loader'].IAppLoader = object

            env = hangar_monitor.WotHangarEnvironment()
            cm_holder[0] = _FakeCM({
                _FakeWindowLayer.FULLSCREEN_WINDOW: DefaultContainer(0),
                _FakeWindowLayer.TOP_SUB_VIEW: SingleViewContainer(None),
                _FakeWindowLayer.SUB_VIEW: SingleViewContainer(_FakeView('hangar')),
            })
            self.assertEqual(env.hangar_state(), (True, 'hangar'))

            cm_holder[0] = _FakeCM({
                _FakeWindowLayer.FULLSCREEN_WINDOW: DefaultContainer(1),
                _FakeWindowLayer.SUB_VIEW: SingleViewContainer(_FakeView('hangar')),
            })
            self.assertEqual(env.hangar_state(), (False, 'fullscreen_window'))
        finally:
            hangar_monitor.WindowLayer = orig_wl
            hangar_monitor.dependency = orig_dep
            for k, orig in orig_sys_mods.items():
                if orig is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = orig

    def test_first_battle_zero_dossier_unknown_tank_fallback_and_api_fallback(self):
        from dm_threemarks.infrastructure.network.mastery_gateway import WgPoliroidMasteryGateway

        knots = {20: 600, 40: 1100, 55: 1500, 65: 1850, 75: 2250, 85: 2700, 95: 3300, 100: 3800}
        points = {}
        kkeys = sorted(knots.keys())
        for i in range(len(kkeys) - 1):
            p0, p1 = kkeys[i], kkeys[i + 1]
            d0, d1 = knots[p0], knots[p1]
            for q in range(p0, p1 + 1):
                points[str(q)] = d0 + (d1 - d0) * (q - p0) // (p1 - p0)

        # 1. Item 1: Battle #1 (0 battles, 0% dossier) with loaded curve shows live forecast & thresholds
        d = self._build_deps()
        d['dossier'].dossiers[77777] = VehicleDossier(0.0, 0.0, 0, 0, 0)
        d['dossier'].battle_ctx = {'int_cd': 77777, 'is_spg': False, 'is_random': True}
        panel = MemoryPanelView()
        tracker_holder = []

        def make_tracker(cb):
            t = FakeTracker(cb)
            t.current = DamageReport(damage=0, radio=0, track=0, source='feedback')
            tracker_holder.append(t)
            return t

        battle = BattleSessionService(
            d['cfg_store'], d['cfg_sync'], d['cache_repo'], d['dossier'],
            d['curves'], d['snapshot_uc'], d['forecast'], d['thr_calc'],
            d['clock'], d['sched'], d['inp'], d['logger'],
            BattlePayloadPresenter(d['cfg_store']), lambda: panel, make_tracker,
        )
        battle.start()
        d['gateway'].queued.append(('curve', '77777', points, d['clock'].now() - 86400, None))
        d['clock'].advance(0.5)
        battle._tick()
        p0 = panel.pushed[-1]
        self.assertTrue(p0['v3d']['hasRating'])
        self.assertEqual(p0['pct'], u'0.00%')
        self.assertEqual(p0['v3d']['tHold'], 0)
        self.assertEqual(p0['v3d']['tNext'], 1850)
        self.assertEqual(p0['v3d']['t95'], 3300)

        tracker_holder[0].current = DamageReport(damage=3000, radio=0, track=0, source='feedback')
        d['clock'].advance(0.1)
        battle._tick()
        p1 = panel.pushed[-1]
        self.assertGreater(p1['v3d']['pct'], 0.0)
        self.assertGreater(p1['v3d']['delta'], 0.0)
        battle.stop()
        self.assertIn('pendingForecast', d['cache_repo'].get_entry('77777'))

        # 2. Item 5a: Unknown tank (curve=None, not pending) computes fallback forecast in battle
        d2 = self._build_deps()
        d2['dossier'].dossiers[88888] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)
        d2['dossier'].battle_ctx = {'int_cd': 88888, 'is_spg': False, 'is_random': True}
        d2['gateway'].available = False
        panel2 = MemoryPanelView()
        tracker2 = []

        def make_tracker2(cb):
            t = FakeTracker(cb)
            t.current = DamageReport(damage=4000, radio=0, track=0, source='feedback')
            tracker2.append(t)
            return t

        battle2 = BattleSessionService(
            d2['cfg_store'], d2['cfg_sync'], d2['cache_repo'], d2['dossier'],
            d2['curves'], d2['snapshot_uc'], d2['forecast'], d2['thr_calc'],
            d2['clock'], d2['sched'], d2['inp'], d2['logger'],
            BattlePayloadPresenter(d2['cfg_store']), lambda: panel2, make_tracker2,
        )
        battle2.start()
        hi_push = panel2.pushed[-1]
        self.assertIsNotNone(hi_push['v3d']['delta'])
        self.assertGreater(hi_push['v3d']['delta'], 0.0)
        self.assertEqual(hi_push['v3d']['tHold'], 2400)

        tracker2[0].current = DamageReport(damage=500, radio=0, track=0, source='feedback')
        d2['clock'].advance(0.1)
        battle2._tick()
        lo_push = panel2.pushed[-1]
        self.assertLess(lo_push['v3d']['delta'], 0.0)
        self.assertEqual(lo_push['v3d']['tHold'], 2400)
        battle2.stop()

        # 3. Item 5b: Official API returning empty distribution falls back to Poliroid on both RU and EU
        class _EmptyOfficialHttp(object):
            def __init__(self):
                self.urls = []

            def is_available(self):
                return True

            def get_json(self, url):
                self.urls.append(url)
                if 'api.tanki.su' in url or 'api.worldoftanks.' in url:
                    return {'status': 'ok', 'data': {'distribution': {}, 'updated_at': 123}}
                return {
                    'status': 'ok',
                    'data': {
                        'data': [{
                            'date': '2026-11-23',
                            'marks': {
                                '20': 666, '30': 1086, '40': 1506, '50': 1856,
                                '55': 2032, '60': 2216, '65': 2401, '70': 2623,
                                '75': 2845, '80': 3122, '85': 3399, '90': 3799,
                                '95': 4200, '100': 4833,
                            },
                        }],
                    },
                }

        class _Q(object):
            def __init__(self):
                self.items = []

            def spawn(self, fn, args):
                fn(*args)

            def post(self, item):
                self.items.append(item)

            def drain(self):
                out = list(self.items)
                del self.items[:]
                return out

        for dom, aid in (('ru', 'lesta_app'), ('eu', 'wg_app')):
            http = _EmptyOfficialHttp()
            gw = WgPoliroidMasteryGateway(http, _Q())
            gw.request_curve('7169', dom, aid)
            res = gw.drain_results()
            self.assertEqual(len(res), 1)
            self.assertIsNone(res[0][4])
            self.assertEqual(res[0][2].get('95'), 4200)
            self.assertTrue(any('poliroid.me/gunmarks/api/v2/data/%s/' % dom in u for u in http.urls))

    def test_wot_damage_tracker_preserves_split_assist_under_summary_fallbacks(self):
        import types

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

        class _FeedbackEvent(object):
            def __init__(self, typ, btype, dmg):
                self._t = typ
                self._b = btype
                self._d = dmg

            def getType(self):
                return self._t

            def getBattleEventType(self):
                return self._b

            def getExtra(self):
                return type('X', (object,), {'getDamage': lambda s: self._d})()

        class _SummaryNoSplit(object):
            def __init__(self, dmg, ast, stun):
                self._d = dmg
                self._a = ast
                self._s = stun

            def getTotalDamage(self):
                return self._d

            def getTotalAssistDamage(self):
                return self._a

            def getTotalStunDamage(self):
                return self._s

        class _CustomSummary(_SummaryNoSplit):
            def __init__(self, dmg, radio, track, stun):
                _SummaryNoSplit.__init__(self, dmg, radio + track, stun)
                self.__radioAssistDamage = radio
                self.__trackAssistDamage = track

        mod_names = (
            'BigWorld', 'BattleFeedbackCommon', 'helpers', 'helpers.dependency',
            'gui', 'gui.battle_control', 'gui.battle_control.battle_constants',
            'skeletons', 'skeletons.gui', 'skeletons.gui.battle_session',
        )
        orig_mods = dict((k, sys.modules.get(k)) for k in mod_names)
        sp = None
        try:
            fb_ctrl = type('FB', (object,), {
                'onPlayerFeedbackReceived': _Ev(),
                'onPlayerSummaryFeedbackReceived': _Ev(),
                'getCachedEvent': lambda s, k: None,
            })()
            sp = type('SP', (object,), {
                'shared': type('Sh', (object,), {'feedback': fb_ctrl, 'personalEfficiencyCtrl': None})(),
                'getArenaDP': lambda s: None,
            })()

            bw = types.ModuleType('BigWorld')
            bw.player = lambda: None
            sys.modules['BigWorld'] = bw

            helpers_pkg = types.ModuleType('helpers')
            helpers_pkg.__path__ = []
            dep_mod = types.ModuleType('helpers.dependency')
            dep_mod.instance = lambda cls: sp
            helpers_pkg.dependency = dep_mod
            sys.modules['helpers'] = helpers_pkg
            sys.modules['helpers.dependency'] = dep_mod

            skel_pkg = types.ModuleType('skeletons')
            skel_pkg.__path__ = []
            skel_gui = types.ModuleType('skeletons.gui')
            skel_gui.__path__ = []
            bs_mod = types.ModuleType('skeletons.gui.battle_session')
            bs_mod.IBattleSessionProvider = object
            skel_pkg.gui = skel_gui
            skel_gui.battle_session = bs_mod
            sys.modules['skeletons'] = skel_pkg
            sys.modules['skeletons.gui'] = skel_gui
            sys.modules['skeletons.gui.battle_session'] = bs_mod

            bfc = types.ModuleType('BattleFeedbackCommon')
            bfc.BATTLE_EVENT_TYPE = type('BET', (object,), {'RADIO_ASSIST': 10, 'TRACK_ASSIST': 11})()
            sys.modules['BattleFeedbackCommon'] = bfc

            gui_pkg = types.ModuleType('gui')
            gui_pkg.__path__ = []
            bctrl_pkg = types.ModuleType('gui.battle_control')
            bctrl_pkg.__path__ = []
            bc = types.ModuleType('gui.battle_control.battle_constants')
            bc.FEEDBACK_EVENT_ID = type('FEI', (object,), {
                'PLAYER_DAMAGED_HP_ENEMY': 1,
                'PLAYER_ASSIST_TO_KILL_ENEMY': 2,
                'PLAYER_ASSIST_TO_STUN_ENEMY': 3,
                'DAMAGE_LOG_SUMMARY': 4,
            })()
            gui_pkg.battle_control = bctrl_pkg
            bctrl_pkg.battle_constants = bc
            sys.modules['gui'] = gui_pkg
            sys.modules['gui.battle_control'] = bctrl_pkg
            sys.modules['gui.battle_control.battle_constants'] = bc

            sys.modules.pop('dm_threemarks.infrastructure.wot.damage_tracker', None)
            from dm_threemarks.infrastructure.wot import damage_tracker

            # 1. Normal split _on_feedback followed by summary without mangled fields preserves split (4539 + 955)
            tr = damage_tracker.WotDamageTracker(lambda: None)
            tr.start()
            tr._on_feedback([
                _FeedbackEvent(1, 0, 4539),
                _FeedbackEvent(2, 10, 293),
                _FeedbackEvent(2, 11, 955),
            ])
            tr._on_feedback_summary(_SummaryNoSplit(4539, 1248, 0))
            rep = tr.report()
            self.assertEqual((rep.damage, rep.radio, rep.track), (4539, 293, 955))
            self.assertEqual(rep.combined(), 4539 + 955)
            tr.stop()

            # 2. Renamed class mangled attributes (__radioAssistDamage / __trackAssistDamage) extracted accurately
            tr2 = damage_tracker.WotDamageTracker(lambda: None)
            tr2.start()
            tr2._on_feedback_summary(_CustomSummary(2000, 300, 700, 100))
            rep2 = tr2.report()
            self.assertEqual((rep2.damage, rep2.radio, rep2.track, rep2.stun), (2000, 300, 700, 100))
            self.assertEqual(rep2.combined(), 2700)
            tr2.stop()

            # 3. Fallback on reconnect replaced cleanly when on_summary later provides true split assist
            tr3 = damage_tracker.WotDamageTracker(lambda: None)
            tr3.start()
            tr3._on_feedback_summary(_SummaryNoSplit(2000, 1000, 0))
            self.assertEqual((tr3.sAssists['radioAssist'], tr3.sAssists['trackAssist']), (1000, 0))
            tr3.on_summary({'damage': 2000, 'radioAssist': 300, 'trackAssist': 700, 'stunAssist': 0})
            self.assertEqual((tr3.sAssists['radioAssist'], tr3.sAssists['trackAssist']), (300, 700))
            self.assertEqual(tr3.report().combined(), 2700)
            tr3.stop()
        finally:
            sys.modules.pop('dm_threemarks.infrastructure.wot.damage_tracker', None)
            for k, orig in orig_mods.items():
                if orig is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = orig

    def test_forecast_result_reconciles_across_tank_switch_early_exit_and_zero_delta(self):
        d = self._build_deps()
        snap = d['snapshot_uc']

        # Tank A (54353): 0-battle first battle, player exits early while still 0/0, switches to Tank B (10529)
        d['dossier'].dossiers[54353] = VehicleDossier(0.0, 0.0, 0, 0, 0)
        d['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 50, 1, 1699999000)
        d['dossier'].current_vehicle = (10529, 10)
        d['cache_repo'].get_entry('54353')['pendingForecast'] = {
            'at': d['clock'].now(),
            'before': 0.0,
            'average': 0.0,
            'battles': 0,
            'predicted': 2.01,
            'combined': 752,
            'curveDay': 739944,
            'parts': {'damage': 595, 'radio': 157},
        }

        panel = MemoryPanelView()
        hangar = HangarSessionService(
            d['cfg_store'], d['cfg_sync'], d['dossier'], d['curves'],
            snap, d['forecast'], d['thr_calc'], d['clock'],
            d['sched'], d['inp'], d['env'], d['menu'], d['logger'],
            HangarPayloadPresenter(), lambda: panel,
        )
        # Early snapshot while Tank A battle not settled must NOT wipe pendingForecast
        snap.snapshot_vehicle(54353)
        self.assertIn('pendingForecast', d['cache_repo'].get_entry('54353'))

        # Enter lobby viewing Tank B -> later Tank A battle settles on server and on_vehicle_changed fires
        hangar.on_lobby()
        self.assertIn('pendingForecast', d['cache_repo'].get_entry('54353'))
        d['clock'].advance(120.0)
        d['dossier'].dossiers[54353] = VehicleDossier(2.01, 15.0, 0, 1, int(d['clock'].now()))
        hangar.on_vehicle_changed(1, {'vehicles': {}})

        fc_logs = [ln for ln in d['logger'].infos if 'FORECAST_RESULT tank=54353' in ln]
        self.assertEqual(len(fc_logs), 1)
        self.assertIn('predicted=2.01 actual=2.01 error=+0.00 pp average=0->15', fc_logs[0])
        self.assertNotIn('pendingForecast', d['cache_repo'].get_entry('54353'))

        # Tank C (32529): avg & percent unchanged (4500->4500, 85.00->85.00), only battles incremented (100->101)
        d['dossier'].dossiers[32529] = VehicleDossier(85.00, 4500.0, 2, 100, int(d['clock'].now()))
        snap.snapshot_vehicle(32529)
        d['cache_repo'].get_entry('32529')['pendingForecast'] = {
            'at': d['clock'].now(),
            'before': 85.00,
            'average': 4500.0,
            'battles': 100,
            'predicted': 85.00,
            'combined': 4500,
            'curveDay': 739944,
            'parts': {'damage': 4500},
        }
        d['clock'].advance(60.0)
        d['dossier'].dossiers[32529] = VehicleDossier(85.00, 4500.0, 2, 101, int(d['clock'].now()))
        hangar._last_update_t = d['clock'].now() - 1.0
        hangar._tick()

        fc_c = [ln for ln in d['logger'].infos if 'FORECAST_RESULT tank=32529' in ln]
        self.assertEqual(len(fc_c), 1)
        self.assertIn('predicted=85.00 actual=85.00 error=+0.00 pp', fc_c[0])
        self.assertNotIn('pendingForecast', d['cache_repo'].get_entry('32529'))

        # Tank D (513): stuck pendingForecast where last already equals dossier still logs if fresh, and expired is popped silently
        d['dossier'].dossiers[513] = VehicleDossier(27.59, 378.0, 0, 12, int(d['clock'].now()))
        e513 = d['cache_repo'].get_entry('513')
        e513['last'] = [378.0, 27.59, 0, 12]
        e513['pendingForecast'] = {
            'at': d['clock'].now() - 30.0,
            'before': 25.80,
            'average': 344.0,
            'battles': 11,
            'predicted': 27.59,
            'combined': 2073,
            'curveDay': 739929,
            'parts': {},
        }
        d['cache_repo'].get_entry('61729')['pendingForecast'] = {
            'at': d['clock'].now() - 30000.0,
            'before': 8.90,
            'average': 204.0,
            'predicted': 9.52,
            'combined': 1164,
        }
        d['dossier'].dossiers[61729] = VehicleDossier(8.90, 204.0, 0, 5, int(d['clock'].now()))
        snap.reconcile_pending()
        self.assertEqual(len([ln for ln in d['logger'].infos if 'FORECAST_RESULT tank=513' in ln]), 1)
        self.assertEqual(len([ln for ln in d['logger'].infos if 'FORECAST_RESULT tank=61729' in ln]), 0)
        self.assertNotIn('pendingForecast', d['cache_repo'].get_entry('513'))
        self.assertNotIn('pendingForecast', d['cache_repo'].get_entry('61729'))
        hangar.on_leave_lobby()

    def test_popup_profile_window_does_not_block_hangar_and_scan_self_heals(self):
        import types
        from dm_threemarks.infrastructure.wot import hangar_monitor

        d = self._build_deps()
        d['dossier'].current_vehicle = (10529, 10)
        d['dossier'].dossiers[10529] = VehicleDossier(72.5, 2400.0, 1, 50, 1699999000)

        panels = []

        def _make_panel():
            p = MemoryPanelView()
            panels.append(p)
            return p

        hangar = HangarSessionService(
            d['cfg_store'], d['cfg_sync'], d['dossier'], d['curves'],
            d['snapshot_uc'], d['forecast'], d['thr_calc'], d['clock'],
            d['sched'], d['inp'], d['env'], d['menu'], d['logger'],
            HangarPayloadPresenter(), _make_panel,
        )
        hangar.on_lobby()
        self.assertIsNotNone(hangar.panel)

        # Popup aliases (profileWindow, contactsPopover, showSimpleDialog) must NOT block hangar
        for popup_alias in ('profilewindow', 'contactspopover', 'showsimpledialog'):
            hangar.on_view_loaded(popup_alias)
            self.assertFalse(hangar._blocked)
            self.assertIsNotNone(hangar.panel)
            self.assertFalse(hangar.panel.destroyed)

        # Real fullscreen alias ('profile') blocks & hides panel, and hangar state restores it automatically
        hangar.on_view_loaded('profile')
        self.assertTrue(hangar._blocked)
        self.assertIsNone(hangar.panel)

        d['env'].state = (False, 'profile')
        hangar._scan_views()
        self.assertTrue(hangar._blocked)
        self.assertIsNone(hangar.panel)

        d['env'].state = (True, 'hangar')
        hangar._scan_views()
        self.assertFalse(hangar._blocked)
        self.assertIsNotNone(hangar.panel)
        hangar.on_leave_lobby()

        # SFWindow (viewKey.alias) fallback in WotHangarEnvironment.hangar_state() when IAppLoader is unavailable
        class _Win(object):
            def __init__(self, layer, alias, status=4, hidden=False):
                self.layer = layer
                self.viewKey = type('VK', (object,), {'alias': alias})()
                self.windowStatus = status
                self._hidden = hidden

            def isHidden(self):
                return self._hidden

        class _WL(object):
            TOP_SUB_VIEW = 3
            LOBBY_TOP_SUB_VIEW = 4
            FULLSCREEN_WINDOW = 5
            SUB_VIEW = 2
            LOBBY_SUB_VIEW = 1
            WINDOW = 6

        class _WS(object):
            LOADING = 3
            LOADED = 4

        orig_wl = hangar_monitor.WindowLayer
        orig_ws = hangar_monitor.WindowStatus
        orig_dep = hangar_monitor.dependency
        orig_gl = hangar_monitor.IGuiLoader
        orig_ok = hangar_monitor._WULF_OK
        mod_names = ('skeletons', 'skeletons.gui', 'skeletons.gui.app_loader')
        orig_mods = dict((k, sys.modules.get(k)) for k in mod_names)
        try:
            hangar_monitor.WindowLayer = _WL
            hangar_monitor.WindowStatus = _WS
            hangar_monitor._WULF_OK = True
            hangar_monitor.IGuiLoader = 'IGuiLoader'
            wins_holder = [[]]
            gui_loader = type('GL', (object,), {
                'windowsManager': type('WM', (object,), {'findWindows': lambda s, pred: list(wins_holder[0])})()
            })()
            hangar_monitor.dependency = type('Dep', (object,), {
                'instance': staticmethod(lambda cls: gui_loader if cls == 'IGuiLoader' else None)
            })()
            for k in mod_names:
                m = types.ModuleType(k)
                if k != 'skeletons.gui.app_loader':
                    m.__path__ = []
                sys.modules[k] = m
            sys.modules['skeletons'].gui = sys.modules['skeletons.gui']
            sys.modules['skeletons.gui'].app_loader = sys.modules['skeletons.gui.app_loader']
            sys.modules['skeletons.gui.app_loader'].IAppLoader = 'IAppLoader'

            env = hangar_monitor.WotHangarEnvironment()
            wins_holder[0] = [_Win(_WL.SUB_VIEW, 'hangar'), _Win(_WL.WINDOW, 'profileWindow')]
            self.assertEqual(env.hangar_state(), (True, 'hangar'))

            wins_holder[0] = [_Win(_WL.SUB_VIEW, 'techtree')]
            self.assertEqual(env.hangar_state(), (False, 'techtree'))

            wins_holder[0] = [_Win(_WL.SUB_VIEW, 'hangar'), _Win(_WL.TOP_SUB_VIEW, 'shop')]
            self.assertEqual(env.hangar_state(), (False, 'shop'))

            # Lesta findViews widget check: distinguishes Hangar from TechTree/Barracks/Reserves/Lootboxes/Login
            views_holder = [[]]
            gui_loader.windowsManager.findViews = lambda pred: list(views_holder[0])
            MainView = type('MainView', (object,), {})
            HangarAmmo = type('HangarAmmunitionPanelView', (object,), {})
            TechTreeView = type('VehicleTechTree', (object,), {})
            BarracksView = type('BarracksView', (object,), {})
            ReservesView = type('ReservesActivationView', (object,), {})
            LootboxesView = type('LootBoxesStorageView', (object,), {})

            wins_holder[0] = [_Win(_WL.SUB_VIEW, 'hangar')]
            views_holder[0] = [MainView(), HangarAmmo()]
            self.assertEqual(env.hangar_state(), (True, 'hangar'))

            for other_cls in (TechTreeView, BarracksView, ReservesView, LootboxesView):
                views_holder[0] = [MainView(), other_cls()]
                self.assertEqual(env.hangar_state(), (False, 'not_hangar'))

            views_holder[0] = [MainView()]
            self.assertEqual(env.hangar_state(), (False, 'not_hangar'))
        finally:
            hangar_monitor.WindowLayer = orig_wl
            hangar_monitor.WindowStatus = orig_ws
            hangar_monitor.dependency = orig_dep
            hangar_monitor.IGuiLoader = orig_gl
            hangar_monitor._WULF_OK = orig_ok
            for k, orig in orig_mods.items():
                if orig is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = orig


if __name__ == '__main__':
    unittest.main()
