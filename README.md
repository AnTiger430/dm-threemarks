# dm.threemarks — Три отметки на стволе (WoT 2.4.1+)

Мод отображения прогресса отметок на стволе (Marks of Excellence) для World of Tanks с тремя пресетами панели в бою (включая Вариант 3 «Тактический / Pro»), панелью в ангаре и живым предпросмотром в Aslain Mod Menu.

## Структура проекта

- `src/mod_three_marks.py` — основной клиентский модуль на Python 2.7 (расчёт отметки сохранён без изменений от базовой версии `10.11.8`).
- `package/meta.xml` — метаданные `.wotmod` и текущая версия.
- `package/res/gui/` — Gameface HTML/CSS/JS интерфейс (`ThreeMarks.html`, `ThreeMarks.css`, `ThreeMarks.js`), ресурс-манифест `gen_resources/dm_threemarks.json` и PNG-ассеты.
- `build.ps1` — скрипт компиляции `.py -> .pyc` (через `win64\python27.dll` клиента WoT), проверки JS и упаковки `ZIP_STORED` в `dist/`.

## Сборка и установка

Собрать `.wotmod` (артефакт появится в `dist/`):

```powershell
.\build.ps1
```

Собрать и сразу установить в клиент игры (при закрытом `WorldOfTanks.exe`, с автоматическим бэкапом прошлой версии в `dist/backups/`):

```powershell
.\build.ps1 -Install
```
