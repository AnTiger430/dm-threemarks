# -*- coding: utf-8 -*-
from __future__ import absolute_import

import BigWorld
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider

from ...domain.value_objects.damage_report import DamageReport


def _extract_split_assist(event):
    """Extract separate (radio, track) assist values from a summary event without summing."""
    for r_name, t_name in (
        ('getTotalRadioAssistDamage', 'getTotalTrackAssistDamage'),
        ('getRadioAssistDamage', 'getTrackAssistDamage'),
    ):
        r_fn = getattr(event, r_name, None)
        t_fn = getattr(event, t_name, None)
        if callable(r_fn) and callable(t_fn):
            return int(r_fn()), int(t_fn())
    spotting = getattr(event, '_BattleSummaryFeedbackEvent__radioAssistDamage', None)
    tracking = getattr(event, '_BattleSummaryFeedbackEvent__trackAssistDamage', None)
    if spotting is not None and tracking is not None:
        return int(spotting), int(tracking)
    ev_dict = getattr(event, '__dict__', None)
    if isinstance(ev_dict, dict):
        r_val = t_val = None
        for k, v in ev_dict.items():
            ks = str(k)
            if ks.endswith('radioAssistDamage') and v is not None:
                r_val = v
            elif ks.endswith('trackAssistDamage') and v is not None:
                t_val = v
        if r_val is not None and t_val is not None:
            return int(r_val), int(t_val)
    return (None, None)


class WotDamageTracker(object):
    """Collects live battle damage, radio assist, track assist, stun, and ally damage."""

    ASSIST_KEYS = ('radioAssist', 'trackAssist', 'stunAssist')

    def __init__(self, on_changed):
        self._on_changed = on_changed
        self._session_provider = dependency.instance(IBattleSessionProvider)
        self.sDamage = 0
        self.sAssists = dict((k, 0) for k in self.ASSIST_KEYS)
        self._split_assist_known = False
        self._summary_seen = False
        self._allies = 0
        self._player_vehicle_id = None
        self._arena = None
        self._arena_dp = None
        self._health_subscribed = False
        self.cDamage = 0
        self.cAssist = 0
        self.cStun = 0
        self._subscribed = False
        self._feedback = None
        self._feedback_active = False
        self._feedback_kinds = {}
        self._assist_kinds = {}

    def start(self):
        try:
            from BattleFeedbackCommon import BATTLE_EVENT_TYPE
            from gui.battle_control.battle_constants import FEEDBACK_EVENT_ID
            feedback = getattr(self._session_provider.shared, 'feedback', None)
            if feedback is not None:
                self._feedback_kinds = {
                    FEEDBACK_EVENT_ID.PLAYER_DAMAGED_HP_ENEMY: 'damage',
                    FEEDBACK_EVENT_ID.PLAYER_ASSIST_TO_KILL_ENEMY: None,
                    FEEDBACK_EVENT_ID.PLAYER_ASSIST_TO_STUN_ENEMY: 'stun',
                }
                self._assist_kinds = {
                    BATTLE_EVENT_TYPE.RADIO_ASSIST: 'radioAssist',
                    BATTLE_EVENT_TYPE.TRACK_ASSIST: 'trackAssist',
                }
                self._feedback = feedback
                feedback.onPlayerFeedbackReceived += self._on_feedback
                feedback.onPlayerSummaryFeedbackReceived += self._on_feedback_summary
                self._feedback_active = True
                cached = feedback.getCachedEvent(FEEDBACK_EVENT_ID.DAMAGE_LOG_SUMMARY)
                if cached is not None:
                    self._on_feedback_summary(cached)
        except Exception:
            self._feedback = None
            self._feedback_active = False
        try:
            ctrl = self._session_provider.shared.personalEfficiencyCtrl
            if ctrl is not None:
                ctrl.onTotalEfficiencyUpdated += self._on_efficiency_updated
                self._subscribed = True
        except Exception:
            pass
        try:
            player = BigWorld.player()
            self._player_vehicle_id = getattr(player, 'playerVehicleID', None)
            self._arena = getattr(player, 'arena', None)
            self._arena_dp = self._session_provider.getArenaDP()
            if self._arena is not None:
                self._arena.onVehicleHealthChanged += self._on_ally_damage
                self._health_subscribed = True
        except Exception:
            pass
        self._refresh_totals()

    def stop(self):
        if self._feedback is not None:
            try:
                self._feedback.onPlayerFeedbackReceived -= self._on_feedback
                self._feedback.onPlayerSummaryFeedbackReceived -= self._on_feedback_summary
            except Exception:
                pass
        self._feedback = None
        self._feedback_active = False
        try:
            ctrl = self._session_provider.shared.personalEfficiencyCtrl
            if ctrl is not None and self._subscribed:
                ctrl.onTotalEfficiencyUpdated -= self._on_efficiency_updated
        except Exception:
            pass
        self._subscribed = False
        try:
            if self._arena is not None and self._health_subscribed:
                self._arena.onVehicleHealthChanged -= self._on_ally_damage
        except Exception:
            pass
        self._health_subscribed = False
        self._arena = None

    def _on_ally_damage(self, vehicle_id, attacker_id, damage, *args):
        try:
            if not damage or damage <= 0 or attacker_id != self._player_vehicle_id:
                return
            if vehicle_id == self._player_vehicle_id or self._arena_dp is None:
                return
            if not self._arena_dp.isAlly(vehicle_id):
                return
            self._allies += int(damage)
            self._on_changed()
        except Exception:
            pass

    def on_summary(self, summary):
        if not isinstance(summary, dict):
            return
        try:
            self.sDamage = max(self.sDamage, int(summary.get('damage') or 0))
            if 'radioAssist' in summary or 'trackAssist' in summary:
                r_val = max(0, int(summary.get('radioAssist') or 0))
                t_val = max(0, int(summary.get('trackAssist') or 0))
                if not self._split_assist_known:
                    self.sAssists['radioAssist'] = r_val
                    self.sAssists['trackAssist'] = t_val
                else:
                    self.sAssists['radioAssist'] = max(self.sAssists['radioAssist'], r_val)
                    self.sAssists['trackAssist'] = max(self.sAssists['trackAssist'], t_val)
                self._split_assist_known = True
            self.sAssists['stunAssist'] = max(self.sAssists['stunAssist'], max(0, int(summary.get('stunAssist') or 0)))
            self._summary_seen = True
            self._on_changed()
        except Exception:
            pass

    def _on_feedback(self, events):
        try:
            changed = False
            for event in events:
                kind = event.getType()
                if kind not in self._feedback_kinds:
                    continue
                name = self._feedback_kinds[kind]
                if name is None:
                    name = self._assist_kinds.get(event.getBattleEventType())
                extra = event.getExtra()
                amount = int(extra.getDamage()) if extra is not None else 0
                if name is not None and amount > 0:
                    if name == 'damage':
                        self.sDamage += amount
                    elif name == 'stun':
                        self.sAssists['stunAssist'] += amount
                    else:
                        self.sAssists[name] += amount
                        self._split_assist_known = True
                    changed = True
            if changed:
                self._on_changed()
        except Exception:
            pass

    def _on_feedback_summary(self, event):
        try:
            self.sDamage = max(0, int(event.getTotalDamage()))
            spotting, tracking = _extract_split_assist(event)
            if spotting is not None and tracking is not None:
                self.sAssists['radioAssist'] = max(0, int(spotting))
                self.sAssists['trackAssist'] = max(0, int(tracking))
                self._split_assist_known = True
            else:
                total_assist = max(0, int(event.getTotalAssistDamage()))
                if not self._split_assist_known and (self.sAssists['radioAssist'] + self.sAssists['trackAssist']) == 0 and total_assist > 0:
                    self.sAssists['radioAssist'] = total_assist
                    self.sAssists['trackAssist'] = 0
            self.sAssists['stunAssist'] = max(0, int(event.getTotalStunDamage()))
            self._summary_seen = True
            self._on_changed()
        except Exception:
            pass

    def _on_efficiency_updated(self, *args, **kwargs):
        self._refresh_totals()
        self._on_changed()

    def _refresh_totals(self):
        try:
            from gui.battle_control.battle_constants import PERSONAL_EFFICIENCY_TYPE as PET
            ctrl = self._session_provider.shared.personalEfficiencyCtrl
            if ctrl is None:
                return
            self.cDamage = max(0, int(ctrl.getTotalEfficiency(PET.DAMAGE)))
            self.cAssist = max(0, int(ctrl.getTotalEfficiency(PET.ASSIST_DAMAGE)))
            if hasattr(PET, 'STUN'):
                self.cStun = max(0, int(ctrl.getTotalEfficiency(PET.STUN)))
        except Exception:
            pass

    def report(self):
        src = 'feedback' if (self._feedback_active or self._summary_seen) else 'efficiency'
        return DamageReport(
            damage=self.sDamage,
            radio=self.sAssists['radioAssist'],
            track=self.sAssists['trackAssist'],
            stun=self.sAssists['stunAssist'],
            allies=self._allies,
            eff_damage=self.cDamage,
            eff_assist=self.cAssist,
            eff_stun=self.cStun,
            source=src,
        )
