# -*- coding: utf-8 -*-
from __future__ import absolute_import

from gui.battle_control.controllers import feedback_adaptor


class WotBattleHooks(object):
    """Installs and cleanly removes the BattleFeedbackAdaptor summary hook."""

    def __init__(self, on_summary):
        self._on_summary = on_summary
        try:
            self._orig_summary = feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary
        except Exception:
            self._orig_summary = None
        self._patched_fn = None

    def install(self):
        if self._orig_summary is None:
            return
        orig = self._orig_summary
        callback = self._on_summary

        def patched(adaptor_self, summary):
            orig(adaptor_self, summary)
            try:
                callback(summary)
            except Exception:
                pass

        self._patched_fn = patched
        try:
            feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary = patched
        except Exception:
            pass

    def uninstall(self):
        if self._orig_summary is None or self._patched_fn is None:
            return
        try:
            cur = feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary
            if getattr(cur, '__func__', cur) is self._patched_fn:
                feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary = self._orig_summary
        except Exception:
            pass
        self._patched_fn = None
