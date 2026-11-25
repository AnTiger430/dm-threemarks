---
name: dm-ui-audit
description: >-
  Visual UI & Aslain Mod Menu render auditor for dm.threemarks. Generates pixel-accurate
  Chrome headless screenshots + DOM geometry/overlap/clipping checks for Battle panel,
  Hangar panel, all 8 TTF fonts, and all Mod Menu tabs/sections, plus Mod Menu cancel
  state-machine verification. Run after any UI, CSS, JS, SVG, or Mod Menu edits.
---

# `dm-ui-audit` — Визуальный рендер и авто-аудит панели и Mod Menu

## Когда запускать
Обязательно запускай этот аудит **после любых правок** в:
- `package/res/gui/gameface/mods/dm/ThreeMarks/` (`ThreeMarks.css`, `ThreeMarks.html`, `ThreeMarks.js`, `js/*.js`, `fonts/`)
- `src/dm_threemarks/adapters/v3/` (`metrics.py`, `svg_renderer.py`, `svg_primitives.py`, `samples.py`)
- `src/dm_threemarks/adapters/menu/` (`template_builder.py`, `tab_definitions.py`, `preview_renderer.py`, `aslain_adapter.py`, `schema.py`)
- `src/dm_threemarks/adapters/presenters/`

## Шаги выполнения

1. **Запусти рендер-аудит** из корня репозитория (не трогает установленные моды в папках игры):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\render_audit.ps1
   ```
   При необходимости открыть интерактивный дашборд в браузере: `.\render_audit.ps1 -Open`.

2. **Проверь автоматический отчёт**:
   - Проверь stdout (`[PASS]` / `[FAIL]` / `[ERROR]` / `[WARN]`) и `dist/ui_audit/report.json`.
   - Убедись, что загружены все кастомные `.ttf` шрифты (`loadedFonts` содержит `ThreeMarksPFDINMax`, `ThreeMarksDINRound`, `ThreeMarksJura`, `ThreeMarksExo2`, `ThreeMarksRubik`, `ThreeMarksFiraCond`, `ThreeMarksTektur`).

3. **Визуально проверь все 6 сгенерированных PNG через `read_file`**:
   - `dist/ui_audit/01_battle_states.png` — все состояния боевой панели (`+`, `-`, `0`, `big`, 1-й бой, `--.--%`, `100%`, `Alt` темп/ассист, `barStyle=1/3`, кириллица `Ж*24`, `HUD`, звёзды в шапке, `Classic/Korben`, сравнение JS DOM vs Python SVG).
   - `dist/ui_audit/02_fonts_matrix.png` — все 8 шрифтов в бою и ангаре + полоса увеличения 32px (`84.95% 3.07% 100.00% --.--%`) для проверки подрезки краёв глифов.
   - `dist/ui_audit/03_hangar_states.png` — все состояния ангара (`0/1/2/3` отметки, `100.00%`, загрузка `--.--% / —`, 5-значные пороги `12345`, `barStyle=1/3`, `Tektur`, `HUD`, сравнение JS DOM vs Python SVG).
   - `dist/ui_audit/04_menu_battle_v3.png` — все 5 подразделов боевой панели в стиле Aslain Mod Menu v2.1.15 + правый столбец превью SVG.
   - `dist/ui_audit/05_menu_hangar.png` — все 4 подраздела вкладки «Ангар» + превью SVG.
   - `dist/ui_audit/06_menu_korben.png` — режим «Отметка Корбена» (2 подраздела + SVG).

4. **Чек-лист дефектов при визуальном осмотре**:
   - **Обрезка глифов**: левый/правый край цифр после точки (`.07%`, `.95%`, `.20%`) и `%` не срезаны контейнером или `line-height`.
   - **Наезд текстов друг на друга**: `%` на дельту, подпись `Сум. урон` на числа, `65%`/`85%`/`95%`/`100%` друг на друга при 5-значных порогах (`10450`, `12345`).
   - **Вылет за рамку**: текст или прогресс-бар не выходят за пределы подложки/рамки.
   - **Расхождение JS DOM и Python SVG**: габариты, расположение звёзд, шрифты и отступы совпадают между игровым Gameface DOM и превью в Mod Menu.
   - **Mod Menu**: ни один подраздел не пуст (`>= 1` видимый контрол), ссылки `masterVarName`/`conditions` валидны, сценарий `Киберспорт -> Корбен -> Выход без сохранения -> Повторное открытие` не ломает левую колонку.

5. **После правок** повторно прогони `.\render_audit.ps1` и стандартный `.\verify.ps1 -NoInstall` (или `.\verify.ps1`, если разрешена установка).
