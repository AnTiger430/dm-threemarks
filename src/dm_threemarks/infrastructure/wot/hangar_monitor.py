# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging

from ...application.ports.hangar_environment import IHangarEnvironment

try:
    from frameworks.wulf import WindowFlags, WindowLayer, WindowStatus
    from skeletons.gui.impl import IGuiLoader
    from helpers import dependency
    _WULF_OK = True
except Exception:
    _WULF_OK = False
    WindowFlags = WindowLayer = WindowStatus = IGuiLoader = dependency = None

_HANGAR_STATE_IDS = (
    'subScope/subLayer/hangar',
    'subScope/subLayer/hangar/{root}',
    'subScope/subLayer/legacyHangar',
)
_SETUP_ROUTE_KEYWORDS = ('tank_setup', 'tanksetup', 'ammunition_setup', 'ammunitionsetup', '/setup')
_LESTA_HANGAR_WIDGETS = ('HangarAmmunitionPanelView', 'HangarCrewWidget')


class WotHangarEnvironment(IHangarEnvironment):
    """Inspects WoT lobby state machine, queue type, WULF coverage, and view classes."""

    def hangar_state(self):
        try:
            from gui.Scaleform.lobby_entry import getLobbyStateMachine
            machine = getLobbyStateMachine()
        except Exception:
            machine = None
        if machine is not None:
            state_id = ''
            try:
                state = machine.visibleState
                state_id = str(state.getStateID()) if state is not None else ''
            except Exception:
                pass
            try:
                from gui.lobby_state_machine.states import isHangarState
                return (bool(isHangarState(machine.visibleState)), state_id)
            except Exception:
                pass
            if state_id:
                return (state_id in _HANGAR_STATE_IDS, state_id)
        try:
            from skeletons.gui.app_loader import IAppLoader
            lobby_app = dependency.instance(IAppLoader).getDefLobbyApp()
            cm = getattr(lobby_app, 'containerManager', None) if lobby_app is not None else None
            if cm is not None and WindowLayer is not None:
                get_container = getattr(cm, 'getContainer', None)
                for top_name in ('TOP_SUB_VIEW', 'LOBBY_TOP_SUB_VIEW', 'FULLSCREEN_WINDOW'):
                    layer = getattr(WindowLayer, top_name, None)
                    if layer is None:
                        continue
                    if callable(get_container):
                        container = get_container(layer)
                        if container is None:
                            continue
                        if type(container).__name__ == 'SingleViewContainer':
                            top_view = container.getView()
                            top_alias = getattr(top_view, 'alias', None) if top_view is not None else None
                            if isinstance(top_alias, basestring) and top_alias and top_alias.lower() != 'hangar':
                                return (False, str(top_alias))
                        else:
                            get_count = getattr(container, 'getViewCount', None)
                            if callable(get_count):
                                cnt = get_count()
                                if isinstance(cnt, (int, long)) and cnt > 0:
                                    return (False, top_name.lower())
                    else:
                        top_view = cm.getView(layer)
                        top_alias = getattr(top_view, 'alias', None) if top_view is not None else None
                        if isinstance(top_alias, basestring) and top_alias and top_alias.lower() != 'hangar':
                            return (False, str(top_alias))
                for sub_name in ('SUB_VIEW', 'LOBBY_SUB_VIEW'):
                    layer = getattr(WindowLayer, sub_name, None)
                    if layer is None:
                        continue
                    if callable(get_container):
                        container = get_container(layer)
                        if container is None or type(container).__name__ != 'SingleViewContainer':
                            continue
                        sub_view = container.getView()
                    else:
                        sub_view = cm.getView(layer)
                    alias = getattr(sub_view, 'alias', None) if sub_view is not None else None
                    if isinstance(alias, basestring) and alias:
                        return (alias.lower() == 'hangar', str(alias))
        except Exception:
            pass
        if _WULF_OK and dependency is not None and IGuiLoader is not None:
            try:
                gui_loader = dependency.instance(IGuiLoader)
                windows_mgr = getattr(gui_loader, 'windowsManager', None) if gui_loader is not None else None
                if windows_mgr is not None and WindowLayer is not None:
                    top_layers = set(l for l in (getattr(WindowLayer, n, None) for n in (
                        'TOP_SUB_VIEW', 'LOBBY_TOP_SUB_VIEW', 'FULLSCREEN_WINDOW')) if l is not None)
                    sub_layers = set(l for l in (getattr(WindowLayer, n, None) for n in (
                        'SUB_VIEW', 'LOBBY_SUB_VIEW')) if l is not None)
                    top_block = None
                    sub_alias = None
                    for win in windows_mgr.findWindows(lambda item: True) or ():
                        if WindowStatus is not None and getattr(win, 'windowStatus', None) not in (
                                WindowStatus.LOADING, WindowStatus.LOADED):
                            continue
                        is_hidden = getattr(win, 'isHidden', None)
                        if callable(is_hidden) and is_hidden():
                            continue
                        alias = getattr(getattr(win, 'viewKey', None), 'alias', None)
                        if not (isinstance(alias, basestring) and alias):
                            continue
                        layer = getattr(win, 'layer', None)
                        if layer in top_layers and alias.lower() != 'hangar':
                            top_block = str(alias)
                        elif layer in sub_layers:
                            if sub_alias is None or alias.lower() != 'hangar':
                                sub_alias = str(alias)
                    if top_block:
                        return (False, top_block)
                    find_views = getattr(windows_mgr, 'findViews', None)
                    if callable(find_views):
                        views = find_views(lambda item: True) or ()
                        if views:
                            if any(type(v).__name__ in _LESTA_HANGAR_WIDGETS for v in views):
                                return (True, 'hangar')
                            return (False, sub_alias if (sub_alias and sub_alias.lower() != 'hangar') else 'not_hangar')
                    if sub_alias:
                        return (sub_alias.lower() == 'hangar', sub_alias)
            except Exception:
                pass
        return (None, '')

    def hangar_mode(self):
        queue_type = None
        desc = path = ''
        try:
            from gui.prb_control.dispatcher import g_prbLoader
            dispatcher = g_prbLoader.getDispatcher()
            entity = dispatcher.getEntity() if dispatcher is not None else None
            if entity is not None:
                cls = type(entity)
                path = '%s.%s' % (cls.__module__, cls.__name__)
                desc = path
                getter = getattr(entity, 'getQueueType', None)
                if getter is not None:
                    queue_type = getter()
        except Exception:
            pass
        if not queue_type:
            try:
                from gui.prb_control import prb_getters
                queue_type = prb_getters.getQueueType()
            except Exception:
                pass
        low = path.lower()
        if '.random.' in low or low.endswith('squad.entity.squadentity'):
            return (True, '%s queue=%s' % (desc, queue_type))
        if not queue_type:
            return (None, desc)
        try:
            from constants import QUEUE_TYPE
            return (queue_type == QUEUE_TYPE.RANDOMS, '%s queue=%s' % (desc, queue_type))
        except Exception:
            return (None, desc)

    def is_covered(self, own_window):
        if not _WULF_OK or dependency is None or IGuiLoader is None:
            return False
        try:
            windows_mgr = dependency.instance(IGuiLoader).windowsManager
            layers = [getattr(WindowLayer, name, None) for name in (
                'TOP_SUB_VIEW', 'WINDOW', 'FULLSCREEN_WINDOW', 'TOP_WINDOW', 'OVERLAY')]
            layers = [layer for layer in layers if layer is not None]

            def predicate(window):
                try:
                    if window is own_window or window.layer not in layers:
                        return False
                    if window.windowStatus not in (WindowStatus.LOADING, WindowStatus.LOADED):
                        return False
                    if window.typeFlag in (WindowFlags.TOOLTIP, WindowFlags.CONTEXT_MENU):
                        return False
                    if window.isHidden():
                        return False
                    size = window.size
                    return size[0] > 1000 and size[1] > 600
                except Exception:
                    return False

            return bool(windows_mgr.findWindows(predicate))
        except Exception:
            return False

    def view_class_names(self):
        if not _WULF_OK or dependency is None or IGuiLoader is None:
            return None
        try:
            windows_mgr = dependency.instance(IGuiLoader).windowsManager
            names = set()
            for view in windows_mgr.findViews(lambda item: True) or ():
                cls = type(view)
                names.add('%s.%s' % (cls.__module__, cls.__name__))
            return names
        except Exception:
            return None


class WotLobbyRouteTap(logging.Handler):
    """Listens to lobby_state_machine route changes to block hangar panel outside /hangar."""

    def __init__(self, on_blocked, logger):
        super(WotLobbyRouteTap, self).__init__()
        self._on_blocked = on_blocked
        self._logger = logger

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return
        if 'Visible route changed' not in msg:
            return
        try:
            low = msg.lower()
            self._logger.once(('route', low[:240]), 'route: %s' % msg[:240])
            if any(k in low for k in _SETUP_ROUTE_KEYWORDS):
                self._on_blocked(True)
            elif '/hangar' in low:
                self._on_blocked(False)
            else:
                self._on_blocked(True)
        except Exception:
            pass
