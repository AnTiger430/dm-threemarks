# -*- coding: utf-8 -*-
from __future__ import absolute_import

import BigWorld
import GUI
import Keys

from ...application.ports.input_provider import IInputProvider

_DEAD_MODES = ('postmortem', 'deathfreecam', 'killcam', 'deathcam')


class WotInputProvider(IInputProvider):
    """Reads WoT keyboard/cursor state, screen dimensions, camera mode, and life state."""

    def __init__(self, logger=None):
        self._logger = logger

    def is_alt_down(self):
        try:
            for name in ('KEY_LALT', 'KEY_RALT'):
                key = getattr(Keys, name, None)
                if key is not None and bool(BigWorld.isKeyDown(key)):
                    return True
        except Exception:
            pass
        return False

    def is_ctrl_down(self):
        return bool(BigWorld.isKeyDown(Keys.KEY_LCONTROL) or BigWorld.isKeyDown(Keys.KEY_RCONTROL))

    def is_tab_down(self):
        try:
            return bool(BigWorld.isKeyDown(Keys.KEY_TAB))
        except Exception:
            return False

    def is_lmb_down(self):
        return bool(BigWorld.isKeyDown(Keys.KEY_LEFTMOUSE))

    def cursor_position(self):
        return GUI.mcursor().position[:2]

    def screen_size(self):
        try:
            w, h = GUI.screenResolution()[:2]
            return (float(w), float(h))
        except Exception:
            return (1920.0, 1080.0)

    def px_w(self, px):
        return float(px) * 2.0 / self.screen_size()[0]

    def px_h(self, px):
        return float(px) * 2.0 / self.screen_size()[1]

    def ctrl_mode_name(self):
        try:
            player = BigWorld.player()
            handler = getattr(player, 'inputHandler', None) if player is not None else None
            name = str(getattr(handler, 'ctrlModeName', '') or '')
        except Exception:
            return ''
        if name and self._logger is not None:
            self._logger.once(('ctrlmode', name), 'battle control mode: %s' % name)
        return name

    def is_sniper_mode(self):
        try:
            return self.ctrl_mode_name().lower() == 'sniper'
        except Exception:
            return False

    def is_intro_active(self):
        name = self.ctrl_mode_name()
        if name and 'prebattle' in name.replace('_', '').lower():
            return True, 'control mode %s' % name
        return False, ''

    def is_killcam_active(self):
        name = self.ctrl_mode_name()
        if not name:
            return False, ''
        low = name.replace('_', '').lower()
        if 'kill' in low or ('death' in low and low != 'deathfreecam'):
            return True, 'control mode %s' % name
        return False, ''

    def is_player_dead(self):
        try:
            player = BigWorld.player()
            if player is not None:
                if getattr(player, 'isVehicleAlive', None) is False:
                    return True, 'player.isVehicleAlive=False'
                arena = getattr(player, 'arena', None)
                vid = getattr(player, 'playerVehicleID', None)
                if arena is not None and vid is not None:
                    vinfo = (arena.vehicles or {}).get(vid)
                    if isinstance(vinfo, dict) and vinfo.get('isAlive') is False:
                        return True, 'arena.vehicles[self].isAlive=False'
        except Exception:
            pass
        name = self.ctrl_mode_name()
        if name and any(m in name.lower() for m in _DEAD_MODES):
            return True, 'control mode %s' % name
        return False, ''
