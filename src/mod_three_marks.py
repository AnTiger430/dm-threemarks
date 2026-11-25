# -*- coding: utf-8 -*-
"""
Три отметки на стволе - точка входа для клиента World of Tanks (`dm.threemarks`).
Тонкий entrypoint: делегирует запуск и остановку в Composition Root (`ModApplication`).
"""
from __future__ import absolute_import

try:
    from gui.mods.dm_threemarks.bootstrap.application import ModApplication
except ImportError:
    from dm_threemarks.bootstrap.application import ModApplication

_app = None


def init():
    global _app
    _app = ModApplication.create_default()
    _app.start()


def fini():
    global _app
    if _app is not None:
        _app.stop()
        _app = None
