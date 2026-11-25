# Правила работы с проектом `dm.threemarks`

## 1. Обязательная самопроверка, пересборка и установка после изменений
После **любых** правок в `src/` или `package/` перед ответом пользователю обязательно выполняй единую команду самопроверки:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

Скрипт [verify.ps1](verify.ps1) и верификатор [tools/verify_mod.py](tools/verify_mod.py) автоматически выполняют:
1. Пересборку `.wotmod` и установку в папку игры через [build.ps1](build.ps1) `-Install` (если процесс `WorldOfTanks.exe` запущен, собирает в `dist/` без `-Install` и предупреждает об этом).
2. **Stage 1 (Tests):** полный прогон `unittest` (`tests/` — математика MoE, golden UI-контракты, Node-тест фронтенда, архитектурные правила и лимит строк).
3. **Stage 2 (Archive):** аудит готового `dist\dm.threemarks_*.wotmod` (`ZIP_STORED`, магия Python 2.7 `\x03\xf3\r\n`, `marshal.loads`, отсутствие `.py`/`.tmp`, наличие всех ресурсов из `gen_resources/*.json`, `ThreeMarks.html` и `ThreeMarks.css`, проверка JS через `node --check`, совпадение SHA-256 установленного файла).
4. **Stage 3 (Runtime):** распаковка скомпилированных `.pyc` прямо из собранного `.wotmod` во временную среду и полный сквозной прогон жизненного цикла (`init()` -> ангар WULF `TmView`/`TmWindow` с проверкой `R.mods...ThreeMarks()` и `onSyncCompleted(reason, diff)` -> Aslain Mod Menu v2.1.15 `getVersionTuple()`, 6/3 вкладки, живые изменения + SVG `updateImage` + кнопки -> бой + `handleBattleEventsSummary` -> `fini()`) с проверкой **нуля ошибок** в логе `three_marks.log`.
5. **Stage 4 (GameLog):** диагностика последней игровой сессии в реальном `mods\configs\three_marks\three_marks.log`. После запуска реального клиента игры для строгой проверки лога вызывай:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\verify.ps1 -NoBuild -CheckGameLog
   ```

**Версионирование:**
- При функциональных и UI-изменениях в `src/` или `package/` перед запуском `.\verify.ps1` синхронно поднимай patch/minor версию в двух файлах: [package/meta.xml](package/meta.xml) (`<version>`) и [src/dm_threemarks/application/config/defaults.py](src/dm_threemarks/application/config/defaults.py) (`MOD_VERSION`), если пользователь не попросил оставить текущую версию.

**Исключения для `-Install`:**
- Если пользователь в текущем запросе явно запретил установку в игру, запускай `powershell -ExecutionPolicy Bypass -File .\verify.ps1 -NoInstall`.

### 1.5. Визуальный рендер и аудит UI и Mod Menu (`render_audit.ps1`)
После любых визуальных, CSS, JS, SVG или Mod Menu правок (а также перед отчётом об изменениях интерфейса) обязательно запускай визуальный рендер и геометрический аудит в headless Chrome:

```powershell
powershell -ExecutionPolicy Bypass -File .\render_audit.ps1
```

Скрипт [tools/render_audit.py](tools/render_audit.py) (см. также локальный скилл `.agents/skills/dm-ui-audit/SKILL.md`):
1. Рендерит реальные `ThreeMarks.css`, `js/*.js`, `.ttf` шрифты и `MenuTemplateBuilder` / `V3SvgRenderer` в `dist/ui_audit/` (`01_battle_states.png` .. `06_menu_korben.png`, `report.json`, `index.html`).
2. Проверяет в живом DOM отсутствие наездов текста, обрезки глифов/границ, расхождений JS DOM vs Python SVG, а также структуру всех подразделов Mod Menu и откат при выходе без сохранения.
3. Обязательно просмотри сгенерированные PNG в `dist/ui_audit/` перед финальным ответом.

## 2. Ключевые инварианты проекта
- **Python 2.7 (`\x03\xf3\r\n`)**: в каждом `.py` файле обязателен `# -*- coding: utf-8 -*-`, классы — только new-style (`class Foo(object):`), вызов родителя через `super(Foo, self)`. Запрещён синтаксис Python 3 (f-строки, type annotations в сигнатурах, `dataclasses`, `pathlib`, `enum`, `nonlocal`, `super()` без аргументов).
- **Frontend ES5**: весь код в `package/res/gui/gameface/mods/dm/ThreeMarks/` должен оставаться совместимым с ES5 (Cohtml / Gameface) и проходить проверку `node --check`.
- **Clean Architecture & границы слоёв**:
  - `src/dm_threemarks/domain/` — ноль внешних импортов (`BigWorld`, `GUI`, `Keys`, `frameworks.wulf`, `urllib2`, ФС). Математика расчёта отметок должна сохранять точную числовую идентичность.
  - Лимит на размер любого `.py` и `.js` файла — не более 500 строк (контролируется тестом `tests/test_architecture_rules.py`).
- **Безопасность данных**: не перезаписывай пользовательский конфиг `mods/configs/three_marks/config.json` без явного запроса и не удаляй исторические архивы в `outputs/`.
