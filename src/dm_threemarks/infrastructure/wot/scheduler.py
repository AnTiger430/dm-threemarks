# -*- coding: utf-8 -*-
from __future__ import absolute_import

import BigWorld

from ...application.ports.scheduler import IScheduler


class WotScheduler(IScheduler):
    """BigWorld main-thread callback scheduler."""

    def schedule(self, delay_sec, callback):
        return BigWorld.callback(delay_sec, callback)

    def cancel(self, handle):
        if handle is not None:
            try:
                BigWorld.cancelCallback(handle)
            except Exception:
                pass
