# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...domain.services.forecast_engine import next_average
from ...domain.services.threshold_calculator import build_fallback_curve
from ...domain.value_objects.forecast_result import BattlePlan


class BattleSessionService(object):
    """Application use case orchestrating battle panel lifecycle, forecast, and HUD updates."""

    TICK = 0.05
    DRAG_TICK = 0.0

    def __init__(self, config_store, config_sync, cache_repo, dossier_provider,
                 curve_sync, snapshot_uc, forecast_engine, threshold_calc,
                 clock, scheduler, input_provider, logger,
                 battle_presenter, panel_factory, tracker_factory,
                 drag_controller=None):
        self._config = config_store
        self._config_sync = config_sync
        self._cache = cache_repo
        self._dossier = dossier_provider
        self._curves = curve_sync
        self._snapshot_uc = snapshot_uc
        self._forecast = forecast_engine
        self._threshold_calc = threshold_calc
        self._clock = clock
        self._scheduler = scheduler
        self._input = input_provider
        self._logger = logger
        self._presenter = battle_presenter
        self._panel_factory = panel_factory
        self._tracker_factory = tracker_factory
        self._drag = drag_controller

        self._session_base = {}
        self._panel = None
        self._tracker = None
        self._active = False
        self._cb_id = None
        self._int_cd = None
        self._rating = 0.0
        self._ema = 0.0
        self._marks = 0
        self._is_spg = False
        self._last_alt = False
        self._last_sniper = False
        self._last_ctrl = False
        self._last_bmin = False
        self._shown_pct = 0.0
        self._shown_bar = 0.0
        self._glow_until = 0.0
        self._last_target = 0.0
        self._last_vis_check = 0.0
        self._last_update_t = 0.0
        self._ui_hidden = False
        self._stats_shown = False
        self._pending_forecast = None
        self._mark = None
        self._fc_key = None
        self._fc = None
        self._vis_unbind = None

    @property
    def panel(self):
        return self._panel

    def bind_visibility_events(self, binder):
        self._vis_unbind = binder(self.on_gui_visibility, self.on_full_stats)

    def start(self):
        if self._active or self._panel is not None:
            self.stop()
        ctx = self._dossier.get_player_battle_context()
        if ctx is None:
            return
        if self._config.get('onlyRandomBattles', True) and not ctx.get('is_random', True):
            return
        min_level = int(self._config.get('minVehicleLevel', 5))
        level = ctx.get('level')
        if level is not None and int(level) < min_level:
            self._logger.info('battle panel skipped: vehicle level %s < %s' % (level, min_level))
            return
        self._active = True
        self._int_cd = ctx.get('int_cd')
        self._is_spg = bool(ctx.get('is_spg', False))
        self._last_alt = False
        self._last_sniper = False
        self._last_ctrl = bool(self._input.is_ctrl_down())
        self._last_bmin = bool(self._config.get('minBattle', False))
        self._snapshot_uc.snapshot_vehicle(self._int_cd)
        self._curves.request_calc(self._int_cd)
        self._mark = self._snapshot_uc.mark_for(self._int_cd)
        self._rating = self._mark.percent if self._mark else 0.0
        self._ema = self._mark.avg if self._mark else 0.0
        self._marks = self._mark.marks if self._mark else 0
        if self._int_cd is not None and self._rating > 0.0 and self._int_cd not in self._session_base:
            self._session_base[self._int_cd] = self._rating
        self._shown_pct = self._rating
        self._shown_bar = self._rating
        self._last_target = self._rating
        self._fc_key = None
        self._fc = None

        self._tracker = self._tracker_factory(self._on_changed)
        if self._tracker is not None:
            self._tracker.start()
        self._last_vis_check = self._clock.battle_time()
        self._last_update_t = self._last_vis_check
        self._panel = self._panel_factory()
        if self._panel is not None:
            self._update()
            self._panel.update_visibility(self._is_hidden())
            self._panel.build()
            self._panel.update_visibility(self._is_hidden())
        self._tick()

    def stop(self):
        self._active = False
        if self._vis_unbind is not None:
            try:
                self._vis_unbind()
            except Exception:
                pass
            self._vis_unbind = None
        self._ui_hidden = False
        self._stats_shown = False
        if self._cb_id is not None:
            self._scheduler.cancel(self._cb_id)
            self._cb_id = None
        if self._tracker is not None:
            try:
                self._tracker.stop()
            except Exception:
                pass
            self._tracker = None
        if self._pending_forecast is not None and self._int_cd:
            self._cache.get_entry(str(self._int_cd))['pendingForecast'] = self._pending_forecast
            self._cache.save()
        self._pending_forecast = None
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        if self._drag is not None:
            self._drag.reset()

    def on_summary(self, summary):
        if self._tracker is not None:
            self._tracker.on_summary(summary)

    def on_gui_visibility(self, visible):
        if not self._active:
            return
        self._ui_hidden = not bool(visible)
        self._sync_visibility()

    def on_full_stats(self, shown):
        if not self._active:
            return
        self._stats_shown = bool(shown)
        self._sync_visibility()

    def _on_changed(self):
        pass

    def _is_hidden(self):
        hidden = bool(self._ui_hidden or self._stats_shown or self._input.is_tab_down())
        if self._config.get('hideInIntro', True):
            intro, why = self._input.is_intro_active()
            if intro:
                self._logger.once(('hideintro', why), 'panel hidden in intro: %s' % why)
                return True
        if self._config.get('hideInKillcam', True):
            kc, why = self._input.is_killcam_active()
            if kc:
                self._logger.once(('hidekillcam', why), 'panel hidden in killcam: %s' % why)
                return True
        if self._config.get('hideAfterDeath', False):
            dead, why = self._input.is_player_dead()
            if dead:
                self._logger.once(('hidedead', why), 'panel hidden after death: %s' % why)
                return True
        return hidden

    def _sync_visibility(self):
        if self._panel is not None and self._active:
            self._panel.update_visibility(self._is_hidden())

    def _tick(self):
        if not self._active:
            self._cb_id = None
            return
        dragging = False
        try:
            toggled = False
            if self._drag is not None and self._panel is not None:
                toggled = bool(self._drag.poll(self._panel, min_key='minBattle'))
                dragging = self._drag.is_dragging()
            now = self._clock.battle_time()
            ctrl_now = bool(self._input.is_ctrl_down())
            bmin_now = bool(self._config.get('minBattle', False))
            ui_state_changed = toggled or (ctrl_now != self._last_ctrl) or (bmin_now != self._last_bmin)
            if ui_state_changed:
                self._last_ctrl = ctrl_now
                self._last_bmin = bmin_now
            if ui_state_changed or (not dragging) or (now - self._last_update_t >= self.TICK):
                self._last_update_t = now
                if self._curves.pump():
                    self._fc_key = None
                if self._config_sync.poll():
                    self._fc_key = None
                alt_changed = False
                if self._config.integer('battlePreset', 0, 1) == 0:
                    alt_now = self._input.is_alt_down()
                    sniper_now = self._input.is_sniper_mode()
                    if alt_now != self._last_alt or sniper_now != self._last_sniper:
                        self._last_alt = alt_now
                        self._last_sniper = sniper_now
                        alt_changed = True
                self._update()
                if alt_changed or now - self._last_vis_check >= 0.25:
                    self._last_vis_check = now
                    self._sync_visibility()
        except Exception:
            self._logger.error('battle tick')
        self._cb_id = self._scheduler.schedule(self.DRAG_TICK if dragging else self.TICK, self._tick)

    def _resolve_battle_curve(self, mark):
        curve = self._curves.curve_for(self._int_cd)
        if curve:
            return (curve, False)
        if mark is not None and mark.avg > 0.0 and mark.percent > 0.0 and not self._curves.is_pending(self._int_cd):
            fb = build_fallback_curve(mark.percent, mark.avg)
            if fb:
                return (fb, True)
        return (None, False)

    def _plan(self, mark, dmg):
        curve, is_fallback = self._resolve_battle_curve(mark)
        if not curve:
            return None
        server_now = self._clock.server_now()
        stamp = (int(dmg), self._curves.version, int(server_now // 30), bool(is_fallback))
        if self._fc_key == stamp:
            return self._fc
        plan = None
        try:
            if not is_fallback and mark.avg > 0 and mark.percent > 0:
                self._snapshot_uc.witness_epoch(str(self._int_cd), mark.avg, mark.percent, mark.written)
            res = self._forecast.forecast(mark, dmg, curve, server_now, self._curves.day_curve)
            hold_dmg = self._forecast.hold_damage(mark, curve, server_now, self._curves.day_curve)
            server = self._forecast.server_curve(mark, curve, server_now, self._curves.day_curve)[0]
            big_at = 0.0
            if self._config.get('bigByDamage', True):
                big_at = (
                    server.damage_of(self._config.number('bigBasePercent', 1.0, 100.0)) *
                    self._config.number('bigDamageFactor', 0.5, 20.0)
                )
            plan = BattlePlan(res.after, res.delta, int(res.whole_avg), server.day, big_at, hold_dmg=hold_dmg)
        except Exception:
            self._logger.error('forecast')
        self._fc_key, self._fc = stamp, plan
        return plan

    def _update(self):
        if self._panel is None:
            return
        report = self._tracker.report() if self._tracker is not None else None
        dmg = report.combined() if report is not None else 0
        mark = self._mark
        curve = self._curves.curve_for(self._int_cd)
        has_dossier = mark is not None and self._rating > 0 and self._ema > 0
        has_first_battle = mark is not None and not has_dossier and curve is not None
        has_rating = has_dossier or has_first_battle

        target, delta = self._rating, None
        big = False
        proj_ema = int(next_average(self._ema, dmg)[0]) if has_rating else 0
        hold_dmg = int(round(self._ema)) if has_dossier else 0
        if has_rating:
            plan = self._plan(mark, dmg)
            if plan is not None:
                target = plan.after
                delta = plan.delta
                proj_ema = plan.whole_avg
                hold_dmg = plan.hold_dmg
                big = bool(plan.big_at > 0 and dmg >= plan.big_at and delta >= 0)
                self._pending_forecast = {
                    'at': self._clock.now(),
                    'before': self._rating,
                    'average': self._ema,
                    'battles': int(mark.battles),
                    'predicted': target,
                    'combined': int(dmg),
                    'curveDay': plan.curve_day,
                    'parts': report.to_parts_dict() if report is not None else {},
                }

        now = self._clock.battle_time()
        if target > self._last_target + 1e-6:
            self._glow_until = now + 0.7
        self._last_target = target

        self._shown_pct = target
        self._shown_bar += (target - self._shown_bar) * 0.15
        if abs(target - self._shown_bar) < 0.002:
            self._shown_bar = target

        thresholds = None
        if has_rating and self._config.integer('battlePreset', 0, 1) == 0:
            thresholds = self._threshold_calc.compute_thresholds(
                mark, self._shown_pct, self._ema, curve, self._clock.server_now(),
                self._curves.day_curve, self._curves.version,
            )

        session_base = self._session_base.get(self._int_cd, self._rating)
        data = self._presenter.build_payload(
            shown_pct=self._shown_pct,
            bar_pct=self._shown_bar,
            delta=delta,
            dmg=dmg,
            proj_ema=proj_ema,
            marks=self._marks,
            glowing=(now < self._glow_until),
            has_rating=has_rating,
            big=big,
            report=report,
            thresholds=thresholds,
            is_spg=self._is_spg,
            alt_down=self._last_alt,
            session_base=session_base,
            hold_dmg=hold_dmg,
        )
        data['bmin'] = bool(self._config.get('minBattle', False))
        data['ctrl'] = bool(self._input.is_ctrl_down())
        self._panel.push(data)
