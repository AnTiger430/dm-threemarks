# -*- coding: utf-8 -*-
from __future__ import absolute_import

import time

import BigWorld

from ...application.ports.clock import IClock


class WotClock(IClock):
    """Concrete clock reading OS time, server UTC time, and BigWorld frame time."""

    def now(self):
        return time.time()

    def server_now(self):
        try:
            from helpers import time_utils
            return float(time_utils.getServerUTCTime())
        except Exception:
            return time.time()

    def battle_time(self):
        return BigWorld.time()
