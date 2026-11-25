# -*- coding: utf-8 -*-
from __future__ import absolute_import

import abc


class IDossierProvider(object):
    """Port for reading WoT vehicle dossiers and active vehicle metadata."""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def read_dossier(self, int_cd):
        raise NotImplementedError

    @abc.abstractmethod
    def get_current_vehicle_info(self):
        """Return (int_cd, level) if present, else None."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_realm_domain(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_player_battle_context(self):
        """Return dict(int_cd, is_spg, arena_bonus_type) or None."""
        raise NotImplementedError
