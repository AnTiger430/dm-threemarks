# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..constants import SERVER_HOLD, SERVER_HOUR, SERVER_LATE
from .curve import day_of


class ServerEpoch(object):
    """Tracks which UTC day curve the game servers are actively using."""

    def __init__(self, server_hour=SERVER_HOUR, server_late=SERVER_LATE):
        self._server_hour = float(server_hour)
        self._server_late = float(server_late)
        self.seen_day = 0
        self.seen_at = 0.0
        self._read = {}

    def by_clock(self, now):
        return day_of(now - self._server_hour * 3600.0)

    def holds(self, when, now):
        if not (when > 0 and now - when > -600.0 and day_of(when) == day_of(now)):
            return False
        return now - when < SERVER_HOLD or when % 86400.0 >= self._server_late * 3600.0

    def day(self, now):
        today = day_of(now)
        if self.seen_day >= today:
            return today
        if self.seen_day == today - 1 and self.holds(self.seen_at, now):
            return today - 1
        return self.by_clock(now)

    def witness(self, key, avg, percent, when, day_curve_fn, live_info, calc_version, log_fn=None):
        if not (avg > 0.0 and percent > 0.0 and when > self.seen_at):
            return
        fetched_at = live_info[1] if live_info else 0.0
        newest = live_info[0] if live_info else None
        reading = (avg, percent, when, calc_version, fetched_at)
        if self._read.get(key) == reading:
            return
        self._read[key] = reading
        day = day_of(when)
        fits = []
        for candidate in (day, day - 1):
            curve = day_curve_fn(key, candidate, newest)
            if curve is None or not curve.exact:
                return
            if curve.explains(avg, percent):
                fits.append(candidate)
        if len(fits) == 1:
            self.seen_day, self.seen_at = fits[0], float(when)
            if log_fn is not None:
                log_fn('servers on the curve of day %d at %d (tank %s)' % (fits[0], when, key))
