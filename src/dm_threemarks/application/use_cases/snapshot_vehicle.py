# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...domain.entities.mark_snapshot import MarkSnapshot


class SnapshotVehicleUseCase(object):
    """Reads live vehicle dossier, logs pending forecast accuracy, and witnesses server epoch."""

    def __init__(self, dossier_provider, cache_repo, curve_sync, forecast_engine, epoch, clock, logger):
        self._dossier = dossier_provider
        self._cache = cache_repo
        self._curves = curve_sync
        self._forecast = forecast_engine
        self._epoch = epoch
        self._clock = clock
        self._logger = logger

    def witness_epoch(self, key, avg, percent, written):
        self._epoch.witness(
            key,
            avg,
            percent,
            written,
            self._curves.day_curve,
            self._curves.live_info(key),
            self._curves.version,
            log_fn=self._logger.info,
        )

    def mark_for(self, int_cd):
        key = str(int_cd)
        entry = self._cache.peek_entry(key)
        if not isinstance(entry, dict):
            entry = {}
        seen = entry.get('seen') if isinstance(entry.get('seen'), dict) else None
        dossier = self._dossier.read_dossier(int_cd)
        if dossier is not None and dossier.avg > 0.0:
            return MarkSnapshot(
                int_cd,
                dossier.percent,
                dossier.avg,
                dossier.battles,
                dossier.marks,
                self._forecast.written_at(seen, dossier.percent, dossier.avg, dossier.battles, dossier.last_battle),
            )
        last = entry.get('last')
        try:
            if last and float(last[0]) > 0.0:
                return MarkSnapshot(
                    int_cd,
                    float(last[1]),
                    float(last[0]),
                    int(last[3]) if len(last) > 3 else 0,
                    int(last[2]) if len(last) > 2 else 0,
                    int(seen.get('w', 0) or 0) if seen else 0,
                )
        except (TypeError, ValueError, IndexError):
            pass
        if dossier is not None:
            return MarkSnapshot(int_cd, dossier.percent, dossier.avg, dossier.battles, dossier.marks, 0)
        return None

    def reconcile_pending(self):
        all_entries = self._cache.get_all()
        if not isinstance(all_entries, dict):
            return
        for key, entry in list(all_entries.items()):
            if not isinstance(entry, dict) or not isinstance(entry.get('pendingForecast'), dict):
                continue
            try:
                int_cd = int(key)
            except (TypeError, ValueError):
                continue
            self.snapshot_vehicle(int_cd)

    def snapshot_vehicle(self, int_cd):
        key = str(int_cd)
        dossier = self._dossier.read_dossier(int_cd)
        if dossier is None:
            return
        entry_peek = self._cache.peek_entry(key)
        pending = entry_peek.get('pendingForecast') if isinstance(entry_peek, dict) else None
        if dossier.avg <= 0.0 and dossier.percent <= 0.0:
            if isinstance(pending, dict):
                try:
                    age = self._clock.now() - float(pending.get('at', 0))
                except Exception:
                    age = 999999.0
                if age < -300 or age > 21600:
                    self._cache.get_entry(key).pop('pendingForecast', None)
                    self._cache.save()
            return
        entry = self._cache.get_entry(key)
        last = entry.get('last')
        seen = entry.get('seen') if isinstance(entry.get('seen'), dict) else None
        changed = (
            not last or
            abs(dossier.avg - float(last[0])) > 0.5 or
            abs(dossier.percent - float(last[1])) > 0.005 or
            (len(last) > 3 and int(dossier.battles) != int(last[3]))
        )
        dirty = False
        pending = entry.get('pendingForecast')
        if isinstance(pending, dict):
            try:
                age = self._clock.now() - float(pending.get('at', 0))
                pend_battles = pending.get('battles')
                battle_done = (pend_battles is not None and int(dossier.battles) > int(pend_battles))
                moved = (
                    battle_done or
                    abs(dossier.avg - float(pending.get('average', dossier.avg))) >= 0.5 or
                    abs(dossier.percent - float(pending.get('before', dossier.percent))) >= 0.005
                )
                if age < -300 or age > 21600:
                    entry.pop('pendingForecast', None)
                    dirty = True
                elif moved:
                    predicted = float(pending.get('predicted', dossier.percent))
                    self._logger.info(
                        'FORECAST_RESULT tank=%s predicted=%.2f actual=%.2f error=%+.2f pp '
                        'average=%d->%d combined=%d curveDay=%s parts=%s' % (
                            key, predicted, dossier.percent, predicted - dossier.percent,
                            int(float(pending.get('average', 0))), int(round(dossier.avg)),
                            int(pending.get('combined', 0)), pending.get('curveDay'),
                            pending.get('parts'),
                        )
                    )
                    entry.pop('pendingForecast', None)
                    dirty = True
            except Exception:
                self._logger.error('forecast result')
                entry.pop('pendingForecast', None)
                dirty = True
        written = self._forecast.written_at(
            seen, dossier.percent, dossier.avg, dossier.battles, dossier.last_battle
        )
        record = {'p': dossier.percent, 'a': dossier.avg, 'b': int(dossier.battles), 'w': int(written)}
        entry['last'] = [dossier.avg, dossier.percent, dossier.marks, dossier.battles]
        entry['seen'] = record
        if changed or seen != record or dirty:
            self._cache.save()
        self.witness_epoch(key, dossier.avg, dossier.percent, written)
