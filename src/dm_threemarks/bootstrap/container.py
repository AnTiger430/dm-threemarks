# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from ..adapters.gameface.panel_adapter import GamefacePanelAdapter
from ..adapters.gameface.visibility_guard import BattleVisibilityGuard
from ..adapters.menu.aslain_adapter import AslainMenuAdapter
from ..adapters.menu.preview_renderer import MenuPreviewRenderer
from ..adapters.menu.schema import MenuValueConverter
from ..adapters.menu.template_builder import MenuTemplateBuilder
from ..adapters.presenters.battle_presenter import BattlePayloadPresenter
from ..adapters.presenters.hangar_presenter import HangarPayloadPresenter
from ..adapters.presenters.ui_config_serializer import UiConfigSerializer
from ..adapters.settings.drag_controller import DragController
from ..adapters.settings.in_game_settings import InGameSettingsController
from ..adapters.v3.metrics import V3MetricsCalculator
from ..adapters.v3.svg_renderer import V3SvgRenderer
from ..application.config.defaults import HWINDOW_H, HWINDOW_W, MOD_VERSION, WINDOW_H, WINDOW_W
from ..application.config.validator import ConfigStore
from ..application.use_cases.battle_session import BattleSessionService
from ..application.use_cases.config_sync import ConfigSyncService
from ..application.use_cases.curve_sync_service import CurveSyncService
from ..application.use_cases.hangar_session import HangarSessionService
from ..application.use_cases.snapshot_vehicle import SnapshotVehicleUseCase
from ..domain.constants import LESTA_SERVER_HOUR, LESTA_SERVER_LATE
from ..domain.entities.server_epoch import ServerEpoch
from ..domain.services.forecast_engine import ForecastEngine
from ..domain.services.threshold_calculator import ThresholdCalculator
from ..infrastructure.logging_adapter.file_logger import ModFileLogger
from ..infrastructure.network.http_client import HttpJsonClient
from ..infrastructure.network.mastery_gateway import WgPoliroidMasteryGateway
from ..infrastructure.network.worker_queue import BackgroundWorkerQueue
from ..infrastructure.storage.cache_repository import FileCacheRepository
from ..infrastructure.storage.config_repository import FileConfigRepository
from ..infrastructure.storage.json_store import JsonFileStore
from ..infrastructure.wot.battle_hooks import WotBattleHooks
from ..infrastructure.wot.clock import WotClock
from ..infrastructure.wot.damage_tracker import WotDamageTracker
from ..infrastructure.wot.dossier_provider import WotDossierProvider
from ..infrastructure.wot.event_registrar import WotEventRegistrar
from ..infrastructure.wot.hangar_monitor import WotHangarEnvironment, WotLobbyRouteTap
from ..infrastructure.wot.input_provider import WotInputProvider
from ..infrastructure.wot.scheduler import WotScheduler


class ModContainer(object):
    """Composition root constructing and wiring the entire object graph manually."""

    def __init__(self, config_dir=None):
        cfg_dir = config_dir or os.path.join('mods', 'configs', 'three_marks')
        self.logger = ModFileLogger(cfg_dir)
        json_store = JsonFileStore(cfg_dir, logger=self.logger)
        self.config_repo = FileConfigRepository(cfg_dir, json_store, logger=self.logger)
        self.cache_repo = FileCacheRepository(cfg_dir, json_store)
        self.config_store = ConfigStore(logger=self.logger)

        self.clock = WotClock()
        self.scheduler = WotScheduler()
        self.dossier_provider = WotDossierProvider(logger=self.logger)
        self.input_provider = WotInputProvider(logger=self.logger)
        self.hangar_env = WotHangarEnvironment()

        http_client = HttpJsonClient('ThreeMarks/%s' % MOD_VERSION, timeout=10)
        worker_queue = BackgroundWorkerQueue()
        self.gateway = WgPoliroidMasteryGateway(http_client, worker_queue)

        self.realm_domain = self.dossier_provider.get_realm_domain()
        if self.realm_domain == 'ru':
            self.epoch = ServerEpoch(server_hour=LESTA_SERVER_HOUR, server_late=LESTA_SERVER_LATE)
        else:
            self.epoch = ServerEpoch()
        self.forecast_engine = ForecastEngine(self.epoch)
        self.threshold_calc = ThresholdCalculator(self.forecast_engine)
        self.curve_sync = CurveSyncService(
            self.cache_repo, self.gateway, self.dossier_provider,
            self.config_store, self.clock, self.logger,
        )
        self.snapshot_uc = SnapshotVehicleUseCase(
            self.dossier_provider, self.cache_repo, self.curve_sync,
            self.forecast_engine, self.epoch, self.clock, self.logger,
        )

        self.ui_serializer = UiConfigSerializer(self.config_store)
        self.metrics_calc = V3MetricsCalculator(self.config_store)
        self.svg_renderer = V3SvgRenderer(self.metrics_calc, self.config_store)
        self.battle_presenter = BattlePayloadPresenter(self.config_store)
        self.hangar_presenter = HangarPayloadPresenter()
        self.visibility_guard = BattleVisibilityGuard()

        self.preview_renderer = MenuPreviewRenderer(self.config_store, self.svg_renderer)
        converter = MenuValueConverter(self.config_store)
        tpl_builder = MenuTemplateBuilder(converter, self.preview_renderer, is_lesta=(self.realm_domain == 'ru'))

        # ConfigSyncService receives menu adapter after menu construction to break circular init.
        self.config_sync = ConfigSyncService(self.config_repo, self.config_store, self.clock, self.logger)
        self.menu_adapter = AslainMenuAdapter(
            self.config_store, self.config_sync, self.preview_renderer, tpl_builder, self.logger,
            clock=self.clock, scheduler=self.scheduler,
        )
        self.config_sync._menu = self.menu_adapter

        self.drag_controller = DragController(self.input_provider, self.config_store, self.config_sync)

        def create_battle_panel():
            return GamefacePanelAdapter(
                'b', 'x', 'y', self.config_store, self.ui_serializer,
                self.metrics_calc, self.input_provider, self.scheduler,
                self.logger, visibility_guard=self.visibility_guard,
                w_px=WINDOW_W, h_px=WINDOW_H,
            )

        def create_hangar_panel():
            settings_ctrl = None
            if not self.menu_adapter.is_registered():
                settings_ctrl = InGameSettingsController(
                    self.config_store, self.config_sync, self.input_provider, self.clock,
                )
            return GamefacePanelAdapter(
                'h', 'hx', 'hy', self.config_store, self.ui_serializer,
                self.metrics_calc, self.input_provider, self.scheduler,
                self.logger, settings_controller=settings_ctrl,
                w_px=HWINDOW_W, h_px=HWINDOW_H,
            )

        self.battle_service = BattleSessionService(
            self.config_store, self.config_sync, self.cache_repo,
            self.dossier_provider, self.curve_sync, self.snapshot_uc,
            self.forecast_engine, self.threshold_calc, self.clock,
            self.scheduler, self.input_provider, self.logger,
            self.battle_presenter, create_battle_panel,
            WotDamageTracker, drag_controller=self.drag_controller,
        )
        self.hangar_service = HangarSessionService(
            self.config_store, self.config_sync, self.dossier_provider,
            self.curve_sync, self.snapshot_uc, self.forecast_engine,
            self.threshold_calc, self.clock, self.scheduler,
            self.input_provider, self.hangar_env, self.menu_adapter,
            self.logger, self.hangar_presenter, create_hangar_panel,
            drag_controller=self.drag_controller,
        )

        self.menu_adapter.bind_runtime(
            on_refresh=self.hangar_service.refresh,
            get_battle_panel=lambda: self.battle_service.panel,
            get_hangar_panel=lambda: self.hangar_service.panel,
        )
        self.battle_hooks = WotBattleHooks(self.battle_service.on_summary)
        self.route_tap = WotLobbyRouteTap(self.hangar_service.set_blocked, self.logger)
        self.registrar = WotEventRegistrar(
            self.dossier_provider, self.route_tap,
            on_avatar_ready=self._on_avatar_ready,
            on_avatar_non_player=self._on_avatar_non_player,
            on_account_show_gui=self._on_account_show_gui,
            on_avatar_become_player=self._on_avatar_become_player,
            on_vehicle_changed=self.hangar_service.on_vehicle_changed,
            on_sync_completed=self.hangar_service.on_vehicle_changed,
            on_load_view=self._on_load_view,
        )

    def _on_avatar_ready(self, *args, **kwargs):
        self.battle_service.bind_visibility_events(WotEventRegistrar.bind_battle_gui_visibility)
        self.battle_service.start()

    def _on_avatar_non_player(self, *args, **kwargs):
        self.battle_service.stop()

    def _on_account_show_gui(self, *args, **kwargs):
        self.hangar_service.on_lobby()

    def _on_avatar_become_player(self, *args, **kwargs):
        self.hangar_service.on_leave_lobby()

    def _on_load_view(self, event):
        alias = unicode(getattr(event, 'alias', '') or '').lower()
        self.hangar_service.on_view_loaded(alias)
