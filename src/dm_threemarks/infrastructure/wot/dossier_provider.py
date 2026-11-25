# -*- coding: utf-8 -*-
from __future__ import absolute_import

import BigWorld
from CurrentVehicle import g_currentVehicle
from constants import ARENA_BONUS_TYPE
from helpers import dependency
from skeletons.gui.shared import IItemsCache

from ...application.ports.dossier_provider import IDossierProvider
from ...domain.entities.mark_snapshot import VehicleDossier


def _random_battle_types():
    types = set()
    for name in ('REGULAR', 'EPIC_RANDOM', 'EPIC_RANDOM_TRAINING'):
        if hasattr(ARENA_BONUS_TYPE, name):
            types.add(getattr(ARENA_BONUS_TYPE, name))
    return tuple(types) or (1,)


class WotDossierProvider(IDossierProvider):
    """Reads vehicle dossiers, realm domain, current hangar vehicle, and battle player context."""

    def __init__(self, logger=None):
        self._logger = logger
        self._items_cache = dependency.instance(IItemsCache)
        self._random_types = _random_battle_types()

    def on_sync_completed_event(self):
        return self._items_cache.onSyncCompleted

    def read_dossier(self, int_cd):
        try:
            dossier = self._items_cache.items.getVehicleDossier(int_cd)
        except Exception:
            if self._logger is not None:
                self._logger.error('getVehicleDossier')
            return None
        if dossier is None:
            return None
        percent = avg = None
        marks = battles = last_battle = 0
        try:
            from dossiers2.ui.achievements import MARK_ON_GUN_RECORD
            achievement = None
            for getter in ('getTotalStats', 'getRandomStats'):
                try:
                    achievement = getattr(dossier, getter)().getAchievement(MARK_ON_GUN_RECORD)
                except Exception:
                    achievement = None
                if achievement is not None:
                    break
            if achievement is not None:
                percent = float(achievement.getDamageRating() or 0.0)
                marks = int(achievement.getValue() or 0)
        except Exception:
            percent = None
        try:
            avg = float(dossier.getRecordValue('achievements', 'movingAvgDamage') or 0.0)
        except Exception:
            avg = None
        if percent is None or avg is None:
            try:
                ach = dossier.getDossierDescr()['achievements']
                if percent is None:
                    percent = ach['damageRating'] / 100.0
                if avg is None:
                    avg = float(ach['movingAvgDamage'])
                marks = max(marks, int(ach['marksOnGun']))
            except Exception:
                if self._logger is not None:
                    self._logger.error('dossier record')
                return None
        try:
            marks = max(marks, int(dossier.getRecordValue('achievements', 'marksOnGun') or 0))
        except Exception:
            pass
        try:
            battles = int(dossier.getRandomStats().getBattlesCount() or 0)
        except Exception:
            battles = 0
        try:
            last_battle = int(dossier.getGlobalStats().getLastBattleTime() or 0)
        except Exception:
            last_battle = 0
        return VehicleDossier(float(percent), float(avg), max(0, min(3, marks)), battles, last_battle)

    def get_current_vehicle_info(self):
        if not g_currentVehicle.isPresent():
            return None
        item = g_currentVehicle.item
        if item is None:
            return None
        return (item.intCD, int(getattr(item, 'level', 10)))

    def get_realm_domain(self):
        consts = __import__('constants')
        raw = getattr(consts, 'CURRENT_REALM', None) or getattr(consts, 'AUTH_REALM', u'EU')
        realm = unicode(raw).upper()
        if 'RU' in realm or 'LESTA' in realm or 'CIS' in realm:
            return 'ru'
        if 'NA' in realm:
            return 'com'
        if 'ASIA' in realm:
            return 'asia'
        return 'eu'

    def get_player_battle_context(self):
        try:
            player = BigWorld.player()
            arena = getattr(player, 'arena', None)
            if arena is None:
                return None
            is_random = (getattr(arena, 'bonusType', None) in self._random_types)
            vdesc = getattr(player, 'vehicleTypeDescriptor', None)
            vtype = getattr(vdesc, 'type', None) if vdesc is not None else None
            int_cd = vtype.compactDescr
            tags = getattr(vtype, 'tags', ()) or ()
            is_spg = bool('SPG' in tags)
            level = getattr(vtype, 'level', None)
            if level is None and vdesc is not None:
                level = getattr(vdesc, 'level', None)
            if level is None:
                vid = getattr(player, 'playerVehicleID', None)
                if vid is not None:
                    vinfo = (getattr(arena, 'vehicles', None) or {}).get(vid)
                    if isinstance(vinfo, dict):
                        vt = vinfo.get('vehicleType')
                        level = getattr(getattr(vt, 'type', None), 'level', None) or getattr(vt, 'level', None)
            if level is None and self._items_cache is not None:
                try:
                    item = self._items_cache.items.getItemByCD(int_cd)
                    if item is not None:
                        level = getattr(item, 'level', None)
                except Exception:
                    pass
            return {
                'int_cd': int_cd,
                'level': (int(level) if level is not None else None),
                'is_spg': is_spg,
                'is_random': is_random,
            }
        except Exception:
            if self._logger is not None:
                self._logger.error('battle context')
            return None
