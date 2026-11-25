# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class ICacheRepository(object):
    """Port for per-vehicle curve/history/forecast cache persistence."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self):
        raise NotImplementedError

    @abc.abstractmethod
    def save(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_entry(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def peek_entry(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def get_all(self):
        raise NotImplementedError

    @abc.abstractmethod
    def replace_all(self, data):
        raise NotImplementedError
