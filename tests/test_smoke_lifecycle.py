# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import shutil
import sys
import tempfile
import unittest


class TestSmokeLifecycle(unittest.TestCase):

    def test_entrypoint_init_events_and_fini(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_dir = os.path.join(repo_root, 'src')
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        class _Event(object):
            def __init__(self):
                self.handlers = []

            def __iadd__(self, fn):
                self.handlers.append(fn)
                return self

            def __isub__(self, fn):
                if fn in self.handlers:
                    self.handlers.remove(fn)
                return self

        class _Dummy(object):
            def __getattr__(self, k):
                if k.startswith('on') or k == 'handlers':
                    ev = _Event()
                    setattr(self, k, ev)
                    return ev
                return _Dummy()

            def __call__(self, *a, **kw):
                return _Dummy()

        class _Mod(object):
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

            def __getattr__(self, k):
                return _Dummy()

        class _FeedbackAdaptor(object):
            def handleBattleEventsSummary(self, summary):
                self.last = summary

        orig_hook = _FeedbackAdaptor.handleBattleEventsSummary
        pe = _Mod(
            onAvatarReady=_Event(),
            onAvatarBecomeNonPlayer=_Event(),
            onAccountShowGUI=_Event(),
            onAvatarBecomePlayer=_Event(),
        )
        cv = _Mod(isPresent=lambda: False, onChanged=_Event())
        items_cache = _Mod(onSyncCompleted=_Event())
        eb = _Mod(addListener=lambda *a, **kw: None, removeListener=lambda *a, **kw: None)

        stubs = {}
        for name in (
            'BigWorld', 'GUI', 'Keys', 'PlayerEvents', 'CurrentVehicle',
            'constants', 'helpers', 'helpers.dependency', 'helpers.time_utils',
            'skeletons', 'skeletons.gui', 'skeletons.gui.shared',
            'skeletons.gui.battle_session', 'skeletons.gui.impl', 'skeletons.gui.app_loader',
            'gui', 'gui.battle_control', 'gui.battle_control.controllers',
            'gui.battle_control.controllers.feedback_adaptor', 'gui.battle_control.battle_constants',
            'gui.shared', 'gui.shared.events',
            'frameworks', 'frameworks.wulf',
            'gui.impl', 'gui.impl.gui_decorators', 'gui.impl.pub', 'gui.impl.gen',
            'BattleFeedbackCommon', 'gui.aslainMenu', 'gui.modsSettingsApi',
        ):
            stubs[name] = _Mod()

        stubs['BigWorld'].callback = lambda delay, fn: 1
        stubs['BigWorld'].cancelCallback = lambda cid: None
        stubs['BigWorld'].time = lambda: 100.0
        stubs['BigWorld'].isKeyDown = lambda k: False
        stubs['BigWorld'].player = lambda: None
        stubs['GUI'].screenResolution = lambda: (1920, 1080)
        stubs['GUI'].mcursor = lambda: _Mod(position=(0.0, 0.0, 0.0))
        stubs['Keys'].KEY_LALT = 56
        stubs['Keys'].KEY_RALT = 184
        stubs['Keys'].KEY_TAB = 15
        stubs['Keys'].KEY_LCONTROL = 29
        stubs['Keys'].KEY_RCONTROL = 157
        stubs['Keys'].KEY_LEFTMOUSE = 256
        stubs['constants'].ARENA_BONUS_TYPE = _Mod(REGULAR=1, EPIC_RANDOM=14)
        stubs['constants'].AUTH_REALM = 'EU'
        stubs['helpers.dependency'].instance = lambda cls: items_cache
        stubs['helpers.time_utils'].getServerUTCTime = lambda: 1700000000.0
        stubs['gui.battle_control.controllers.feedback_adaptor'].BattleFeedbackAdaptor = _FeedbackAdaptor
        stubs['PlayerEvents'].g_playerEvents = pe
        stubs['CurrentVehicle'].g_currentVehicle = cv
        stubs['gui.shared'].EVENT_BUS_SCOPE = _Mod(BATTLE='BATTLE')
        stubs['gui.shared'].g_eventBus = eb
        stubs['gui.shared.events'].ViewEventType = _Mod(LOAD_VIEW='LOAD_VIEW')
        view_settings_calls = []

        class _ViewSettings(object):
            def __init__(self, layoutID=None, flags=None, model=None):
                view_settings_calls.append(layoutID)

        class _ViewModel(object):
            def __init__(self, *a, **kw):
                pass

            def _initialize(self):
                pass

            def _addStringProperty(self, name, val):
                pass

            def _addCommand(self, name):
                return object()

        class _ViewImpl(object):
            def __init__(self, settings):
                self.settings = settings

        stubs['frameworks.wulf'].ViewFlags = _Mod(VIEW=1)
        stubs['frameworks.wulf'].ViewModel = _ViewModel
        stubs['frameworks.wulf'].ViewSettings = _ViewSettings
        stubs['frameworks.wulf'].WindowFlags = _Mod(WINDOW=1, TOOLTIP=2, CONTEXT_MENU=3)
        stubs['frameworks.wulf'].WindowLayer = _Mod(FULLSCREEN_WINDOW=1, TOP_WINDOW=2, OVERLAY=3, WINDOW=4)
        stubs['frameworks.wulf'].WindowStatus = _Mod(DESTROYING=1, DESTROYED=2, LOADING=3, LOADED=4)
        stubs['gui.impl.gui_decorators'].args2params = lambda *a: (lambda fn: fn)
        stubs['gui.impl.pub'].ViewImpl = _ViewImpl
        stubs['gui.impl.pub'].WindowImpl = object
        stubs['gui.impl.gen'].R = _Mod(mods=_Mod(dm=_Mod(threemarks=_Mod(views=_Mod(ThreeMarks=lambda: 11)))))
        stubs['gui.aslainMenu'].g_modsSettingsApi = None
        stubs['gui.modsSettingsApi'].g_modsSettingsApi = None

        saved = {}
        tmp_cfg_dir = tempfile.mkdtemp(prefix='tm_smoke_')
        orig_cwd = os.getcwd()
        for k, v in stubs.items():
            saved[k] = sys.modules.get(k)
            sys.modules[k] = v

        # Run in temp cwd so mods/configs/three_marks writes inside temp dir
        try:
            os.chdir(tmp_cfg_dir)
            for mname in list(sys.modules):
                if mname == 'mod_three_marks' or mname.startswith('dm_threemarks'):
                    sys.modules.pop(mname, None)

            import mod_three_marks
            from dm_threemarks.adapters.gameface.wulf_views import TmView
            TmView(_Mod(payload='{}', model=None))
            self.assertEqual(view_settings_calls, [11])
            mod_three_marks.init()
            self.assertIsNotNone(mod_three_marks._app)
            self.assertTrue(os.path.isfile(os.path.join(tmp_cfg_dir, 'mods', 'configs', 'three_marks', 'config.json')))
            self.assertTrue(os.path.isfile(os.path.join(tmp_cfg_dir, 'mods', 'configs', 'three_marks', 'config_help.txt')))
            self.assertEqual(len(pe.onAvatarReady.handlers), 1)
            self.assertEqual(len(cv.onChanged.handlers), 1)
            self.assertIsNot(_FeedbackAdaptor.handleBattleEventsSummary, orig_hook)

            # Trigger hangar lobby enter & leave
            for fn in list(pe.onAccountShowGUI.handlers):
                fn()
            for fn in list(pe.onAvatarBecomePlayer.handlers):
                fn()

            mod_three_marks.fini()
            self.assertIsNone(mod_three_marks._app)
            self.assertEqual(len(pe.onAvatarReady.handlers), 0)
            self.assertEqual(len(cv.onChanged.handlers), 0)
            self.assertEqual(_FeedbackAdaptor.handleBattleEventsSummary, orig_hook)
            self.assertTrue(os.path.isfile(os.path.join(tmp_cfg_dir, 'mods', 'configs', 'three_marks', 'cache.json')))
        finally:
            os.chdir(orig_cwd)
            for k, prev in saved.items():
                if prev is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = prev
            shutil.rmtree(tmp_cfg_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
