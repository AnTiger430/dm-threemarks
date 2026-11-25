# Architecture of `dm.threemarks` (`10.12.7`)

## 1. Architectural Overview & Dependency Rule

`dm.threemarks` follows **Clean Architecture** combined with **Hexagonal Architecture (Ports & Adapters)** and tactical **DDD** building blocks (`Entities`, `Value Objects`, `Domain Services`):

```text
+-------------------------------------------------------------------+
|                           bootstrap/                              |
|  Composition Root (ModContainer, ModApplication)                  |
|  Thin WoT Entrypoint: src/mod_three_marks.py (init / fini)        |
+------------------+------------------------------+-----------------+
                   | wires via Constructor Injection |
                   v                              v
+----------------------------------+   +----------------------------+
|         infrastructure/          |   |         adapters/          |
| Concrete WoT / OS / HTTP / Log:  |   | Presenters, V3 SVG/Metrics |
| storage/, network/, wot/,        |   | Gameface, Aslain Menu,     |
| logging_adapter/                 |   | InGameSettings, Drag       |
+------------------+---------------+   +-------------+--------------+
                   | implements                      | translates/calls
                   v                                 v
+-------------------------------------------------------------------+
|                           application/                            |
| Ports (abc.ABCMeta), ConfigSchema/ConfigStore, DTOs & Use Cases:  |
| CurveSyncService, SnapshotVehicleUseCase, ConfigSyncService,      |
| BattleSessionService, HangarSessionService                        |
+---------------------------------+---------------------------------+
                                  | depends only on
                                  v
+-------------------------------------------------------------------+
|                             domain/                               |
| Zero external imports (stdlib only: math, datetime).              |
| Exact MoE math (10.11.8/10.12.7 invariant):                       |
| Curve, ServerEpoch, MarkSnapshot, ForecastEngine,                 |
| ThresholdCalculator, AssistResolver, Value Objects                |
+-------------------------------------------------------------------+
```

**Strict Dependency Rule**: Dependencies point **strictly inward**:
1. `domain` imports **nothing** from `application`, `adapters`, `infrastructure`, `bootstrap`, WoT modules (`BigWorld`, `GUI`, `Keys`, `gui`, `helpers`, `skeletons`, `frameworks`), `os`, `threading`, or `urllib2`.
2. `application` imports **only** `domain` and Python 2.7 stdlib (`abc`, `math`, `time`).
3. `adapters` imports `application` and `domain` (plus guarded `frameworks.wulf` / `gui.impl` / `gui.Scaleform` only inside `adapters/gameface/` and `adapters/menu/` where directly interfacing WULF/ModsSettingsAPI).
4. `infrastructure` implements `application.ports` using WoT APIs, filesystem atomic writes, `urllib2`, `threading`, and `logging`.
5. `bootstrap` assembles all concrete instances manually in `ModContainer` and manages the `init()` / `fini()` lifecycle in `ModApplication`. No internal layer imports `bootstrap`.

---

## 2. Module Responsibilities

### 2.1 Backend Python (`src/dm_threemarks/` — Python 2.7 strict)

| Layer | Package / Module | Responsibility |
| :--- | :--- | :--- |
| **Entrypoint** | `src/mod_three_marks.py` | Thin WoT mod entrypoint exposing `init()` and `fini()` backed by `ModApplication`. |
| **Domain** | `domain/constants.py` | MoE mathematical & epoch constants (`_EMA_K`, `_KNOTS`, `_ANCHORS`, `_LEVELS`, server hold windows). |
| | `domain/value_objects/color.py` | `ColorRgb` and pure RGB/HEX conversions (`rgb_of_hex`, `hex_of_rgb`, `mix_rgb`, `rgb_css`, `clamp01`). |
| | `domain/value_objects/damage_report.py` | Immutable `DamageReport` with `combined()` calculation and `parts()` dictionary projection. |
| | `domain/value_objects/forecast_result.py` | `ForecastResult` and `BattlePlan` value objects. |
| | `domain/value_objects/thresholds.py` | `Thresholds` (`t65`, `t85`, `t95`, `t100`, `next_for(pct)`). |
| | `domain/value_objects/panel_geometry.py` | `PanelGeometry` (`win_w`, `win_h`, `anchor_offset()`). |
| | `domain/entities/curve.py` | `Curve` (piecewise linear distribution, integer `cell()`, `explains()`, `whole_damage()`, `thresholds()`), `served_on_knots`, UTC ordinal helpers. |
| | `domain/entities/server_epoch.py` | `ServerEpoch` (`by_clock`, `holds`, `day`, `witness`) tracking server curve switchovers without globals. |
| | `domain/entities/mark_snapshot.py` | `MarkSnapshot` and `VehicleDossier` snapshots. |
| | `domain/services/forecast_engine.py` | `floor_pct`, `next_average`, `ForecastEngine` (`server_curve`, `current_percent`, `forecast`, `written_at`). |
| | `domain/services/threshold_calculator.py` | `calc_percent`, `calc_statistics`, `ThresholdCalculator` (`compute_v3_thresholds`). |
| | `domain/services/assist_resolver.py` | `AssistResolver` resolving combined damage & active assist channels. |
| **Application** | `application/ports/*.py` | Abstract `abc.ABCMeta` ports (`IConfigRepository`, `ICacheRepository`, `IMasteryGateway`, `IDossierProvider`, `IPanelView`, `ISettingsMenu`, `IClock`, `ILogger`, `IInputProvider`, `IScheduler`, `IHangarEnvironment`). |
| | `application/config/defaults.py` | `MOD_VERSION`, `V3_DEFAULTS`, `VH_DEFAULTS`, `DEFAULT_CONFIG`, window sizes, `CONFIG_HELP_TEXT`. |
| | `application/config/validator.py` | `ConfigStore` encapsulating live settings, type/range clamping, hex validation, and `vh -> v3` projection. |
| | `application/use_cases/curve_sync_service.py` | `CurveSyncService` managing cached/live/history curves and pumping background results on the main thread. |
| | `application/use_cases/snapshot_vehicle.py` | `SnapshotVehicleUseCase` reconciling dossier state, forecast error logging, and server epoch witnessing. |
| | `application/use_cases/config_sync.py` | `ConfigSyncService` polling external `config.json` edits every 2s while preserving panel coordinates. |
| | `application/use_cases/battle_session.py` | `BattleSessionService` orchestrating live battle ticks, forecast caching, EMA smoothing, visibility rules, and presenter updates. |
| | `application/use_cases/hangar_session.py` | `HangarSessionService` orchestrating lobby monitoring, view hiding, vehicle dossier refresh, drag, and settings polling. |
| **Adapters** | `adapters/presenters/formatters.py` | Number & SVG string formatters (`fmt_int`, `v3_fmt_num`, `svg_escape`, `svg_advance`). |
| | `adapters/presenters/ui_config_serializer.py` | `UiConfigSerializer` projecting `ConfigStore` into `ui`, `v3`, and `vh` Gameface JSON payloads. |
| | `adapters/presenters/battle_presenter.py` | `BattlePayloadPresenter` creating battle HUD payloads (`v3d`, `ast`, classic fields). |
| | `adapters/presenters/hangar_presenter.py` | `HangarPayloadPresenter` creating hangar HUD payloads (`t65..t100` without `~`, `v3d`). |
| | `adapters/v3/samples.py` | Preview sample datasets (`PREVIEW_ORDER`, `PREVIEW_SAMPLES`, `PREVIEW_SAMPLES_V3`), SVG icon bitmaps. |
| | `adapters/v3/metrics.py` | `V3MetricsCalculator` computing exact pixel layout (`cw`, `fh`, `winW`, `winH`, rows, compact hangar 2x2 grid). |
| | `adapters/v3/svg_primitives.py` | SVG paths, rounded corners, tactical brackets, stars, arrows, assist icons. |
| | `adapters/v3/svg_renderer.py` | `V3SvgRenderer` rendering V3/Hangar SVG data URIs (including custom text fill clipPath for `barStyle == 4`). |
| | `adapters/settings/in_game_settings.py` | `InGameSettingsController` for fallback in-game color/slider page when Mod Menu is absent. |
| | `adapters/settings/drag_controller.py` | `DragController` handling Ctrl+LMB panel dragging and minimize toggle button hit-testing. |
| | `adapters/menu/schema.py` | Aslain menu varName metadata and `MenuValueConverter`. |
| | `adapters/menu/preview_renderer.py` | `MenuPreviewRenderer` rendering scaled V3/Classic/Korben/Hangar live SVG previews. |
| | `adapters/menu/tab_definitions.py` | Declarative Mod Menu tab & preview column builders. |
| | `adapters/menu/template_builder.py` | `MenuTemplateBuilder` assembling the complete Mod Menu template. |
| | `adapters/menu/aslain_adapter.py` | `AslainMenuAdapter(ISettingsMenu)` handling Mod Menu registration, live updates, apply/cancel, and preset resets. |
| | `adapters/gameface/visibility_guard.py` | `BattleVisibilityGuard` detecting covering WULF/Scaleform modal windows. |
| | `adapters/gameface/wulf_views.py` | Guarded `ViewModel`/`ViewImpl`/`WindowImpl` (`R.mods.dm.threemarks.views.ThreeMarks`). |
| | `adapters/gameface/panel_adapter.py` | `GamefacePanelAdapter(IPanelView)` managing Gameface view lifecycle, anchor-compensated resizing, and JSON push. |
| **Infrastructure** | `infrastructure/logging_adapter/file_logger.py` | `ModFileLogger(ILogger)` writing rotated logs to `three_marks.log`. |
| | `infrastructure/storage/json_store.py` | `JsonFileStore` with atomic `.tmp` + rename writes. |
| | `infrastructure/storage/config_repository.py` | `FileConfigRepository(IConfigRepository)` for `config.json` and `config_help.txt`. |
| | `infrastructure/storage/cache_repository.py` | `FileCacheRepository(ICacheRepository)` for `cache.json`. |
| | `infrastructure/network/http_client.py` | `HttpJsonClient` using `urllib2`. |
| | `infrastructure/network/worker_queue.py` | `BackgroundWorkerQueue` isolating daemon worker threads from main-thread state. |
| | `infrastructure/network/mastery_gateway.py` | `WgPoliroidMasteryGateway(IMasteryGateway)` fetching WG mastery & Poliroid history asynchronously. |
| | `infrastructure/wot/clock.py` | `WotClock(IClock)` using `time`, `time_utils`, and `BigWorld.time`. |
| | `infrastructure/wot/scheduler.py` | `WotScheduler(IScheduler)` wrapping `BigWorld.callback` / `BigWorld.cancelCallback`. |
| | `infrastructure/wot/dossier_provider.py` | `WotDossierProvider(IDossierProvider)` reading `IItemsCache` and `g_currentVehicle`. |
| | `infrastructure/wot/input_provider.py` | `WotInputProvider(IInputProvider)` reading `Keys`, `GUI`, and camera/death modes. |
| | `infrastructure/wot/damage_tracker.py` | `WotDamageTracker` subscribing to `feedback` / `personalEfficiencyCtrl` / ally damage. |
| | `infrastructure/wot/battle_hooks.py` | `WotBattleHooks` wrapping/unwrapping `BattleFeedbackAdaptor.handleBattleEventsSummary`. |
| | `infrastructure/wot/hangar_monitor.py` | `WotHangarEnvironment(IHangarEnvironment)` and `WotLobbyRouteTap(logging.Handler)`. |
| | `infrastructure/wot/event_registrar.py` | `WotEventRegistrar` wiring/unwiring all WoT events and loggers cleanly. |
| **Bootstrap** | `bootstrap/container.py` | `ModContainer` manually constructing the full dependency graph. |
| | `bootstrap/application.py` | `ModApplication` managing `start()` (`init`) and `stop()` (`fini`). |

### 2.2 Frontend Gameface JS (`package/res/gui/gameface/mods/dm/ThreeMarks/` — ES5 strict)

Loaded deterministically via `<script defer src="...">` in `ThreeMarks.html` under the single namespace `window.DmThreeMarks`:

1. `js/defaults.js` — `SIZES`, layout constants, `DEF_UI`, `DEF_V3`, `ARROW_ROWS`, `METRICS`, bitmap URLs.
2. `js/utils.js` — pure formatting, color interpolation, base64 ASCII encoding, Warhelios text advance estimation.
3. `js/v3_metrics.js` — 1-to-1 JS parity metrics (`v3ComputeMetrics`), delta/target/assist/tempo/hangar 2x2 resolvers.
4. `js/renderer_v3.js` — `V3Renderer` building V3 tactical frame/corners/stars SVG background + smooth HTML fill + custom text fill (`barStyle === 4`) + compact hangar threshold grid.
5. `js/renderer_classic.js` — `ClassicRenderer` rendering classic & Korben battle modes and bitmap font layout.
6. `js/renderer_settings.js` — `SettingsRenderer` rendering interactive fallback in-game settings overlay.
7. `js/gameface_bridge.js` — `GamefaceBridge` wrapping `viewEnv`, `window.engine`, and `window.model`.
8. `ThreeMarks.js` — `ThreeMarksApp` thin UI orchestrator dispatching payloads between the bridge and active renderer.

---

## 3. Lifecycle Sequence (`init()` -> `fini()`)

1. **Startup (`init()` -> `ModApplication.start()`)**:
   - Load and normalize `config.json` into `ConfigStore` (`hangarOnlyRandom = True`, `hideUnderWindows = False` enforced).
   - Load `cache.json` into `FileCacheRepository` and ensure `config_help.txt` matches `MOD_VERSION`.
   - Install `BattleFeedbackAdaptor.handleBattleEventsSummary` hook via `WotBattleHooks`.
   - Register template and live callbacks with Aslain Mod Menu (`AslainMenuAdapter.register()`).
   - Subscribe WoT events (`g_playerEvents`, `g_currentVehicle`, `IItemsCache.onSyncCompleted`, `g_eventBus`, `gui.lobby_state_machine`).
2. **Hangar**:
   - `onAccountShowGUI` -> `HangarSessionService.on_lobby()` -> starts 0.3s watcher (`_watchTick`) + 0.05s UI/drag/settings tick (`_tick`).
   - Vehicle changes snapshot dossier & trigger async WG/Poliroid fetches via `IMasteryGateway`; background results are pushed to `BackgroundWorkerQueue` and consumed strictly on the main thread via `CurveSyncService.pump()`.
3. **Battle**:
   - `onAvatarReady` -> `BattleSessionService.start()` builds `'b'` `GamefacePanelAdapter`, starts `WotDamageTracker`, snapshots current vehicle, schedules 0.05s tick.
   - `_update()` computes exact `ForecastEngine` prediction, smooths `_shownBar`, resolves `ThresholdCalculator`, and pushes payload through `BattlePayloadPresenter`.
   - `onAvatarBecomeNonPlayer` -> `BattleSessionService.stop()` stops tracker, persists pending forecast into cache, destroys panel.
4. **Shutdown (`fini()` -> `ModApplication.stop()`)**:
   - Stops `BattleSessionService` and leaves hangar (`HangarSessionService.on_leave_lobby()`).
   - Unregisters Mod Menu callbacks, unhooks `BattleFeedbackAdaptor`, detaches all WoT event listeners and route tap, and flushes `cache.json` to disk.

---

## 4. Python 2.7 & WoT 2.4.1+ Notes

- All internal imports in `src/dm_threemarks/` use `from __future__ import absolute_import` and explicit **relative imports** so the package resolves seamlessly both as `dm_threemarks` in `unittest` and as `gui.mods.dm_threemarks` inside World of Tanks.
- Every `.py` module is compiled to `.pyc` by `win64\python27.dll` with verified Python 2.7 magic `\x03\xf3\r\n`.
- Logging adapter package is named `infrastructure.logging_adapter` to never shadow stdlib `logging`.
