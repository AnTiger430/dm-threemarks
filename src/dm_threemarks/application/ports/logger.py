# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class ILogger(object):
    """Port for diagnostic mod logging."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def info(self, msg):
        raise NotImplementedError

    @abc.abstractmethod
    def once(self, key, msg):
        raise NotImplementedError

    @abc.abstractmethod
    def error(self, where):
        raise NotImplementedError
