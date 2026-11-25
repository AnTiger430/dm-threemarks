# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..adapters.gameface.wulf_views import GF_ERR, GF_OK
from ..application.config.defaults import CONFIG_HELP, MOD_VERSION
from ..infrastructure.wot.event_registrar import EB_OK
from .container import ModContainer


class ModApplication(object):
    """Top-level mod lifecycle facade orchestrating start() and stop()."""

    def __init__(self, container):
        self._c = container

    @classmethod
    def create_default(cls, config_dir=None):
        return cls(ModContainer(config_dir=config_dir))

    def start(self):
        try:
            self._c.config_sync.load_initial()
            self._c.cache_repo.load()
            self._c.config_repo.write_help(MOD_VERSION, CONFIG_HELP)
            self._c.logger.info('init, version %s, realm=%s, gameface ok=%s, event bus ok=%s' % (
                MOD_VERSION, getattr(self._c, 'realm_domain', '?'), GF_OK, EB_OK,
            ))
            if not GF_OK and GF_ERR:
                self._c.logger.info('gameface import failed, no panel will be shown:\n%s' % GF_ERR)
            self._c.battle_hooks.install()
            self._c.menu_adapter.register()
            self._c.registrar.subscribe()
        except Exception:
            self._c.logger.error('init')

    def stop(self):
        try:
            self._c.battle_service.stop()
            self._c.hangar_service.on_leave_lobby()
            self._c.menu_adapter.unregister()
            self._c.battle_hooks.uninstall()
            self._c.registrar.unsubscribe()
            self._c.cache_repo.save()
        except Exception:
            pass
