# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IClock(object):
    """Port for wall clock, server UTC clock, and battle monotonic clock."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def now(self):
        raise NotImplementedError

    @abc.abstractmethod
    def server_now(self):
        raise NotImplementedError

    @abc.abstractmethod
    def battle_time(self):
        raise NotImplementedError
