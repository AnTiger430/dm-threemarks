# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class ISettingsMenu(object):
    """Port for external Mod Settings Menu (Aslain / ModsSettingsAPI)."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def register(self):
        raise NotImplementedError

    @abc.abstractmethod
    def unregister(self):
        raise NotImplementedError

    @abc.abstractmethod
    def push_values(self):
        raise NotImplementedError

    @abc.abstractmethod
    def refresh_preview(self):
        raise NotImplementedError

    @abc.abstractmethod
    def sync_tabs(self, force=False):
        raise NotImplementedError

    @abc.abstractmethod
    def is_registered(self):
        raise NotImplementedError

    @abc.abstractmethod
    def set_hardware_alt(self, active):
        raise NotImplementedError

    @abc.abstractmethod
    def swap_settings_page(self, panel):
        raise NotImplementedError
