# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .wulf_views import COVERING_LAYERS, GF_OK, WindowStatus, IGuiLoader, dependency


class BattleVisibilityGuard(object):
    """Detects battle scoreboard/modal/Scaleform overlays covering the HUD panel."""

    def is_covered(self, own_window):
        if not GF_OK or dependency is None or IGuiLoader is None:
            return False
        try:
            windows_mgr = dependency.instance(IGuiLoader).windowsManager
            windows = []
            seen_ids = set()

            def add_window(window):
                if window is None:
                    return
                try:
                    uid = window.uniqueID
                except Exception:
                    return
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    windows.append(window)

            try:
                for w in windows_mgr.findWindows(lambda item: True) or ():
                    add_window(w)
            except Exception:
                pass
            try:
                for view in windows_mgr.findViews(lambda item: True) or ():
                    try:
                        add_window(view.getParentWindow())
                    except Exception:
                        pass
            except Exception:
                pass

            for w in windows:
                if w is own_window:
                    continue
                try:
                    if w.layer in COVERING_LAYERS and w.windowStatus == WindowStatus.LOADED and not bool(w.isHidden()):
                        return True
                except Exception:
                    pass

            try:
                from skeletons.gui.app_loader import IAppLoader
                app = dependency.instance(IAppLoader).getDefBattleApp()
                cm = getattr(app, 'containerManager', None) if app is not None else None
                if cm is not None:
                    for layer in COVERING_LAYERS:
                        container = cm.getContainer(layer)
                        if container is not None and container.getViewCount():
                            return True
                    if cm.isModalViewsIsExists():
                        return True
            except Exception:
                pass
        except Exception:
            pass
        return False
