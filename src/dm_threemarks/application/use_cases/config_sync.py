# -*- coding: utf-8 -*-
from __future__ import absolute_import


class ConfigSyncService(object):
    """Detects external edits to config.json on disk while preserving panel positions."""

    def __init__(self, config_repo, config_store, clock, logger, menu_port=None):
        self._repo = config_repo
        self._config = config_store
        self._clock = clock
        self._logger = logger
        self._menu = menu_port
        self._last_stamp = 0.0
        self._last_polled = 0.0

    def sync_stamp(self):
        self._last_stamp = self._repo.get_mtime()

    def load_initial(self):
        stored = self._repo.load()
        cfg = self._config.replace_normalized(stored)
        self._repo.save(cfg)
        self.sync_stamp()

    def save_current(self):
        self._repo.save(self._config.snapshot())
        self.sync_stamp()

    def poll(self):
        if self._config.settings_open:
            return False
        now = self._clock.now()
        if now - self._last_polled < 2.0:
            return False
        self._last_polled = now
        stamp = self._repo.get_mtime()
        if not stamp or stamp == self._last_stamp:
            return False
        before = self._config.snapshot()
        stored = self._repo.load()
        cfg = self._config.replace_normalized(stored)
        for key in ('x', 'y', 'hx', 'hy'):
            cfg[key] = before.get(key, cfg.get(key))
        self._last_stamp = stamp
        self._logger.info('config reloaded')
        if self._menu is not None:
            self._menu.push_values()
        return True
