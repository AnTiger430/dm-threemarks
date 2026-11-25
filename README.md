# dm.threemarks — Три отметки на стволе (`v10.12.45`)

Мод отображения прогресса отметок на стволе (Marks of Excellence) для **World of Tanks EU (`2.4.2.0+`, `.wotmod`)** и **Lesta «Мир танков» (`1.46.0.0+`, `.mtmod`)** в модульной архитектуре (**Clean Architecture + Hexagonal Ports & Adapters**) с точной математикой расчёта отметок, адаптивными кривыми и Gameface UI.

## Основные возможности

- **Два пресета боевой панели**:
  - **Вариант 1 — «Киберспорт»**: настраиваемая тактическая рамка, звёзды отметок (6 позиций, 3 стиля, мягкое свечение), гибкая полоска прогресса (`Сплошная`, `Пороги 65/85/95/100%`, `Без полоски`, `Свой текст с заполнением`), урон (`набито / нужно`), каналы ассиста (засвет / гусеницы) и пороги темпа (следующая отметка и 95%, в т.ч. по клавише `Alt`).
  - **Вариант 2 — «Отметка Корбена»**: минималистичный процент и строка `набито / нужно`.
- **Ангарная панель (стиль «Киберспорт»)**: текущий процент отметки, суммарный урон, сетка порогов `65% / 85% / 95% / 100%`, отдельное масштабирование и настройка рамки/звёзд/полоски.
- **8 шрифтов на выбор**: `PFDINMax`, `Warhelios`, `DIN Round Pro + Warhelios`, `Jura`, `Exo 2`, `Rubik`, `Fira Sans Condensed`, `Tektur`.
- **Интеграция с Aslain Mod Menu 2.x / ModsSettingsAPI**: живое SVG/DOM-превью боевой и ангарной панелей, умная видимость параметров и мгновенное обновление при вводе текста.

## Структура проекта

- `src/mod_three_marks.py` — точка входа (`init()` / `fini()`), делегирующая жизненный цикл в `ModApplication`.
- `src/dm_threemarks/` — модульный Python 2.7 пакет:
  - `domain/` — чистая математика MoE (`Curve`, `ServerEpoch`, `MarkSnapshot`, `ForecastEngine`, `ThresholdCalculator`, `AssistResolver`, Value Objects).
  - `application/` — порты (`abc.ABCMeta`), схема/валидация конфигурации (`ConfigStore`) и Use Cases (`BattleSessionService`, `HangarSessionService`, `CurveSyncService`, `SnapshotVehicleUseCase`, `ConfigSyncService`).
  - `adapters/` — Gameface/SVG презентеры (`BattlePayloadPresenter`, `HangarPayloadPresenter`, `UiConfigSerializer`), расчёт метрик/SVG (`V3MetricsCalculator`, `V3SvgRenderer`), адаптер Aslain Mod Menu и `GamefacePanelAdapter`.
  - `infrastructure/` — файловое хранилище (`config.json`/`cache.json`), HTTP-клиенты WG/Poliroid с фоновой очередью, WoT-хуки и файловый логгер.
  - `bootstrap/` — Composition Root (`ModContainer`, `ModApplication`).
- `package/meta.xml` — метаданные `.wotmod`/`.mtmod` и версия мода.
- `package/res/gui/` — ES5/Gameface UI (`ThreeMarks.html`, `ThreeMarks.css`, `js/*.js`, оркестратор `ThreeMarks.js`), шрифты `fonts/*.ttf`, манифест `dm_threemarks.json` и PNG-иконки звёзд.
- `tests/` — автотесты Python 2.7 (`unittest`): golden-тесты математики и SVG/метрик, unit-тесты Use Cases, контрактный Python+Node тест фронтенда, smoke-тест `init()`/`fini()` и AST-аудит правил Clean Architecture.
- `tools/` — скрипты проверки сборки (`verify_mod.py`), визуального рендер-аудита (`render_audit.py`), заглушки WoT (`wot_stubs.py`) и патчер шрифтов/превью для Aslain Mod Menu (`patch_modmenu.py`).
- `docs/ARCHITECTURE.md` — архитектурная документация (ADR), карта слоёв и жизненного цикла.

## Тестирование (Python 2.7)

```powershell
C:\Python27\python.exe -m unittest discover -s tests -v
```

## Сборка, проверка и рендер-аудит

```powershell
# Сборка + установка (при закрытом клиенте) + все 4 стадии проверки (автодетект версии из version.xml):
powershell -ExecutionPolicy Bypass -File .\verify.ps1 -Client EU
powershell -ExecutionPolicy Bypass -File .\verify.ps1 -Client Lesta

# Только сборка в dist/ без установки:
powershell -ExecutionPolicy Bypass -File .\build.ps1 -Client EU
powershell -ExecutionPolicy Bypass -File .\build.ps1 -Client Lesta

# Визуальный рендер-аудит панелей и мод-меню в headless Chrome:
powershell -ExecutionPolicy Bypass -File .\render_audit.ps1
```

При использовании **Aslain Mod Menu** патч шрифтов и живого превью в архив меню можно применить командой:

```powershell
python tools\patch_modmenu.py --archive "<путь_к_aslain.modmenu.wotmod_или_mtmod>"
```
