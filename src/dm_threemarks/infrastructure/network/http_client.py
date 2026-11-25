# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json

try:
    import urllib2
except ImportError:
    urllib2 = None


class HttpJsonClient(object):
    """HTTP GET JSON client wrapping Python 2.7 urllib2."""

    def __init__(self, user_agent, timeout=10):
        self._user_agent = user_agent
        self._timeout = timeout

    def is_available(self):
        return urllib2 is not None

    def get_json(self, url):
        if urllib2 is None:
            raise RuntimeError('urllib2 unavailable')
        request = urllib2.Request(url, headers={'User-Agent': self._user_agent})
        response = urllib2.urlopen(request, timeout=self._timeout)
        try:
            return json.loads(response.read())
        finally:
            response.close()
