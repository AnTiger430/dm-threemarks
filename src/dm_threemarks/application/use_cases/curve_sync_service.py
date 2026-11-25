# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...domain.constants import (
    ANCHORS,
    API_DAY_LAG,
    CURVE_RECHECK,
    CURVE_TTL,
    EPOCH_DAY,
    FETCH_RETRY,
    HISTORY_DAYS,
    HISTORY_RETRY,
)
from ...domain.entities.curve import Curve, api_day, day_number, day_of, day_text, utc_day_text


class CurveSyncService(object):
    """Coordinates live curve caching, Poliroid history snapshots, and async fetch requests."""

    def __init__(self, cache_repo, gateway, dossier_provider, config_store, clock, logger):
        self._cache = cache_repo
        self._gateway = gateway
        self._dossier = dossier_provider
        self._config = config_store
        self._clock = clock
        self._logger = logger
        self._calc_version = 0
        self._live = {}
        self._pending = set()
        self._failed = {}
        self._empty = {}
        self._restamped = set()
        self._hist_pending = set()
        self._hist_failed = {}
        self._day_cache = {}

    @property
    def version(self):
        return self._calc_version

    def live_info(self, key):
        return self._live.get(key)

    def _history_curve(self, key):
        entry = self._cache.peek_entry(key)
        history = entry.get('curveHistory') if isinstance(entry, dict) else None
        if not isinstance(history, dict):
            return None
        for day in sorted(history, reverse=True):
            try:
                from ...domain.entities.curve import day_number
                curve = Curve.from_row(history[day], day_number(day))
            except (ValueError, TypeError):
                curve = None
            if curve:
                return curve
        return None

    def _cached_curve(self, key):
        got = self._live.get(key)
        if got is not None:
            return got
        entry = self._cache.peek_entry(key)
        stored = entry.get('curve') if isinstance(entry, dict) else None
        if isinstance(stored, dict):
            now = self._clock.now()
            curve = Curve(stored.get('p') or {}, api_day(stored.get('u'), now=now))
            if curve:
                got = (curve, float(stored.get('t', 0) or 0))
                self._live[key] = got
                return got
        return None

    def curve_for(self, int_cd):
        if not int_cd:
            return None
        key = str(int_cd)
        got = self._cached_curve(key)
        if got is None:
            self.request_curve(key)
            return self._history_curve(key)
        curve, fetched_at = got
        now = self._clock.now()
        age = now - fetched_at
        unstamped = curve.day is None and key not in self._restamped
        if unstamped:
            self._restamped.add(key)
        if age > CURVE_TTL or unstamped or \
                ((curve.day is None or curve.day < day_of(now)) and age > CURVE_RECHECK):
            self.request_curve(key)
        return curve

    def is_pending(self, int_cd):
        key = str(int_cd)
        return (key in self._pending) or (key in self._hist_pending)

    def request_calc(self, int_cd):
        self.ensure_history(str(int_cd))
        self.curve_for(int_cd)

    def request_curve(self, key):
        if not self._gateway.is_available() or key in self._pending:
            return
        wait = FETCH_RETRY * (2 ** min(4, max(0, self._empty.get(key, 0) - 1)))
        if self._clock.now() - self._failed.get(key, 0.0) < wait:
            return
        domain = self._dossier.get_realm_domain()
        if domain == 'ru':
            app_id = str(self._config.get('lestaApiApplicationId', '') or '').strip()
            if not app_id and key in self._hist_pending:
                return
        else:
            app_id = str(self._config.get('wgApiApplicationId', '') or '').strip()
            if not app_id:
                self._logger.once('noappid', 'wgApiApplicationId is empty in config.json - no curves can be loaded')
                return
        self._pending.add(key)
        self._gateway.request_curve(key, domain, app_id)

    def ensure_history(self, key):
        if not self._gateway.is_available() or not self._config.get('onlineHistory', True):
            return
        now = self._clock.now()
        if key in self._hist_pending or now - self._hist_failed.get(key, 0.0) < HISTORY_RETRY:
            return
        if self._cache.get_entry(key).get('histFetched') == utc_day_text(now):
            return
        self._hist_pending.add(key)
        self._gateway.request_history(key, self._dossier.get_realm_domain())

    def day_curve(self, key, number, newest=None):
        if newest is not None and newest.day == number:
            return newest
        cached = self._day_cache.get((key, number))
        if cached is not None and cached[0] == self._calc_version:
            return cached[1]
        curve = None
        entry = self._cache.peek_entry(key)
        history = entry.get('curveHistory') if isinstance(entry, dict) else None
        if isinstance(history, dict):
            try:
                curve = Curve.from_row(history.get(day_text(number)), number)
            except (ValueError, OverflowError):
                curve = None
        if len(self._day_cache) > 64:
            self._day_cache.clear()
        self._day_cache[(key, number)] = (self._calc_version, curve)
        return curve

    def _snapshot_curve(self, entry, points, updated, now):
        try:
            values = [int(points[str(p)]) for p in ANCHORS]
        except (KeyError, TypeError, ValueError):
            return
        served = api_day(updated, now=now)
        day = day_text(served) if served else utc_day_text(now)
        history = entry.get('curveHistory')
        if not isinstance(history, dict):
            history = {}
        if day not in history:
            history[day] = values
            entry['curveHistory'] = history

    def _apply_curve(self, key, points, updated, error):
        self._pending.discard(key)
        now = self._clock.now()
        curve = Curve(points, api_day(updated, now=now)) if points else None
        if error is not None or not curve:
            self._failed[key] = now
            if error is None:
                self._empty[key] = self._empty.get(key, 0) + 1
            self._logger.once(
                ('curvefail', key, error),
                'curve for tank %s not loaded: %s' % (key, error or 'no distribution in the answer'),
            )
            return False
        entry = self._cache.get_entry(key)
        entry['curve'] = {'t': now, 'p': points}
        if updated:
            entry['curve']['u'] = updated
        self._live[key] = (curve, now)
        self._empty.pop(key, None)
        self._snapshot_curve(entry, points, updated, now)
        self._logger.info('curve loaded for tank %s%s' % (
            key, '' if curve.exact else ' (NOT the eight-knot shape, read as served)'))
        return True

    def _apply_history(self, key, rows, answered, error):
        self._hist_pending.discard(key)
        now = self._clock.now()
        if not answered:
            self._hist_failed[key] = now
            self._logger.once(('histfail', key, error), 'history for tank %s unavailable: %s' % (key, error))
            return False
        entry = self._cache.get_entry(key)
        history = entry.get('curveHistory')
        if not isinstance(history, dict):
            history = {}
        history.update(rows)
        for day in sorted(history)[:-HISTORY_DAYS]:
            del history[day]
        entry['curveHistory'] = history
        entry['histFetched'] = utc_day_text(now)
        if error is not None or not rows:
            self._logger.once(('histempty', key), 'history for tank %s: no usable rows (%s)' % (key, error))
        else:
            self._logger.info('history loaded for tank %s (%d days)' % (key, len(rows)))
            if self._dossier.get_realm_domain() == 'ru' and not str(self._config.get('lestaApiApplicationId', '') or '').strip():
                try:
                    best_day = max(rows.keys())
                    pts = dict((str(p), int(round(float(v)))) for p, v in zip(ANCHORS, rows[best_day]))
                    updated = (day_number(best_day) - EPOCH_DAY - API_DAY_LAG) * 86400 + 43200
                    curve = Curve(pts, api_day(updated, now=now))
                    if curve:
                        entry['curve'] = {'t': now, 'p': pts, 'u': updated}
                        self._live[key] = (curve, now)
                        self._empty.pop(key, None)
                        self._pending.discard(key)
                        self._logger.info('curve loaded for tank %s (from history)' % key)
                except Exception:
                    pass
        return True

    def pump(self):
        items = self._gateway.drain_results()
        if not items:
            return False
        changed = False
        for item in items:
            try:
                if item[0] == 'curve':
                    changed = self._apply_curve(*item[1:]) or changed
                elif item[0] == 'history':
                    changed = self._apply_history(*item[1:]) or changed
            except Exception:
                self._logger.error('apply %s' % item[0])
        if changed:
            self._calc_version += 1
            self._cache.save()
        return changed
