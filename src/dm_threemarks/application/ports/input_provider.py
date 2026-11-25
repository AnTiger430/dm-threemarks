# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IInputProvider(object):
    """Port for keyboard, mouse cursor, screen geometry, and battle camera state."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def is_alt_down(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_ctrl_down(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_tab_down(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_lmb_down(self):
        raise NotImplementedError

    @abc.abstractmethod
    def cursor_position(self):
        raise NotImplementedError

    @abc.abstractmethod
    def screen_size(self):
        raise NotImplementedError

    @abc.abstractmethod
    def px_w(self, px):
        raise NotImplementedError

    @abc.abstractmethod
    def px_h(self, px):
        raise NotImplementedError

    @abc.abstractmethod
    def is_sniper_mode(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_intro_active(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_killcam_active(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_player_dead(self):
        raise NotImplementedError
