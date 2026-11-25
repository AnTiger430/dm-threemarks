# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IScheduler(object):
    """Port for main-thread delayed callbacks."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def schedule(self, delay_sec, callback):
        raise NotImplementedError

    @abc.abstractmethod
    def cancel(self, handle):
        raise NotImplementedError
