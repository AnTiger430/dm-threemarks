# -*- coding: utf-8 -*-
from __future__ import absolute_import

import sys


class EventStub(object):
    """Minimal WoT Event (+= / -=) stub."""

    def __init__(self):
        self.handlers = []

    def __iadd__(self, fn):
        if fn not in self.handlers:
            self.handlers.append(fn)
        return self

    def __isub__(self, fn):
        for idx, existing in enumerate(list(self.handlers)):
            if existing == fn:
                self.handlers.pop(idx)
                break
        return self

    def emit(self, *args, **kwargs):
        for fn in list(self.handlers):
            fn(*args, **kwargs)


class ResAccessorStub(object):
    """Callable R.* accessor mimicking WoT ResAccessor (must be called as fn() -> int)."""

    def __init__(self, res_id):
        self._res_id = int(res_id)

    def __call__(self):
        return self._res_id

    def __repr__(self):
        return 'ResAccessor(resId=%d)' % self._res_id


class _Ns(object):
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class _StrictViewSettings(object):
    def __init__(self, layoutID=None, flags=None, model=None):
        if not isinstance(layoutID, (int, long)) or isinstance(layoutID, bool):
            raise TypeError(
                'ViewSettings(layoutID: int) invoked with invalid %r (forgot () on ResAccessor?)' % (layoutID,)
            )
        self.layoutID = layoutID
        self.flags = flags
        self.model = model


class _StrictViewModel(object):
    def __init__(self, properties=0, commands=0):
        self._props = {}
        self._cmds = {}

    def _initialize(self):
        pass

    def _addStringProperty(self, name, val):
        self._props[name] = val

    def _setString(self, _idx, val):
        self._props['payload'] = val

    def _addCommand(self, name):
        ev = EventStub()
        self._cmds[name] = ev
        return ev

    def transaction(self):
        model = self

        class _Tx(object):
            def __enter__(self):
                return model

            def __exit__(self, *a):
                return False

        return _Tx()


class _StrictViewImpl(object):
    def __init__(self, settings):
        self._settings = settings
        self.getViewModel()._initialize()
        for ev, handler in self._getEvents():
            ev += handler

    def getViewModel(self):
        return self._settings.model

    def _getEvents(self):
        return ()

    def _finalize(self):
        pass


class _StrictWindowImpl(object):
    def __init__(self, flags, content=None, layer=None, name='', parent=None):
        self.flags = flags
        self.content = content
        self.layer = layer
        self.name = name
        self.parent = parent
        self.proxy = object()
        self.windowStatus = 3  # LOADING
        self.hidden = True
        self.pos = (0, 0)
        self.destroyed = False

    def load(self):
        self.windowStatus = 4  # LOADED
        on_ready = getattr(self, '_onReady', None)
        if on_ready is not None:
            on_ready()

    def _onReady(self):
        pass

    def show(self, _focus=False):
        self.hidden = False

    def hide(self):
        self.hidden = True

    def isHidden(self):
        return self.hidden

    def move(self, x, y):
        self.pos = (x, y)

    def destroy(self):
        self.destroyed = True
        self.windowStatus = 2  # DESTROYED
        if self.content is not None:
            fin = getattr(self.content, '_finalize', None)
            if fin is not None:
                fin()


class StrictAslainApiV2(object):
    """Strict Aslain Mod Menu v2.1.15 API contract (no legacy .version or .onSettingsChanged)."""

    def __init__(self):
        self.onWindowOpened = EventStub()
        self.onWindowClosed = EventStub()
        self.templates = {}
        self.defaults = {}
        self.apply_cb = None
        self.button_cb = None
        self.live_cb = None
        self.images = []
        self.reloaded = []
        self.control_values = []
        self.unregistered_live = False
        self.input_previews = {}
        self.input_preview_replies = []
        self.unregistered_previews = []

    def getVersionTuple(self):
        return (2, 1, 15)

    def setModTemplate(self, linkage, template, apply_cb, button_cb):
        self.templates[linkage] = template
        self.apply_cb = apply_cb
        self.button_cb = button_cb
        return {'v3BarStyle': 0, 'hangarPanel': True}

    def setModDefaults(self, linkage, defaults):
        self.defaults[linkage] = dict(defaults)

    def registerLiveSettingsChange(self, linkage, cb, include_all=False):
        self.live_cb = cb

    def unregisterLiveSettingsChange(self, linkage, cb):
        if self.live_cb == cb:
            self.unregistered_live = True
            self.live_cb = None

    def registerInputPreview(self, linkage, var_name, handler):
        self.input_previews[var_name] = handler

    def unregisterInputPreview(self, linkage, var_name):
        self.unregistered_previews.append((linkage, var_name))
        self.input_previews.pop(var_name, None)

    def setInputPreview(self, linkage, var_name, content, token=None):
        self.input_preview_replies.append((linkage, var_name, content, token))

    def updateImage(self, linkage, var_name, source, width, height):
        self.images.append((linkage, var_name, source, width, height))

    def reloadModTemplate(self, linkage, template):
        self.templates[linkage] = template
        self.reloaded.append((linkage, template))

    def updateModSettings(self, linkage, vals):
        pass

    def setControlValue(self, linkage, key, val):
        self.control_values.append((linkage, key, val))

    def getModSettings(self, linkage, template):
        return {}


class StrictAslainTemplatesV2(object):
    """Strict Aslain v2.1.15 templates factory."""

    def __init__(self):
        self.tabs_created = []

    def generateOptions(self, labels):
        return [{'label': s} for s in labels]

    def createLabel(self, text):
        return {'type': 'Label', 'text': text}

    def createSlider(self, text, var_name, val, low, high, step, format='%.2f', tooltip=''):
        return {'type': 'Slider', 'text': text, 'varName': var_name, 'value': val, 'tooltip': tooltip}

    def createCheckbox(self, text, var_name, val, tooltip=''):
        return {'type': 'CheckBox', 'text': text, 'varName': var_name, 'value': val, 'tooltip': tooltip}

    def createColorChoice(self, text, var_name, val, tooltip=''):
        return {'type': 'ColorChoice', 'text': text, 'varName': var_name, 'value': val, 'tooltip': tooltip}

    def createRadioButtonGroup(self, text, var_name, opts, val, tooltip='', inline=False):
        return {'type': 'RadioButtonGroup', 'text': text, 'varName': var_name, 'options': opts, 'value': val, 'inline': inline}

    def createDropdown(self, text, var_name, opts, val, tooltip=''):
        return {'type': 'Dropdown', 'text': text, 'varName': var_name, 'options': opts, 'value': val}

    def createInput(self, text, var_name, val, tooltip=''):
        return {'type': 'TextInput', 'text': text, 'varName': var_name, 'value': val}

    def createActionButton(self, var_name, btn_text, label='', width=148, tooltip=''):
        return {'type': 'Button', 'varName': var_name, 'text': label, 'btnText': btn_text, 'width': width}

    def visibleWhen(self, ctl, master, val, indent=False, condition='=='):
        ctl['masterVarName'] = master
        ctl['masterValue'] = val
        ctl['condition'] = condition
        ctl['gateHides'] = True
        return ctl

    def createTab(self, title, items):
        self.tabs_created.append(title)
        return [{'type': 'Tab', 'title': title, 'items': items}]


def build_strict_wot_env():
    """Creates strict WoT + Aslain v2.1.15 stubs for runtime bytecode verification."""
    env = {'callbacks': [], 'next_cb_id': 1, 'time_now': 100.0}
    main_window = _Ns(proxy=object(), windowStatus=4)
    created_windows = []

    class _TrackedWindow(_StrictWindowImpl):
        def __init__(self, flags, content=None, layer=None, name='', parent=None):
            super(_TrackedWindow, self).__init__(flags, content=content, layer=layer, name=name, parent=parent)
            created_windows.append(self)

    class _FeedbackAdaptor(object):
        def handleBattleEventsSummary(self, summary):
            self.last_summary = summary

    def bw_callback(_delay, fn):
        cid = env['next_cb_id']
        env['next_cb_id'] += 1
        env['callbacks'].append((cid, fn))
        return cid

    def bw_cancel(cid):
        env['callbacks'][:] = [(i, f) for i, f in env['callbacks'] if i != cid]

    def flush_callbacks(limit=10):
        rounds = 0
        while env['callbacks'] and rounds < limit:
            rounds += 1
            batch = list(env['callbacks'])
            env['callbacks'][:] = []
            for _cid, fn in batch:
                fn()

    def _mk_dossier(pct, avg, marks):
        ach = _Ns(getDamageRating=lambda: pct, getValue=lambda: marks)
        st = _Ns(getAchievement=lambda _rec: ach, getBattlesCount=lambda: 42, getLastBattleTime=lambda: 1700000000)
        return _Ns(getTotalStats=lambda: st, getRandomStats=lambda: st, getGlobalStats=lambda: st,
                   getRecordValue=lambda _k1, _k2: avg)

    dossiers = {
        10529: _mk_dossier(65.12, 1200.0, 1),
        62273: _mk_dossier(44.11, 1071.0, 0),
    }
    items_cache = _Ns(onSyncCompleted=EventStub(), items=_Ns(getVehicleDossier=lambda cd: dossiers.get(cd)))

    feedback_ctrl = _Ns(onPlayerFeedbackReceived=EventStub(), onPlayerSummaryFeedbackReceived=EventStub(),
                        getCachedEvent=lambda _eid: None)
    battle_session = _Ns(shared=_Ns(feedback=feedback_ctrl, personalEfficiencyCtrl=_Ns(onTotalEfficiencyUpdated=EventStub()),
                                    vehicleState=_Ns(isInPostmortem=False)),
                         getArenaDP=lambda: None)
    gui_loader = _Ns(windowsManager=_Ns(getMainWindow=lambda: main_window, findWindows=lambda _p: created_windows, findViews=lambda _p: []))
    app_loader = _Ns(getDefBattleApp=lambda: None, getDefLobbyApp=lambda: None)

    player_obj = _Ns(
        playerVehicleID=77,
        arena=_Ns(bonusType=1, onVehicleHealthChanged=EventStub()),
        vehicleTypeDescriptor=_Ns(type=_Ns(compactDescr=10529, tags=())),
        inputHandler=_Ns(ctrlModeName='arcade'),
        isVehicleAlive=True,
    )

    class RandomEntity(object):
        def getQueueType(self):
            return 1

    lobby_machine = _Ns(visibleState=_Ns(getStateID=lambda: 'subScope/subLayer/hangar/{root}'))
    pe = _Ns(onAvatarReady=EventStub(), onAvatarBecomeNonPlayer=EventStub(),
             onAccountShowGUI=EventStub(), onAvatarBecomePlayer=EventStub())
    cv = _Ns(isPresent=lambda: True, item=_Ns(intCD=10529, level=10), onChanged=EventStub())
    api = StrictAslainApiV2()
    tpl = StrictAslainTemplatesV2()

    deps_map = {'IItemsCache': items_cache, 'IBattleSessionProvider': battle_session, 'IGuiLoader': gui_loader, 'IAppLoader': app_loader}

    modules = {
        'BigWorld': _Ns(callback=bw_callback, cancelCallback=bw_cancel, time=lambda: env['time_now'], isKeyDown=lambda _k: False, player=lambda: player_obj),
        'GUI': _Ns(screenResolution=lambda: (1920, 1080), mcursor=lambda: _Ns(visible=False, position=(0.0, 0.0, 0.0))),
        'Keys': _Ns(KEY_LALT=56, KEY_RALT=184, KEY_TAB=15, KEY_LCONTROL=29, KEY_RCONTROL=157, KEY_LEFTMOUSE=256),
        'PlayerEvents': _Ns(g_playerEvents=pe),
        'CurrentVehicle': _Ns(g_currentVehicle=cv),
        'constants': _Ns(ARENA_BONUS_TYPE=_Ns(REGULAR=1, EPIC_RANDOM=14), AUTH_REALM='EU', QUEUE_TYPE=_Ns(RANDOMS=1)),
        'helpers': _Ns(),
        'helpers.dependency': _Ns(instance=lambda cls: deps_map[cls]),
        'helpers.time_utils': _Ns(getServerUTCTime=lambda: 1700000000.0),
        'skeletons': _Ns(),
        'skeletons.gui': _Ns(),
        'skeletons.gui.shared': _Ns(IItemsCache='IItemsCache'),
        'skeletons.gui.battle_session': _Ns(IBattleSessionProvider='IBattleSessionProvider'),
        'skeletons.gui.impl': _Ns(IGuiLoader='IGuiLoader'),
        'skeletons.gui.app_loader': _Ns(IAppLoader='IAppLoader'),
        'dossiers2': _Ns(),
        'dossiers2.ui': _Ns(),
        'dossiers2.ui.achievements': _Ns(MARK_ON_GUN_RECORD='marksOnGun'),
        'BattleFeedbackCommon': _Ns(BATTLE_EVENT_TYPE=_Ns(RADIO_ASSIST=1, TRACK_ASSIST=2)),
        'gui': _Ns(),
        'gui.battle_control': _Ns(),
        'gui.battle_control.battle_constants': _Ns(FEEDBACK_EVENT_ID=_Ns(PLAYER_DAMAGED_HP_ENEMY=1, PLAYER_ASSIST_TO_KILL_ENEMY=2, PLAYER_ASSIST_TO_STUN_ENEMY=3, DAMAGE_LOG_SUMMARY=4)),
        'gui.battle_control.controllers': _Ns(),
        'gui.battle_control.controllers.feedback_adaptor': _Ns(BattleFeedbackAdaptor=_FeedbackAdaptor),
        'gui.shared': _Ns(EVENT_BUS_SCOPE=_Ns(BATTLE='BATTLE'), g_eventBus=_Ns(addListener=lambda *a, **kw: None, removeListener=lambda *a, **kw: None)),
        'gui.shared.events': _Ns(ViewEventType=_Ns(LOAD_VIEW='LOAD_VIEW'), GameEvent=_Ns(GUI_VISIBILITY='GUI_VISIBILITY', FULL_STATS='FULL_STATS')),
        'gui.Scaleform': _Ns(),
        'gui.Scaleform.lobby_entry': _Ns(getLobbyStateMachine=lambda: lobby_machine),
        'gui.lobby_state_machine': _Ns(),
        'gui.lobby_state_machine.states': _Ns(isHangarState=lambda s: 'hangar' in str(s.getStateID())),
        'gui.prb_control': _Ns(),
        'gui.prb_control.dispatcher': _Ns(g_prbLoader=_Ns(getDispatcher=lambda: _Ns(getEntity=lambda: RandomEntity()))),
        'frameworks': _Ns(),
        'frameworks.wulf': _Ns(
            ViewFlags=_Ns(VIEW=1), ViewModel=_StrictViewModel, ViewSettings=_StrictViewSettings,
            WindowFlags=_Ns(WINDOW=1, TOOLTIP=2, CONTEXT_MENU=3),
            WindowLayer=_Ns(SUB_VIEW=2, TOP_SUB_VIEW=3, WINDOW=4, FULLSCREEN_WINDOW=5, TOP_WINDOW=6, OVERLAY=7),
            WindowStatus=_Ns(DESTROYING=1, DESTROYED=2, LOADING=3, LOADED=4),
        ),
        'gui.impl': _Ns(),
        'gui.impl.gui_decorators': _Ns(args2params=lambda *a: (lambda fn: fn)),
        'gui.impl.pub': _Ns(ViewImpl=_StrictViewImpl, WindowImpl=_TrackedWindow),
        'gui.impl.gen': _Ns(R=_Ns(mods=_Ns(dm=_Ns(threemarks=_Ns(views=_Ns(ThreeMarks=ResAccessorStub(11))))))),
        'gui.aslainMenu': _Ns(g_modsSettingsApi=api, templates=tpl),
        'gui.modsSettingsApi': _Ns(g_modsSettingsApi=api, templates=tpl),
    }

    env.update({
        'modules': modules, 'api': api, 'tpl': tpl, 'pe': pe, 'cv': cv,
        'items_cache': items_cache, 'FeedbackAdaptor': _FeedbackAdaptor,
        'orig_feedback': _FeedbackAdaptor.handleBattleEventsSummary,
        'windows': created_windows, 'flush_callbacks': flush_callbacks,
    })
    return env


def install_modules(modules):
    for mod_name, mod_obj in modules.items():
        if '.' in mod_name:
            parent_name, child_attr = mod_name.rsplit('.', 1)
            parent = modules.get(parent_name)
            if parent is not None:
                setattr(parent, child_attr, mod_obj)
    saved = {}
    for k, v in modules.items():
        saved[k] = sys.modules.get(k)
        sys.modules[k] = v
    return saved


def restore_modules(saved):
    for k, prev in saved.items():
        if prev is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = prev
