# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from ...application.ports.config_repository import IConfigRepository


class FileConfigRepository(IConfigRepository):
    """Persists config.json and config_help.txt in WoT mods/configs/three_marks/."""

    def __init__(self, config_dir, json_store, logger=None):
        self._dir = config_dir
        self._path = os.path.join(config_dir, 'config.json')
        self._help_path = os.path.join(config_dir, 'config_help.txt')
        self._store = json_store
        self._logger = logger

    def load(self):
        return self._store.load_json(self._path, None)

    def save(self, data):
        return self._store.save_json(self._path, data, pretty=True)

    def get_mtime(self):
        return self._store.mtime(self._path)

    def write_help(self, mod_version, help_text):
        try:
            if not os.path.isdir(self._dir):
                os.makedirs(self._dir)
            if not os.path.isfile(self._help_path) or mod_version not in self._store.load_text(self._help_path)[:300]:
                with open(self._help_path, 'wb') as f:
                    f.write((u'[%s]\n' % mod_version + help_text).encode('utf-8'))
        except Exception:
            if self._logger is not None:
                self._logger.error('config help')
