# -*- coding: utf-8 -*-
from __future__ import absolute_import

import threading


class BackgroundWorkerQueue(object):
    """Thread-safe FIFO result queue with daemon thread spawner."""

    def __init__(self):
        self._results = []
        self._lock = threading.Lock()

    def post(self, item):
        with self._lock:
            self._results.append(item)

    def drain(self):
        with self._lock:
            if not self._results:
                return []
            items = list(self._results)
            del self._results[:]
            return items

    @staticmethod
    def spawn(target, args):
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        thread.start()
