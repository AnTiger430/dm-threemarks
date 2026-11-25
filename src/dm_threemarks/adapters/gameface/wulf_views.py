# -*- coding: utf-8 -*-
from __future__ import absolute_import

import traceback

try:
    from frameworks.wulf import (
        ViewFlags,
        ViewModel,
        ViewSettings,
        WindowFlags,
        WindowLayer,
        WindowStatus,
    )
    from gui.impl.gui_decorators import args2params
    from gui.impl.pub import ViewImpl, WindowImpl
    from skeletons.gui.impl import IGuiLoader
    from gui.impl.gen import R
    from helpers import dependency
    GF_ERR = None
    try:
        GF_LAYOUT = R.mods.dm.threemarks.views.ThreeMarks
    except Exception:
        GF_LAYOUT = None
        try:
            from openwg_gameface import ModDynAccessor
            GF_LAYOUT = ModDynAccessor('mods/dm/ThreeMarks/layoutID')
        except Exception:
            GF_LAYOUT = None
            GF_ERR = traceback.format_exc()
    GF_OK = GF_LAYOUT is not None
    COVERING_LAYERS = (WindowLayer.FULLSCREEN_WINDOW, WindowLayer.TOP_WINDOW, WindowLayer.OVERLAY)
    GONE_WINDOW_STATUSES = (WindowStatus.DESTROYING, WindowStatus.DESTROYED)
except Exception:
    GF_LAYOUT = None
    GF_OK = False
    GF_ERR = traceback.format_exc()
    COVERING_LAYERS = ()
    GONE_WINDOW_STATUSES = ()
    ViewFlags = ViewModel = ViewSettings = WindowFlags = WindowLayer = WindowStatus = None
    IGuiLoader = dependency = None
    ViewImpl = object
    WindowImpl = object

    def args2params(*_args):
        return lambda fn: fn


def window_alive(window):
    try:
        return (
            window is not None and
            window.proxy is not None and
            window.windowStatus not in GONE_WINDOW_STATUSES
        )
    except Exception:
        return False


def resolve_layout_id():
    if GF_LAYOUT is None:
        return None
    try:
        res_id = int(GF_LAYOUT())
        return res_id if res_id > 0 else None
    except Exception:
        return None


def get_main_window():
    if not GF_OK or dependency is None or IGuiLoader is None:
        return None
    return dependency.instance(IGuiLoader).windowsManager.getMainWindow()


if GF_OK:
    class TmModel(ViewModel):

        def __init__(self, payload):
            self.__payload = payload
            super(TmModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(TmModel, self)._initialize()
            self._addStringProperty('payload', self.__payload)
            self.onReady = self._addCommand('onReady')

        def setPayload(self, value):
            self._setString(0, value)


    class TmView(ViewImpl):

        def __init__(self, owner):
            self.__owner = owner
            model = TmModel(owner.payload)
            owner.model = model
            layout_id = resolve_layout_id()
            if layout_id is None:
                raise RuntimeError('ThreeMarks Gameface layoutID not ready')
            settings = ViewSettings(layoutID=layout_id, flags=ViewFlags.VIEW, model=model)
            super(TmView, self).__init__(settings)

        def _getEvents(self):
            model = self.getViewModel()
            return ((model.onReady, self.__onReady),)

        @args2params(str)
        def __onReady(self, message):
            self.__owner.on_js_ready()

        def _finalize(self):
            self.__owner.model = None
            super(TmView, self)._finalize()


    class TmWindow(WindowImpl):

        def __init__(self, content, parent, owner=None):
            self.__owner = owner
            super(TmWindow, self).__init__(
                WindowFlags.WINDOW, content=content,
                layer=WindowLayer.WINDOW, name='ThreeMarksPanel', parent=parent,
            )

        def _onReady(self):
            if self.__owner is not None:
                self.__owner.on_window_ready()
            else:
                self.show(False)
else:
    TmModel = None
    TmView = None
    TmWindow = None
