# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IMasteryGateway(object):
    """Port for fetching WG mastery curves and Poliroid daily history asynchronously."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def is_available(self):
        raise NotImplementedError

    @abc.abstractmethod
    def request_curve(self, key, domain, app_id):
        raise NotImplementedError

    @abc.abstractmethod
    def request_history(self, key, domain):
        raise NotImplementedError

    @abc.abstractmethod
    def drain_results(self):
        raise NotImplementedError
