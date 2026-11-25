# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from ...application.ports.cache_repository import ICacheRepository


class FileCacheRepository(ICacheRepository):
    """Manages per-vehicle curve/history cache in memory and serializes to cache.json."""

    def __init__(self, config_dir, json_store):
        self._path = os.path.join(config_dir, 'cache.json')
        self._store = json_store
        self._data = {}

    def load(self):
        loaded = self._store.load_json(self._path, {})
        if not isinstance(loaded, dict):
            loaded = {}
        loaded.pop('__historyPending', None)
        self._data = loaded
        return self._data

    def save(self):
        return self._store.save_json(self._path, self._data, pretty=False)

    def get_entry(self, key):
        entry = self._data.get(key)
        if not isinstance(entry, dict):
            entry = {}
            self._data[key] = entry
        return entry

    def peek_entry(self, key):
        return self._data.get(key)

    def get_all(self):
        return self._data

    def replace_all(self, data):
        self._data = dict(data) if isinstance(data, dict) else {}
