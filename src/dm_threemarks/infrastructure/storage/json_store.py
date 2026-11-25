# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os


class JsonFileStore(object):
    """Atomic UTF-8 JSON file persistence helper."""

    def __init__(self, base_dir, logger=None):
        self._dir = base_dir
        self._logger = logger

    @staticmethod
    def mtime(path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    @staticmethod
    def load_text(path):
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', 'replace')

    def load_json(self, path, default):
        try:
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    return json.loads(f.read().decode('utf-8'))
        except Exception:
            pass
        return default

    def save_json(self, path, data, pretty=False):
        try:
            if not os.path.isdir(self._dir):
                os.makedirs(self._dir)
            if pretty:
                raw = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, separators=(',', ': ')).encode('utf-8')
            else:
                raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
            tmp = path + '.tmp'
            with open(tmp, 'wb') as f:
                f.write(raw)
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
            return True
        except Exception:
            if self._logger is not None:
                self._logger.error('save %s' % path)
            return False
