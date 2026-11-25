# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging

from CurrentVehicle import g_currentVehicle
from PlayerEvents import g_playerEvents

try:
    from gui.shared import EVENT_BUS_SCOPE, g_eventBus
    from gui.shared import events as gui_events
    EB_OK = True
except Exception:
    EB_OK = False
    EVENT_BUS_SCOPE = g_eventBus = gui_events = None


class WotEventRegistrar(object):
    """Subscribes and cleanly unsubscribes all WoT client events and loggers."""

    def __init__(self, dossier_provider, route_tap,
                 on_avatar_ready, on_avatar_non_player,
                 on_account_show_gui, on_avatar_become_player,
                 on_vehicle_changed, on_sync_completed, on_load_view):
        self._dossier = dossier_provider
        self._route_tap = route_tap
        self._on_avatar_ready = on_avatar_ready
        self._on_avatar_non_player = on_avatar_non_player
        self._on_account_show_gui = on_account_show_gui
        self._on_avatar_become_player = on_avatar_become_player
        self._on_vehicle_changed = on_vehicle_changed
        self._on_sync_completed = on_sync_completed
        self._on_load_view = on_load_view

    def subscribe(self):
        g_playerEvents.onAvatarReady += self._on_avatar_ready
        g_playerEvents.onAvatarBecomeNonPlayer += self._on_avatar_non_player
        g_playerEvents.onAccountShowGUI += self._on_account_show_gui
        g_playerEvents.onAvatarBecomePlayer += self._on_avatar_become_player
        g_currentVehicle.onChanged += self._on_vehicle_changed
        sync_ev = self._dossier.on_sync_completed_event()
        if sync_ev is not None:
            sync_ev += self._on_sync_completed
        if EB_OK:
            try:
                g_eventBus.addListener(gui_events.ViewEventType.LOAD_VIEW, self._on_load_view)
                if hasattr(EVENT_BUS_SCOPE, 'LOBBY'):
                    g_eventBus.addListener(gui_events.ViewEventType.LOAD_VIEW, self._on_load_view, EVENT_BUS_SCOPE.LOBBY)
            except Exception:
                pass
        try:
            logging.getLogger('gui.lobby_state_machine').addHandler(self._route_tap)
        except Exception:
            pass

    def unsubscribe(self):
        for fn in (
            lambda: g_playerEvents.onAvatarReady.__isub__(self._on_avatar_ready),
            lambda: g_playerEvents.onAvatarBecomeNonPlayer.__isub__(self._on_avatar_non_player),
            lambda: g_playerEvents.onAccountShowGUI.__isub__(self._on_account_show_gui),
            lambda: g_playerEvents.onAvatarBecomePlayer.__isub__(self._on_avatar_become_player),
            lambda: g_currentVehicle.onChanged.__isub__(self._on_vehicle_changed),
        ):
            try:
                fn()
            except Exception:
                pass
        try:
            sync_ev = self._dossier.on_sync_completed_event()
            if sync_ev is not None:
                sync_ev -= self._on_sync_completed
        except Exception:
            pass
        if EB_OK:
            try:
                g_eventBus.removeListener(gui_events.ViewEventType.LOAD_VIEW, self._on_load_view)
                if hasattr(EVENT_BUS_SCOPE, 'LOBBY'):
                    g_eventBus.removeListener(gui_events.ViewEventType.LOAD_VIEW, self._on_load_view, EVENT_BUS_SCOPE.LOBBY)
            except Exception:
                pass
        try:
            logging.getLogger('gui.lobby_state_machine').removeHandler(self._route_tap)
        except Exception:
            pass

    @staticmethod
    def bind_battle_gui_visibility(on_gui_vis, on_full_stats):
        if not EB_OK:
            return None
        try:
            from gui.shared.events import GameEvent

            def on_event(event):
                ctx = event.ctx or {}
                if event.eventType == GameEvent.GUI_VISIBILITY:
                    on_gui_vis(ctx.get('visible', True))
                elif event.eventType == GameEvent.FULL_STATS:
                    on_full_stats(ctx.get('shown', False))

            for ev_type in (GameEvent.GUI_VISIBILITY, GameEvent.FULL_STATS):
                g_eventBus.addListener(ev_type, on_event, EVENT_BUS_SCOPE.BATTLE)

            def unbind():
                for ev_type in (GameEvent.GUI_VISIBILITY, GameEvent.FULL_STATS):
                    try:
                        g_eventBus.removeListener(ev_type, on_event, EVENT_BUS_SCOPE.BATTLE)
                    except Exception:
                        pass

            return unbind
        except Exception:
            return None
