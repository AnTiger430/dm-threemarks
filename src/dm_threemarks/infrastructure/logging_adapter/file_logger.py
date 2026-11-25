# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import time
import traceback

from ...application.ports.logger import ILogger


class ModFileLogger(ILogger):
    """Thread-safe/main-thread file and stdout diagnostic logger implementing ILogger."""

    LIMIT = 200 * 1024

    def __init__(self, log_dir, log_filename='three_marks.log'):
        self._dir = log_dir
        self._path = os.path.join(log_dir, log_filename)
        self._seen = set()

    def info(self, msg):
        try:
            if isinstance(msg, unicode):
                msg = msg.encode('utf-8')
            line = '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
            print('[ThreeMarks] ' + str(msg))
            if not os.path.isdir(self._dir):
                os.makedirs(self._dir)
            if os.path.isfile(self._path) and os.path.getsize(self._path) > self.LIMIT:
                with open(self._path, 'rb') as f:
                    f.seek(-self.LIMIT // 2, 2)
                    tail = f.read()
                with open(self._path, 'wb') as f:
                    f.write(tail[tail.find('\n') + 1:])
            with open(self._path, 'ab') as f:
                f.write(line + '\n')
        except Exception:
            pass

    def once(self, key, msg):
        if key not in self._seen:
            self._seen.add(key)
            self.info(msg)

    def error(self, where):
        try:
            text = traceback.format_exc().strip().splitlines()
            self.once(
                ('err', where, text[-1] if text else ''),
                'ERROR in %s: %s' % (where, ' | '.join(text[-3:])),
            )
        except Exception:
            pass
