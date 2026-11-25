# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.config.defaults import LESTA_API_URL, WG_API_URL, WG_HISTORY_URL
from ...application.ports.mastery_gateway import IMasteryGateway
from ...domain.constants import ANCHORS, API_DAY_LAG, EPOCH_DAY
from ...domain.entities.curve import day_number


class WgPoliroidMasteryGateway(IMasteryGateway):
    """Asynchronous gateway to WG/Lesta Mastery API and Poliroid gunmarks curves."""

    def __init__(self, http_client, worker_queue):
        self._http = http_client
        self._queue = worker_queue

    def is_available(self):
        return self._http.is_available()

    def request_curve(self, key, domain, app_id):
        self._queue.spawn(self._curve_worker, (key, domain, app_id))

    def request_history(self, key, domain):
        self._queue.spawn(self._history_worker, (key, domain))

    def drain_results(self):
        return self._queue.drain()

    def _fetch_official_curve(self, key, domain, app_id):
        points, stamps = {}, set()
        for start in xrange(1, 101, 10):
            batch = '%2C'.join(str(p) for p in xrange(start, min(start + 10, 101)))
            url = (LESTA_API_URL % (app_id, batch, key)) if domain == 'ru' else (WG_API_URL % (domain, app_id, batch, key))
            payload = self._http.get_json(url)
            if payload.get('status') != 'ok':
                raise ValueError((payload.get('error') or {}).get('message') or 'status not ok')
            data = payload.get('data') or {}
            try:
                stamps.add(int(float(data.get('updated_at') or 0)))
            except (TypeError, ValueError):
                stamps.add(0)
            record = (data.get('distribution') or {}).get(key) or {}
            for percentile, damage in record.items():
                try:
                    points[str(int(percentile))] = int(round(float(damage)))
                except (TypeError, ValueError):
                    pass
        if len(stamps) > 1:
            raise ValueError('the curve changed while it was being read')
        if not points:
            raise ValueError('no distribution in official API answer')
        return points, (stamps.pop() if len(stamps) == 1 else 0)

    def _fetch_poliroid_latest_curve(self, key, domain):
        url = WG_HISTORY_URL % (domain, key, ','.join(str(p) for p in ANCHORS))
        payload = self._http.get_json(url)
        if payload.get('status') != 'ok':
            raise ValueError((payload.get('error') or {}).get('message') or 'status not ok')
        best_ord = None
        best_points = None
        for row in (payload.get('data') or {}).get('data') or []:
            try:
                ord_day = day_number(str(row['date']))
                marks = row.get('marks') or {}
                pts = {}
                for p in ANCHORS:
                    val = int(round(float(marks[str(p)])))
                    if val <= 0:
                        raise ValueError('non-positive anchor')
                    pts[str(p)] = val
            except Exception:
                continue
            if best_ord is None or ord_day > best_ord:
                best_ord, best_points = ord_day, pts
        if best_points is None:
            raise ValueError('no distribution in Poliroid answer')
        updated = (best_ord - EPOCH_DAY - API_DAY_LAG) * 86400 + 43200
        return best_points, updated

    def _curve_worker(self, key, domain, app_id):
        points, updated, error = {}, 0, None
        try:
            if domain == 'ru':
                if app_id:
                    try:
                        points, updated = self._fetch_official_curve(key, 'ru', app_id)
                    except Exception:
                        points, updated = self._fetch_poliroid_latest_curve(key, 'ru')
                else:
                    points, updated = self._fetch_poliroid_latest_curve(key, 'ru')
            else:
                if app_id:
                    try:
                        points, updated = self._fetch_official_curve(key, domain, app_id)
                    except Exception:
                        points, updated = self._fetch_poliroid_latest_curve(key, domain)
                else:
                    points, updated = self._fetch_poliroid_latest_curve(key, domain)
        except Exception as err:
            error = '%s: %s' % (type(err).__name__, err)
        self._queue.post(('curve', key, points, updated, error))

    def _history_worker(self, key, domain):
        rows, answered, error = {}, False, None
        try:
            url = WG_HISTORY_URL % (domain, key, ','.join(str(p) for p in ANCHORS))
            payload = self._http.get_json(url)
            answered = True
            if payload.get('status') != 'ok':
                raise ValueError((payload.get('error') or {}).get('message') or 'status not ok')
            for row in (payload.get('data') or {}).get('data') or []:
                try:
                    day = str(row['date'])
                    day_number(day)
                    marks = row.get('marks') or {}
                    values = [int(round(float(marks[str(p)]))) for p in ANCHORS]
                except Exception:
                    continue
                if min(values) > 0:
                    rows[day] = values
        except Exception as err:
            error = '%s: %s' % (type(err).__name__, err)
        self._queue.post(('history', key, rows, answered, error))
