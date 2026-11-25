# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IConfigRepository(object):
    """Port for persisting and reloading user configuration."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self):
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def get_mtime(self):
        raise NotImplementedError

    @abc.abstractmethod
    def write_help(self, mod_version, help_text):
        raise NotImplementedError
