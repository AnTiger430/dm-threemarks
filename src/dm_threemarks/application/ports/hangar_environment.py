# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IHangarEnvironment(object):
    """Port inspecting WoT hangar lobby state, queue mode, and overlapping views."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def hangar_state(self):
        raise NotImplementedError

    @abc.abstractmethod
    def hangar_mode(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_covered(self, own_window):
        raise NotImplementedError

    @abc.abstractmethod
    def view_class_names(self):
        raise NotImplementedError
