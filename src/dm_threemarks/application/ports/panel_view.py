# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IPanelView(object):
    """Port for HUD overlay panels (Gameface window or test stub)."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def build(self):
        raise NotImplementedError

    @abc.abstractmethod
    def push(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def destroy(self):
        raise NotImplementedError

    @abc.abstractmethod
    def move_to(self, x, y):
        raise NotImplementedError

    @abc.abstractmethod
    def contains(self, pos):
        raise NotImplementedError

    @abc.abstractmethod
    def update_visibility(self, hidden=False):
        raise NotImplementedError

    @abc.abstractmethod
    def open_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def close_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_settings_open(self):
        raise NotImplementedError

    @abc.abstractmethod
    def set_mini(self, mini):
        raise NotImplementedError

    @property
    def settings_controller(self):
        return None
