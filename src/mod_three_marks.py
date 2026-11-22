# -*- coding: utf-8 -*-
"""
Три отметки на стволе - прогноз отметки в бою для World of Tanks
=================================================================
Панель: HTML/CSS через Gameface.
Расчёт боевого процента повторяет серверный:
  - комбинированный урон = прямой + max(засвет, гусеницы, оглушение),
    минус урон союзникам
  - целое скользящее среднее: avg' = round_half_up(avg + (урон - avg) * 2/101)
  - процент = среднее по суточной кривой WG (8 узлов, прямые между ними),
    отброшенный до сотых; кривая берётся за те сутки, на которых сейчас
    серверы (суточная история + сверка с досье)
Перетаскивание: Ctrl (курсор) + ЛКМ. Позиция сохраняется в конфиг.
Конфиг:  <WoT>/mods/configs/three_marks/config.json
Журнал:  <WoT>/mods/configs/three_marks/three_marks.log
"""

import base64
import datetime
import json
import logging
import math
import os
import threading
import time
import traceback

import BigWorld
import GUI
import Keys
from PlayerEvents import g_playerEvents
from CurrentVehicle import g_currentVehicle
from constants import ARENA_BONUS_TYPE
from helpers import dependency
from skeletons.gui.shared import IItemsCache
from skeletons.gui.battle_session import IBattleSessionProvider
from gui.battle_control.controllers import feedback_adaptor

try:
    import urllib2
except ImportError:
    urllib2 = None

try:
    from gui.shared import EVENT_BUS_SCOPE, g_eventBus
    from gui.shared import events as gui_events
    _EB_OK = True
except Exception:
    _EB_OK = False

try:
    from frameworks.wulf import ViewFlags, ViewModel, ViewSettings, \
        WindowFlags, WindowLayer, WindowStatus
    from gui.impl.gui_decorators import args2params
    from gui.impl.pub import ViewImpl, WindowImpl
    from skeletons.gui.impl import IGuiLoader
    # Since WG 2.4.1 custom Gameface resources are registered natively in
    # gui/gen_resources/*.json.  The old OpenWG ModDynAccessor is now a
    # compatibility stub on the EU client and always resolves to -1.
    from gui.impl.gen import R
    _GF_LAYOUT = R.mods.dm.threemarks.views.ThreeMarks
    _GF_OK = True
    _GF_ERR = None
except Exception:
    _GF_OK = False
    _GF_ERR = traceback.format_exc()

_COVERING_LAYERS = ()
_GONE_WINDOW_STATUSES = ()
if _GF_OK:
    _COVERING_LAYERS = (WindowLayer.FULLSCREEN_WINDOW,
                        WindowLayer.TOP_WINDOW, WindowLayer.OVERLAY)
    _GONE_WINDOW_STATUSES = (WindowStatus.DESTROYING,
                             WindowStatus.DESTROYED)

CONFIG_DIR = os.path.join('mods', 'configs', 'three_marks')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
CACHE_PATH = os.path.join(CONFIG_DIR, 'cache.json')

_WINDOW_W, _WINDOW_H = (244, 96)
_HWINDOW_W, _HWINDOW_H = (244, 144)
_PCT_WINDOW_W, _PCT_WINDOW_H = (220, 72)

MOD_VERSION = '10.12.7'
_WG_API_URL = 'https://api.worldoftanks.%s/wot/tanks/mastery/?application_id=%s&distribution=damage&percentile=%s&tank_id=%s'
_WG_HISTORY_URL = 'https://poliroid.me/gunmarks/api/v2/data/%s/vehicle/%s/%s'

_V3_DEFAULTS = {
    'v3Density': 1,
    'v3MinWidth': 0,
    'v3Anchor': 0,
    'v3HideInSniper': False,
    'v3FrameStyle': 0,
    'v3Radius': 5,
    'v3CornerColor': '#FFFFFF',
    'v3CornerAlpha': 0.90,
    'v3BorderAlpha': 0.28,
    'v3BgColor': '#0B1016',
    'v3BgOpacity': 0.48,
    'v3StarsPos': 0,
    'v3StarsStyle': 0,
    'v3StarsDivider': False,
    'v3StarsSize': 15,
    'v3StarsGap': 6,
    'v3StarsGlow': True,
    'v3StarOnColor': '#FFFFFF',
    'v3StarOffColor': '#9AA3AE',
    'v3HeaderOrder': 0,
    'v3PctDecimals': 1,
    'v3DeltaIcon': 0,
    'v3DeltaColorMode': 0,
    'v3BarStyle': 0,
    'v3BarScale': 0,
    'v3BarHeight': 4,
    'v3BarTrackHeight': 2,
    'v3BarCustomText': u'KIBERSPORT',
    'v3BarTextSize': 15,
    'v3BarEndTicks': True,
    'v3BarCursor': True,
    'v3BarMarks': False,
    'v3BarColorMode': 0,
    'v3BarCustomColor': '#A7D080',
    'v3ShowDamage': True,
    'v3DamageLabel': 0,
    'v3DamageCustomLabel': u'Сум. урон',
    'v3ThousandsSep': 1,
    'v3DamageDynColor': True,
    'v3AssistShow': 0,
    'v3AssistMode': 0,
    'v3AssistPlace': 0,
    'v3AssistHideZero': False,
    'v3TempoShow': 0,
    'v3TempoMode': 0,
    'v3TempoPlace': 0,
    'v3AccentPlus': '#A7D080',
    'v3AccentMinus': '#E57373',
    'v3AccentZero': '#9AA3AE',
    'v3AccentBig': '#B07CFF',
    'v3TextMain': '#FFFFFF',
    'v3TextMuted': '#B8BDC4',
}

_VH_DEFAULTS = {
    'vhScale': 1.0,
    'vhDensity': 1,
    'vhFrameStyle': 0,
    'vhRadius': 5,
    'vhCornerColor': '#FFFFFF',
    'vhCornerAlpha': 0.90,
    'vhBorderAlpha': 0.28,
    'vhBgColor': '#0B1016',
    'vhBgOpacity': 0.48,
    'vhStarsPos': 0,
    'vhStarsStyle': 0,
    'vhStarsDivider': False,
    'vhStarsSize': 15,
    'vhStarsGap': 6,
    'vhStarsGlow': True,
    'vhStarOnColor': '#FFFFFF',
    'vhStarOffColor': '#9AA3AE',
    'vhPctDecimals': 1,
    'vhBarStyle': 0,
    'vhBarScale': 0,
    'vhBarHeight': 4,
    'vhBarTrackHeight': 2,
    'vhBarCustomText': u'KIBERSPORT',
    'vhBarTextSize': 15,
    'vhBarEndTicks': True,
    'vhBarCursor': True,
    'vhBarMarks': False,
    'vhBarColor': '#A7D080',
    'vhShowEma': True,
    'vhShowThresholds': True,
    'vhThousandsSep': 1,
    'vhTextMain': '#FFFFFF',
    'vhTextMuted': '#B8BDC4',
}

DEFAULT_CONFIG = {
    'x': -0.55,
    'y': 0.95,
    'hx': 0.35,
    'hy': 0.60,
    'hangarPanel': True,
    'onlyRandomBattles': True,
    'minVehicleLevel': 5,
    'dragEnabled': True,
    # Суточная история кривых с poliroid.me (нужна для точного прогноза в
    # первые часы после смены суток). False - только кривые из API WG.
    'onlineHistory': True,
    # Что делает панель в бою под меню Esc / диалогами:
    # 'show' - остаётся как есть, 'dim' - затемняется, 'hide' - скрывается.
    'battleMenu': 'show',
    # Пресет боевой панели: 0 - Вариант 1 (Киберспорт), 1 - Вариант 2 (Отметка Корбена).
    'battlePreset': 0,
    # Обратная совместимость: True соответствует battlePreset == 1.
    'battlePercentOnly': False,
    # True - прятать панель ангара под любым большим окном (диалоги, Mod Menu...).
    'hideUnderWindows': False,
    # True - панель ангара только для случайных боёв (включая взвод): в
    # Натиске, событиях, ранговых и т.п. отметка не считается, панель не нужна
    'hangarOnlyRandom': True,
    # В бою: True - панель скрывается во вступлении ("В центре внимания":
    # карточки игроков и обратный отсчёт перед боем), потом появляется
    'hideInIntro': True,
    # В бою: True - панель скрывается на просмотре выстрела, которым вас
    # уничтожили (экран "Продолжить"), и возвращается, когда он закончился
    'hideInKillcam': True,
    # True - панель скрывается после гибели насовсем (и при наблюдении)
    'hideAfterDeath': False,

    # ---- внешний вид (правки подхватываются без перезапуска игры) ----------
    # Размер всей панели: 1.0 - как есть, 0.5 .. 2.5
    'uiScale': 1.0,
    # Непрозрачность тёмного фона: 0 - совсем прозрачный, 1 - сплошной
    'bgOpacity': 0.82,
    # Общая непрозрачность панели; фон настраивается отдельно через bgOpacity.
    'panelOpacity': 1.0,
    # Цвет изменения процента (число и стрелка): отметка выросла / упала / ~0
    'colorPlus': '#86EF6A',
    'colorMinus': '#FF6060',
    'colorZero': '#EAEAEA',
    # Цвет полоски прогресса в бою: отметка растёт / падает / ~0
    'barColorPlus': '#8FE37D',
    'barColorMinus': '#FF6060',
    'barColorZero': '#DDE6EE',
    # Цвет полоски в ангаре
    'barColorHangar': '#F0F2F6',
    # Полоска в бою: True - цвет по состоянию отметки (плюс / минус / ноль /
    # большой плюс), False - всегда один цвет barColorStandard
    'barBySign': True,
    'barColorStandard': '#8FE37D',
    # Непрозрачность пустой части полоски и цвет бегунка
    'trackOpacity': 0.18,
    'tickColor': '#FFFFFF',
    # Цвет большого процента; pctFollowsSign - красить его как изменение
    'pctColor': '#F4F4F4',
    'pctFollowsSign': False,
    # Вспышка полоски, когда процент вырос
    'glow': True,
    # Строка под панелью в бою: showSpot - помощь по засвету, showTrack - помощь
    # по гусенице (каждое включается отдельно). То, чего больше, красится цветом
    # изменения (плюс/минус/ноль), меньшее - цветом большого процента
    'showSpot': True,
    'showTrack': True,
    # Изменение в пределах +-zeroBand процентных пунктов считается нулём
    'zeroBand': 0.02,
    # Большой плюс (отдельный цвет, по умолчанию фиолетовый).
    # bigByDamage=True: когда урон за бой не меньше bigDamageFactor x (средний
    # урон, нужный на bigBasePercent процентах). Пример: на 95% нужно 4196,
    # множитель 2.0 -> фиолетовый от 8392 урона.
    # bigByDamage=False: когда процент вырос на bigFrom п.п. и больше.
    'bigByDamage': True,
    'bigDamageFactor': 2.0,
    'bigBasePercent': 95.0,
    'bigFrom': 4.0,
    'colorBig': '#B07CFF',
    'barColorBig': '#B07CFF',
    # Числа "Сум. урон: X / Y": X берёт цвет изменения (если dmgFollowsSign),
    # иначе colorDmg; "/ Y" - colorProj
    'dmgFollowsSign': True,
    'colorDmg': '#86EF6A',
    'colorProj': '#EAEAEA',
    'minHangar': False,
    'textDamageTitle': u'Сум. урон:',
    # Public application id used by the reference overlay; can be replaced
    # in config.json with a personal Wargaming API application id.
    'wgApiApplicationId': 'bce57ac20af6b67b08be09fd66847ed9',
}
DEFAULT_CONFIG.update(_V3_DEFAULTS)
DEFAULT_CONFIG.update(_VH_DEFAULTS)

_itemsCache = dependency.instance(IItemsCache)
_sessionProvider = dependency.instance(IBattleSessionProvider)

g_config = dict(DEFAULT_CONFIG)
g_cache = {}
_SESSION_BASE = {}

try:
    _ORIG_SUMMARY = feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary
except Exception:
    _ORIG_SUMMARY = None


# ==========================================================================
# утилиты

def _fmt(n):
    try:
        return u'{:,}'.format(int(round(n))).replace(',', u' ')
    except Exception:
        return unicode(n)


def _loadJson(path, default):
    try:
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return json.loads(f.read().decode('utf-8'))
    except Exception:
        pass
    return default


def _saveJson(path, data):
    try:
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if path == CONFIG_PATH:      # конфиг правят руками - читаемый вид
            raw = json.dumps(data, ensure_ascii=False, sort_keys=True,
                             indent=2, separators=(',', ': ')).encode('utf-8')
        else:
            raw = json.dumps(data, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')
        tmp = path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(raw)
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)
        if path == CONFIG_PATH:
            _cfgStamp[0] = _mtime(path)
    except Exception:
        _logError('save %s' % path)


def _loadConfig():
    global g_config
    cfg = dict(DEFAULT_CONFIG)
    stored = _loadJson(CONFIG_PATH, None)
    if isinstance(stored, dict):
        for key in DEFAULT_CONFIG:
            if key in stored:
                cfg[key] = stored[key]
        if 'battlePreset' not in stored:
            cfg['battlePreset'] = 1 if bool(cfg.get('battlePercentOnly', False)) else 0
    try:
        rawPreset = int(round(float(cfg.get('battlePreset', 0))))
        preset = 1 if rawPreset == 1 else 0
    except (TypeError, ValueError):
        preset = 0
    cfg['battlePreset'] = preset
    cfg['battlePercentOnly'] = (preset == 1)
    cfg['hangarOnlyRandom'] = True
    cfg['hideUnderWindows'] = False
    _saveJson(CONFIG_PATH, cfg)
    g_config = cfg
    _cfgStamp[0] = _mtime(CONFIG_PATH)


_cfgStamp = [0.0]
_cfgPolled = [0.0]


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _pollConfig():
    """Подхватить правки config.json на лету (раз в пару секунд)."""
    if _SETTINGS_OPEN[0]:
        return False
    now = time.time()
    if now - _cfgPolled[0] < 2.0:
        return False
    _cfgPolled[0] = now
    stamp = _mtime(CONFIG_PATH)
    if not stamp or stamp == _cfgStamp[0]:
        return False
    before = dict(g_config)
    _loadConfig()
    # положение панелей хранят сами панели; из файла его не перечитываем
    for key in ('x', 'y', 'hx', 'hy'):
        g_config[key] = before.get(key, g_config.get(key))
    _log('config reloaded')
    _menuPush()
    return True


_CONFIG_HELP = u"""Три отметки на стволе - настройки внешнего вида (config.json)
Правки подхватываются без перезапуска игры (в течение пары секунд).
Если установлен Mod Menu (Aslain), внешний вид настраивается в нём: мод
«Три отметки на стволе», там же выбор цвета и сброс. Значения, сохранённые
в Mod Menu, главнее config.json при запуске игры; изменения из Mod Menu
записываются и в config.json.
В ангаре: кнопка с четырьмя цветными квадратами рядом с процентом
открывает экран настроек - то же самое можно менять мышью, без файла.
Цвета - в виде #RRGGBB, например #FF6060. Неверное значение заменяется стандартным.

uiScale          размер всей панели: 1.0 как есть, 0.5 ... 2.5
bgOpacity        непрозрачность тёмного фона: 0 - прозрачный, 1 - сплошной
panelOpacity     общая непрозрачность панели: 0 - невидимая, 1 - сплошная
battlePercentOnly true - режим 2: в бою процент и строка суммарного урона;
                  false - режим 1: полная текущая панель
colorPlus        цвет числа и стрелки, когда процент растёт
colorMinus       цвет числа и стрелки, когда процент падает
colorZero        цвет, когда изменение около нуля
barColorPlus     цвет полоски в бою, когда процент растёт
barColorMinus    цвет полоски в бою, когда процент падает
barColorZero     цвет полоски в бою, когда изменение около нуля
barColorHangar   цвет полоски в ангаре
showSpot         true - под панелью в бою показывать помощь по засвету
showTrack        true - под панелью в бою показывать помощь по гусенице
                 (то, чего больше, подсвечивается цветом изменения, меньшее - цветом
                 большого процента; выключены оба - строки нет)
barBySign        true - полоска в бою красится по состоянию отметки (+/-/0/большой плюс);
                 false - всегда цветом barColorStandard
barColorStandard цвет полоски в бою, когда barBySign выключен
trackOpacity     непрозрачность пустой части полоски (0 ... 1)
tickColor        цвет бегунка на полоске
pctColor         цвет большого процента
pctFollowsSign   true - красить большой процент цветом изменения (+/-/0)
glow             true - вспышка полоски, когда процент вырос
zeroBand         изменение в пределах +-этого значения (п.п.) считается нулём
bigByDamage      true - "большой плюс" по урону за бой, false - по росту процента (bigFrom)
bigDamageFactor  большой плюс, когда урон >= это число x средний урон, нужный на bigBasePercent
bigBasePercent   какой процент берётся за основу (95 - отметка 95%); 65 / 85 / 95 / 100
bigFrom          при bigByDamage=false: рост процента (п.п.) и выше - "большой плюс" (0 - выкл.)
colorBig         цвет числа и стрелки при большом плюсе (по умолчанию фиолетовый)
barColorBig      цвет полоски при большом плюсе
dmgFollowsSign   true - число урона в "Сум. урон" берёт цвет изменения (+/-/0/большой плюс)
colorDmg         цвет числа урона, если dmgFollowsSign выключен
colorProj        цвет "/ 745" (прогнозное среднее) справа от числа урона
battleMenu       поведение в бою под меню Esc: show / dim / hide
hideUnderWindows true - прятать панель ангара под любым большим окном
hideInIntro      true - в бою прятать панель во вступлении ("В центре внимания") перед боем
hideInKillcam    true - в бою прятать панель на просмотре выстрела, которым вас уничтожили
                 (после него она возвращается, пока вы наблюдаете за боем)
hideAfterDeath   true - прятать панель после гибели насовсем, в том числе при наблюдении
hangarOnlyRandom true - панель ангара только в случайных боях (в Натиске, событиях и
                 т.п. отметка не считается); false - показывать везде
"""


def _writeConfigHelp():
    path = os.path.join(CONFIG_DIR, 'config_help.txt')
    try:
        if not os.path.isfile(path) or MOD_VERSION not in _loadText(path)[:300]:
            with open(path, 'wb') as f:
                f.write((u'[%s]\n' % MOD_VERSION + _CONFIG_HELP).encode('utf-8'))
    except Exception:
        _logError('config help')


def _loadText(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', 'replace')


def _cfgColor(key):
    value = str(g_config.get(key, DEFAULT_CONFIG.get(key, '#FFFFFF')) or '').strip()
    if len(value) == 6:
        value = '#' + value
    if len(value) == 7 and value[0] == '#':
        try:
            int(value[1:], 16)
            return value.upper()
        except ValueError:
            pass
    _logOnce(('badcolor', key, value),
             'config: "%s" is not a #RRGGBB colour (%r), using the default' % (key, value))
    return str(DEFAULT_CONFIG.get(key, '#FFFFFF')).upper()


def _cfgNumber(key, low, high):
    try:
        value = float(g_config.get(key, DEFAULT_CONFIG.get(key)))
    except (TypeError, ValueError):
        _logOnce(('badnum', key), 'config: "%s" is not a number, using the default' % key)
        value = float(DEFAULT_CONFIG.get(key))
    return max(low, min(high, value))


def _cfgInt(key, low, high, cfg=None):
    src = g_config if cfg is None else cfg
    try:
        raw = src.get(key, DEFAULT_CONFIG.get(key, low))
        if isinstance(raw, bool):
            value = int(raw)
        else:
            value = int(round(float(raw)))
    except (TypeError, ValueError):
        value = int(DEFAULT_CONFIG.get(key, low))
    return max(low, min(high, value))


def _cfgNumFrom(cfg, key, low, high):
    try:
        value = float(cfg.get(key, DEFAULT_CONFIG.get(key, low)))
    except (TypeError, ValueError):
        value = float(DEFAULT_CONFIG.get(key, low))
    return max(low, min(high, value))


def _cfgColFrom(cfg, key):
    value = str(cfg.get(key, DEFAULT_CONFIG.get(key, '#FFFFFF')) or '').strip()
    if len(value) == 6:
        value = '#' + value
    if len(value) == 7 and value[0] == '#':
        try:
            int(value[1:], 16)
            return value.upper()
        except ValueError:
            pass
    return str(DEFAULT_CONFIG.get(key, '#FFFFFF')).upper()


def _cfgStr(key, default=u'', maxLen=24, cfg=None):
    src = g_config if cfg is None else cfg
    raw = src.get(key, DEFAULT_CONFIG.get(key, default))
    try:
        if raw is None:
            txt = default
        elif isinstance(raw, unicode):
            txt = raw
        elif isinstance(raw, str):
            txt = raw.decode('utf-8', 'replace')
        else:
            txt = unicode(raw)
        txt = txt.strip()
        if maxLen > 0 and len(txt) > maxLen:
            txt = txt[:maxLen]
        return txt
    except Exception:
        return default


def _v3UiPayload():
    return {
        'den': _cfgInt('v3Density', 0, 2),
        'minW': _cfgInt('v3MinWidth', 0, 360),
        'anc': _cfgInt('v3Anchor', 0, 5),
        'fs': _cfgInt('v3FrameStyle', 0, 3),
        'rad': _cfgInt('v3Radius', 0, 14),
        'cc': _cfgColor('v3CornerColor'),
        'ca': round(_cfgNumber('v3CornerAlpha', 0.0, 1.0), 3),
        'ba': round(_cfgNumber('v3BorderAlpha', 0.0, 1.0), 3),
        'bgc': _cfgColor('v3BgColor'),
        'bgo': round(_cfgNumber('v3BgOpacity', 0.0, 1.0), 3),
        'sp': _cfgInt('v3StarsPos', 0, 5),
        'ss': _cfgInt('v3StarsStyle', 0, 2),
        'sd': bool(g_config.get('v3StarsDivider', False)),
        'sz': _cfgInt('v3StarsSize', 10, 22),
        'sg': _cfgInt('v3StarsGap', 2, 14),
        'sgl': bool(g_config.get('v3StarsGlow', True)),
        'son': _cfgColor('v3StarOnColor'),
        'sof': _cfgColor('v3StarOffColor'),
        'ho': _cfgInt('v3HeaderOrder', 0, 2),
        'dec': _cfgInt('v3PctDecimals', 0, 1),
        'di': _cfgInt('v3DeltaIcon', 0, 3),
        'dc': _cfgInt('v3DeltaColorMode', 0, 1),
        'bs': _cfgInt('v3BarStyle', 0, 4),
        'bsc': _cfgInt('v3BarScale', 0, 1),
        'bh': _cfgInt('v3BarHeight', 2, 10),
        'bth': _cfgInt('v3BarTrackHeight', 1, 10),
        'bt': _cfgStr('v3BarCustomText', u'KIBERSPORT', 24) or u'KIBERSPORT',
        'bts': _cfgInt('v3BarTextSize', 10, 26),
        'bet': bool(g_config.get('v3BarEndTicks', True)),
        'bcur': bool(g_config.get('v3BarCursor', True)),
        'bmk': bool(g_config.get('v3BarMarks', False)),
        'bcm': _cfgInt('v3BarColorMode', 0, 2),
        'bcc': _cfgColor('v3BarCustomColor'),
        'dmgOn': bool(g_config.get('v3ShowDamage', True)),
        'dl': _cfgInt('v3DamageLabel', 0, 2),
        'dlc': _cfgStr('v3DamageCustomLabel', u'Сум. урон', 24),
        'sep': _cfgInt('v3ThousandsSep', 0, 2),
        'ddyn': bool(g_config.get('v3DamageDynColor', True)),
        'ash': _cfgInt('v3AssistShow', 0, 3),
        'am': _cfgInt('v3AssistMode', 0, 1),
        'ap': _cfgInt('v3AssistPlace', 0, 1),
        'ahz': bool(g_config.get('v3AssistHideZero', False)),
        'tsh': _cfgInt('v3TempoShow', 0, 3),
        'tmm': _cfgInt('v3TempoMode', 0, 2),
        'tp': _cfgInt('v3TempoPlace', 0, 1),
        'up': _cfgColor('v3AccentPlus'),
        'dn': _cfgColor('v3AccentMinus'),
        'zr': _cfgColor('v3AccentZero'),
        'big': _cfgColor('v3AccentBig'),
        'tm': _cfgColor('v3TextMain'),
        'tmu': _cfgColor('v3TextMuted'),
        'hThr': True,
        'h100': True,
    }


def _vhToV3Cfg(cfg=None):
    src = g_config if cfg is None else cfg
    return {
        'panelOpacity': src.get('panelOpacity', 1.0),
        'v3Density': src.get('vhDensity', 1),
        'v3MinWidth': 0,
        'v3Anchor': 0,
        'v3FrameStyle': src.get('vhFrameStyle', 0),
        'v3Radius': src.get('vhRadius', 5),
        'v3CornerColor': src.get('vhCornerColor', '#FFFFFF'),
        'v3CornerAlpha': src.get('vhCornerAlpha', 0.90),
        'v3BorderAlpha': src.get('vhBorderAlpha', 0.28),
        'v3BgColor': src.get('vhBgColor', '#0B1016'),
        'v3BgOpacity': src.get('vhBgOpacity', 0.48),
        'v3StarsPos': src.get('vhStarsPos', 0),
        'v3StarsStyle': src.get('vhStarsStyle', 0),
        'v3StarsDivider': src.get('vhStarsDivider', False),
        'v3StarsSize': src.get('vhStarsSize', 15),
        'v3StarsGap': src.get('vhStarsGap', 6),
        'v3StarsGlow': src.get('vhStarsGlow', True),
        'v3StarOnColor': src.get('vhStarOnColor', '#FFFFFF'),
        'v3StarOffColor': src.get('vhStarOffColor', '#9AA3AE'),
        'v3HeaderOrder': 0,
        'v3PctDecimals': src.get('vhPctDecimals', 1),
        'v3DeltaIcon': 3,
        'v3DeltaColorMode': 0,
        'v3BarStyle': src.get('vhBarStyle', 0),
        'v3BarScale': src.get('vhBarScale', 0),
        'v3BarHeight': src.get('vhBarHeight', 4),
        'v3BarTrackHeight': src.get('vhBarTrackHeight', 2),
        'v3BarCustomText': src.get('vhBarCustomText', u'KIBERSPORT'),
        'v3BarTextSize': src.get('vhBarTextSize', 15),
        'v3BarEndTicks': src.get('vhBarEndTicks', True),
        'v3BarCursor': src.get('vhBarCursor', True),
        'v3BarMarks': src.get('vhBarMarks', False),
        'v3BarColorMode': 0,
        'v3BarCustomColor': src.get('vhBarColor', '#A7D080'),
        'v3ShowDamage': src.get('vhShowEma', True),
        'v3DamageLabel': 0,
        'v3DamageCustomLabel': u'Ср. урон',
        'v3ThousandsSep': src.get('vhThousandsSep', 1),
        'v3DamageDynColor': True,
        'v3AssistShow': 3,
        'v3AssistMode': 0,
        'v3AssistPlace': 0,
        'v3AssistHideZero': False,
        'v3TempoShow': 3,
        'v3TempoMode': 0,
        'v3TempoPlace': 0,
        'v3AccentPlus': src.get('vhBarColor', '#A7D080'),
        'v3AccentMinus': '#E57373',
        'v3AccentZero': '#9AA3AE',
        'v3AccentBig': '#B07CFF',
        'v3TextMain': src.get('vhTextMain', '#FFFFFF'),
        'v3TextMuted': src.get('vhTextMuted', '#B8BDC4'),
        'vhShowThresholds': src.get('vhShowThresholds', True),
        'vhShow100': True,
    }


def _vhUiPayload():
    return {
        'den': _cfgInt('vhDensity', 0, 2),
        'minW': 0,
        'anc': 0,
        'fs': _cfgInt('vhFrameStyle', 0, 3),
        'rad': _cfgInt('vhRadius', 0, 14),
        'cc': _cfgColor('vhCornerColor'),
        'ca': round(_cfgNumber('vhCornerAlpha', 0.0, 1.0), 3),
        'ba': round(_cfgNumber('vhBorderAlpha', 0.0, 1.0), 3),
        'bgc': _cfgColor('vhBgColor'),
        'bgo': round(_cfgNumber('vhBgOpacity', 0.0, 1.0), 3),
        'sp': _cfgInt('vhStarsPos', 0, 5),
        'ss': _cfgInt('vhStarsStyle', 0, 2),
        'sd': bool(g_config.get('vhStarsDivider', False)),
        'sz': _cfgInt('vhStarsSize', 10, 22),
        'sg': _cfgInt('vhStarsGap', 2, 14),
        'sgl': bool(g_config.get('vhStarsGlow', True)),
        'son': _cfgColor('vhStarOnColor'),
        'sof': _cfgColor('vhStarOffColor'),
        'ho': 0,
        'dec': _cfgInt('vhPctDecimals', 0, 1),
        'di': 3,
        'dc': 0,
        'bs': _cfgInt('vhBarStyle', 0, 4),
        'bsc': _cfgInt('vhBarScale', 0, 1),
        'bh': _cfgInt('vhBarHeight', 2, 10),
        'bth': _cfgInt('vhBarTrackHeight', 1, 10),
        'bt': _cfgStr('vhBarCustomText', u'KIBERSPORT', 24) or u'KIBERSPORT',
        'bts': _cfgInt('vhBarTextSize', 10, 26),
        'bet': bool(g_config.get('vhBarEndTicks', True)),
        'bcur': bool(g_config.get('vhBarCursor', True)),
        'bmk': bool(g_config.get('vhBarMarks', False)),
        'bcm': 0,
        'bcc': _cfgColor('vhBarColor'),
        'dmgOn': bool(g_config.get('vhShowEma', True)),
        'dl': 0,
        'dlc': u'Ср. урон',
        'sep': _cfgInt('vhThousandsSep', 0, 2),
        'ddyn': True,
        'ash': 3,
        'am': 0,
        'ap': 0,
        'ahz': False,
        'tsh': 3,
        'tmm': 0,
        'tp': 0,
        'up': _cfgColor('vhBarColor'),
        'dn': '#E57373',
        'zr': '#9AA3AE',
        'big': '#B07CFF',
        'tm': _cfgColor('vhTextMain'),
        'tmu': _cfgColor('vhTextMuted'),
        'hThr': bool(g_config.get('vhShowThresholds', True)),
        'h100': True,
    }


def _uiScale():
    return _cfgNumber('uiScale', 0.5, 2.5)


def _vhScale():
    return _cfgNumber('vhScale', 0.5, 2.5)


def _uiPayload():
    """Настройки внешнего вида для панели (JS)."""
    preset = _cfgInt('battlePreset', 0, 1)
    return {
        's': round(_uiScale(), 3),
        'hs': round(_vhScale(), 3),
        'preset': preset,
        'bg': round(_cfgNumber('bgOpacity', 0.0, 1.0), 3),
        'alpha': round(_cfgNumber('panelOpacity', 0.0, 1.0), 3),
        'onlyPct': bool(preset == 1 or g_config.get('battlePercentOnly', False)),
        'up': _cfgColor('colorPlus'),
        'dn': _cfgColor('colorMinus'),
        'zr': _cfgColor('colorZero'),
        'bUp': _cfgColor('barColorPlus'),
        'bDn': _cfgColor('barColorMinus'),
        'bZr': _cfgColor('barColorZero'),
        'bH': _cfgColor('barColorHangar'),
        'bSign': bool(g_config.get('barBySign', True)),
        'bStd': _cfgColor('barColorStandard'),
        'trk': round(_cfgNumber('trackOpacity', 0.0, 1.0), 3),
        'tick': _cfgColor('tickColor'),
        'pct': _cfgColor('pctColor'),
        'pctSign': bool(g_config.get('pctFollowsSign', False)),
        'glow': bool(g_config.get('glow', True)),
        'band': round(_cfgNumber('zeroBand', 0.0, 5.0), 3),
        'big': _cfgColor('colorBig'),
        'bBig': _cfgColor('barColorBig'),
        'bigFrom': round(_cfgNumber('bigFrom', 0.0, 100.0), 3),
        'bigDmg': bool(g_config.get('bigByDamage', True)),
        'dmgSign': bool(g_config.get('dmgFollowsSign', True)),
        'dmg': _cfgColor('colorDmg'),
        'proj': _cfgColor('colorProj'),
        'v3': _v3UiPayload() if preset == 0 else None,
        'vh': _vhUiPayload(),
    }


def _loadCache():
    global g_cache
    g_cache = _loadJson(CACHE_PATH, {})
    if not isinstance(g_cache, dict):
        g_cache = {}
    g_cache.pop('__historyPending', None)


def _screen():
    try:
        w, h = GUI.screenResolution()[:2]
        return (float(w), float(h))
    except Exception:
        return (1920.0, 1080.0)


def _pxW(px):
    return px * 2.0 / _screen()[0]


def _pxH(px):
    return px * 2.0 / _screen()[1]


# ==========================================================================
# журнал (файл <WoT>/mods/configs/three_marks/three_marks.log + python.log)

_LOG_PATH = os.path.join(CONFIG_DIR, 'three_marks.log')
_LOG_LIMIT = 200 * 1024
_logSeen = set()


def _log(msg):
    try:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        line = '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
        print('[ThreeMarks] ' + str(msg))
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if os.path.isfile(_LOG_PATH) and os.path.getsize(_LOG_PATH) > _LOG_LIMIT:
            with open(_LOG_PATH, 'rb') as f:
                f.seek(-_LOG_LIMIT // 2, 2)
                tail = f.read()
            with open(_LOG_PATH, 'wb') as f:
                f.write(tail[tail.find('\n') + 1:])
        with open(_LOG_PATH, 'ab') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _logOnce(key, msg):
    if key not in _logSeen:
        _logSeen.add(key)
        _log(msg)


def _logError(where):
    """Исключение - в журнал (один раз на вид ошибки), а не в пустоту."""
    try:
        text = traceback.format_exc().strip().splitlines()
        _logOnce(('err', where, text[-1] if text else ''),
                 'ERROR in %s: %s' % (where, ' | '.join(text[-3:])))
    except Exception:
        pass


# ==========================================================================
# расчёт отметки: кривая урона WG, суточные кривые, прогноз
#
# Как это устроено на серверах WG (как работает MoE Pro, переписано заново):
#  * сервер хранит среднее урона целым числом; после каждого боя
#    avg' = round_half_up(avg + (урон_боя - avg) * 2/101);
#  * процент = среднее, прочитанное по кривой танка за текущие сутки:
#    восемь узлов (20/40/55/65/75/85/95/100 %), между ними прямые линии,
#    ниже первого узла - прямая из нуля; процент отбрасывается до сотых;
#  * кривая пересчитывается раз в сутки, а серверы переходят на новую
#    с задержкой (примерно 07-11 UTC), поэтому нужно знать, по какой кривой
#    считает сервер сейчас: по ней и строится прогноз.

_EMA_K = 2.0 / 101.0
_KNOTS = (20, 40, 55, 65, 75, 85, 95, 100)
_ANCHORS = (20, 30, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100)
_CURVE_TTL = 6 * 3600.0
_CURVE_RECHECK = 3600.0
_FETCH_RETRY = 120.0
_HISTORY_RETRY = 900.0
_HISTORY_DAYS = 40
_STALE_GAP = 0.15
_PCT_CELL = 0.01
_API_DAY_LAG = 2
_SERVER_HOUR = 9.0
_SERVER_LATE = 11.0
_SERVER_HOLD = 2 * 3600.0
_EPOCH_DAY = 719163  # datetime.date(1970, 1, 1).toordinal()


def _floorPct(value):
    """Процент так, как его пишет игра: отброшен до сотых, не округлён."""
    return math.floor(float(value) * 100.0 + 1e-6) / 100.0


def _nextAverage(avg, combined):
    """(целое среднее после боя, оно же до округления)."""
    avg = float(avg)
    projected = avg + (float(combined) - avg) * _EMA_K
    return (float(int(projected + 0.5)) if projected > 0.0 else 0.0,
            projected)


def _dayOf(ts):
    """Номер дня (date.toordinal) для времени UTC."""
    return _EPOCH_DAY + int(float(ts) // 86400)


def _utcDayText(ts=None):
    return time.strftime('%Y-%m-%d', time.gmtime(time.time() if ts is None else ts))


def _dayNumber(text):
    year, month, dom = [int(part) for part in str(text).split('-')]
    return datetime.date(year, month, dom).toordinal()


def _dayText(number):
    return datetime.date.fromordinal(int(number)).isoformat()


def _apiDay(updated):
    """Сутки, на которые API отдаёт кривую, по её updated_at (или None)."""
    try:
        updated = float(updated or 0)
    except (TypeError, ValueError):
        return None
    if updated <= 0.0:
        return None
    day = _dayOf(updated) + _API_DAY_LAG
    return day if abs(day - _dayOf(time.time())) <= 60 else None


def _serverNow():
    """Время по часам серверов (часы ПК могут спешить или отставать на часы)."""
    try:
        from helpers import time_utils
        return float(time_utils.getServerUTCTime())
    except Exception:
        return time.time()


def _servedOnKnots(served):
    """Все ли отданные API точки лежат на прямых между узлами (с отбрасыванием
    до целого)? Если WG сменит форму кривой, это станет заметно здесь."""
    for i in range(len(_KNOTS) - 1):
        p0, p1 = _KNOTS[i], _KNOTS[i + 1]
        d0, d1 = int(served[float(p0)]), int(served[float(p1)])
        for q in range(p0 + 1, p1):
            value = served.get(float(q))
            if value is not None and \
                    int(value) != d0 + (d1 - d0) * (q - p0) // (p1 - p0):
                return False
    return True


class _Curve(object):
    """Распределение урона танка: точки (процент, урон).

    exact=True - кривая читается строго по восьми узлам (так считает сервер);
    иначе точки используются как пришли. day - сутки, на которые кривая
    отдана API (если известно)."""
    __slots__ = ('points', 'exact', 'day')

    def __init__(self, raw, day=None):
        pts = []
        for key, value in raw.items():
            try:
                p, d = float(key), float(value)
            except (TypeError, ValueError):
                continue
            if 0.0 < p <= 100.0 and d > 0.0:
                pts.append((p, d))
        pts.sort()
        served = dict(pts)
        self.exact = False
        if all(float(k) in served for k in _KNOTS):
            knots = [(float(k), float(int(served[float(k)]))) for k in _KNOTS]
            rising = all(a[1] < b[1] for a, b in zip(knots, knots[1:]))
            if rising and _servedOnKnots(served):
                pts, self.exact = knots, True
            elif all(float(a) in served for a in _ANCHORS):
                pts = [(float(a), served[float(a)]) for a in _ANCHORS]
        clean = []
        for p, d in pts:
            if len(clean) == 1 and d == clean[0][1]:
                clean[0] = (p, d)
                continue
            if clean and d <= clean[-1][1]:
                continue
            clean.append((p, d))
        self.points = clean
        self.day = day

    def __nonzero__(self):
        return len(self.points) >= 2

    __bool__ = __nonzero__

    def damageOf(self, percent):
        pts = self.points
        if not pts:
            return 0.0
        if percent <= pts[0][0]:
            return pts[0][1] * (percent / pts[0][0]) if pts[0][0] > 0 else pts[0][1]
        for i in range(1, len(pts)):
            p0, d0 = pts[i - 1]
            p1, d1 = pts[i]
            if percent <= p1:
                return d0 + (percent - p0) * (d1 - d0) / (p1 - p0)
        return pts[-1][1]

    def percentOf(self, damage):
        pts = self.points
        if not pts:
            return 0.0
        if damage <= pts[0][1]:
            return pts[0][0] * (damage / pts[0][1]) if pts[0][1] > 0 else 0.0
        for i in range(1, len(pts)):
            p0, d0 = pts[i - 1]
            p1, d1 = pts[i]
            if damage <= d1:
                return p0 + (damage - d0) * (p1 - p0) / (d1 - d0)
        return 100.0

    def cell(self, damage):
        """Процент в сотых (целое число), отброшенный как в игре. На узлах и
        при целом уроне - целочисленная арифметика, без ошибок float
        (85.00 не станет 84.99)."""
        if not self.exact or damage != int(damage):
            return int(math.floor(self.percentOf(damage) * 100.0 + 1e-6))
        damage = int(damage)
        pts = self.points
        p0, d0 = int(pts[0][0]), int(pts[0][1])
        if damage <= d0:
            return p0 * 100 * damage // d0 if damage > 0 else 0
        for i in range(1, len(pts)):
            p1, d1 = int(pts[i][0]), int(pts[i][1])
            if damage <= d1:
                return p0 * 100 + (damage - d0) * (p1 - p0) * 100 // (d1 - d0)
            p0, d0 = p1, d1
        return 10000

    def explains(self, damage, percent):
        """Мог ли сервер прочитать именно этот процент для этого среднего
        по этой кривой?"""
        shown = int(round(percent * 100.0))
        if self.exact:
            return self.cell(damage) == shown
        return abs(self.percentOf(damage) * 100.0 - (shown + 0.5)) <= 1.25

    def wholeDamage(self, percent):
        """Наименьшее целое среднее, дающее не меньше этого процента."""
        if percent > 0.0:
            return math.ceil(self.damageOf(percent) - 1e-6)
        return 0.0

    def thresholds(self):
        """Средний урон на 65 / 85 / 95 / 100 %."""
        return (self.damageOf(65.0), self.damageOf(85.0),
                self.damageOf(95.0), self.damageOf(100.0))


def _curveOfRow(values, day=None):
    if not isinstance(values, list) or len(values) != len(_ANCHORS):
        return None
    try:
        raw = dict((str(p), float(v)) for p, v in zip(_ANCHORS, values))
    except (TypeError, ValueError):
        return None
    if min(raw.values()) <= 0.0:
        return None
    curve = _Curve(raw, day)
    return curve if curve else None


# --------------------------------------------------------------------------
# кэш кривых и история по дням. Сеть - только в фоновых потоках; результат
# кладётся в очередь, а применяет её главный поток (_pump). Ни один фоновый
# поток не трогает ни BigWorld, ни g_cache.

_calcVersion = [0]
_live = {}            # key -> (curve, fetchedAt)
_pending = set()
_failed = {}
_empty = {}
_restamped = set()
_histPending = set()
_histFailed = {}
_dayCache = {}
_results = []
_resultsLock = threading.Lock()


def _entryOf(key):
    entry = g_cache.get(key)
    if not isinstance(entry, dict):
        entry = {}
        g_cache[key] = entry
    return entry


def _post(item):
    with _resultsLock:
        _results.append(item)


def _httpJson(url):
    request = urllib2.Request(url, headers={'User-Agent': 'ThreeMarks/%s' % MOD_VERSION})
    response = urllib2.urlopen(request, timeout=10)
    try:
        return json.loads(response.read())
    finally:
        response.close()


def _curveWorker(key, domain, appID):
    points, stamps, error = {}, set(), None
    try:
        for start in xrange(1, 101, 10):
            batch = '%2C'.join(str(p) for p in xrange(start, min(start + 10, 101)))
            payload = _httpJson(_WG_API_URL % (domain, appID, batch, key))
            if payload.get('status') != 'ok':
                raise ValueError((payload.get('error') or {}).get('message') or
                                 'status not ok')
            data = payload.get('data') or {}
            try:
                stamps.add(int(float(data.get('updated_at') or 0)))
            except (TypeError, ValueError):
                stamps.add(0)
            record = (data.get('distribution') or {}).get(key) or {}
            for percentile, damage in record.items():
                try:
                    points[str(int(percentile))] = int(round(float(damage)))
                except (TypeError, ValueError):
                    pass
        if len(stamps) > 1:
            raise ValueError('the curve changed while it was being read')
    except Exception as error_:
        error = '%s: %s' % (type(error_).__name__, error_)
    _post(('curve', key, points, stamps.pop() if len(stamps) == 1 else 0, error))


def _historyWorker(key, domain):
    rows, answered, error = {}, False, None
    try:
        url = _WG_HISTORY_URL % (domain, key, ','.join(str(p) for p in _ANCHORS))
        payload = _httpJson(url)
        answered = True
        if payload.get('status') != 'ok':
            raise ValueError((payload.get('error') or {}).get('message') or
                             'status not ok')
        for row in (payload.get('data') or {}).get('data') or []:
            try:
                day = str(row['date'])
                _dayNumber(day)
                marks = row.get('marks') or {}
                values = [int(round(float(marks[str(p)]))) for p in _ANCHORS]
            except Exception:
                continue
            if min(values) > 0:
                rows[day] = values
    except Exception as error_:
        error = '%s: %s' % (type(error_).__name__, error_)
    _post(('history', key, rows, answered, error))


def _requestCurve(key):
    if urllib2 is None or key in _pending:
        return
    wait = _FETCH_RETRY * 2 ** min(4, max(0, _empty.get(key, 0) - 1))
    if time.time() - _failed.get(key, 0.0) < wait:
        return
    appID = str(g_config.get('wgApiApplicationId', '') or '').strip()
    if not appID:
        _logOnce('noappid', 'wgApiApplicationId is empty in config.json - no curves can be loaded')
        return
    _pending.add(key)
    thread = threading.Thread(target=_curveWorker, args=(key, _apiDomain(), appID))
    thread.daemon = True
    thread.start()


def _ensureHistory(key):
    if urllib2 is None or not g_config.get('onlineHistory', True):
        return
    if key in _histPending or \
            time.time() - _histFailed.get(key, 0.0) < _HISTORY_RETRY:
        return
    if _entryOf(key).get('histFetched') == _utcDayText():
        return
    _histPending.add(key)
    thread = threading.Thread(target=_historyWorker, args=(key, _apiDomain()))
    thread.daemon = True
    thread.start()


def _snapshotCurve(entry, points, updated, now):
    """Каждую скачанную кривую запоминаем как строку суток: история растёт и
    без сайта-источника."""
    try:
        values = [int(points[str(p)]) for p in _ANCHORS]
    except (KeyError, TypeError, ValueError):
        return
    served = _apiDay(updated)
    day = _dayText(served) if served else _utcDayText(now)
    history = entry.get('curveHistory')
    if not isinstance(history, dict):
        history = {}
    if day not in history:
        history[day] = values
        entry['curveHistory'] = history


def _applyCurve(key, points, updated, error):
    _pending.discard(key)
    now = time.time()
    curve = _Curve(points, _apiDay(updated)) if points else None
    if error is not None or not curve:
        _failed[key] = now
        if error is None:
            _empty[key] = _empty.get(key, 0) + 1
        _logOnce(('curvefail', key, error),
                 'curve for tank %s not loaded: %s' % (key, error or 'no distribution in the answer'))
        return False
    entry = _entryOf(key)
    entry['curve'] = {'t': now, 'p': points}
    if updated:
        entry['curve']['u'] = updated
    _live[key] = (curve, now)
    _empty.pop(key, None)
    _snapshotCurve(entry, points, updated, now)
    _log('curve loaded for tank %s%s' % (
        key, '' if curve.exact else ' (NOT the eight-knot shape, read as served)'))
    return True


def _applyHistory(key, rows, answered, error):
    _histPending.discard(key)
    if not answered:
        _histFailed[key] = time.time()
        _logOnce(('histfail', key, error), 'history for tank %s unavailable: %s' % (key, error))
        return False
    entry = _entryOf(key)
    history = entry.get('curveHistory')
    if not isinstance(history, dict):
        history = {}
    history.update(rows)
    for day in sorted(history)[:-_HISTORY_DAYS]:
        del history[day]
    entry['curveHistory'] = history
    entry['histFetched'] = _utcDayText()
    if error is not None or not rows:
        _logOnce(('histempty', key), 'history for tank %s: no usable rows (%s)' % (key, error))
    else:
        _log('history loaded for tank %s (%d days)' % (key, len(rows)))
    return True


def _pump():
    """Только главный поток: принять то, что принесли фоновые потоки."""
    with _resultsLock:
        if not _results:
            return False
        items = list(_results)
        del _results[:]
    changed = False
    for item in items:
        try:
            if item[0] == 'curve':
                changed = _applyCurve(*item[1:]) or changed
            elif item[0] == 'history':
                changed = _applyHistory(*item[1:]) or changed
        except Exception:
            _logError('apply %s' % item[0])
    if changed:
        _calcVersion[0] += 1
        _saveJson(CACHE_PATH, g_cache)
    return changed


def _cachedCurve(key):
    got = _live.get(key)
    if got is not None:
        return got
    entry = g_cache.get(key)
    stored = entry.get('curve') if isinstance(entry, dict) else None
    if isinstance(stored, dict):
        curve = _Curve(stored.get('p') or {}, _apiDay(stored.get('u')))
        if curve:
            got = (curve, float(stored.get('t', 0) or 0))
            _live[key] = got
            return got
    return None


_histCurves = {}


def _historyCurve(key):
    """Запасной вариант без API WG (например, если не принят application_id):
    последняя строка суточной истории - она приходит с poliroid.me без ключа."""
    cached = _histCurves.get(key)
    if cached is not None and cached[0] == _calcVersion[0]:
        return cached[1]
    curve = None
    entry = g_cache.get(key)
    history = entry.get('curveHistory') if isinstance(entry, dict) else None
    if isinstance(history, dict):
        for day in sorted(history, reverse=True):
            try:
                curve = _curveOfRow(history[day], _dayNumber(day))
            except (ValueError, TypeError):
                curve = None
            if curve:
                break
    if len(_histCurves) > 64:
        _histCurves.clear()
    _histCurves[key] = (_calcVersion[0], curve)
    return curve


def _curveFor(intCD):
    """Новейшая кривая танка; устаревшую обновляет в фоне."""
    if not intCD:
        return None
    key = _vehKey(intCD)
    got = _cachedCurve(key)
    if got is None:
        _requestCurve(key)
        return _historyCurve(key)
    curve, fetchedAt = got
    now = time.time()
    age = now - fetchedAt
    unstamped = curve.day is None and key not in _restamped
    if unstamped:
        _restamped.add(key)
    if age > _CURVE_TTL or unstamped or \
            ((curve.day is None or curve.day < _dayOf(now)) and age > _CURVE_RECHECK):
        _requestCurve(key)
    return curve


def _requestCalc(intCD):
    """Запустить подгрузку кривой и истории танка (если нужно)."""
    _curveFor(intCD)
    _ensureHistory(_vehKey(intCD))


def _dayCurve(key, number, newest=None):
    """Кривая танка за одни сутки: свежая, если она за эти сутки, иначе
    сохранённая строка истории; None - нет ни той ни другой."""
    if newest is not None and newest.day == number:
        return newest
    cached = _dayCache.get((key, number))
    if cached is not None and cached[0] == _calcVersion[0]:
        return cached[1]
    curve = None
    entry = g_cache.get(key)
    history = entry.get('curveHistory') if isinstance(entry, dict) else None
    if isinstance(history, dict):
        try:
            curve = _curveOfRow(history.get(_dayText(number)), number)
        except (ValueError, OverflowError):
            curve = None
    if len(_dayCache) > 64:
        _dayCache.clear()
    _dayCache[(key, number)] = (_calcVersion[0], curve)
    return curve


# --------------------------------------------------------------------------
# какие сутки сейчас у серверов

class _ServerEpoch(object):
    """Сутки, по кривой которых считают серверы. Часы - лишь первое
    приближение: каждое прочитанное досье его уточняет. Процент в нём
    записан в lastBattleTime по одной конкретной кривой; если из кривых тех
    суток и предыдущих ровно одна даёт этот процент для этого среднего -
    значит, серверы были на ней. Все танки переключаются разом, поэтому бой
    на одном танке подсказывает про другой."""

    def __init__(self):
        self.seenDay = 0
        self.seenAt = 0.0
        self._read = {}

    @staticmethod
    def byClock(now):
        return _dayOf(now - _SERVER_HOUR * 3600.0)

    @staticmethod
    def holds(when, now):
        """Действует ли ещё кривая, замеченная в момент when? Утром смена
        ожидается с минуты на минуту, поэтому лишь пару часов; серверы,
        застрявшие на вчерашней кривой после обычных часов смены, остаются
        на ней до конца дня."""
        if not (when > 0 and now - when > -600.0 and _dayOf(when) == _dayOf(now)):
            return False
        return now - when < _SERVER_HOLD or when % 86400.0 >= _SERVER_LATE * 3600.0

    def day(self, now=None):
        now = _serverNow() if now is None else now
        today = _dayOf(now)
        if self.seenDay >= today:
            return today
        if self.seenDay == today - 1 and self.holds(self.seenAt, now):
            return today - 1
        return self.byClock(now)

    def witness(self, key, avg, percent, when):
        """Досье: процент `percent` записан для среднего `avg` в момент when."""
        if not (avg > 0.0 and percent > 0.0 and when > self.seenAt):
            return
        got = _live.get(key)
        reading = (avg, percent, when, _calcVersion[0], got[1] if got else 0.0)
        if self._read.get(key) == reading:
            return
        self._read[key] = reading
        day = _dayOf(when)
        newest = got[0] if got else None
        fits = []
        for candidate in (day, day - 1):
            curve = _dayCurve(key, candidate, newest)
            if curve is None or not curve.exact:
                return
            if curve.explains(avg, percent):
                fits.append(candidate)
        if len(fits) == 1:
            self.seenDay, self.seenAt = fits[0], float(when)
            _log('servers on the curve of day %d at %d (tank %s)' % (fits[0], when, key))


_epoch = _ServerEpoch()


# --------------------------------------------------------------------------
# досье и запомненное состояние

class _Mark(object):
    """Что записал сервер в досье танка."""
    __slots__ = ('intCD', 'percent', 'avg', 'battles', 'marks', 'written')

    def __init__(self, intCD, percent, avg, battles, marks, written):
        self.intCD = intCD
        self.percent = float(percent)
        self.avg = float(avg)
        self.battles = int(battles or 0)
        self.marks = int(marks or 0)
        self.written = int(written or 0)


def _vehKey(intCD):
    return str(intCD)


def _apiDomain():
    realm = unicode(getattr(__import__('constants'), 'AUTH_REALM', u'EU')).upper()
    if 'NA' in realm:
        return 'com'
    if 'ASIA' in realm:
        return 'asia'
    return 'eu'


def _readDossier(intCD):
    """(процент, среднее урона, отметок, боёв, lastBattleTime) или None."""
    try:
        dossier = _itemsCache.items.getVehicleDossier(intCD)
    except Exception:
        _logError('getVehicleDossier')
        return None
    if dossier is None:
        return None
    percent = avg = None
    marks = battles = lastBattle = 0
    try:
        # объект достижения от самой игры: getDamageRating() уже делит на 100
        from dossiers2.ui.achievements import MARK_ON_GUN_RECORD
        achievement = None
        for getter in ('getTotalStats', 'getRandomStats'):
            try:
                achievement = getattr(dossier, getter)().getAchievement(MARK_ON_GUN_RECORD)
            except Exception:
                achievement = None
            if achievement is not None:
                break
        if achievement is not None:
            percent = float(achievement.getDamageRating() or 0.0)
            marks = int(achievement.getValue() or 0)
    except Exception:
        percent = None
    try:
        avg = float(dossier.getRecordValue('achievements', 'movingAvgDamage') or 0.0)
    except Exception:
        avg = None
    if percent is None or avg is None:
        try:
            ach = dossier.getDossierDescr()['achievements']
            if percent is None:
                percent = ach['damageRating'] / 100.0
            if avg is None:
                avg = float(ach['movingAvgDamage'])
            marks = max(marks, int(ach['marksOnGun']))
        except Exception:
            _logError('dossier record')
            return None
    try:
        marks = max(marks, int(dossier.getRecordValue('achievements', 'marksOnGun') or 0))
    except Exception:
        pass
    try:
        battles = int(dossier.getRandomStats().getBattlesCount() or 0)
    except Exception:
        battles = 0
    try:
        lastBattle = int(dossier.getGlobalStats().getLastBattleTime() or 0)
    except Exception:
        lastBattle = 0
    return (float(percent), float(avg), max(0, min(3, marks)), battles, lastBattle)


def _writtenAt(seen, percent, avg, battles, lastBattle):
    """Время сервера, когда записан процент из досье; 0 - неизвестно.

    lastBattleTime для этого не годится: сервер ставит его за любой бой, что
    идёт в общую статистику танка (Натиск, Укрепрайоны, Рейтинговые...), а
    отметку переписывает не во всех. Поэтому метка берётся, только если
    отметка сдвинулась вместе с ней; неизменное чтение хранит время, с
    которым было впервые замечено, а впервые увиденный танк его не имеет."""
    if not seen:
        return 0
    try:
        same = (abs(float(seen.get('p', 0.0) or 0.0) - percent) < 0.005 and
                float(seen.get('a', 0.0) or 0.0) == float(avg or 0.0) and
                int(seen.get('b', battles)) == int(battles))
        if same:
            return int(seen.get('w', 0) or 0)
        return int(lastBattle or 0)
    except (TypeError, ValueError):
        return 0


def _markFor(intCD):
    """Текущее состояние танка: живое досье, иначе запомненное. None - нечего
    показывать."""
    key = _vehKey(intCD)
    entry = g_cache.get(key)
    entry = entry if isinstance(entry, dict) else {}
    seen = entry.get('seen') if isinstance(entry.get('seen'), dict) else None
    data = _readDossier(intCD)
    if data is not None and data[1] > 0.0:
        percent, avg, marks, battles, lastBattle = data
        return _Mark(intCD, percent, avg, battles, marks,
                     _writtenAt(seen, percent, avg, battles, lastBattle))
    last = entry.get('last')
    try:
        if last and float(last[0]) > 0.0:
            return _Mark(intCD, float(last[1]), float(last[0]),
                         int(last[3]) if len(last) > 3 else 0,
                         int(last[2]) if len(last) > 2 else 0,
                         int(seen.get('w', 0) or 0) if seen else 0)
    except (TypeError, ValueError, IndexError):
        pass
    if data is not None:
        return _Mark(intCD, data[0], data[1], data[3], data[2], 0)
    return None


# --------------------------------------------------------------------------
# выбор кривой серверов и прогноз

def _serverCurve(mark, curve, now=None):
    """(кривая, сдвиг, привязана): по какой кривой сервер читает этот танк.

    curve - новейшая известная кривая; ответ - её версия за те сутки, на
    которых серверы сейчас. привязана=True - процент в досье лежит на этой
    кривой; сдвиг - поправка к её показаниям (0 для кривой по узлам, она
    точна). Если досье не ложится на кривую текущих суток, оно записано по
    другой: по одной из предыдущих (серверы были на ней и считаются там, пока
    это держится - см. holds()), иначе кривые сохранены недостаточно хорошо,
    и тогда кривая текущих суток сдвигается на досье, пока серверы не должны
    были переключиться с момента записи."""
    now = _serverNow() if now is None else now
    key = _vehKey(mark.intCD)
    pick, days = curve, [curve]
    if curve.day is not None:
        today = _dayOf(now)
        byDay = {}
        for day in range(today, today - 4, -1):
            found = _dayCurve(key, day, curve)
            if found:
                byDay[day] = found
        byDay.setdefault(curve.day, curve)
        want = _epoch.day(now)
        nearest = min(byDay, key=lambda day: (abs(day - want), -day))
        pick = byDay[nearest]
        days = [byDay[day] for day in sorted(byDay, reverse=True)]
    avg, percent = mark.avg, mark.percent
    if not (avg > 0.0 and percent > 0.0):
        return (pick, 0.0, False)

    def onto(c):
        if c.exact:
            return 0.0
        return percent + _PCT_CELL / 2.0 - c.percentOf(avg)

    if pick.explains(avg, percent):
        return (pick, onto(pick), True)
    last = mark.written
    fresh = _epoch.holds(last, now)
    later = _epoch.seenDay if _epoch.seenAt > last else 0
    for other in days:
        if other is not pick and other.explains(avg, percent):
            if fresh and later <= other.day:
                return (other, onto(other), True)
            return (pick, 0.0, False)
    if later and pick.exact and pick.day is not None and later >= pick.day:
        return (pick, 0.0, False)
    if fresh or (last > 0 and _epoch.byClock(last) == _epoch.byClock(now)):
        return (pick, percent + _PCT_CELL / 2.0 - pick.percentOf(avg), True)
    return (pick, 0.0, False)


def _currentPercent(mark, curve, now=None):
    """Где отметка на самом деле сейчас. Процент в досье меняется только
    после боя, а кривая пересчитывается раз в сутки, поэтому он устаревает;
    точное среднее сервера, прочитанное по актуальной кривой, - нет. Если они
    совпали, остаётся число из досье (оно точное и как в подсказке игры)."""
    if mark.avg > 0.0 and curve:
        server, _shift, anchored = _serverCurve(mark, curve, now)
        if not anchored:
            live = server.cell(mark.avg) / 100.0
            if abs(live - mark.percent) >= _STALE_GAP:
                return (max(0.0, min(100.0, live)), True)
    return (mark.percent, False)


def _forecast(mark, combined, curve, now=None):
    """(процент после этого боя, его отличие от текущего, среднее после
    боя целым, оно же до округления). Делает то же, что сервер: двигает целое
    среднее, читает его по своей кривой и отбрасывает до сотых."""
    base, _recomputed = _currentPercent(mark, curve, now)
    server, shift, _anchored = _serverCurve(mark, curve, now)
    if mark.avg > 0.0 or mark.percent <= 0.0:
        avg = float(mark.avg)
        whole, projected = _nextAverage(avg, combined)
        if not shift:
            after = server.cell(whole) / 100.0
            return (after, after - base, whole, projected)
        pct = server.percentOf(whole)
        first = server.points[0][1]
        if 0.0 < avg <= first and whole <= first:
            pct *= 1.0 + shift / server.percentOf(avg)
        else:
            pct += shift
    else:
        avg = server.wholeDamage(mark.percent)
        whole, projected = _nextAverage(avg, combined)
        if server.explains(avg, mark.percent):
            after = server.cell(whole) / 100.0
            return (after, after - base, whole, projected)
        pct = mark.percent + _PCT_CELL / 2.0 + server.percentOf(whole) - \
            server.percentOf(avg)
    after = _floorPct(max(0.0, min(100.0, pct)))
    return (after, after - base, whole, projected)


def _snapshotVehicle(intCD):
    """Запомнить досье танка; свериться с прогнозом прошлого боя."""
    data = _readDossier(intCD)
    if data is None:
        return
    percent, avg, marks, battles, lastBattle = data
    if avg <= 0 and percent <= 0:
        return
    key = _vehKey(intCD)
    entry = _entryOf(key)
    last = entry.get('last')
    seen = entry.get('seen') if isinstance(entry.get('seen'), dict) else None
    changed = (not last or abs(avg - float(last[0])) > 0.5 or
               abs(percent - float(last[1])) > 0.005 or
               (len(last) > 3 and int(battles) != int(last[3])))
    pending = entry.get('pendingForecast')
    if changed and isinstance(pending, dict):
        try:
            age = time.time() - float(pending.get('at', 0))
            moved = (abs(avg - float(pending.get('average', avg))) >= 0.5 or
                     abs(percent - float(pending.get('before', percent))) >= 0.005)
            if 0 <= age <= 21600 and moved:
                predicted = float(pending.get('predicted', percent))
                _log('FORECAST_RESULT tank=%s predicted=%.2f actual=%.2f error=%+.2f pp '
                     'average=%d->%d combined=%d curveDay=%s parts=%s' % (
                         key, predicted, percent, predicted - percent,
                         int(float(pending.get('average', 0))), int(round(avg)),
                         int(pending.get('combined', 0)), pending.get('curveDay'),
                         pending.get('parts')))
        except Exception:
            _logError('forecast result')
        entry.pop('pendingForecast', None)
    written = _writtenAt(seen, percent, avg, battles, lastBattle)
    record = {'p': percent, 'a': avg, 'b': int(battles), 'w': int(written)}
    entry['last'] = [avg, percent, marks, battles]
    entry['seen'] = record
    if changed or seen != record:
        _saveJson(CACHE_PATH, g_cache)
    _epoch.witness(key, avg, percent, written)


# ==========================================================================
# комбинированный урон

class _DamageTracker(object):

    ASSIST_KEYS = ('radioAssist', 'trackAssist', 'stunAssist')

    def __init__(self, onChanged):
        self._onChanged = onChanged
        self.sDamage = 0
        self.sAssists = dict((k, 0) for k in self.ASSIST_KEYS)
        self._summarySeen = False
        self._allies = 0
        self._playerVehicleID = None
        self._arena = None
        self._arenaDP = None
        self._healthSubscribed = False
        self.cDamage = 0
        self.cAssist = 0
        self.cStun = 0
        self._subscribed = False
        self._feedback = None
        self._feedbackActive = False
        self._feedbackKinds = {}
        self._assistKinds = {}

    def start(self):
        try:
            from BattleFeedbackCommon import BATTLE_EVENT_TYPE
            from gui.battle_control.battle_constants import FEEDBACK_EVENT_ID
            feedback = getattr(_sessionProvider.shared, 'feedback', None)
            if feedback is not None:
                self._feedbackKinds = {
                    FEEDBACK_EVENT_ID.PLAYER_DAMAGED_HP_ENEMY: 'damage',
                    FEEDBACK_EVENT_ID.PLAYER_ASSIST_TO_KILL_ENEMY: None,
                    FEEDBACK_EVENT_ID.PLAYER_ASSIST_TO_STUN_ENEMY: 'stun',
                }
                self._assistKinds = {
                    BATTLE_EVENT_TYPE.RADIO_ASSIST: 'radioAssist',
                    BATTLE_EVENT_TYPE.TRACK_ASSIST: 'trackAssist',
                }
                self._feedback = feedback
                feedback.onPlayerFeedbackReceived += self._onFeedback
                feedback.onPlayerSummaryFeedbackReceived += \
                    self._onFeedbackSummary
                self._feedbackActive = True
                cached = feedback.getCachedEvent(
                    FEEDBACK_EVENT_ID.DAMAGE_LOG_SUMMARY)
                if cached is not None:
                    self._onFeedbackSummary(cached)
        except Exception:
            self._feedback = None
            self._feedbackActive = False
        try:
            ctrl = _sessionProvider.shared.personalEfficiencyCtrl
            if ctrl is not None:
                ctrl.onTotalEfficiencyUpdated += self._onEfficiencyUpdated
                self._subscribed = True
        except Exception:
            pass
        try:
            player = BigWorld.player()
            self._playerVehicleID = getattr(player, 'playerVehicleID', None)
            self._arena = getattr(player, 'arena', None)
            self._arenaDP = _sessionProvider.getArenaDP()
            if self._arena is not None:
                self._arena.onVehicleHealthChanged += self._onAllyDamage
                self._healthSubscribed = True
        except Exception:
            pass
        self._refreshTotals()

    def stop(self):
        if self._feedback is not None:
            try:
                self._feedback.onPlayerFeedbackReceived -= self._onFeedback
                self._feedback.onPlayerSummaryFeedbackReceived -= \
                    self._onFeedbackSummary
            except Exception:
                pass
        self._feedback = None
        self._feedbackActive = False
        try:
            ctrl = _sessionProvider.shared.personalEfficiencyCtrl
            if ctrl is not None and self._subscribed:
                ctrl.onTotalEfficiencyUpdated -= self._onEfficiencyUpdated
        except Exception:
            pass
        self._subscribed = False
        try:
            if self._arena is not None and self._healthSubscribed:
                self._arena.onVehicleHealthChanged -= self._onAllyDamage
        except Exception:
            pass
        self._healthSubscribed = False
        self._arena = None

    def _onAllyDamage(self, vehicleID, attackerID, damage, *args):
        try:
            if not damage or damage <= 0 or attackerID != self._playerVehicleID:
                return
            if vehicleID == self._playerVehicleID or self._arenaDP is None:
                return
            if not self._arenaDP.isAlly(vehicleID):
                return
            self._allies += int(damage)
            self._onChanged()
        except Exception:
            pass

    def onSummary(self, summary):
        if not isinstance(summary, dict):
            return
        try:
            self.sDamage = max(self.sDamage, int(summary.get('damage') or 0))
            for k in self.ASSIST_KEYS:
                self.sAssists[k] = max(self.sAssists[k],
                                       int(summary.get(k) or 0))
            self._summarySeen = True
            self._onChanged()
        except Exception:
            pass

    def _onFeedback(self, events):
        try:
            changed = False
            for event in events:
                kind = event.getType()
                if kind not in self._feedbackKinds:
                    continue
                name = self._feedbackKinds[kind]
                if name is None:
                    name = self._assistKinds.get(event.getBattleEventType())
                extra = event.getExtra()
                amount = int(extra.getDamage()) if extra is not None else 0
                if name is not None and amount > 0:
                    if name == 'damage':
                        self.sDamage += amount
                    elif name == 'stun':
                        self.sAssists['stunAssist'] += amount
                    else:
                        self.sAssists[name] += amount
                    changed = True
            if changed:
                self._onChanged()
        except Exception:
            pass

    def _onFeedbackSummary(self, event):
        try:
            self.sDamage = int(event.getTotalDamage())
            spotting = getattr(
                event, '_BattleSummaryFeedbackEvent__radioAssistDamage', None)
            tracking = getattr(
                event, '_BattleSummaryFeedbackEvent__trackAssistDamage', None)
            if spotting is None or tracking is None:
                spotting, tracking = event.getTotalAssistDamage(), 0
            self.sAssists['radioAssist'] = int(spotting)
            self.sAssists['trackAssist'] = int(tracking)
            self.sAssists['stunAssist'] = int(event.getTotalStunDamage())
            self._summarySeen = True
            self._onChanged()
        except Exception:
            pass

    def _onEfficiencyUpdated(self, *args, **kwargs):
        self._refreshTotals()
        self._onChanged()

    def _refreshTotals(self):
        try:
            from gui.battle_control.battle_constants import PERSONAL_EFFICIENCY_TYPE as PET
            ctrl = _sessionProvider.shared.personalEfficiencyCtrl
            if ctrl is None:
                return
            self.cDamage = max(0, int(ctrl.getTotalEfficiency(PET.DAMAGE)))
            self.cAssist = max(0, int(ctrl.getTotalEfficiency(PET.ASSIST_DAMAGE)))
            if hasattr(PET, 'STUN'):
                self.cStun = max(0, int(ctrl.getTotalEfficiency(PET.STUN)))
        except Exception:
            pass

    def parts(self):
        """Из чего сложен урон (для журнала)."""
        return {'damage': self.sDamage, 'radio': self.sAssists['radioAssist'],
                'track': self.sAssists['trackAssist'],
                'stun': self.sAssists['stunAssist'], 'allies': self._allies,
                'effDamage': self.cDamage, 'effAssist': self.cAssist,
                'effStun': self.cStun,
                'src': 'feedback' if (self._feedbackActive or self._summarySeen)
                else 'efficiency'}

    def combined(self):
        if self._feedbackActive or self._summarySeen:
            return max(0, self.sDamage + max(self.sAssists.values()) -
                       self._allies)
        return max(0, self.cDamage + max(self.cAssist, self.cStun) -
                   self._allies)


def _panelInButton(panel, px, py):
    """Попадает ли точка (клип-координаты) в кнопку свернуть/развернуть."""
    try:
        ui = getattr(panel, 'ui', 1.0)
        if panel.mode == 'h':
            visW = panel.wPx - 24.0 * ui
            bx1, bx2 = visW - 22.0 * ui, visW - 2.0 * ui
            by1, by2 = 2.0 * ui, 22.0 * ui
        else:
            bx1, bx2 = 2.0 * ui, 22.0 * ui
            by1, by2 = 2.0 * ui, 22.0 * ui
        left = panel.x + _pxW(12.0 * ui)
        top = panel.y - _pxH(12.0 * ui)
        return (left + _pxW(bx1) <= px <= left + _pxW(bx2) and
                top - _pxH(by2) <= py <= top - _pxH(by1))
    except Exception:
        return False


# ==========================================================================
# настройки внешнего вида прямо в игре (экран в панели ангара)
#
# Окно панели не получает событий мыши от Gameface (как и кнопка -/+, клики
# читаются опросом курсора), поэтому экран настроек устроен так: Python
# знает раскладку и обрабатывает нажатия, а JS лишь рисует список элементов,
# который Python присылает в payload ('set').

import colorsys

_SET_H = 500.0
_SET_LABEL_W = {'title': 69, 'plus': 36, 'minus': 42, 'zero': 34, 'hangar': 39, 'pct': 39, 'size': 48, 'bg': 28, 'glow': 61, 'sign': 97, 'reset': 40, 'done': 45, 'dmg': 91, 'big': 41, 'barsign': 113, 'std': 44, 'spot': 44, 'track': 61}
_SETTINGS_OPEN = [False]
_GEAR = (114.0, 4.0, 134.0, 24.0)        # кнопка настроек, координаты панели
_SWATCHES = (
    '#86EF6A', '#4FD8FF', '#3C8DFF', '#B07CFF', '#FF6FD8',
    '#FF6060', '#FF9A3C', '#FFD23C', '#C8FF3C', '#2FE0A0',
    '#FFFFFF', '#EAEAEA', '#CFCFCF', '#A8A8A8', '#808080',
    '#5A5A5A', '#FF3030', '#00D060', '#00A0FF', '#FFB000',
)
_APPEARANCE_KEYS = ('uiScale', 'bgOpacity', 'colorPlus', 'colorMinus',
                    'colorZero', 'colorBig', 'barColorPlus', 'barColorMinus',
                    'barColorZero', 'barColorBig', 'barColorHangar',
                    'barBySign', 'barColorStandard', 'showSpot', 'showTrack', 'bigByDamage',
                    'bigDamageFactor', 'bigBasePercent',
                    'trackOpacity', 'tickColor', 'pctColor', 'pctFollowsSign',
                    'glow', 'zeroBand', 'bigFrom', 'dmgFollowsSign',
                    'colorDmg', 'colorProj', 'panelOpacity',
                    'battlePercentOnly')
_HUE_STRIP = ('linear-gradient(90deg,#FF0000,#FFFF00,#00FF00,#00FFFF,'
              '#0000FF,#FF00FF,#FF0000)')
_SHADE_STRIP = ('linear-gradient(180deg,#FFFFFF,rgba(255,255,255,0) 50%,'
                'rgba(0,0,0,0) 50%,#000000)')


def _rgbOfHex(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _hexOfRgb(rgb):
    return '#%02X%02X%02X' % tuple(int(round(max(0.0, min(255.0, v)))) for v in rgb)


def _mixRgb(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _rgbCss(rgb):
    return 'rgb(%d,%d,%d)' % tuple(int(round(v)) for v in rgb)


def _clamp01(v):
    return max(0.0, min(1.0, v))


class _SettingsUI(object):
    """Экран настроек: что нарисовать и что делает каждый клик."""

    # что красит выбранная вкладка (плюс/минус/ноль - число, стрелку и полоску)
    TARGETS = (
        ('plus', ('colorPlus', 'barColorPlus')),
        ('minus', ('colorMinus', 'barColorMinus')),
        ('zero', ('colorZero', 'barColorZero')),
        ('big', ('colorBig', 'barColorBig')),
        ('hangar', ('barColorHangar',)),
        ('pct', ('pctColor',)),
        ('std', ('barColorStandard',)),
    )
    PICKER = (10.0, 188.0, 200.0, 56.0)      # x, y, w, h
    TRACK = {'size': (72.0, 288.0), 'bg': (72.0, 310.0),
             'alpha': (72.0, 332.0)}
    TRACK_W = 100.0
    HOLD_STEP = 0.05                          # не чаще 20 перерисовок в секунду

    def __init__(self):
        self.open = False
        self.target = 0
        self.pick = None
        self.active = None
        self.pressed = False
        self.gearPress = False
        self.changed = False
        self.wantClose = False
        self.dirty = False
        self.items = []
        self._hits = []
        self._held = None
        self._t = 0.0
        self.build()

    # ---- раскладка ---------------------------------------------------------

    def _color(self, key):
        return _cfgColor(key)

    def build(self):
        items, hits = [], []

        def box(x, y, w, h, bg=None, bd=None, r=0):
            it = {'t': 'b', 'x': x, 'y': y, 'w': w, 'h': h}
            if bg:
                it['bg'] = bg
            if bd:
                it['bd'] = bd
            if r:
                it['r'] = r
            items.append(it)

        def label(name, x, y, op=1.0):
            items.append({'t': 'i', 'n': name, 'x': x, 'y': y,
                          'w': _SET_LABEL_W[name], 'op': op})

        def hit(wid, x, y, w, h):
            hits.append((wid, x, y, x + w, y + h))

        label('title', 10, 7)
        # --- образец: как выглядят четыре состояния -------------------------
        track = 'rgba(226,235,244,%.3f)' % _cfgNumber('trackOpacity', 0.0, 1.0)
        rows = (('colorPlus', 'barColorPlus', '+1.23%', 0),
                ('colorMinus', 'barColorMinus', '-0.85%', 1),
                ('colorZero', 'barColorZero', '0.00%', None),
                ('colorBig', 'barColorBig', '+4.20%', 0))
        for i, (tKey, bKey, text, arrow) in enumerate(rows):
            y0 = 30 + i * 18
            if arrow is not None:
                items.append({'t': 'a', 'x': 12, 'y': y0 + 4, 'c': self._color(tKey),
                              'd': arrow})
            else:
                items.append({'t': 'a', 'x': -30, 'y': -30, 'c': '#000000', 'd': 0})
            items.append({'t': 'x', 'x': 28, 'y': y0 + 1, 's': text,
                          'c': self._color(tKey)})
            box(96, y0 + 5, 114, 8, track, None, 2)
            base = _rgbOfHex(self._color(
                bKey if g_config.get('barBySign', True) else 'barColorStandard'))
            box(96, y0 + 5, 71, 8,
                'linear-gradient(90deg,%s,%s)' % (
                    _rgbCss(_mixRgb(base, (0, 0, 0), 0.42)), _rgbCss(base)),
                None, 2)
        # --- что красим (2 ряда по 3) ---------------------------------------
        names = ('plus', 'minus', 'zero', 'big', 'hangar', 'pct', 'std')
        keys = ('colorPlus', 'colorMinus', 'colorZero', 'colorBig',
                'barColorHangar', 'pctColor', 'barColorStandard')
        for i, name in enumerate(names):
            x = 6 + (i % 3) * 70
            y = 108 + (i // 3) * 26
            on = (i == self.target)
            box(x, y, 66, 22, 'rgba(255,255,255,%s)' % ('0.14' if on else '0.04'),
                'rgba(244,244,244,0.95)' if on else 'rgba(255,255,255,0.14)', 3)
            label(name, x + (66 - _SET_LABEL_W[name]) // 2, y + 1, 1.0 if on else 0.6)
            box(x + 4, y + 19, 58, 2, self._color(keys[i]))
            hit('chip:%d' % i, x, y, 66, 22)
        # --- цветовой круг (оттенок x яркость) и палитра ----------------------
        px, py, pw, ph = self.PICKER
        box(px, py, pw, ph, _HUE_STRIP, 'rgba(255,255,255,0.18)', 3)
        box(px, py, pw, ph, _SHADE_STRIP, None, 3)
        if self.pick is not None:      # метка всегда есть в списке: число элементов постоянно
            box(self.pick[0] - 4, self.pick[1] - 4, 8, 8, None, '#FFFFFF', 4)
        else:
            box(-20, -20, 0, 0)
        hit('picker', px, py, pw, ph)
        for k, color in enumerate(_SWATCHES):
            x = 11 + (k % 10) * 20
            y = 250 + (k // 10) * 17
            box(x, y, 17, 14, color, 'rgba(255,255,255,0.28)', 2)
            hit('sw:%d' % k, x, y, 17, 14)
        # --- ползунки -------------------------------------------------------
        for name, labelName, key, lo, span in (
                ('size', 'size', 'uiScale', 0.5, 2.0),
                ('bg', 'bg', 'bgOpacity', 0.0, 1.0),
                ('alpha', None, 'panelOpacity', 0.0, 1.0)):
            tx, ty = self.TRACK[name]
            value = _cfgNumber(key, lo, lo + span)
            t = _clamp01((value - lo) / span)
            if labelName is None:
                items.append({'t': 'x', 'x': 10, 'y': ty, 'w': 58,
                              'h': 17, 's': u'Панель', 'c': '#EAEAEA'})
            else:
                label(labelName, 10, ty)
            box(tx, ty + 6, self.TRACK_W, 6, 'rgba(255,255,255,0.16)', None, 3)
            box(tx, ty + 6, t * self.TRACK_W, 6, '#B8C4D0', None, 3)
            box(tx + t * self.TRACK_W - 3, ty + 2, 6, 14, '#F4F4F4', None, 2)
            items.append({'t': 'n', 'x': 180, 'y': ty, 'c': 'white',
                          's': '%d%%' % int(round(value * 100))})
            hit(name, tx - 4, ty, self.TRACK_W + 8, 18)
        # --- переключатели --------------------------------------------------
        for x, y, key, labelName, wid, width in (
                (10, 356, 'glow', 'glow', 'tog:glow', 82),
                (96, 356, 'pctFollowsSign', 'sign', 'tog:sign', 120),
                (10, 378, 'dmgFollowsSign', 'dmg', 'tog:dmg', 120),
                (10, 400, 'barBySign', 'barsign', 'tog:bar', 140),
                (10, 422, 'showSpot', 'spot', 'tog:spot', 90),
                (112, 422, 'showTrack', 'track', 'tog:track', 100)):
            on = bool(g_config.get(key, DEFAULT_CONFIG.get(key)))
            box(x, y + 2, 12, 12, 'rgba(255,255,255,0.06)', 'rgba(244,244,244,0.8)', 2)
            if on:
                box(x + 3, y + 5, 6, 6, '#F4F4F4', None, 1)
            else:
                box(-20, -20, 0, 0)
            label(labelName, x + 17, y - 1)
            hit(wid, x, y, width, 18)
        # --- два режима боевой панели ---------------------------------------
        onlyPct = bool(g_config.get('battlePercentOnly', True))
        box(10, 444, 200, 20,
            'rgba(134,239,106,0.12)' if onlyPct else 'rgba(255,255,255,0.04)',
            'rgba(134,239,106,0.55)' if onlyPct else 'rgba(255,255,255,0.18)', 3)
        items.append({'t': 'x', 'x': 16, 'y': 445, 'w': 188, 'h': 18,
                      's': u'Режим 2: % + суммарный урон' if onlyPct
                           else u'Режим 1: полная панель',
                      'c': '#EAEAEA'})
        hit('tog:panel', 10, 444, 200, 20)
        # --- кнопки ---------------------------------------------------------
        for x, name in ((10, 'reset'), (112, 'done')):
            box(x, 474, 98, 20, 'rgba(255,255,255,0.08)', 'rgba(255,255,255,0.28)', 3)
            label(name, x + (98 - _SET_LABEL_W[name]) // 2, 475)
            hit(name, x, 474, 98, 20)
        self.items = items
        self._hits = hits

    # ---- действия ---------------------------------------------------------

    def _hitTest(self, x, y):
        for wid, x1, y1, x2, y2 in reversed(self._hits):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return wid
        return None

    def _setColor(self, color):
        for key in self.TARGETS[self.target][1]:
            g_config[key] = color
        self.dirty = True

    def _drag(self, wid, x, y):
        if wid == 'picker':
            px, py, pw, ph = self.PICKER
            rx = _clamp01((x - px) / pw)
            ry = _clamp01((y - py) / ph)
            # верхние и нижние 5% - чистый белый и чёрный (в край пикселя не попасть)
            light = _clamp01((0.95 - ry) / 0.9)
            r, g, b = colorsys.hls_to_rgb(rx, light, 1.0)
            self._setColor(_hexOfRgb((r * 255, g * 255, b * 255)))
            self.pick = (px + rx * pw, py + ry * ph)
        elif wid in ('size', 'bg', 'alpha'):
            t = _clamp01((x - self.TRACK[wid][0]) / self.TRACK_W)
            if wid == 'size':
                g_config['uiScale'] = round((0.5 + 2.0 * t) * 20.0) / 20.0
            elif wid == 'bg':
                g_config['bgOpacity'] = round(t * 50.0) / 50.0
            else:
                g_config['panelOpacity'] = round(t * 50.0) / 50.0
            self.dirty = True

    def onDown(self, x, y):
        wid = self._hitTest(x, y)
        if wid is None:
            return
        if wid in ('picker', 'size', 'bg', 'alpha'):
            self.active = wid
            self._drag(wid, x, y)
        elif wid.startswith('chip:'):
            self.target = int(wid[5:])
            self.pick = None
        elif wid.startswith('sw:'):
            self._setColor(_SWATCHES[int(wid[3:])])
            self.pick = None
        elif wid == 'tog:glow':
            g_config['glow'] = not g_config.get('glow', True)
            self.dirty = True
        elif wid == 'tog:sign':
            g_config['pctFollowsSign'] = not g_config.get('pctFollowsSign', False)
            self.dirty = True
        elif wid == 'tog:dmg':
            g_config['dmgFollowsSign'] = not g_config.get('dmgFollowsSign', True)
            self.dirty = True
        elif wid == 'tog:bar':
            g_config['barBySign'] = not g_config.get('barBySign', True)
            self.dirty = True
        elif wid == 'tog:spot':
            g_config['showSpot'] = not g_config.get('showSpot', True)
            self.dirty = True
        elif wid == 'tog:track':
            g_config['showTrack'] = not g_config.get('showTrack', True)
            self.dirty = True
        elif wid == 'tog:panel':
            g_config['battlePercentOnly'] = not g_config.get('battlePercentOnly', True)
            self.dirty = True
        elif wid == 'reset':
            for key in _APPEARANCE_KEYS:
                g_config[key] = DEFAULT_CONFIG[key]
            self.pick = None
            self.dirty = True
        elif wid == 'done':
            self.wantClose = True
        self.build()
        self.changed = True

    def _sig(self):
        return (tuple(g_config.get(k) for k in _APPEARANCE_KEYS), self.pick, self.target)

    def onHold(self, x, y):
        """Тянем ползунок/круг: не чаще HOLD_STEP, последнее положение
        докручивается при отпускании."""
        if self.active is None:
            return
        now = time.time()
        self._held = (x, y)
        if now - self._t < self.HOLD_STEP:
            return
        self._t = now
        self._applyHeld()

    def _applyHeld(self):
        if self._held is None or self.active is None:
            return
        x, y = self._held
        self._held = None
        before = self._sig()
        self._drag(self.active, x, y)
        if self._sig() != before:
            self.build()
            self.changed = True

    def onUp(self, x, y):
        self._applyHeld()
        self.active = None
        self.save()

    def save(self):
        if self.dirty:
            self.dirty = False
            _saveJson(CONFIG_PATH, g_config)


def _panelLocal(panel, px, py):
    """Курсор (экранные -1..1) -> пиксели панели от её левого верхнего угла."""
    ui = getattr(panel, 'ui', 1.0) or 1.0
    return ((px - panel.x) / _pxW(1.0) / ui - 12.0,
            (panel.y - py) / _pxH(1.0) / ui - 12.0)


def _settingsPoll(owner, panel, st, px, py, down, ctrl):
    """True - клик достался настройкам, остальную обработку пропустить."""
    if ctrl or owner._drag is not None:
        return False
    lx, ly = _panelLocal(panel, px, py)
    if st.open:
        if down:
            if not st.pressed:
                st.pressed = True
                st.onDown(lx, ly)
            else:
                st.onHold(lx, ly)
        elif st.pressed:
            st.pressed = False
            st.onUp(lx, ly)
        if st.changed:
            st.changed = False
            owner._needRefresh = True
        if st.wantClose:
            st.wantClose = False
            panel.closeSettings()
            owner._needRefresh = True
        return True
    inGear = (panel.mode == 'h' and _GEAR[0] <= lx <= _GEAR[2] and
              _GEAR[1] <= ly <= _GEAR[3])
    if down:
        if inGear and not st.gearPress and not getattr(owner, '_btnPress', False):
            st.gearPress = True
        return st.gearPress
    if st.gearPress:
        st.gearPress = False
        if inGear:
            panel.openSettings()
            owner._needRefresh = True
        return True
    return False


# ==========================================================================
# Mod Menu (Aslain) / ModsSettingsAPI: настройки внешнего вида в общем окне
#
# Окно, цветовой выбор (HEX/RGB, палитра), ползунки и сброс - всё своё у меню,
# мод лишь описывает элементы и применяет пришедшие значения. Если меню не
# установлено, остаётся встроенная страница настроек (кнопка с цветными
# квадратами в ангаре). Значения из меню главнее config.json при запуске:
# меню само хранит настройки, а мы зеркалим их в config.json.

# Живой предпросмотр: пока окно Mod Menu открыто, панель в ангаре показывает боевой
# вид с примерными числами и текущими (ещё не применёнными) настройками.
_PREVIEW_ORDER = ('plus', 'minus', 'zero', 'big')
_PREVIEW = {'state': 'plus', 'uiState': 0, 'alt': False, 'hwAlt': False, 'target': 0, 'source': None, 'key': None, 'syncing': False}
_PREVIEW_SAMPLES = {
    'plus': dict(pct=43.28, delta=1.63, dmg=2266, proj=1480, big=False, glow=False, assist=(577, 120)),
    'minus': dict(pct=70.64, delta=-0.70, dmg=1120, proj=2320, big=False, glow=False, assist=(0, 0)),
    'zero': dict(pct=85.47, delta=0.0, dmg=2890, proj=2890, big=False, glow=False, assist=(12, 12)),
    'big': dict(pct=97.83, delta=4.52, dmg=6820, proj=3750, big=True, glow=True, assist=(210, 1830)),
}
_PREVIEW_SAMPLES_V3 = {
    'plus': dict(pct=43.28, delta=1.25, sDelta=1.85, dmg=1850, tHold=1480, tMark=2150, tPlus1=1480,
                 tNextPct=65, tNext=2150, t65=2150, t85=2890, t95=3450, t100=3920,
                 own=1100, spot=750, track=0, stun=0, marks=0, big=False, isSpg=False, hasRating=True),
    'minus': dict(pct=70.64, delta=-1.15, sDelta=-1.15, dmg=1420, tHold=2320, tMark=2890, tPlus1=2320,
                  tNextPct=85, tNext=2890, t65=2150, t85=2890, t95=3450, t100=3920,
                  own=900, spot=0, track=520, stun=0, marks=1, big=False, isSpg=False, hasRating=True),
    'zero': dict(pct=85.47, delta=0.0, sDelta=0.0, dmg=2890, tHold=2890, tMark=3450, tPlus1=2890,
                 tNextPct=95, tNext=3450, t65=2150, t85=2890, t95=3450, t100=3920,
                 own=2410, spot=480, track=480, stun=0, marks=2, big=False, isSpg=False, hasRating=True),
    'big': dict(pct=97.83, delta=4.65, sDelta=5.20, dmg=6820, tHold=3750, tMark=3920, tPlus1=3750,
                tNextPct=100, tNext=3920, t65=2150, t85=2890, t95=3450, t100=3920,
                own=4120, spot=1200, track=2700, stun=850, marks=3, big=True, isSpg=True, hasRating=True),
}

_PREVIEW_CONTAINER_W = 280
_PREVIEW_CONTAINER_H = 176
_SVG_FONT = u'WarheliosCondensedBold,Warhelios Condensed Bold,Arial,sans-serif'

_SVG_SPOT_RUNS = (
    (3, 2, 3, 2), (6, 2, 1, 1), (3, 3, 1, 1), (4, 3, 4, 2), (8, 3, 1, 1),
    (6, 4, 1, 1), (7, 4, 3, 2), (3, 5, 3, 2), (8, 5, 1, 1), (9, 5, 2, 2),
    (3, 6, 1, 1), (4, 6, 4, 2), (9, 6, 1, 1), (10, 6, 2, 2), (6, 7, 3, 2),
    (10, 7, 1, 1), (11, 7, 2, 2), (3, 8, 2, 2), (5, 8, 1, 1), (7, 8, 1, 1),
    (8, 8, 2, 2), (11, 8, 2, 2), (3, 9, 4, 2), (8, 9, 2, 2), (11, 9, 1, 1),
    (12, 9, 1, 2), (13, 9, 1, 1), (5, 10, 2, 2), (7, 10, 1, 1), (9, 10, 2, 2),
    (12, 10, 2, 2), (1, 11, 1, 1), (2, 11, 2, 2), (4, 11, 1, 1), (6, 11, 2, 2),
    (9, 11, 2, 2), (12, 11, 2, 2), (1, 12, 4, 2), (6, 12, 2, 2), (9, 12, 1, 1),
    (10, 12, 1, 2), (12, 12, 1, 1), (13, 12, 1, 2), (1, 13, 4, 2),
    (1, 14, 1, 1), (2, 14, 2, 2), (4, 14, 1, 1),
)
_SVG_TRACK_RUNS = (
    (6, 1, 2, 2), (8, 1, 1, 1), (10, 1, 1, 1), (6, 2, 6, 2), (4, 3, 1, 1),
    (7, 3, 6, 2), (3, 4, 3, 2), (7, 4, 1, 2), (8, 4, 1, 1), (10, 4, 1, 1),
    (11, 4, 3, 2), (3, 5, 1, 1), (4, 5, 5, 2), (11, 5, 1, 1), (12, 5, 2, 2),
    (0, 6, 2, 1), (4, 6, 1, 1), (5, 6, 5, 2), (11, 6, 3, 2), (0, 7, 3, 2),
    (3, 7, 1, 1), (4, 7, 2, 2), (7, 7, 1, 1), (8, 7, 7, 2), (0, 8, 1, 1),
    (1, 8, 5, 2), (6, 8, 1, 1), (8, 8, 1, 1), (9, 8, 2, 2), (12, 8, 1, 1),
    (13, 8, 2, 2), (1, 9, 1, 1), (2, 9, 5, 2), (7, 9, 1, 1), (8, 9, 3, 2),
    (13, 9, 1, 1), (5, 10, 7, 2), (6, 11, 2, 2), (9, 11, 1, 1), (10, 11, 2, 2),
    (5, 12, 1, 1), (6, 12, 2, 2), (10, 12, 1, 1), (5, 13, 1, 1), (6, 13, 3, 2),
    (7, 14, 2, 2),
)


def _previewStateFor(key):
    """Какой пример показать после изменения настройки key (None - оставить)."""
    low = str(key).lower()
    for word, state in (('minus', 'minus'), ('zero', 'zero'), ('big', 'big'), ('plus', 'plus')):
        if word in low:
            return state
    return None


def _svgEsc(text):
    if isinstance(text, unicode):
        u = text
    elif isinstance(text, str):
        u = unicode(text, 'utf-8', 'replace')
    else:
        u = unicode(text)
    return (u.replace(u'&', u'&amp;')
             .replace(u'<', u'&lt;')
             .replace(u'>', u'&gt;')
             .replace(u'"', u'&quot;'))


def _svgAdvance(text, size):
    """Approximate horizontal width in WarheliosCondensedBold for SVG placement."""
    if not isinstance(text, unicode):
        text = unicode(text, 'utf-8', 'replace') if isinstance(text, str) else unicode(text)
    w = 0.0
    s = float(size)
    for ch in text:
        if u'0' <= ch <= u'9':
            w += 0.50 * s
        elif ch == u' ':
            w += 0.24 * s
        elif ch == u'/':
            w += 0.38 * s
        elif ch in (u'.', u',', u':'):
            w += 0.26 * s
        elif ch in (u'+', u'-', u'\u2212'):
            w += 0.48 * s
        elif ch == u'%':
            w += 0.78 * s
        elif ch == u'\u2014':
            w += 0.62 * s
        else:
            w += 0.52 * s
    return w


def _svgText(x, y, text, fill, size, anchor=u'start', shadow=True, shadowOp=0.85, family=_SVG_FONT):
    """Cohtml-safe SVG text: explicit fill per <text>, no <tspan>, no CSS filter."""
    safe = _svgEsc(text)
    parts = []
    if shadow and shadowOp > 0.01:
        parts.append(
            u'<text x="%.1f" y="%.1f" text-anchor="%s" font-family="%s" '
            u'font-size="%d" font-weight="700" fill="#000000" '
            u'fill-opacity="%.2f">%s</text>' % (
                x, y + 1.0, anchor, family, int(size), shadowOp, safe))
    parts.append(
        u'<text x="%.1f" y="%.1f" text-anchor="%s" font-family="%s" '
        u'font-size="%d" font-weight="700" fill="%s">%s</text>' % (
            x, y, anchor, family, int(size), fill, safe))
    return u''.join(parts)


def _svgStar(cx, cy, r, fill, opacity=1.0):
    pts = []
    inner = r * 0.42
    for i in range(10):
        ang = -math.pi * 0.5 + i * math.pi * 0.2
        rad = r if (i % 2 == 0) else inner
        pts.append(u'%.2f,%.2f' % (cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return u'<polygon points="%s" fill="%s" fill-opacity="%.3f"/>' % (
        u' '.join(pts), fill, opacity)


def _svgArrow(x, y, fill, down=False):
    if down:
        pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x, y, x + 10.0, y, x + 5.0, y + 9.0)
    else:
        pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x + 5.0, y, x + 10.0, y + 9.0, x, y + 9.0)
    return u'<polygon points="%s" fill="%s"/>' % (pts, fill)


def _svgBitmapIcon(ox, oy, runs, opacity, color=u'#DCE2E8'):
    out = []
    for rx, ry, rw, tier in runs:
        op = opacity * (1.0 if tier == 2 else 0.45)
        out.append(
            u'<rect x="%.1f" y="%.1f" width="%d" height="1" fill="%s" '
            u'fill-opacity="%.2f"/>' % (ox + rx, oy + ry, rw, color, op))
    return u''.join(out)


def _v3FmtNum(n, sepMode):
    try:
        val = int(round(float(n)))
    except Exception:
        return unicode(n)
    neg = val < 0
    s = str(abs(val))
    if sepMode == 2:
        res = unicode(s)
    else:
        sep = u' ' if sepMode == 0 else u','
        parts = []
        while len(s) > 3:
            parts.append(unicode(s[-3:]))
            s = s[:-3]
        parts.append(unicode(s))
        res = sep.join(reversed(parts))
    return (u'-' + res) if neg else res


def _v3ResolveAssist(cfg, sample, alt=False):
    spot = max(0, int(sample.get('spot', 0) or 0))
    track = max(0, int(sample.get('track', 0) or 0))
    maxAst = max(spot, track)
    if maxAst <= 0:
        activeCh = None
    elif spot >= track:
        activeCh = 'spot'
    else:
        activeCh = 'track'

    showMode = _cfgInt('v3AssistShow', 0, 3, cfg)
    rawMode = _cfgInt('v3AssistMode', 0, 1, cfg)
    if showMode == 3 or (showMode == 1 and not alt) or (showMode == 2 and alt):
        return [], activeCh, maxAst, False

    if rawMode == 0:
        rows = [('spot', spot), ('track', track)]
    else:
        rows = [(activeCh or 'spot', maxAst)]

    if bool(cfg.get('v3AssistHideZero', False)):
        rows = [(ch, val) for ch, val in rows if val > 0]

    sep = _cfgInt('v3ThousandsSep', 0, 2, cfg)
    items = []
    for ch, val in rows:
        isAct = (ch == activeCh and val > 0)
        items.append({'ch': ch, 'val': val, 'active': isAct, 'text': _v3FmtNum(val, sep)})
    return items, activeCh, maxAst, False


def _v3ResolveTempo(cfg, sample, alt=False):
    showMode = _cfgInt('v3TempoShow', 0, 3, cfg)
    rawMode = _cfgInt('v3TempoMode', 0, 2, cfg)
    if showMode == 3 or (showMode == 1 and not alt) or (showMode == 2 and alt):
        return []

    pct = float(sample.get('pct', 0.0) or 0.0)
    tNextPct = int(sample.get('tNextPct', 0) or (
        65 if pct < 65.0 else (85 if pct < 85.0 else (95 if pct < 95.0 else 100))))
    tNext = max(0, int(sample.get('tNext', 0) or 0))
    t95 = max(0, int(sample.get('t95', 0) or 0))
    dmg = max(0, int(sample.get('dmg', 0) or 0))

    mode = rawMode
    if mode == 1:
        pairs = [(tNextPct, tNext)]
    elif mode == 2:
        pairs = [(95, t95)]
    else:
        if tNextPct == 95:
            pairs = [(95, t95 if t95 > 0 else tNext)]
        elif tNextPct < 95:
            pairs = [(tNextPct, tNext), (95, t95)]
        else:
            pairs = [(95, t95), (100, tNext)]

    sep = _cfgInt('v3ThousandsSep', 0, 2, cfg)
    items = []
    for pLbl, val in pairs:
        valStr = _v3FmtNum(val, sep) if val > 0 else u'\u2014'
        lbl = u'%d%%' % int(pLbl)
        text = u'%s %s' % (lbl, valStr)
        done = bool(val > 0 and dmg >= val)
        items.append({'pct': int(pLbl), 'val': val, 'done': done,
                      'lbl': lbl, 'valStr': valStr, 'text': text})
    return items


def _v3DeltaInfo(cfg, sample):
    hasRating = bool(sample.get('hasRating', True))
    pct = float(sample.get('pct', 0.0) or 0.0)
    dec = 0 if _cfgInt('v3PctDecimals', 0, 1, cfg) == 0 else 2
    if not hasRating:
        pctText = u'--%' if dec == 0 else u'--.--%'
        return pctText, u'', 'zero', _cfgColFrom(cfg, 'v3AccentZero'), False
    pctText = (u'%.*f%%' % (dec, pct))
    rawDelta = sample.get('delta')
    if rawDelta is None:
        return pctText, u'', 'zero', _cfgColFrom(cfg, 'v3AccentZero'), False
    val = float(rawDelta)
    zeroBand = _cfgNumFrom(cfg, 'zeroBand', 0.0, 5.0)
    bigByDmg = bool(cfg.get('bigByDamage', True))
    bigFrom = _cfgNumFrom(cfg, 'bigFrom', 0.0, 100.0)
    if bigByDmg and sample.get('big') and val >= 0.0:
        kind = 'big'
    elif (not bigByDmg) and bigFrom > 0.0 and val >= bigFrom:
        kind = 'big'
    elif abs(val) <= zeroBand:
        kind = 'zero'
    elif val < 0.0:
        kind = 'minus'
    else:
        kind = 'plus'
    accents = {
        'plus': _cfgColFrom(cfg, 'v3AccentPlus'),
        'minus': _cfgColFrom(cfg, 'v3AccentMinus'),
        'zero': _cfgColFrom(cfg, 'v3AccentZero'),
        'big': _cfgColFrom(cfg, 'v3AccentBig'),
    }
    deltaText = u'%+.*f%%' % (dec, val)
    showDelta = (_cfgInt('v3DeltaIcon', 0, 3, cfg) != 3)
    return pctText, deltaText, kind, accents[kind], showDelta


def _v3TargetInfo(cfg, sample):
    dmg = max(0, int(sample.get('dmg', 0) or 0))
    tgt = max(0, int(sample.get('tHold', 0) or 0))
    sep = _cfgInt('v3ThousandsSep', 0, 2, cfg)
    dmgStr = _v3FmtNum(dmg, sep)
    tgtStr = _v3FmtNum(tgt, sep) if tgt > 0 else u'\u2014'
    remVal = max(0, tgt - dmg) if tgt > 0 else 0
    remStr = _v3FmtNum(remVal, sep) if tgt > 0 else u'\u2014'
    return dmg, tgt, dmgStr, tgtStr, remStr


def _v3BarRatio(cfg, sample, dmg, tgt):
    pct = max(0.0, min(100.0, float(sample.get('pct', 0.0) or 0.0)))
    scale = _cfgInt('v3BarScale', 0, 1, cfg)
    if scale == 1:
        if pct < 65.0:
            return pct / 65.0
        if pct < 85.0:
            return (pct - 65.0) / 20.0
        if pct < 95.0:
            return (pct - 85.0) / 10.0
        return (pct - 95.0) / 5.0
    return pct / 100.0


def _v3ResolveHangarRows(cfg, sample):
    if not bool(sample.get('isHangar', False)):
        return []
    if bool(sample.get('mini', False)) or not bool(cfg.get('vhShowThresholds', True)):
        return []
    sep = _cfgInt('v3ThousandsSep', 0, 2, cfg)
    hasRating = bool(sample.get('hasRating', True))
    pct = float(sample.get('pct', 0.0) or 0.0)

    def mkCell(pLbl, key):
        val = max(0, int(sample.get(key, 0) or 0))
        valStr = _v3FmtNum(val, sep) if (hasRating and 0 < val < 30000) else u'\u2014'
        lbl = u'%d%%' % int(pLbl)
        done = bool(hasRating and val > 0 and pct >= float(pLbl))
        return {'pct': int(pLbl), 'val': val, 'done': done,
                'lbl': lbl, 'valStr': valStr, 'text': u'%s %s' % (lbl, valStr)}

    row1 = [mkCell(65, 't65'), mkCell(85, 't85')]
    row2 = [mkCell(95, 't95'), mkCell(100, 't100')]
    return [row1, row2]


def _v3Metrics(cfg, sample=None, alt=False):
    if sample is None:
        sample = _PREVIEW_SAMPLES_V3['plus']
    isHangar = bool(sample.get('isHangar', False))
    den = _cfgInt('v3Density', 0, 2, cfg)
    padX, padY, gapRow, pctSize, deltaSize, dmgSize, astSize = (
        (10, 7, 4, 24, 14, 13, 13),
        (12, 9, 6, 26, 15, 14, 14),
        (15, 11, 8, 28, 16, 15, 15),
    )[den]

    pctText, deltaText, kind, deltaAccent, showDelta = _v3DeltaInfo(cfg, sample)
    if isHangar:
        showDelta = False
    dmg, tgt, dmgStr, tgtStr, remStr = _v3TargetInfo(cfg, sample)
    if isHangar and not (bool(sample.get('hasRating', True)) and dmg > 0):
        dmgStr = u'\u2014'
    astItems, activeCh, maxAst, altExp = ([], None, 0, False) if isHangar else _v3ResolveAssist(cfg, sample, alt=alt)
    thrItems = [] if isHangar else _v3ResolveTempo(cfg, sample, alt=alt)
    hRows = _v3ResolveHangarRows(cfg, sample) if isHangar else []

    frameStyle = _cfgInt('v3FrameStyle', 0, 3, cfg)
    starsPos = _cfgInt('v3StarsPos', 0, 5, cfg)
    starsDiv = bool(cfg.get('v3StarsDivider', True))
    starSize = _cfgInt('v3StarsSize', 10, 22, cfg)
    starGap = _cfgInt('v3StarsGap', 2, 14, cfg)
    starsSpan = 3 * starSize + 2 * starGap

    deltaIcon = _cfgInt('v3DeltaIcon', 0, 3, cfg)
    deltaIconW = 12 if (showDelta and deltaIcon in (0, 1)) else 0
    pctW = _svgAdvance(pctText, pctSize)
    deltaW = (_svgAdvance(deltaText, deltaSize) + (deltaIconW + 5 if deltaIconW > 0 else 0)) if showDelta else 0
    inlineStarsW = (starsSpan + 10) if starsPos == 4 else 0
    headerMinW = pctW + deltaW + (14 if (showDelta and pctW > 0) else 0) + inlineStarsW

    showDmg = bool(cfg.get('v3ShowDamage', True))
    dmgLblMode = _cfgInt('v3DamageLabel', 0, 2, cfg)
    if isHangar:
        dmgLblText = u'\u0421\u0440. \u0443\u0440\u043e\u043d'
        dmgValStr = dmgStr
    else:
        if dmgLblMode == 0:
            dmgLblText = u'\u0421\u0443\u043c. \u0443\u0440\u043e\u043d'
        elif dmgLblMode == 1:
            dmgLblText = _cfgStr('v3DamageCustomLabel', u'\u0421\u0443\u043c. \u0443\u0440\u043e\u043d', 24, cfg)
        else:
            dmgLblText = u''
        dmgValStr = dmgStr + u' / ' + tgtStr
    lblW = _svgAdvance(dmgLblText, dmgSize) if dmgLblText else 0
    dmgRowMinW = (lblW + (12 if lblW > 0 else 0) + _svgAdvance(dmgValStr, dmgSize)) if showDmg else 0

    astIconSize = max(14, astSize + 1)
    astItemGap = 18 if len(astItems) <= 2 else 11
    astWidths = [astIconSize + 5 + _svgAdvance(it['text'], astSize) for it in astItems]
    astRowMinW = (sum(astWidths) + max(0, len(astWidths) - 1) * astItemGap) if astWidths else 0
    astInside = (_cfgInt('v3AssistPlace', 0, 1, cfg) == 0)

    thrSize = max(11, astSize - 1)
    thrIconSize = 0
    thrItemGap = 14
    thrWidths = [_svgAdvance(it['text'], thrSize) for it in thrItems]
    thrRowMinW = (sum(thrWidths) + max(0, len(thrWidths) - 1) * thrItemGap) if thrWidths else 0
    thrInside = (_cfgInt('v3TempoPlace', 0, 1, cfg) == 0)

    barMinW = (156, 178, 200)[den]
    barStyle = _cfgInt('v3BarStyle', 0, 4, cfg)
    barH = _cfgInt('v3BarHeight', 2, 10, cfg)
    trackH = _cfgInt('v3BarTrackHeight', 1, 10, cfg)
    barText = (_cfgStr('v3BarCustomText', u'KIBERSPORT', 24, cfg) or u'KIBERSPORT') if barStyle == 4 else u''
    barTextSize = _cfgInt('v3BarTextSize', 10, 26, cfg)
    barTextW = _svgAdvance(barText, barTextSize) if barStyle == 4 else 0.0
    barTextMinW = int(math.ceil(barTextW + 8.0)) if barStyle == 4 else 0

    hCol0W = 0
    hCol1W = 0
    hColGap = 16
    if hRows and len(hRows) >= 2:
        lblW0 = int(math.ceil(_svgAdvance(u'95%', thrSize))) + 5
        valW0 = int(math.ceil(max(_svgAdvance(hRows[0][0]['valStr'], thrSize),
                                  _svgAdvance(hRows[1][0]['valStr'], thrSize))))
        hCol0W = lblW0 + valW0
        lblW1 = int(math.ceil(_svgAdvance(u'100%', thrSize))) + 5
        valW1 = int(math.ceil(max(_svgAdvance(hRows[0][1]['valStr'], thrSize),
                                  _svgAdvance(hRows[1][1]['valStr'], thrSize))))
        hCol1W = lblW1 + valW1

    minWOpt = _cfgInt('v3MinWidth', 0, 360, cfg)
    minContentW = max(0, minWOpt - 2 * padX) if minWOpt > 0 else 0

    radius = _cfgInt('v3Radius', 0, 14, cfg)
    minBracket = max(12, radius + 8)
    starsMinFrameW = (starsSpan + 12 + 2 * minBracket) if (starsPos in (0, 1) and frameStyle != 3) else (starsSpan + 8 if starsPos in (0, 1) else 0)

    cw = int(math.ceil(max(barMinW, barTextMinW, headerMinW, dmgRowMinW,
                           minContentW, starsMinFrameW - 2 * padX)))

    framed = (frameStyle != 3)
    sideBorderStars = framed and (starsPos in (2, 3))
    sideOutsideStars = (not framed) and (starsPos in (2, 3))
    halfStar = int(math.ceil(starSize * 0.5))

    extraTop = max(0, halfStar + 5 - padY) if starsPos == 0 else 0
    extraBot = max(0, halfStar + 5 - padY) if starsPos == 1 else 0
    extraLeft = max(0, halfStar + 5 - padX) if (sideBorderStars and starsPos == 2) else 0
    extraRight = max(0, halfStar + 5 - padX) if (sideBorderStars and starsPos == 3) else 0

    y = padY + extraTop
    headerH = int(round(pctSize * 1.15))
    if starsPos == 4:
        headerH = max(headerH, starSize + 2)
    headerY = y
    y += headerH

    effBarH = max(barH, trackH)
    barY = None
    barBlockH = 0
    if barStyle == 4:
        y += gapRow
        barY = y
        barBlockH = int(round(barTextSize * 1.18))
        y += barBlockH
    elif barStyle != 3:
        y += gapRow
        barY = y
        barBlockH = max(effBarH, 10 if bool(cfg.get('v3BarCursor', True)) else effBarH,
                        8 if (barStyle in (0, 2) and bool(cfg.get('v3BarEndTicks', True))) else effBarH)
        y += barBlockH

    dmgY = None
    dmgH = int(round(dmgSize * 1.25))
    if showDmg:
        y += gapRow
        dmgY = y
        y += dmgH

    astY = None
    astH = max(astSize + 2, astIconSize)
    if astItems and astInside:
        y += gapRow + 1
        astY = y
        y += astH

    thrY = None
    thrH = thrSize + 2
    if thrItems and thrInside:
        y += (gapRow if astY is not None else gapRow + 1)
        thrY = y
        y += thrH

    hSepY = None
    hRow1Y = None
    hRow2Y = None
    if hRows:
        y += gapRow + 1
        hSepY = y
        y += gapRow
        hRow1Y = y
        y += thrH
        y += 2
        hRow2Y = y
        y += thrH

    fh = y + padY + extraBot
    if starsPos in (2, 3):
        minSideH = starsSpan + (2 * (minBracket + 8) if sideBorderStars else 8)
        if fh < minSideH:
            diff = minSideH - fh
            fh = minSideH
            # keep vertical balance inside frame
            deltaShift = diff // 2
            headerY += deltaShift
            if barY is not None:
                barY += deltaShift
            if dmgY is not None:
                dmgY += deltaShift
            if astY is not None:
                astY += deltaShift
            if thrY is not None:
                thrY += deltaShift
            if hSepY is not None:
                hSepY += deltaShift
            if hRow1Y is not None:
                hRow1Y += deltaShift
            if hRow2Y is not None:
                hRow2Y += deltaShift

    fw = cw + 2 * padX + extraLeft + extraRight
    margin = 6
    fx = margin
    fy = margin
    if starsPos == 0:
        fy = margin + halfStar
    if sideBorderStars and starsPos == 2:
        fx = margin + halfStar
    if sideOutsideStars and starsPos == 2:
        fx = margin + starSize + (14 if starsDiv else 8)

    cx = fx + padX + extraLeft

    starsCoords = []
    divLine = None
    if starsPos == 0:
        sx0 = fx + fw * 0.5 - starsSpan * 0.5 + starSize * 0.5
        for i in range(3):
            starsCoords.append((sx0 + i * (starSize + starGap), fy))
    elif starsPos == 1:
        sx0 = fx + fw * 0.5 - starsSpan * 0.5 + starSize * 0.5
        for i in range(3):
            starsCoords.append((sx0 + i * (starSize + starGap), fy + fh))
    elif starsPos == 2:
        sy0 = fy + fh * 0.5 - starsSpan * 0.5 + starSize * 0.5
        scx = fx if sideBorderStars else (margin + starSize * 0.5)
        for i in range(3):
            starsCoords.append((scx, sy0 + i * (starSize + starGap)))
        if sideOutsideStars and starsDiv:
            divLine = (fx - 7.0, fy + 3.0, fx - 7.0, fy + fh - 3.0)
    elif starsPos == 3:
        sy0 = fy + fh * 0.5 - starsSpan * 0.5 + starSize * 0.5
        scx = (fx + fw) if sideBorderStars else (fx + fw + (14 if starsDiv else 8) + starSize * 0.5)
        for i in range(3):
            starsCoords.append((scx, sy0 + i * (starSize + starGap)))
        if sideOutsideStars and starsDiv:
            divLine = (fx + fw + 7.0, fy + 3.0, fx + fw + 7.0, fy + fh - 3.0)

    rightExtend = 0
    if sideBorderStars and starsPos == 3:
        rightExtend = halfStar
    elif sideOutsideStars and starsPos == 3:
        rightExtend = (14 if starsDiv else 8) + starSize

    winW = int(math.ceil(fx + fw + rightExtend + margin))

    botExtend = halfStar if starsPos == 1 else 0
    curBelowY = fy + fh + (halfStar + 6 if starsPos == 1 else 6)
    astBelowY = None
    thrBelowY = None
    if astItems and not astInside:
        astBelowY = curBelowY
        curBelowY += astH + 4
    if thrItems and not thrInside:
        thrBelowY = curBelowY
        curBelowY += thrH + 4
    if astBelowY is not None or thrBelowY is not None:
        winH = int(math.ceil(curBelowY - 4 + margin))
    else:
        winH = int(math.ceil(fy + fh + botExtend + margin))

    return {
        'winW': winW, 'winH': winH,
        'fx': fx, 'fy': fy, 'fw': fw, 'fh': fh,
        'cx': cx, 'cy': fy + headerY, 'cw': cw,
        'padX': padX, 'padY': padY,
        'headerY': fy + headerY, 'headerH': headerH,
        'pctSize': pctSize, 'deltaSize': deltaSize,
        'pctText': pctText, 'deltaText': deltaText,
        'kind': kind, 'deltaAccent': deltaAccent, 'showDelta': showDelta,
        'deltaIconW': deltaIconW, 'pctW': pctW, 'deltaW': deltaW,
        'barY': (fy + barY) if barY is not None else None, 'barH': barH, 'trackH': trackH, 'barBlockH': barBlockH,
        'barStyle': barStyle, 'barText': barText, 'barTextSize': barTextSize, 'barTextW': barTextW,
        'dmgY': (fy + dmgY) if dmgY is not None else None, 'dmgH': dmgH, 'dmgSize': dmgSize,
        'dmg': dmg, 'tgt': tgt, 'dmgStr': dmgStr, 'tgtStr': tgtStr, 'remStr': remStr,
        'dmgLblText': dmgLblText, 'dmgLblMode': dmgLblMode, 'dmgValStr': dmgValStr,
        'astY': (fy + astY) if astInside and astY is not None else astBelowY,
        'astH': astH, 'astSize': astSize, 'astIconSize': astIconSize,
        'astItemGap': astItemGap, 'astItems': astItems, 'astWidths': astWidths,
        'astRowMinW': astRowMinW, 'astInside': astInside,
        'thrY': (fy + thrY) if thrInside and thrY is not None else thrBelowY,
        'thrH': thrH, 'thrSize': thrSize, 'thrIconSize': thrIconSize, 'thrItemGap': thrItemGap,
        'thrItems': thrItems, 'thrWidths': thrWidths, 'thrRowMinW': thrRowMinW, 'thrInside': thrInside,
        'isHangar': isHangar, 'hRows': hRows,
        'hCol0W': hCol0W, 'hCol1W': hCol1W, 'hColGap': hColGap,
        'hSepY': (fy + hSepY) if hSepY is not None else None,
        'hRow1Y': (fy + hRow1Y) if hRow1Y is not None else None,
        'hRow2Y': (fy + hRow2Y) if hRow2Y is not None else None,
        'starsCoords': starsCoords, 'starSize': starSize, 'starGap': starGap,
        'starsSpan': starsSpan, 'starsPos': starsPos,
        'sideBorderStars': sideBorderStars, 'divLine': divLine,
        'altExp': altExp, 'activeCh': activeCh, 'maxAst': maxAst,
    }


def _v3FramePath(x, y, w, h, r, gapSide=None, g0=0.0, g1=0.0):
    r = max(0.0, min(float(r), min(w, h) * 0.45))
    x0, y0, x1, y1 = float(x), float(y), float(x + w), float(y + h)
    def arc(ax, ay):
        return (u' A %.1f %.1f 0 0 1 %.1f %.1f' % (r, r, ax, ay)) if r > 0.1 else u''
    if gapSide is None:
        if r <= 0.1:
            return u'M %.1f %.1f H %.1f V %.1f H %.1f Z' % (x0, y0, x1, y1, x0)
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s Z') % (
            x0 + r, y0, x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1),
            x0 + r, arc(x0, y1 - r),
            y0 + r, arc(x0 + r, y0))
    if gapSide == 'top':
        g0 = max(x0 + r + 2.0, min(x1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(x1 - r - 2.0, g1))
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s H %.1f') % (
            g1, y0, x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1),
            x0 + r, arc(x0, y1 - r),
            y0 + r, arc(x0 + r, y0), g0)
    if gapSide == 'bottom':
        g0 = max(x0 + r + 2.0, min(x1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(x1 - r - 2.0, g1))
        return (u'M %.1f %.1f H %.1f%s V %.1f%s H %.1f%s V %.1f%s H %.1f') % (
            g0, y1, x0 + r, arc(x0, y1 - r),
            y0 + r, arc(x0 + r, y0),
            x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1), g1)
    if gapSide == 'left':
        g0 = max(y0 + r + 2.0, min(y1 - r - 4.0, g0))
        g1 = max(g0 + 2.0, min(y1 - r - 2.0, g1))
        return (u'M %.1f %.1f V %.1f%s H %.1f%s V %.1f%s H %.1f%s V %.1f') % (
            x0, g0, y0 + r, arc(x0 + r, y0),
            x1 - r, arc(x1, y0 + r),
            y1 - r, arc(x1 - r, y1),
            x0 + r, arc(x0, y1 - r), g1)
    # right
    g0 = max(y0 + r + 2.0, min(y1 - r - 4.0, g0))
    g1 = max(g0 + 2.0, min(y1 - r - 2.0, g1))
    return (u'M %.1f %.1f V %.1f%s H %.1f%s V %.1f%s H %.1f%s V %.1f') % (
        x1, g1, y1 - r, arc(x1 - r, y1),
        x0 + r, arc(x0, y1 - r),
        y0 + r, arc(x0 + r, y0),
        x1 - r, arc(x1, y0 + r), g0)


def _v3CornersPaths(x, y, w, h, r):
    r = max(0.0, min(float(r), min(w, h) * 0.45))
    arm = max(r + 4.0, min(10.0, min(w, h) * 0.22))
    x0, y0, x1, y1 = float(x), float(y), float(x + w), float(y + h)
    if r <= 0.1:
        return [
            u'M %.1f %.1f V %.1f H %.1f' % (x0, y0 + arm, y0, x0 + arm),
            u'M %.1f %.1f H %.1f V %.1f' % (x1 - arm, y0, x1, y0 + arm),
            u'M %.1f %.1f V %.1f H %.1f' % (x1, y1 - arm, y1, x1 - arm),
            u'M %.1f %.1f H %.1f V %.1f' % (x0 + arm, y1, x0, y1 - arm),
        ]
    return [
        u'M %.1f %.1f V %.1f A %.1f %.1f 0 0 1 %.1f %.1f H %.1f' % (x0, y0 + arm, y0 + r, r, r, x0 + r, y0, x0 + arm),
        u'M %.1f %.1f H %.1f A %.1f %.1f 0 0 1 %.1f %.1f V %.1f' % (x1 - arm, y0, x1 - r, r, r, x1, y0 + r, y0 + arm),
        u'M %.1f %.1f V %.1f A %.1f %.1f 0 0 1 %.1f %.1f H %.1f' % (x1, y1 - arm, y1 - r, r, r, x1 - r, y1, x1 - arm),
        u'M %.1f %.1f H %.1f A %.1f %.1f 0 0 1 %.1f %.1f V %.1f' % (x0 + arm, y1, x0 + r, r, r, x0, y1 - r, y1 - arm),
    ]


def _v3StarSvg(cx, cy, r, earned, style, onCol, offCol, glow):
    pts = []
    inner = r * 0.43
    for i in range(10):
        ang = -math.pi * 0.5 + i * math.pi * 0.2
        rad = r if (i % 2 == 0) else inner
        pts.append(u'%.2f,%.2f' % (cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    ptsStr = u' '.join(pts)
    out = []
    if earned:
        fill = u'#FFD23C' if style == 2 else onCol
        if glow:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.24" stroke="%s" stroke-width="2.0" stroke-opacity="0.22"/>' % (ptsStr, fill, fill))
        out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.96"/>' % (ptsStr, fill))
    else:
        if style == 1:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.50"/>' % (ptsStr, offCol))
        else:
            out.append(u'<polygon points="%s" fill="%s" fill-opacity="0.10" stroke="%s" stroke-width="1.15" stroke-opacity="0.55"/>' % (ptsStr, offCol, offCol))
    return u''.join(out)


def _v3DeltaIconSvg(x, y, kind, down, color):
    if kind == 0:
        if down:
            pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x, y, x + 10.0, y, x + 5.0, y + 9.0)
        else:
            pts = u'%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x + 5.0, y, x + 10.0, y + 9.0, x, y + 9.0)
        return u'<polygon points="%s" fill="%s"/>' % (pts, color)
    if kind == 1:
        if down:
            return (u'<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f L %.1f %.1f" '
                    u'fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' % (
                        x + 1.5, y + 1.5, x + 9.5, y + 9.5,
                        x + 4.5, y + 9.5, x + 9.5, y + 9.5, x + 9.5, y + 4.5, color))
        return (u'<path d="M %.1f %.1f L %.1f %.1f M %.1f %.1f L %.1f %.1f L %.1f %.1f" '
                u'fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' % (
                    x + 1.5, y + 9.5, x + 9.5, y + 1.5,
                    x + 4.5, y + 1.5, x + 9.5, y + 1.5, x + 9.5, y + 6.5, color))
    return u''


def _v3AssistIconSvg(ch, x, y, size, color, opacity):
    s = float(size) / 16.0
    cx = float(x) + float(size) * 0.5
    cy = float(y) + float(size) * 0.5
    if ch == 'spot':
        r1 = 3.5 * s
        dx1, dy1 = 2.68 * s, 2.25 * s
        r2 = 5.8 * s
        dx2, dy2 = 4.31 * s, 3.88 * s
        sw = 1.25 * s
        return (
            u'<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" fill-opacity="%.2f"/>'
            u'<path d="M %.2f %.2f A %.2f %.2f 0 0 0 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 0 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 1 %.2f %.2f '
            u'M %.2f %.2f A %.2f %.2f 0 0 1 %.2f %.2f" '
            u'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
                cx, cy, 1.45 * s, color, opacity,
                cx - dx1, cy - dy1, r1, r1, cx - dx1, cy + dy1,
                cx - dx2, cy - dy2, r2, r2, cx - dx2, cy + dy2,
                cx + dx1, cy - dy1, r1, r1, cx + dx1, cy + dy1,
                cx + dx2, cy - dy2, r2, r2, cx + dx2, cy + dy2,
                color, sw, opacity))
    if ch == 'track':
        ca = math.cos(math.radians(-35.0))
        sa = math.sin(math.radians(-35.0))
        def rot(dx, dy):
            return (cx + (dx * ca - dy * sa) * s, cy + (dx * sa + dy * ca) * s)
        rails = []
        for rx in (-2.1, 2.1):
            x0, y0 = rot(rx, -3.8)
            x1, y1 = rot(rx, 3.8)
            rails.append(u'M %.2f %.2f L %.2f %.2f' % (x0, y0, x1, y1))
        treads = []
        for ty in (-3.8, 0.0, 3.8):
            x0, y0 = rot(-4.0, ty)
            x1, y1 = rot(4.0, ty)
            treads.append(u'M %.2f %.2f L %.2f %.2f' % (x0, y0, x1, y1))
        return (
            u'<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-opacity="%.2f"/>'
            u'<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
                u' '.join(rails), color, 1.15 * s, opacity * 0.85,
                u' '.join(treads), color, 1.3 * s, opacity))
    if ch == 'stun':
        rays = []
        for i in range(6):
            ang = i * math.pi / 3.0
            rays.append(u'M %.1f %.1f L %.1f %.1f' % (
                cx + 2.2 * math.cos(ang), cy + 2.2 * math.sin(ang),
                cx + 5.8 * math.cos(ang), cy + 5.8 * math.sin(ang)))
        return (
            u'<circle cx="%.1f" cy="%.1f" r="2.0" fill="none" stroke="%s" stroke-width="1.4" stroke-opacity="%.2f"/>'
            u'<path d="%s" fill="none" stroke="%s" stroke-width="1.35" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
                cx, cy, color, opacity, u' '.join(rays), color, opacity))
    # own damage crosshair
    return (
        u'<circle cx="%.1f" cy="%.1f" r="4.6" fill="none" stroke="%s" stroke-width="1.3" stroke-opacity="%.2f"/>'
        u'<path d="M %.1f %.1f V %.1f M %.1f %.1f V %.1f M %.1f %.1f H %.1f M %.1f %.1f H %.1f" '
        u'fill="none" stroke="%s" stroke-width="1.3" stroke-linecap="round" stroke-opacity="%.2f"/>' % (
            cx, cy, color, opacity,
            cx, cy - 6.5, cy - 2.6, cx, cy + 2.6, cy + 6.5,
            cx - 6.5, cy, cx - 2.6, cx + 2.6, cy, cx + 6.5,
            color, opacity))


def _v3BarColor(cfg, pct, kind, deltaAccent):
    mode = _cfgInt('v3BarColorMode', 0, 2, cfg)
    if mode == 1:
        return deltaAccent
    if mode == 2:
        return _cfgColFrom(cfg, 'v3BarCustomColor')
    return _cfgColFrom(cfg, 'v3AccentPlus')


def _v3BarSvg(cfg, m, sample, ratio, barCol):
    bx = float(m['cx'])
    bw = float(m['cw'])
    barStyle = _cfgInt('v3BarStyle', 0, 4, cfg)
    if barStyle == 3 or m['barY'] is None:
        return u''
    if barStyle == 4:
        bTxt = m.get('barText') or _cfgStr('v3BarCustomText', u'KIBERSPORT', 24, cfg) or u'KIBERSPORT'
        bSz = int(m.get('barTextSize', _cfgInt('v3BarTextSize', 10, 26, cfg)))
        tw = max(1.0, float(m.get('barTextW') or _svgAdvance(bTxt, bSz)))
        tx0 = bx + (bw - tw) * 0.5
        ty = float(m['barY']) + float(bSz) * 0.90
        fillW = max(0.0, min(tw, tw * ratio))
        safe = _svgEsc(bTxt)
        out = [
            u'<text x="%.1f" y="%.1f" text-anchor="start" font-family="%s" font-size="%d" font-weight="700" fill="#FFFFFF" fill-opacity="0.25">%s</text>' % (
                tx0, ty, _SVG_FONT, bSz, safe)
        ]
        if fillW > 0.2:
            out.append(
                u'<defs><clipPath id="v3tc"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath></defs>'
                u'<g clip-path="url(#v3tc)">%s</g>' % (
                    tx0, float(m['barY']) - 2.0, fillW, float(m['barBlockH']) + 6.0,
                    _svgText(tx0, ty, bTxt, barCol, bSz, anchor=u'start', shadow=True, shadowOp=0.85)))
        return u''.join(out)
    bh = float(m['barH'])
    trackH = float(m.get('trackH', _cfgInt('v3BarTrackHeight', 1, 10, cfg)))
    by = float(m['barY']) + (float(m['barBlockH']) - bh) * 0.5
    trackY = by + (bh - trackH) * 0.5
    out = []
    if barStyle == 1:
        gap = 2.0
        spans = [(0.0, 65.0), (65.0, 85.0), (85.0, 95.0), (95.0, 100.0)]
        weights = [0.65, 0.20, 0.10, 0.05]
        usableW = bw - gap * (len(spans) - 1)
        curX = bx
        curPct = max(0.0, min(100.0, ratio * 100.0))
        cursorTipX = bx
        for idx, (s0, s1) in enumerate(spans):
            sw = usableW * weights[idx]
            segFill = max(0.0, min(1.0, (curPct - s0) / max(1e-6, s1 - s0)))
            out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>' % (
                curX, trackY, sw, trackH))
            if segFill > 0.005:
                fw = max(1.0, sw * segFill)
                out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="%s" stroke="#000000" stroke-width="0.6" stroke-opacity="0.60"/>' % (
                    curX, by, fw, bh, barCol))
                cursorTipX = curX + fw
            curX += sw + gap
        if bool(cfg.get('v3BarCursor', True)):
            curH = max(10.0, max(bh, trackH) + 6.0)
            curY = by + (bh - curH) * 0.5
            tipX = max(bx, min(bx + bw - 2.5, cursorTipX - 1.25))
            out.append(u'<rect x="%.1f" y="%.1f" width="2.5" height="%.1f" rx="0.8" fill="#FFFFFF" fill-opacity="0.95"/>' % (
                tipX, curY, curH))
        return u''.join(out)

    # Style 0 (continuous + ticks + cursor) or Style 2 (solid)
    out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>' % (
        bx, trackY, bw, trackH))
    if bool(cfg.get('v3BarEndTicks', True)):
        tickH = max(8.0, max(bh, trackH) + 4.0)
        tickTop = by + (bh - tickH) * 0.5
        out.append(u'<rect x="%.1f" y="%.1f" width="1.2" height="%.1f" fill="#FFFFFF" fill-opacity="0.45"/>' % (
            bx, tickTop, tickH))
        out.append(u'<rect x="%.1f" y="%.1f" width="1.2" height="%.1f" fill="#FFFFFF" fill-opacity="0.45"/>' % (
            bx + bw - 1.2, tickTop, tickH))
    if bool(cfg.get('v3BarMarks', False)) and _cfgInt('v3BarScale', 0, 1, cfg) == 0:
        markH = max(bh, trackH) + 3.0
        markTop = by + (bh - markH) * 0.5
        for th in (65.0, 85.0, 95.0):
            tx = bx + bw * (th / 100.0)
            out.append(u'<rect x="%.1f" y="%.1f" width="1.0" height="%.1f" fill="#FFFFFF" fill-opacity="0.40"/>' % (
                tx - 0.5, markTop, markH))
    fillW = max(0.0, min(bw, bw * ratio))
    if fillW > 0.5:
        out.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1" fill="%s"/>' % (
            bx, by, fillW, bh, barCol))
    if bool(cfg.get('v3BarCursor', True)):
        curH = max(10.0, max(bh, trackH) + 6.0)
        curY = by + (bh - curH) * 0.5
        curX = max(bx, min(bx + bw - 2.5, bx + fillW - 1.25))
        out.append(u'<rect x="%.1f" y="%.1f" width="2.5" height="%.1f" rx="0.8" fill="#FFFFFF" fill-opacity="0.95"/>' % (
            curX, curY, curH))
    return u''.join(out)


def _v3BuildSvg(cfg, sample, alt=False):
    m = _v3Metrics(cfg, sample, alt=alt)
    winW, winH = m['winW'], m['winH']
    fx, fy, fw, fh = float(m['fx']), float(m['fy']), float(m['fw']), float(m['fh'])
    cx, cw = float(m['cx']), float(m['cw'])

    panelOp = _cfgNumFrom(cfg, 'panelOpacity', 0.0, 1.0)
    textMain = _cfgColFrom(cfg, 'v3TextMain')
    textMuted = _cfgColFrom(cfg, 'v3TextMuted')
    frameStyle = _cfgInt('v3FrameStyle', 0, 3, cfg)
    shadowOp = 0.95 if frameStyle == 3 else 0.85
    rad = _cfgInt('v3Radius', 0, 14, cfg)
    bgCol = _cfgColFrom(cfg, 'v3BgColor')
    bgOp = _cfgNumFrom(cfg, 'v3BgOpacity', 0.0, 1.0)
    cornerCol = _cfgColFrom(cfg, 'v3CornerColor')
    cornerOp = _cfgNumFrom(cfg, 'v3CornerAlpha', 0.0, 1.0)
    borderOp = _cfgNumFrom(cfg, 'v3BorderAlpha', 0.0, 1.0)

    parts = []
    # 1. Backdrop + Frame + L-corners + Optional divider
    if frameStyle != 3:
        if bgOp > 0.01:
            parts.append(u'<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" fill-opacity="%.3f"/>' % (
                fx, fy, fw, fh, rad, bgCol, bgOp))
        if frameStyle in (0, 2) and borderOp > 0.01:
            gapSide, g0, g1 = None, 0.0, 0.0
            if frameStyle in (0, 2):
                sp = m['starsPos']
                halfGap = m['starsSpan'] * 0.5 + 6.0
                if sp == 0:
                    gapSide, g0, g1 = 'top', fx + fw * 0.5 - halfGap, fx + fw * 0.5 + halfGap
                elif sp == 1:
                    gapSide, g0, g1 = 'bottom', fx + fw * 0.5 - halfGap, fx + fw * 0.5 + halfGap
                elif sp == 2 and m['sideBorderStars']:
                    gapSide, g0, g1 = 'left', fy + fh * 0.5 - halfGap, fy + fh * 0.5 + halfGap
                elif sp == 3 and m['sideBorderStars']:
                    gapSide, g0, g1 = 'right', fy + fh * 0.5 - halfGap, fy + fh * 0.5 + halfGap
            parts.append(u'<path d="%s" fill="none" stroke="%s" stroke-width="1.0" stroke-opacity="%.3f"/>' % (
                _v3FramePath(fx, fy, fw, fh, rad, gapSide, g0, g1), cornerCol, borderOp))
        if frameStyle in (0, 1) and cornerOp > 0.01:
            for cp in _v3CornersPaths(fx, fy, fw, fh, rad):
                parts.append(u'<path d="%s" fill="none" stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-opacity="%.3f"/>' % (
                    cp, cornerCol, cornerOp))
    if m['divLine'] is not None:
        x1, y1, x2, y2 = m['divLine']
        parts.append(u'<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.2" stroke-opacity="0.45"/>' % (
            x1, y1, x2, y2, cornerCol))

    # 2. Stars (Top/Bottom/Left/Right)
    marks = int(sample.get('marks', 0) or 0)
    starStyle = _cfgInt('v3StarsStyle', 0, 2, cfg)
    starOn = _cfgColFrom(cfg, 'v3StarOnColor')
    starOff = _cfgColFrom(cfg, 'v3StarOffColor')
    starGlow = bool(cfg.get('v3StarsGlow', True))
    starR = float(m['starSize']) * 0.5
    for idx, (scx, scy) in enumerate(m['starsCoords']):
        parts.append(_v3StarSvg(scx, scy, starR, idx < marks, starStyle, starOn, starOff, starGlow))

    # 3. Header row (% + delta + optional inline stars)
    hy = float(m['headerY'])
    pctBaseY = hy + float(m['pctSize']) * 0.90
    delBaseY = hy + float(m['pctSize']) * 0.84
    ho = _cfgInt('v3HeaderOrder', 0, 2, cfg)
    di = _cfgInt('v3DeltaIcon', 0, 3, cfg)
    dc = _cfgInt('v3DeltaColorMode', 0, 1, cfg)
    delIconCol = m['deltaAccent'] if dc == 0 else textMuted
    delTextCol = m['deltaAccent'] if dc == 0 else textMuted
    rawDelta = sample.get('delta')
    down = (rawDelta is not None and float(rawDelta) < 0.0)

    def drawDeltaBlock(xLeft):
        cur = xLeft
        if m['deltaIconW'] > 0:
            iy = delBaseY - 10.0
            parts.append(_v3DeltaIconSvg(cur, iy, di, down, delIconCol))
            cur += m['deltaIconW'] + 4.0
        parts.append(_svgText(cur, delBaseY, m['deltaText'], delTextCol, m['deltaSize'],
                              anchor=u'start', shadow=True, shadowOp=shadowOp))

    if ho == 0:
        parts.append(_svgText(cx, pctBaseY, m['pctText'], textMain, m['pctSize'],
                              anchor=u'start', shadow=True, shadowOp=shadowOp))
        if m['showDelta']:
            drawDeltaBlock(cx + cw - m['deltaW'] - (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0))
    elif ho == 1:
        if m['showDelta']:
            drawDeltaBlock(cx)
        parts.append(_svgText(cx + cw - (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0),
                              pctBaseY, m['pctText'], textMain, m['pctSize'],
                              anchor=u'end', shadow=True, shadowOp=shadowOp))
    else:
        totalHW = m['pctW'] + (10.0 + m['deltaW'] if m['showDelta'] else 0.0) + (m['starsSpan'] + 8 if m['starsPos'] == 4 else 0.0)
        hx = cx + (cw - totalHW) * 0.5
        parts.append(_svgText(hx, pctBaseY, m['pctText'], textMain, m['pctSize'],
                              anchor=u'start', shadow=True, shadowOp=shadowOp))
        if m['showDelta']:
            drawDeltaBlock(hx + m['pctW'] + 10.0)
    if m['starsPos'] == 4:
        sx0 = cx + cw - m['starsSpan'] + starR
        scy = hy + m['headerH'] * 0.5
        for idx in range(3):
            parts.append(_v3StarSvg(sx0 + idx * (m['starSize'] + m['starGap']), scy, starR,
                                    idx < marks, starStyle, starOn, starOff, starGlow))

    # 4. Progress bar
    pctVal = float(sample.get('pct', 0.0) or 0.0)
    ratio = _v3BarRatio(cfg, sample, m['dmg'], m['tgt'])
    barCol = _v3BarColor(cfg, pctVal, m['kind'], m['deltaAccent'])
    parts.append(_v3BarSvg(cfg, m, sample, ratio, barCol))

    # 5. Damage row
    plusCol = _cfgColFrom(cfg, 'v3AccentPlus')
    if m['dmgY'] is not None:
        dy = float(m['dmgY']) + float(m['dmgSize']) * 0.92
        if m['dmgLblText']:
            parts.append(_svgText(cx, dy, m['dmgLblText'], textMuted, m['dmgSize'],
                                  anchor=u'start', shadow=True, shadowOp=shadowOp))
        if m.get('isHangar'):
            emaCol = plusCol if (bool(sample.get('hasRating', True)) and m['dmg'] > 0) else textMuted
            parts.append(_svgText(cx + cw, dy, m['dmgStr'], emaCol, m['dmgSize'],
                                  anchor=u'end', shadow=True, shadowOp=shadowOp))
        else:
            dynCol = bool(cfg.get('v3DamageDynColor', True))
            if dynCol:
                dmgCol = plusCol if (m['dmg'] >= m['tgt'] > 0 or m['kind'] in ('plus', 'big')) else (
                    _cfgColFrom(cfg, 'v3AccentMinus') if m['kind'] == 'minus' else textMain)
            else:
                dmgCol = textMain
            rightTxt = u'/ ' + m['tgtStr']
            wRight = _svgAdvance(rightTxt, m['dmgSize'])
            parts.append(_svgText(cx + cw - wRight - 4.0, dy, m['dmgStr'], dmgCol, m['dmgSize'],
                                  anchor=u'end', shadow=True, shadowOp=shadowOp))
            parts.append(_svgText(cx + cw, dy, rightTxt, textMuted, m['dmgSize'],
                                  anchor=u'end', shadow=True, shadowOp=shadowOp))

    # 6. Assist row
    if m['astItems'] and m['astY'] is not None:
        ay = float(m['astY'])
        abY = ay + float(m['astSize']) * 0.92
        icSz = float(m['astIconSize'])
        items = m['astItems']
        widths = m['astWidths']
        baseW = cw if m['astInside'] else float(max(cw, m['astRowMinW']))
        baseX = cx if m['astInside'] else float(winW - baseW) * 0.5
        gap = float(m['astItemGap'])
        totalAstW = sum(widths) + gap * max(0, len(items) - 1)
        curX = baseX + (baseW - totalAstW) * 0.5
        for idx, it in enumerate(items):
            col = plusCol if it['active'] else textMuted
            op = 1.0 if it['active'] else 0.82
            parts.append(_v3AssistIconSvg(it['ch'], curX, ay + (m['astH'] - icSz) * 0.5, icSz, col, op))
            parts.append(_svgText(curX + icSz + 5.0, abY, it['text'], col, m['astSize'],
                                  anchor=u'start', shadow=True, shadowOp=shadowOp))
            curX += widths[idx] + gap

    # 7. Tempo / Thresholds row (no star icons - % and value only)
    if m['thrItems'] and m['thrY'] is not None:
        ty = float(m['thrY'])
        tSz = float(m['thrSize'])
        tbY = ty + tSz * 0.92
        tItems = m['thrItems']
        tWidths = m['thrWidths']
        tBaseW = cw
        tBaseX = cx
        tGap = float(m['thrItemGap'])
        totalThrW = sum(tWidths) + tGap * max(0, len(tItems) - 1)
        curX = tBaseX + (tBaseW - totalThrW) * 0.5
        for idx, it in enumerate(tItems):
            isDone = bool(it['done'])
            lCol = plusCol if isDone else textMuted
            vCol = plusCol if isDone else textMain
            parts.append(_svgText(curX, tbY, it['lbl'], lCol, m['thrSize'],
                                  anchor=u'start', shadow=True, shadowOp=shadowOp))
            lblAdv = _svgAdvance(it['lbl'] + u' ', m['thrSize'])
            parts.append(_svgText(curX + lblAdv, tbY, it['valStr'], vCol, m['thrSize'],
                                  anchor=u'start', shadow=True, shadowOp=shadowOp))
            curX += tWidths[idx] + tGap

    # 8. Hangar 2x2 thresholds grid (65% / 85% / 95% / 100%, compact centered columns)
    if m.get('hRows'):
        if m.get('hSepY') is not None:
            sy = float(m['hSepY'])
            parts.append(u'<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.0" stroke-opacity="0.18"/>' % (
                cx, sy, cx + cw, sy, cornerCol))
        tSz = float(m['thrSize'])
        col0W = float(m.get('hCol0W') or 68.0)
        col1W = float(m.get('hCol1W') or 72.0)
        colGap = float(m.get('hColGap') or 16.0)
        totalGridW = col0W + colGap + col1W
        gx0 = cx + (cw - totalGridW) * 0.5
        gx1 = gx0 + col0W + colGap
        for rowY, rowItems in ((m.get('hRow1Y'), m['hRows'][0]),
                               (m.get('hRow2Y'), m['hRows'][1] if len(m['hRows']) > 1 else [])):
            if rowY is None or not rowItems:
                continue
            tbY = float(rowY) + tSz * 0.92
            if len(rowItems) >= 2:
                it0, it1 = rowItems[0], rowItems[1]
                lCol0 = plusCol if it0['done'] else textMuted
                vCol0 = plusCol if it0['done'] else textMain
                parts.append(_svgText(gx0, tbY, it0['lbl'], lCol0, m['thrSize'],
                                      anchor=u'start', shadow=True, shadowOp=shadowOp))
                parts.append(_svgText(gx0 + col0W, tbY, it0['valStr'], vCol0, m['thrSize'],
                                      anchor=u'end', shadow=True, shadowOp=shadowOp))
                lCol1 = plusCol if it1['done'] else textMuted
                vCol1 = plusCol if it1['done'] else textMain
                parts.append(_svgText(gx1, tbY, it1['lbl'], lCol1, m['thrSize'],
                                      anchor=u'start', shadow=True, shadowOp=shadowOp))
                parts.append(_svgText(gx1 + col1W, tbY, it1['valStr'], vCol1, m['thrSize'],
                                      anchor=u'end', shadow=True, shadowOp=shadowOp))

    body = u'<g opacity="%.3f">%s</g>' % (panelOp, u''.join(parts))
    svg = u'<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (
        winW, winH, winW, winH, body)
    encoded = base64.b64encode(svg.encode('utf-8'))
    return 'data:image/svg+xml;base64,' + encoded, winW, winH


def _menuPreviewRender():
    """Return (dataUri, baseW, baseH, dispW, dispH) matching battle/hangar HUD 1-to-1."""
    state = _PREVIEW.get('state', 'plus')
    target = int(_PREVIEW.get('target', 0) or 0)
    if target == 1:
        baseSample = _PREVIEW_SAMPLES_V3.get(state) or _PREVIEW_SAMPLES_V3['plus']
        hSample = dict(baseSample)
        hSample['isHangar'] = True
        hSample['dmg'] = int(baseSample.get('tHold', 2450) or 2450)
        vhScale = _cfgNumber('vhScale', 0.5, 2.5)
        uri, width, height = _v3BuildSvg(_vhToV3Cfg(g_config), hSample, alt=False)
        scale = min(float(_PREVIEW_CONTAINER_W) / float(width),
                    float(_PREVIEW_CONTAINER_H) / float(height),
                    vhScale)
        dispW = max(1, int(round(width * scale)))
        dispH = max(1, int(round(height * scale)))
        return uri, width, height, dispW, dispH

    preset = _cfgInt('battlePreset', 0, 1)
    uiScale = _cfgNumber('uiScale', 0.5, 2.5)
    if preset == 0:
        sample = _PREVIEW_SAMPLES_V3.get(state) or _PREVIEW_SAMPLES_V3['plus']
        altActive = bool(_PREVIEW.get('alt', False) or _PREVIEW.get('hwAlt', False))
        uri, width, height = _v3BuildSvg(g_config, sample, alt=altActive)
        scale = min(float(_PREVIEW_CONTAINER_W) / float(width),
                    float(_PREVIEW_CONTAINER_H) / float(height),
                    uiScale)
        dispW = max(1, int(round(width * scale)))
        dispH = max(1, int(round(height * scale)))
        return uri, width, height, dispW, dispH

    sample = _PREVIEW_SAMPLES.get(state) or _PREVIEW_SAMPLES['plus']
    delta = float(sample['delta'])
    zeroBand = _cfgNumber('zeroBand', 0.0, 1.0)
    bigByDamage = bool(g_config.get('bigByDamage', True))
    if sample['big'] and bigByDamage:
        kind = 'big'
    elif abs(delta) <= zeroBand:
        kind = 'zero'
    elif delta < 0:
        kind = 'minus'
    elif not bigByDamage and delta >= _cfgNumber('bigFrom', 0.0, 10.0):
        kind = 'big'
    else:
        kind = 'plus'
    colors = {
        'plus': _cfgColor('colorPlus'),
        'minus': _cfgColor('colorMinus'),
        'zero': _cfgColor('colorZero'),
        'big': _cfgColor('colorBig'),
    }
    deltaColor = colors[kind]
    onlyPct = (preset == 1 or bool(g_config.get('battlePercentOnly', False)))
    pctColor = deltaColor if (onlyPct or g_config.get('pctFollowsSign', False)) else _cfgColor('pctColor')
    dmgColor = deltaColor if g_config.get('dmgFollowsSign', True) else _cfgColor('colorDmg')
    projColor = _cfgColor('colorProj')
    bgOpacity = _cfgNumber('bgOpacity', 0.0, 1.0)
    panelOpacity = _cfgNumber('panelOpacity', 0.0, 1.0)
    trackOpacity = _cfgNumber('trackOpacity', 0.0, 1.0)
    tickColor = _cfgColor('tickColor')
    glowOn = bool(sample['glow'] and g_config.get('glow', True))
    pctText = u'%.2f%%' % sample['pct']
    deltaText = u'%+.2f%%' % sample['delta']
    dmgText = _fmt(sample['dmg'])
    projText = _fmt(sample['proj'])
    needText = u'/ ' + projText
    barKey = {'plus': 'barColorPlus', 'minus': 'barColorMinus',
              'zero': 'barColorZero', 'big': 'barColorBig'}[kind]
    barColor = _cfgColor(barKey) if g_config.get('barBySign', True) else _cfgColor('barColorStandard')

    if onlyPct:
        width, height = 220, 72
        wDmg = _svgAdvance(dmgText, 15)
        wNeed = _svgAdvance(needText, 15)
        gap = 4.0
        splitX = 110.0 - (wDmg + gap + wNeed) * 0.5 + wDmg
        items = [
            _svgText(110.0, 31.0, pctText, pctColor, 22, anchor=u'middle'),
            _svgText(splitX, 57.0, dmgText, dmgColor, 15, anchor=u'end'),
            _svgText(splitX + gap, 57.0, needText, projColor, 15, anchor=u'start'),
        ]
        body = u'<g opacity="%.3f">%s</g>' % (panelOpacity, u''.join(items))
    else:
        showSpot = bool(g_config.get('showSpot', False))
        showTrack = bool(g_config.get('showTrack', False))
        astOn = showSpot or showTrack
        width = 244
        height = 118 if astOn else 96
        panelH = 94 if astOn else 72
        strokeK = min(1.0, bgOpacity / 0.8) if bgOpacity > 0.0 else 0.0
        fillWidth = max(0.0, min(200.0, float(sample['pct']) * 2.0))
        pctW = _svgAdvance(pctText, 22)
        pctLeft = 12.0 + (220.0 - pctW) * 0.5
        arrowX = pctLeft + pctW + 9.0
        deltaX = arrowX + 10.0 + 6.0
        tickX = 22.0 + fillWidth - 1.0
        marks = 3 if sample['pct'] >= 95.0 else (2 if sample['pct'] >= 85.0 else (1 if sample['pct'] >= 65.0 else 0))

        items = [
            u'<rect x="12" y="12" width="220" height="%d" rx="9" '
            u'fill="#0C1219" fill-opacity="%.3f" stroke="#BAD2E5" stroke-opacity="%.3f"/>' % (
                panelH, bgOpacity, 0.20 * strokeK),
            _svgText(122.0, 33.0, pctText, pctColor, 22, anchor=u'middle'),
            _svgArrow(arrowX, 22.0, deltaColor, down=(delta < 0.0)),
            _svgText(deltaX, 32.0, deltaText, deltaColor, 15, anchor=u'start'),
            u'<rect x="22" y="45" width="200" height="8" rx="4" fill="#E2EBF4" fill-opacity="%.3f"/>' % trackOpacity,
        ]
        if glowOn and fillWidth > 0.0:
            items.append(
                u'<rect x="20" y="43" width="%.1f" height="12" rx="6" fill="%s" fill-opacity="0.32"/>' % (
                    fillWidth + 4.0, barColor))
        if fillWidth > 0.0:
            items.append(
                u'<rect x="22" y="45" width="%.1f" height="8" rx="4" fill="%s"/>' % (
                    fillWidth, barColor))
            items.append(
                u'<rect x="%.1f" y="41" width="2" height="16" rx="1" fill="%s"/>' % (
                    tickX, tickColor))
        dmgX = 85.0
        needX = dmgX + _svgAdvance(dmgText, 15) + 4.0
        items.extend([
            _svgText(18.0, 75.0, u'Сум. урон:', '#C8D0D8', 13, anchor=u'start'),
            _svgText(dmgX, 75.0, dmgText, dmgColor, 15, anchor=u'start'),
            _svgText(needX, 75.0, needText, projColor, 15, anchor=u'start'),
            _svgStar(187.0, 70.0, 6.5, '#FFD23C' if marks >= 1 else '#6E7884', 1.0 if marks >= 1 else 0.45),
            _svgStar(204.0, 70.0, 6.5, '#FFD23C' if marks >= 2 else '#6E7884', 1.0 if marks >= 2 else 0.45),
            _svgStar(221.0, 70.0, 6.5, '#FFD23C' if marks >= 3 else '#6E7884', 1.0 if marks >= 3 else 0.45),
        ])
        if astOn:
            rVal = int(sample['assist'][0]) if showSpot else 0
            tVal = int(sample['assist'][1]) if showTrack else 0
            mainColor = deltaColor if g_config.get('pctFollowsSign', False) else _cfgColor('pctColor')
            rText = _fmt(rVal)
            tText = _fmt(tVal)
            iconW = 16.0
            iconGap = 6.0
            pairGap = 28.0
            rItemW = iconW + iconGap + _svgAdvance(rText, 15)
            tItemW = iconW + iconGap + _svgAdvance(tText, 15)
            totalW = (rItemW if showSpot else 0.0) + (pairGap if (showSpot and showTrack) else 0.0) + (tItemW if showTrack else 0.0)
            curX = 122.0 - totalW * 0.5
            if showSpot:
                rColor = deltaColor if rVal > tVal else mainColor
                rOp = 1.0 if rVal > tVal else 0.6
                items.append(_svgBitmapIcon(curX, 87.0, _SVG_SPOT_RUNS, rOp))
                items.append(_svgText(curX + iconW + iconGap, 100.0, rText, rColor, 15, anchor=u'start'))
                curX += rItemW + pairGap
            if showTrack:
                tColor = deltaColor if tVal > rVal else mainColor
                tOp = 1.0 if tVal > rVal else 0.6
                items.append(_svgBitmapIcon(curX, 87.0, _SVG_TRACK_RUNS, tOp))
                items.append(_svgText(curX + iconW + iconGap, 100.0, tText, tColor, 15, anchor=u'start'))
        body = u'<g opacity="%.3f">%s</g>' % (panelOpacity, u''.join(items))

    svg = u'<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (
        width, height, width, height, body)
    encoded = base64.b64encode(svg.encode('utf-8'))
    scale = min(float(_PREVIEW_CONTAINER_W) / float(width),
                float(_PREVIEW_CONTAINER_H) / float(height),
                uiScale)
    dispW = max(1, int(round(width * scale)))
    dispH = max(1, int(round(height * scale)))
    return 'data:image/svg+xml;base64,' + encoded, width, height, dispW, dispH


def _menuPreviewImage():
    return _menuPreviewRender()[0]


def _menuPreviewRefresh():
    """Refresh the inline Aslain Image without forcing an overlay in the hangar."""
    api = _MENU.get('api')
    template = _MENU.get('template')
    if api is None or template is None:
        return
    try:
        source, _bw, _bh, width, height = _menuPreviewRender()
        key = (source, width, height)
        if key == _PREVIEW.get('key'):
            return
        imageFound = False
        for colKey in ('column1', 'column2', 'column3', 'column4'):
            for component in template.get(colKey, ()) or ():
                if component.get('varName') == 'marksLivePreview':
                    component['source'] = source
                    component['width'] = width
                    component['height'] = height
                    imageFound = True
        if not imageFound:
            return
        # Aslain's Gameface API updates an image in the already-open page with
        # updateImage(); re-registering the template alone only updates storage
        # and can leave the visible preview unchanged.
        updateImage = getattr(api, 'updateImage', None)
        if updateImage is not None:
            try:
                updateImage(_MENU_LINKAGE, 'marksLivePreview', source, width, height)
                _PREVIEW['source'] = source
                _PREVIEW['key'] = key
                return
            except Exception:
                pass
        api.setModTemplate(_MENU_LINKAGE, template, _onMenuApplied)
        _PREVIEW['source'] = source
        _PREVIEW['key'] = key
    except Exception:
        _logError('menu preview refresh')


_MENU_LINKAGE = 'dm.threemarks'
_MENU = {'api': None, 'tpl': None, 'ver': (1, 0, 0), 'ok': False, 'tries': 0,
         'next': 0.0, 'busy': False, 'template': None, 'fullTemplate': None, 'tplV3': True}
_MENU_NUM = (('uiScale', 0.5, 2.5), ('panelOpacity', 0.0, 1.0),
             ('zeroBand', 0.0, 1.0), ('bigFrom', 0.0, 10.0),
             ('bigDamageFactor', 1.0, 10.0))
_MENU_BOOL = ('dmgFollowsSign', 'bigByDamage', 'hideInIntro', 'hideInKillcam', 'hideAfterDeath')
_MENU_COLORS = ('colorPlus', 'colorMinus', 'colorZero', 'colorBig',
                'pctColor', 'colorDmg', 'colorProj')

_MENU_V3_INT = (
    ('v3Density', 0, 2),
    ('v3MinWidth', 0, 360),
    ('v3Anchor', 0, 5),
    ('v3FrameStyle', 0, 3),
    ('v3Radius', 0, 14),
    ('v3StarsPos', 0, 5),
    ('v3StarsStyle', 0, 2),
    ('v3StarsSize', 10, 22),
    ('v3StarsGap', 2, 14),
    ('v3HeaderOrder', 0, 2),
    ('v3PctDecimals', 0, 1),
    ('v3DeltaIcon', 0, 3),
    ('v3DeltaColorMode', 0, 1),
    ('v3BarStyle', 0, 4),
    ('v3BarScale', 0, 1),
    ('v3BarHeight', 2, 10),
    ('v3BarTrackHeight', 1, 10),
    ('v3BarTextSize', 10, 26),
    ('v3BarColorMode', 0, 2),
    ('v3DamageLabel', 0, 2),
    ('v3ThousandsSep', 0, 2),
    ('v3AssistShow', 0, 3),
    ('v3AssistMode', 0, 1),
    ('v3AssistPlace', 0, 1),
    ('v3TempoShow', 0, 3),
    ('v3TempoMode', 0, 2),
    ('v3TempoPlace', 0, 1),
)
_MENU_V3_FLOAT = (
    ('v3CornerAlpha', 0.0, 1.0),
    ('v3BorderAlpha', 0.0, 1.0),
    ('v3BgOpacity', 0.0, 1.0),
)
_MENU_V3_BOOL = (
    'v3HideInSniper',
    'v3StarsDivider',
    'v3StarsGlow',
    'v3BarEndTicks',
    'v3BarCursor',
    'v3BarMarks',
    'v3ShowDamage',
    'v3DamageDynColor',
    'v3AssistHideZero',
)
_MENU_V3_STR = ('v3DamageCustomLabel', 'v3BarCustomText', 'vhBarCustomText')
_MENU_V3_COLORS = (
    'v3CornerColor',
    'v3BgColor',
    'v3StarOnColor',
    'v3StarOffColor',
    'v3BarCustomColor',
    'v3AccentPlus',
    'v3AccentMinus',
    'v3AccentZero',
    'v3AccentBig',
    'v3TextMain',
    'v3TextMuted',
)

_MENU_VH_INT = (
    ('vhDensity', 0, 2),
    ('vhFrameStyle', 0, 3),
    ('vhRadius', 0, 14),
    ('vhStarsPos', 0, 5),
    ('vhStarsStyle', 0, 2),
    ('vhStarsSize', 10, 22),
    ('vhStarsGap', 2, 14),
    ('vhPctDecimals', 0, 1),
    ('vhBarStyle', 0, 4),
    ('vhBarScale', 0, 1),
    ('vhBarHeight', 2, 10),
    ('vhBarTrackHeight', 1, 10),
    ('vhBarTextSize', 10, 26),
    ('vhThousandsSep', 0, 2),
)
_MENU_VH_FLOAT = (
    ('vhScale', 0.5, 2.5),
    ('vhCornerAlpha', 0.0, 1.0),
    ('vhBorderAlpha', 0.0, 1.0),
    ('vhBgOpacity', 0.0, 1.0),
)
_MENU_VH_BOOL = (
    'hangarPanel',
    'vhStarsDivider',
    'vhStarsGlow',
    'vhBarEndTicks',
    'vhBarCursor',
    'vhBarMarks',
    'vhShowEma',
    'vhShowThresholds',
)
_MENU_VH_COLORS = (
    'vhBarColor',
    'vhTextMain',
    'vhTextMuted',
    'vhCornerColor',
    'vhBgColor',
    'vhStarOnColor',
    'vhStarOffColor',
)

_MENU_ALL_KEYS = (
    ('previewTarget', 'previewState', 'previewAlt', 'battlePanelVariant') +
    _MENU_BOOL + _MENU_V3_BOOL + _MENU_VH_BOOL + _MENU_V3_STR +
    _MENU_COLORS + _MENU_V3_COLORS + _MENU_VH_COLORS +
    tuple(n for n, _l, _h in (_MENU_NUM + _MENU_V3_INT + _MENU_V3_FLOAT + _MENU_VH_INT + _MENU_VH_FLOAT))
)


def _menuImport():
    """(api, templates) - сначала само Mod Menu, затем любой, кто отдаёт
    gui.modsSettingsApi (оригинал izeberg / Flash-версия); (None, None) - нет."""
    try:
        from gui.aslainMenu import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except Exception:
        pass
    try:
        from gui.modsSettingsApi import g_modsSettingsApi, templates
        return g_modsSettingsApi, templates
    except Exception:
        return None, None


def _menuColorValue(raw):
    """Любой вид цвета, который отдаёт меню, -> '#RRGGBB' (или None)."""
    try:
        if isinstance(raw, basestring):
            text = raw.strip().lstrip('#')
            if len(text) >= 6:
                int(text[:6], 16)
                return '#' + text[:6].upper()
        elif isinstance(raw, bool):
            return None
        elif isinstance(raw, (int, long)):
            return '#%06X' % (raw & 0xFFFFFF)
        elif isinstance(raw, (list, tuple)) and len(raw) >= 3:
            return _hexOfRgb([float(v) for v in raw[:3]])
    except (ValueError, TypeError):
        pass
    return None


def _menuConvert(key, raw):
    if key in _MENU_BOOL or key in _MENU_V3_BOOL or key in _MENU_VH_BOOL:
        return bool(raw)
    if key in _MENU_V3_STR:
        if isinstance(raw, basestring):
            text = raw.decode('utf-8', 'replace') if isinstance(raw, str) else raw
            return text.replace(u'\r', u' ').replace(u'\n', u' ')[:24]
        return None
    if key in _MENU_COLORS or key in _MENU_V3_COLORS or key in _MENU_VH_COLORS:
        return _menuColorValue(raw)
    for name, low, high in _MENU_V3_INT + _MENU_VH_INT:
        if name == key:
            try:
                return int(round(max(low, min(high, float(raw)))))
            except (TypeError, ValueError):
                return None
    for name, low, high in _MENU_NUM + _MENU_V3_FLOAT + _MENU_VH_FLOAT:
        if name == key:
            try:
                return round(max(low, min(high, float(raw))), 4)
            except (TypeError, ValueError):
                return None
    return None


def _menuValues():
    """Текущие значения в том виде, в каком их ждёт меню."""
    values = {}
    for name, low, high in _MENU_NUM + _MENU_V3_FLOAT + _MENU_VH_FLOAT:
        values[name] = round(_cfgNumber(name, low, high), 4)
    for name, low, high in _MENU_V3_INT + _MENU_VH_INT:
        values[name] = _cfgInt(name, low, high)
    for name in _MENU_BOOL + _MENU_V3_BOOL + _MENU_VH_BOOL:
        values[name] = bool(g_config.get(name, DEFAULT_CONFIG.get(name)))
    for name in _MENU_V3_STR:
        values[name] = _cfgStr(name, DEFAULT_CONFIG.get(name, u''), 24)
    for name in _MENU_COLORS + _MENU_V3_COLORS + _MENU_VH_COLORS:
        values[name] = _cfgColor(name)
    values['battlePanelVariant'] = _cfgInt('battlePreset', 0, 1)
    state = _PREVIEW.get('state', 'plus')
    values['previewState'] = _PREVIEW_ORDER.index(state) if state in _PREVIEW_ORDER else 0
    values['previewAlt'] = 1 if _PREVIEW.get('alt', False) else 0
    values['previewTarget'] = 1 if int(_PREVIEW.get('target', 0) or 0) == 1 else 0
    return values


def _menuDefaults():
    values = {}
    for name, low, high in _MENU_NUM + _MENU_V3_FLOAT + _MENU_VH_FLOAT:
        values[name] = float(DEFAULT_CONFIG[name])
    for name, low, high in _MENU_V3_INT + _MENU_VH_INT:
        values[name] = int(DEFAULT_CONFIG[name])
    for name in _MENU_BOOL + _MENU_V3_BOOL + _MENU_VH_BOOL:
        values[name] = bool(DEFAULT_CONFIG[name])
    for name in _MENU_V3_STR:
        values[name] = unicode(DEFAULT_CONFIG[name])
    for name in _MENU_COLORS + _MENU_V3_COLORS + _MENU_VH_COLORS:
        values[name] = str(DEFAULT_CONFIG[name]).upper()
    values['battlePanelVariant'] = int(DEFAULT_CONFIG.get('battlePreset', 0))
    values['previewState'] = 0
    values['previewAlt'] = 0
    values['previewTarget'] = 0
    return values


def _menuRefresh():
    """Перерисовать панель ангара с новыми значениями."""
    try:
        g_hangar.refresh()
    except Exception:
        _logError('menu refresh')


def _applyMenuSettings(settings, save):
    """Значения из меню -> g_config (и config.json, если save)."""
    if not isinstance(settings, dict):
        return False
    changed = False
    if 'previewTarget' in settings:
        try:
            tgtIdx = 1 if int(settings['previewTarget']) == 1 else 0
        except (TypeError, ValueError):
            tgtIdx = 0
        _PREVIEW['target'] = tgtIdx
    if 'previewState' in settings:
        try:
            idx = max(0, min(len(_PREVIEW_ORDER) - 1, int(settings['previewState'])))
        except (TypeError, ValueError):
            idx = 0
        if idx != _PREVIEW.get('uiState'):
            _PREVIEW['uiState'] = idx
            _PREVIEW['state'] = _PREVIEW_ORDER[idx]
    if 'previewAlt' in settings:
        try:
            altIdx = 1 if int(settings['previewAlt']) == 1 else 0
        except (TypeError, ValueError):
            altIdx = 0
        _PREVIEW['alt'] = bool(altIdx == 1)
    if 'battlePanelVariant' in settings:
        try:
            rawVar = int(settings['battlePanelVariant'])
            preset = 1 if rawVar == 1 else 0
        except (TypeError, ValueError):
            preset = None
            rawVar = None
        if preset is not None:
            if g_config.get('battlePreset') != preset:
                g_config['battlePreset'] = preset
                changed = True
            onlyPct = (preset == 1)
            if g_config.get('battlePercentOnly') != onlyPct:
                g_config['battlePercentOnly'] = onlyPct
                changed = True
            if rawVar == 2:
                api = _MENU.get('api')
                setVal = getattr(api, 'setControlValue', None) if api is not None else None
                if setVal is not None and not _PREVIEW.get('syncing'):
                    _PREVIEW['syncing'] = True
                    try:
                        setVal(_MENU_LINKAGE, 'battlePanelVariant', 0)
                    except Exception:
                        pass
                    finally:
                        _PREVIEW['syncing'] = False
    applyKeys = (_MENU_BOOL + _MENU_V3_BOOL + _MENU_VH_BOOL + _MENU_V3_STR +
                 _MENU_COLORS + _MENU_V3_COLORS + _MENU_VH_COLORS +
                 tuple(n for n, _l, _h in (_MENU_NUM + _MENU_V3_INT + _MENU_V3_FLOAT + _MENU_VH_INT + _MENU_VH_FLOAT)))
    vhTouch = False
    bTouch = False
    for key in applyKeys:
        if key not in settings:
            continue
        value = _menuConvert(key, settings[key])
        if value is None:
            _logOnce(('menubad', key), 'Mod Menu sent an unreadable value for "%s": %r' % (key, settings[key]))
            continue
        if g_config.get(key) != value:
            g_config[key] = value
            changed = True
            if key.startswith('vh') or key in ('hangarPanel', 'hangarOnlyRandom', 'hideUnderWindows'):
                vhTouch = True
            elif key.startswith('v3') or key.startswith('color') or key in ('uiScale', 'dmgFollowsSign', 'pctColor'):
                bTouch = True
            state = _previewStateFor(key)
            if state:
                _PREVIEW['state'] = state
                newIdx = _PREVIEW_ORDER.index(state)
                if not save and not _PREVIEW.get('syncing'):
                    api = _MENU.get('api')
                    setVal = getattr(api, 'setControlValue', None) if api is not None else None
                    if setVal is not None:
                        _PREVIEW['syncing'] = True
                        try:
                            if setVal(_MENU_LINKAGE, 'previewState', newIdx) is not False:
                                _PREVIEW['uiState'] = newIdx
                        except Exception:
                            pass
                        finally:
                            _PREVIEW['syncing'] = False
                elif save:
                    _PREVIEW['uiState'] = newIdx
    if not save and 'previewTarget' not in settings:
        wantTarget = 1 if (vhTouch and not bTouch) else (0 if (bTouch and not vhTouch) else None)
        if wantTarget is not None and _PREVIEW.get('target') != wantTarget:
            _PREVIEW['target'] = wantTarget
            api = _MENU.get('api')
            setVal = getattr(api, 'setControlValue', None) if api is not None else None
            if setVal is not None and not _PREVIEW.get('syncing'):
                _PREVIEW['syncing'] = True
                try:
                    setVal(_MENU_LINKAGE, 'previewTarget', wantTarget)
                except Exception:
                    pass
                finally:
                    _PREVIEW['syncing'] = False
    if changed:
        if save:
            _saveJson(CONFIG_PATH, g_config)
        _menuRefresh()
    return changed


def _menuArgs(args):
    linkage = settings = None
    for arg in args:
        if isinstance(arg, basestring) and linkage is None:
            linkage = arg
        elif isinstance(arg, dict) and settings is None:
            settings = arg
    return linkage, settings


def _resetV3Preset():
    """Сбросить визуальные настройки Варианта 1 («Киберспорт») к эталону по умолчанию."""
    for key, val in _V3_DEFAULTS.iteritems():
        g_config[key] = val
    _saveJson(CONFIG_PATH, g_config)
    api = _MENU.get('api')
    if api is not None:
        vals = _menuValues()
        _PREVIEW['syncing'] = True
        try:
            upd = getattr(api, 'updateModSettings', None)
            if upd is not None:
                try:
                    upd(_MENU_LINKAGE, vals)
                except Exception:
                    pass
            setVal = getattr(api, 'setControlValue', None)
            if setVal is not None:
                for key in _V3_DEFAULTS:
                    if key in vals:
                        try:
                            setVal(_MENU_LINKAGE, key, vals[key])
                        except Exception:
                            pass
        finally:
            _PREVIEW['syncing'] = False
    _menuRefresh()
    _PREVIEW['source'] = None
    _PREVIEW['key'] = None
    _menuPreviewRefresh()


def _resetVhPreset():
    """Сбросить визуальные настройки ангарной панели к эталону по умолчанию."""
    for key, val in _VH_DEFAULTS.iteritems():
        g_config[key] = val
    _saveJson(CONFIG_PATH, g_config)
    api = _MENU.get('api')
    if api is not None:
        vals = _menuValues()
        _PREVIEW['syncing'] = True
        try:
            upd = getattr(api, 'updateModSettings', None)
            if upd is not None:
                try:
                    upd(_MENU_LINKAGE, vals)
                except Exception:
                    pass
            setVal = getattr(api, 'setControlValue', None)
            if setVal is not None:
                for key in _VH_DEFAULTS:
                    if key in vals:
                        try:
                            setVal(_MENU_LINKAGE, key, vals[key])
                        except Exception:
                            pass
        finally:
            _PREVIEW['syncing'] = False
    _menuRefresh()
    _PREVIEW['source'] = None
    _PREVIEW['key'] = None
    _menuPreviewRefresh()


def _resetPanelPosition():
    """Вернуть боевую панель на позицию по умолчанию."""
    g_config['x'] = DEFAULT_CONFIG['x']
    g_config['y'] = DEFAULT_CONFIG['y']
    _saveJson(CONFIG_PATH, g_config)
    try:
        if g_controller._panel is not None:
            g_controller._panel.moveTo(g_config['x'], g_config['y'])
    except Exception:
        pass
    _menuRefresh()


def _resetHangarPosition():
    """Вернуть ангарную панель на позицию по умолчанию."""
    g_config['hx'] = DEFAULT_CONFIG['hx']
    g_config['hy'] = DEFAULT_CONFIG['hy']
    _saveJson(CONFIG_PATH, g_config)
    try:
        if g_hangar._panel is not None:
            g_hangar._panel.moveTo(g_config['hx'], g_config['hy'])
    except Exception:
        pass
    _menuRefresh()


def _onMenuButton(*args, **kwargs):
    """Обработка кнопок действия в Mod Menu."""
    try:
        linkage = kwargs.get('linkage')
        varName = kwargs.get('varName')
        btnName = kwargs.get('buttonName') or kwargs.get('button') or kwargs.get('name')
        strs = [a for a in args if isinstance(a, basestring)]
        if linkage is None and strs:
            linkage = strs[0]
        if linkage != _MENU_LINKAGE:
            return
        if varName is None and len(strs) >= 2:
            varName = strs[1]
        if btnName is None and len(strs) >= 3:
            btnName = strs[2]
        action = btnName or varName
        if action in ('v3ResetPreset', 'resetPreset'):
            _resetV3Preset()
        elif action == 'vhResetPreset':
            _resetVhPreset()
        elif action in ('resetPosition', 'v3ResetPosition'):
            _resetPanelPosition()
        elif action == 'resetHangarPosition':
            _resetHangarPosition()
    except Exception:
        _logError('menu button')


def _onMenuApplied(*args):
    """Нажали Применить (или окно сохранило): записываем и в config.json."""
    try:
        linkage, settings = _menuArgs(args)
        if linkage == _MENU_LINKAGE:
            _applyMenuSettings(settings, True)
            _PREVIEW['key'] = None
            _menuPreviewRefresh()
    except Exception:
        _logError('menu apply')


def _syncMenuTabs(force=False):
    """Перестроить вкладки Mod Menu: 6 вкладок для Варианта 1 (Киберспорт), 3 вкладки для Варианта 2 (Отметка Корбена)."""
    api = _MENU.get('api')
    tpl = _MENU.get('tpl')
    ver = _MENU.get('ver') or (1, 0, 0)
    if api is None or tpl is None:
        return False
    reloadFn = getattr(api, 'reloadModTemplate', None)
    wantV3 = (_cfgInt('battlePreset', 0, 1) == 0)
    if not force and _MENU.get('tplV3') == wantV3:
        return False
    if reloadFn is None:
        return False
    try:
        newTpl = _menuTemplate(tpl, ver, showV3=wantV3)
        _MENU['template'] = newTpl
        _MENU['tplV3'] = wantV3
        _PREVIEW['syncing'] = True
        try:
            reloadFn(_MENU_LINKAGE, newTpl)
        finally:
            _PREVIEW['syncing'] = False
        _PREVIEW['source'] = None
        _PREVIEW['key'] = None
        return True
    except Exception:
        _logError('menu sync tabs')
        return False


def _onMenuOpened(*args):
    """Окно Mod Menu открылось: обновить картинку предпросмотра в его странице."""
    try:
        _syncMenuTabs()
        _PREVIEW['key'] = None
        _menuPreviewRefresh()
    except Exception:
        _logError('menu opened')


def _onMenuLive(*args):
    """Двигают ползунок/выбирают цвет: показываем сразу, но не сохраняем."""
    try:
        if _PREVIEW.get('syncing'):
            return
        linkage, settings = _menuArgs(args)
        if linkage == _MENU_LINKAGE or (isinstance(settings, dict) and
                any(key in settings for key in _MENU_ALL_KEYS)):
            _applyMenuSettings(settings, False)
            _syncMenuTabs()
            _menuRefresh()
            # Some Mod Menu builds reuse a template snapshot and skip redraw
            # when the previous Image source is still cached.
            _PREVIEW['source'] = None
            _PREVIEW['key'] = None
            _menuPreviewRefresh()
    except Exception:
        _logError('menu live')


def _onMenuClosed(*args):
    """Окно закрыто: непримённый просмотр (Отмена) откатываем к сохранённому."""
    try:
        _PREVIEW['state'] = 'plus'
        _PREVIEW['uiState'] = 0
        _PREVIEW['key'] = None
        api = _MENU['api']
        srcTpl = _MENU.get('fullTemplate') or _MENU.get('template')
        if api is not None and srcTpl is not None:
            _applyMenuSettings(api.getModSettings(_MENU_LINKAGE, srcTpl), False)
        _syncMenuTabs()
        _menuRefresh()          # вернуть обычный вид панели
        _menuPreviewRefresh()
    except Exception:
        _logError('menu closed')


def _menuPush():
    """config.json правили руками: показать это и в окне меню."""
    api = _MENU['api']
    if not _MENU['ok'] or api is None:
        return
    try:
        api.updateModSettings(_MENU_LINKAGE, _menuValues())
    except Exception:
        _logError('menu push')


def _ctl(fn, *args, **kwargs):
    """Построить элемент; если у этой версии API нет какого-то необязательного
    аргумента (tooltip, format) - построить без него."""
    try:
        return fn(*args, **kwargs)
    except TypeError:
        return fn(*args)


def _menuTemplate(tpl, ver, showV3=True):
    new = tuple(ver) >= (2, 0, 0)
    values = _menuValues()
    f2 = '%.2f' if new else '{{value}}'
    f1 = '%.1f' if new else '{{value}}'
    f0 = '%.0f' if new else '{{value}}'

    def defText(key, kind, dfmt=None, labels=None):
        val = DEFAULT_CONFIG.get(key)
        if kind == 'slider':
            try:
                fval = float(val)
            except Exception:
                return None
            if key == 'v3MinWidth' and int(round(fval)) == 0:
                return u'0 (авто)'
            if dfmt == '%.0f':
                return u'%.0f' % fval
            if dfmt == '%.1f':
                return u'%.1f' % fval
            return u'%.2f' % fval
        if kind == 'check':
            return u'Вкл' if bool(val) else u'Выкл'
        if kind == 'color':
            return unicode(val).upper()
        if kind == 'str':
            return unicode(val) if val is not None else u''
        if kind == 'choice' and labels:
            if key == 'battlePanelVariant':
                idx = int(DEFAULT_CONFIG.get('battlePreset', 0))
            elif key in ('previewState', 'previewAlt', 'previewTarget'):
                idx = 0
            else:
                idx = int(val)
            if 0 <= idx < len(labels):
                return labels[idx]
        return None

    def tip(head, body, defaultText=None):
        if new:
            extra = (u'<br><font color="#B8BDC4">По умолчанию:</font> <b>%s</b>' % defaultText) if defaultText is not None else u''
            return u'{HEADER}%s{/HEADER}{BODY}%s%s{/BODY}' % (head, body, extra)
        extra = (u' (по умолчанию: %s)' % defaultText) if defaultText is not None else u''
        return u'%s: %s%s' % (head, body, extra)

    def slider(text, key, low, high, step, fmt, head, body):
        dfmt = '%.0f' if fmt == f0 else ('%.1f' if fmt == f1 else '%.2f')
        return _ctl(tpl.createSlider, text, key, values[key], low, high, step,
                    format=fmt, tooltip=tip(head, body, defText(key, 'slider', dfmt=dfmt)))

    def check(text, key, head, body):
        return _ctl(tpl.createCheckbox, text, key, values[key],
                    tooltip=tip(head, body, defText(key, 'check')))

    def color(text, key, body):
        return _ctl(tpl.createColorChoice, text, key, values[key],
                    tooltip=tip(text, body, defText(key, 'color')))

    def label(text):
        return _ctl(tpl.createLabel, text)

    def gated(control, master, value):
        """Серым, пока переключатель master не равен value (если API умеет)."""
        fn = getattr(tpl, 'enableWhen', None)
        if fn is None:
            return control
        try:
            return fn(control, master, value, indent=False)
        except TypeError:
            try:
                return fn(control, master, value)
            except Exception:
                return control
        except Exception:
            return control

    def vis(control, master, value, cond='=='):
        """Скрыть элемент, пока условие над master не выполнено (для Gameface Mod Menu)."""
        fn = getattr(tpl, 'visibleWhen', None)
        if fn is not None and not isinstance(value, (list, tuple)):
            if cond == '==':
                try:
                    return fn(control, master, value, indent=False)
                except TypeError:
                    try:
                        return fn(control, master, value)
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                try:
                    return fn(control, master, value, indent=False, condition=cond)
                except TypeError:
                    pass
                except Exception:
                    pass
        if new and isinstance(control, dict):
            control['masterVarName'] = master
            control['masterValue'] = list(value) if isinstance(value, tuple) else value
            if cond != '==':
                control['condition'] = cond
            control['gateHides'] = True
            control['masterIndent'] = False
            return control
        return gated(control, master, value)

    def visAll(control, conds):
        """Скрыть элемент, пока не выполнены все условия [(master, value[, cond]), ...]."""
        if new and isinstance(control, dict):
            built = []
            for item in conds:
                if len(item) >= 3:
                    m, v, c = item[0], item[1], item[2]
                else:
                    m, v, c = item[0], item[1], '=='
                entry = {'masterVarName': m,
                         'masterValue': list(v) if isinstance(v, tuple) else v}
                if c != '==':
                    entry['condition'] = c
                built.append(entry)
            control['conditions'] = built
            control['conditionsLogic'] = 'AND'
            control['gateHides'] = True
            control['masterIndent'] = False
            return control
        m, v = conds[-1][0], conds[-1][1]
        return gated(control, m, v)

    def radio(text, key, labels, head, body, inline=False):
        gen = getattr(tpl, 'generateOptions', None)
        opts = gen(list(labels)) if gen is not None else [{'label': s} for s in labels]
        tText = tip(head, body, defText(key, 'choice', labels=labels))
        try:
            return tpl.createRadioButtonGroup(
                text, key, opts, values[key],
                tooltip=tText, inline=inline)
        except TypeError:
            return _ctl(tpl.createRadioButtonGroup, text, key, opts,
                        values[key], tooltip=tText)

    def dropdown(text, key, labels, head, body):
        fn = getattr(tpl, 'createDropdown', None)
        if fn is None:
            return radio(text, key, labels, head, body, inline=False)
        gen = getattr(tpl, 'generateOptions', None)
        opts = gen(list(labels)) if gen is not None else [{'label': s} for s in labels]
        tText = tip(head, body, defText(key, 'choice', labels=labels))
        try:
            return fn(text, key, opts, values[key], tooltip=tText)
        except TypeError:
            try:
                return fn(text, key, opts, values[key])
            except Exception:
                return radio(text, key, labels, head, body, inline=False)
        except Exception:
            return radio(text, key, labels, head, body, inline=False)

    def textInput(text, key, head, body, maxLen=24, width=240):
        tText = tip(head, body, defText(key, 'str'))
        fn = getattr(tpl, 'createInput', None) or getattr(tpl, 'createTextInput', None)
        if fn is not None:
            ctl = _ctl(fn, text, key, values[key], tooltip=tText)
        else:
            ctl = {'type': 'TextInput', 'text': text, 'varName': key, 'value': values[key], 'tooltip': tText}
        if isinstance(ctl, dict):
            ctl['maxLength'] = int(maxLen)
            if width:
                ctl['width'] = int(width)
        return ctl

    def actionBtn(varName, btnText, labelText, head, body, width=148):
        fn = getattr(tpl, 'createActionButton', None)
        if fn is not None:
            try:
                return fn(varName, btnText, label=labelText, width=width, tooltip=tip(head, body))
            except TypeError:
                try:
                    return fn(varName, btnText, label=labelText, tooltip=tip(head, body))
                except Exception:
                    pass
            except Exception:
                pass
        if new:
            comp = {'type': 'Button', 'varName': varName, 'text': labelText,
                    'button': {'name': varName, 'text': btnText, 'width': width, 'align': 'right'}}
            t = tip(head, body)
            if t:
                comp['tooltip'] = t
            return comp
        return label(labelText)

    def tab(title, items):
        fn = getattr(tpl, 'createTab', None) if new else None
        if fn is not None:
            try:
                return fn(title, list(items))
            except Exception:
                pass
        return [label(u'<b>%s</b>' % title)] + list(items)

    tabMain = [
        label(u'<b>Размер и положение (бой)</b>'),
        slider(u'Размер боевой панели', 'uiScale', 0.5, 2.5, 0.05, f2, u'Размер',
               u'Масштаб боевой панели: 1.00 — исходный (масштаб ангарной панели настраивается отдельно во вкладке «Ангар»).'),
        slider(u'Непрозрачность всей панели', 'panelOpacity', 0.0, 1.0, 0.02, f2,
               u'Непрозрачность панели', u'0 — панель невидима, 1 — полностью видима.'),
    ]
    if showV3:
        tabMain.extend([
            vis(dropdown(u'Плотность компоновки', 'v3Density',
                         [u'Компактный', u'Стандартный', u'Крупный'],
                         u'Плотность компоновки',
                         u'Отступы и базовые размеры шрифтов для Варианта 1 («Киберспорт»).'),
                'battlePanelVariant', 0),
            vis(slider(u'Минимальная ширина (0 — авто)', 'v3MinWidth', 0, 360, 10, f0,
                       u'Минимальная ширина',
                       u'0 — ширина подбирается автоматически по содержимому. Иначе задаёт минимум в пикселях.'),
                'battlePanelVariant', 0),
            vis(dropdown(u'Точка привязки при изменении размера', 'v3Anchor',
                         [u'Верх-лево', u'Верх-центр', u'Верх-право',
                          u'Низ-лево', u'Низ-центр', u'Низ-право'],
                         u'Якорь панели',
                         u'Какой край/угол остаётся на месте, когда панель сжимается или расширяется (например, по Alt).'),
                'battlePanelVariant', 0),
        ])
    tabMain.extend([
        label(u'<b>Поведение в бою</b>'),
        check(u'Скрывать панель во вступлении («В центре внимания»)', 'hideInIntro',
              u'Вступление',
              u'Пока перед боем показывают карточки игроков, панель убирается и появляется после отсчёта.'),
        check(u'Скрывать панель на просмотре выстрела (посмертие)', 'hideInKillcam',
              u'Просмотр выстрела',
              u'Когда вас уничтожили и показывают выстрел, панель убирается и возвращается после него.'),
        check(u'Скрывать панель после гибели насовсем', 'hideAfterDeath',
              u'После гибели',
              u'Панель не показывается и при наблюдении за союзниками.'),
    ])
    if showV3:
        tabMain.extend([
            vis(check(u'Скрывать в снайперском прицеле', 'v3HideInSniper',
                      u'Снайперский режим',
                      u'Убирает панель «Киберспорт», пока активен снайперский прицел.'),
                'battlePanelVariant', 0),
        ])
    tabMain.extend([
        label(u'<b>Пороги оценки (+ / 0 / большой +)</b>'),
        slider(u'Считать нулём изменение до', 'zeroBand', 0.0, 1.0, 0.01, f2,
               u'Порог нуля', u'Изменение в пределах этого значения (в процентных пунктах) красится цветом «ноль».'),
        check(u'Большой плюс по урону (а не по росту процента)', 'bigByDamage',
              u'Большой плюс',
              u'Включено: цвет «большой плюс» включается от высокого суммарного урона относительно 95%. Выключено: от роста в п.п.'),
        vis(slider(u'Большой плюс: урон в N раз больше 95%',
                   'bigDamageFactor', 1.0, 6.0, 0.1, f1, u'Множитель урона',
                   u'Например, при 2.0 цвет включится от двойного порога среднего урона на 95%.'),
            'bigByDamage', True),
        vis(slider(u'Большой плюс от роста процента (п.п.)', 'bigFrom', 0.0, 10.0,
                   0.5, f1, u'Большой плюс по проценту',
                   u'С какого роста процента (в процентных пунктах) включается цвет «большой плюс». 0 — выключено.'),
            'bigByDamage', False),
    ])

    tabFrameStars = [
        vis(label(u'<b>Тактическая рамка и подложка</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Стиль рамки', 'v3FrameStyle',
                     [u'Тактическая (уголки + контур)', u'Только уголки',
                      u'Сплошная рамка', u'Без рамки (HUD)'],
                     u'Стиль рамки',
                     u'Тактическая: полупрозрачная подложка, тонкий контур с вырезом под звёзды и белые L-уголки.'),
            'battlePanelVariant', 0),
        visAll(slider(u'Скругление углов рамки', 'v3Radius', 0, 14, 1, f0,
                      u'Скругление углов', u'Радиус скругления подложки и контура в пикселях.'),
               (('battlePanelVariant', 0), ('v3FrameStyle', [0, 1, 2]))),
        visAll(slider(u'Непрозрачность подложки', 'v3BgOpacity', 0.0, 1.0, 0.02, f2,
                      u'Подложка', u'Читаемость на снежных и тёмных картах.'),
               (('battlePanelVariant', 0), ('v3FrameStyle', [0, 1, 2]))),
        visAll(slider(u'Яркость угловых скобок', 'v3CornerAlpha', 0.0, 1.0, 0.05, f2,
                      u'Угловые акценты', u'Непрозрачность белых L-образных скобок по углам.'),
               (('battlePanelVariant', 0), ('v3FrameStyle', [0, 1]))),
        visAll(slider(u'Непрозрачность контура', 'v3BorderAlpha', 0.0, 1.0, 0.02, f2,
                      u'Тонкий периметр', u'Непрозрачность тонкой линии рамки по периметру.'),
               (('battlePanelVariant', 0), ('v3FrameStyle', [0, 2]))),
        vis(label(u'<b>Звёзды отметок</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Расположение звёзд', 'v3StarsPos',
                     [u'Сверху (горизонтально)', u'Снизу (горизонтально)',
                      u'Слева (вертикально)', u'Справа (вертикально)',
                      u'В шапке (рядом с %)', u'Скрыть'],
                     u'Позиция звёзд',
                     u'При включённой рамке звёзды сидят прямо на границе с аккуратным вырезом без лишней разделительной полосы.'),
            'battlePanelVariant', 0),
        visAll(dropdown(u'Стиль звёзд', 'v3StarsStyle',
                        [u'Белые / контур', u'Белые / серые залитые', u'Золотые / контур'],
                        u'Стиль звёзд',
                        u'1-й вариант — яркая ★ / тонкий контур ☆; 2-й — приглушённые серые; 3-й — золотые.'),
               (('battlePanelVariant', 0), ('v3StarsPos', 5, '!='))),
        visAll(check(u'Вертикальный разделитель | (без рамки)', 'v3StarsDivider',
                     u'Вертикальный разделитель',
                     u'Отделяет вертикальные звёзды тонкой линией | в режиме «Без рамки (HUD)».'),
               (('battlePanelVariant', 0), ('v3FrameStyle', 3), ('v3StarsPos', [2, 3]))),
        visAll(slider(u'Размер звёзд', 'v3StarsSize', 10, 22, 1, f0,
                      u'Размер звёзд', u'Диаметр одной звезды в пикселях.'),
               (('battlePanelVariant', 0), ('v3StarsPos', 5, '!='))),
        visAll(slider(u'Расстояние между звёздами', 'v3StarsGap', 2, 14, 1, f0,
                      u'Зазор между звёздами', u'Расстояние между краями соседних звёзд.'),
               (('battlePanelVariant', 0), ('v3StarsPos', 5, '!='))),
        visAll(check(u'Мягкое свечение полученных звёзд', 'v3StarsGlow',
                     u'Свечение звёзд', u'Лёгкий ореол вокруг уже заработанных отметок.'),
               (('battlePanelVariant', 0), ('v3StarsPos', 5, '!='))),
    ]

    tabHeaderBar = [
        vis(label(u'<b>Шапка (% и дельта)</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Порядок элементов шапки', 'v3HeaderOrder',
                     [u'Процент слева, дельта справа',
                      u'Дельта слева, процент справа',
                      u'По центру (% + дельта)'],
                     u'Порядок шапки',
                     u'Позволяет переключить шапку с левого % на правый % или по центру.'),
            'battlePanelVariant', 0),
        vis(dropdown(u'Точность процента', 'v3PctDecimals',
                     [u'Целые (79%)', u'2 знака (78.94%)'],
                     u'Знаки после запятой', u'Целый процент или 2 знака после запятой (стандарт).'),
            'battlePanelVariant', 0),
        vis(dropdown(u'Значок дельты', 'v3DeltaIcon',
                     [u'Треугольники (▲ / ▼)', u'Стрелки (↗ / ↘)',
                      u'Только + / −', u'Скрыть дельту'],
                     u'Индикатор изменения',
                     u'Форма значка изменения отметки или полное скрытие дельты.'),
            'battlePanelVariant', 0),
        visAll(dropdown(u'Цвет дельты', 'v3DeltaColorMode',
                        [u'По изменению (иконка и текст)',
                         u'Нейтральный (приглушённый)'],
                        u'Окраска дельты',
                        u'Подсветка значка и числа цветом изменения (+ / − / 0) либо нейтральный приглушённый цвет.'),
               (('battlePanelVariant', 0), ('v3DeltaIcon', 3, '!='))),
        vis(label(u'<b>Полоска прогресса</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Стиль полоски', 'v3BarStyle',
                     [u'Тактическая (трек + курсор)',
                      u'Пороги 65 / 85 / 95 / 100%',
                      u'Сплошная',
                      u'Без полоски',
                      u'Свой текст (с заполнением)'],
                     u'Стиль полоски прогресса',
                     u'Тактическая: тонкий трек с засечками | — | и ярким маркером. Пороги: 4 сегмента 65 / 85 / 95 / 100%. Свой текст: надпись, заполняемая цветом по мере роста отметки.'),
            'battlePanelVariant', 0),
        visAll(textInput(u'Текст вместо полоски', 'v3BarCustomText',
                         u'Свой текст полоски',
                         u'Текст, который заполняется цветом прогресса отметки (до 24 символов).'),
               (('battlePanelVariant', 0), ('v3BarStyle', 4))),
        visAll(slider(u'Размер текста полоски (px)', 'v3BarTextSize', 10, 26, 1, f0,
                      u'Размер текста полоски', u'Размер шрифта заполняемого текста в пикселях.'),
               (('battlePanelVariant', 0), ('v3BarStyle', 4))),
        visAll(dropdown(u'Масштаб полоски', 'v3BarScale',
                        [u'0 — 100%', u'До следующей отметки'],
                        u'Шкала полоски',
                        u'От общего % (0–100) или внутри текущего интервала до следующей отметки.'),
               (('battlePanelVariant', 0), ('v3BarStyle', 3, '!='))),
        visAll(slider(u'Высота заполненной полоски (px)', 'v3BarHeight', 2, 10, 1, f0,
                      u'Толщина заполненной полоски', u'Высота закрашенной линии прогресса.'),
               (('battlePanelVariant', 0), ('v3BarStyle', [0, 1, 2]))),
        visAll(slider(u'Толщина незаполненной полоски (px)', 'v3BarTrackHeight', 1, 10, 1, f0,
                      u'Толщина пустой белой полоски', u'Высота белой незаполненной линии трека прогресса.'),
               (('battlePanelVariant', 0), ('v3BarStyle', [0, 1, 2]))),
        visAll(dropdown(u'Цвет полоски', 'v3BarColorMode',
                        [u'Тактический зелёный',
                         u'По изменению (+ / − / 0)',
                         u'Свой цвет'],
                        u'Цвет полоски',
                        u'Определяет логику окрашивания заполненной части полоски или текста.'),
               (('battlePanelVariant', 0), ('v3BarStyle', 3, '!='))),
        visAll(check(u'Крайние засечки | — |', 'v3BarEndTicks',
                     u'Засечки по краям', u'Вертикальные ограничители | в начале и в конце полоски.'),
               (('battlePanelVariant', 0), ('v3BarStyle', [0, 2]))),
        visAll(check(u'Вертикальный курсор на значении', 'v3BarCursor',
                     u'Маркер-курсор', u'Яркая светлая риска точно на текущем заполнении полоски.'),
               (('battlePanelVariant', 0), ('v3BarStyle', [0, 1, 2]))),
        visAll(check(u'Риски порогов 65 / 85 / 95%', 'v3BarMarks',
                     u'Отметки 65 / 85 / 95%', u'Тонкие деления на полоске в точках получения 1, 2 и 3 отметок (при шкале 0–100%).'),
               (('battlePanelVariant', 0), ('v3BarStyle', [0, 2]), ('v3BarScale', 0))),
    ]

    tabDmgAssist = [
        vis(label(u'<b>Строка урона</b>'), 'battlePanelVariant', 0),
        vis(check(u'Показывать строку урона', 'v3ShowDamage',
                  u'Строка урона', u'Включает или убирает строку «Набито / Нужно».'),
            'battlePanelVariant', 0),
        visAll(dropdown(u'Подпись строки урона', 'v3DamageLabel',
                        [u'Сум. урон', u'Своя подпись', u'Без подписи'],
                        u'Подпись слева', u'Текст слева от чисел урона: «Сум. урон», своя надпись или без подписи.'),
               (('battlePanelVariant', 0), ('v3ShowDamage', True))),
        visAll(textInput(u'Своя подпись урона', 'v3DamageCustomLabel',
                         u'Своя надпись', u'Произвольный текст слева от чисел урона (до 24 символов).'),
               (('battlePanelVariant', 0), ('v3ShowDamage', True), ('v3DamageLabel', 1))),
        vis(dropdown(u'Разделитель тысяч', 'v3ThousandsSep',
                     [u'Пробел (3 308)', u'Запятая (3,308)', u'Без разделителя (3308)'],
                     u'Формат тысяч', u'Единый разделитель для всех чисел урона и ассиста в Варианте 1 («Киберспорт»).'),
            'battlePanelVariant', 0),
        visAll(check(u'Выделять текущий урон цветом', 'v3DamageDynColor',
                     u'Динамический цвет урона',
                     u'Подсвечивает набранный урон тактическим зелёным при достижении цели или росте, коралловым при падении.'),
               (('battlePanelVariant', 0), ('v3ShowDamage', True))),
        vis(label(u'<b>Каналы ассиста (Засвет и Гусеницы)</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Когда показывать ассист', 'v3AssistShow',
                     [u'Всегда (без Alt)',
                      u'Только при нажатом Alt',
                      u'Скрывать при нажатом Alt',
                      u'Выключено'],
                     u'Показ засвета и гусениц',
                     u'Отдельная настройка показа строки ассиста: постоянно, только по клавише Alt, скрывать по Alt или выключить.'),
            'battlePanelVariant', 0),
        visAll(dropdown(u'Отображаемые каналы', 'v3AssistMode',
                        [u'Засвет + Гусеницы',
                         u'Только активный канал'],
                        u'Режим ассиста',
                        u'Активный канал (максимальный среди засвета и гусениц) автоматически подсвечивается зелёным.'),
               (('battlePanelVariant', 0), ('v3AssistShow', 3, '!='))),
        visAll(dropdown(u'Место строки ассиста', 'v3AssistPlace',
                        [u'Внутри снизу', u'Под панелью'],
                        u'Расположение ассиста', u'Внутри тактической рамки или отдельной строкой под ней.'),
               (('battlePanelVariant', 0), ('v3AssistShow', 3, '!='))),
        visAll(check(u'Скрывать нулевые каналы', 'v3AssistHideZero',
                     u'Скрывать нули', u'Прячет каналы со значением 0, чтобы виджет был компактнее.'),
               (('battlePanelVariant', 0), ('v3AssistShow', 3, '!='))),
        vis(label(u'<b>Темп на отметку (средний урон до цели и 95%)</b>'), 'battlePanelVariant', 0),
        vis(dropdown(u'Когда показывать темп', 'v3TempoShow',
                     [u'Всегда (без Alt)',
                      u'Только при нажатом Alt',
                      u'Скрывать при нажатом Alt',
                      u'Выключено'],
                     u'Показ темпа на отметку',
                     u'Отдельная настройка показа темпа (независимо от засвета и гусениц): постоянно, только при нажатом Alt, скрывать по Alt или выключить.'),
            'battlePanelVariant', 0),
        visAll(dropdown(u'Отображаемые пороги темпа', 'v3TempoMode',
                        [u'До следующей отметки + 95%',
                         u'Только до следующей отметки',
                         u'Только на 3 отметку (95%)'],
                        u'Выбор порогов темпа',
                        u'Сколько суммарного урона нужно держать на следующую отметку (65 / 85 / 95 / 100%) и/или на 3 отметку (95%). При выполнении темпа в бою подсвечивается зелёным.'),
               (('battlePanelVariant', 0), ('v3TempoShow', 3, '!='))),
        visAll(dropdown(u'Место строки темпа', 'v3TempoPlace',
                        [u'Внутри снизу', u'Под панелью'],
                        u'Расположение темпа',
                        u'Снизу внутри рамки или под панелью. Автоматически располагается отдельной строкой от засвета и гусениц, чтобы они не мешали друг другу.'),
               (('battlePanelVariant', 0), ('v3TempoShow', 3, '!='))),
    ]

    tabColorsV3 = [
        vis(label(u'<b>Акцентные цвета (Вариант 1 — Киберспорт)</b>'), 'battlePanelVariant', 0),
        vis(color(u'Плюс (тактический зелёный)', 'v3AccentPlus',
                  u'Цвет роста дельты, активной полоски и лидирующего канала ассиста.'),
            'battlePanelVariant', 0),
        vis(color(u'Минус (коралловый)', 'v3AccentMinus',
                  u'Цвет снижения отметки.'),
            'battlePanelVariant', 0),
        vis(color(u'Ноль (нейтральный)', 'v3AccentZero',
                  u'Цвет нулевого изменения.'),
            'battlePanelVariant', 0),
        vis(color(u'Большой плюс (рекорд)', 'v3AccentBig',
                  u'Цвет рекордно высокого роста/урона.'),
            'battlePanelVariant', 0),
        visAll(color(u'Свой цвет полоски', 'v3BarCustomColor',
                     u'Используется, когда цвет полоски выставлен в «Свой цвет».'),
               (('battlePanelVariant', 0), ('v3BarColorMode', 2))),
        vis(label(u'<b>Рамка, текст и звёзды (Киберспорт)</b>'), 'battlePanelVariant', 0),
        vis(color(u'Основной текст (процент и числа)', 'v3TextMain',
                  u'Цвет крупного процента и основных значений.'),
            'battlePanelVariant', 0),
        vis(color(u'Приглушённый текст (подписи)', 'v3TextMuted',
                  u'Цвет подписи урона, целевого числа и неактивного ассиста.'),
            'battlePanelVariant', 0),
        vis(color(u'Угловые скобки и контур рамки', 'v3CornerColor',
                  u'Цвет L-уголков, тонкой рамки и разделителя звёзд.'),
            'battlePanelVariant', 0),
        vis(color(u'Подложка фона', 'v3BgColor',
                  u'Базовый тёмный тон подложки панели.'),
            'battlePanelVariant', 0),
        vis(color(u'Полученная звезда', 'v3StarOnColor',
                  u'Цвет заливки заработанных отметок.'),
            'battlePanelVariant', 0),
        vis(color(u'Неполученная звезда', 'v3StarOffColor',
                  u'Цвет контура или приглушённой заливки незаработанных отметок.'),
            'battlePanelVariant', 0),
    ]

    tabColorsLegacy = [
        vis(label(u'<b>Изменение отметки (Вариант 2 — Отметка Корбена)</b>'), 'battlePanelVariant', 1),
        vis(color(u'Плюс', 'colorPlus', u'Цвет, когда процент растёт.'), 'battlePanelVariant', 1),
        vis(color(u'Минус', 'colorMinus', u'Цвет, когда процент падает.'), 'battlePanelVariant', 1),
        vis(color(u'Ноль', 'colorZero', u'Цвет, когда изменение около нуля.'), 'battlePanelVariant', 1),
        vis(color(u'Большой плюс', 'colorBig', u'Цвет при большом росте.'), 'battlePanelVariant', 1),
        vis(label(u'<b>Текст и числа (Отметка Корбена)</b>'), 'battlePanelVariant', 1),
        vis(check(u'Число урона по цвету изменения', 'dmgFollowsSign',
                  u'Цвет числа урона',
                  u'Число набитого урона берёт цвет изменения (+ / − / 0).'),
            'battlePanelVariant', 1),
        visAll(color(u'Число урона', 'colorDmg',
                     u'Цвет числа набитого урона, когда отключён цвет по изменению.'),
               (('battlePanelVariant', 1), ('dmgFollowsSign', False))),
        vis(color(u'Прогнозное среднее («/ нужно»)', 'colorProj', u'Цвет «/ нужно» справа от набитого урона.'),
            'battlePanelVariant', 1),
        vis(color(u'Большой процент (без изменения)', 'pctColor',
                  u'Цвет процента до первого выстрела/изменения.'),
            'battlePanelVariant', 1),
    ]

    tabHangar = [
        label(u'<b>Панель в ангаре (стиль «Киберспорт»)</b>'),
        check(u'Показывать панель в ангаре', 'hangarPanel',
              u'Панель в ангаре', u'Включает или выключает виджет отметок в ангаре.'),
        vis(slider(u'Размер панели в ангаре', 'vhScale', 0.5, 2.5, 0.05, f2,
                   u'Масштаб в ангаре', u'Отдельный размер панели в ангаре (независимо от боевой панели).'),
            'hangarPanel', True),
        vis(dropdown(u'Плотность компоновки (ангар)', 'vhDensity',
                     [u'Компактный', u'Стандартный', u'Крупный'],
                     u'Плотность в ангаре', u'Отступы и размеры шрифтов ангарной панели.'),
            'hangarPanel', True),
        vis(label(u'<b>Рамка и звёзды (ангар)</b>'), 'hangarPanel', True),
        vis(dropdown(u'Стиль рамки (ангар)', 'vhFrameStyle',
                     [u'Тактическая (уголки + контур)', u'Только уголки',
                      u'Сплошная рамка', u'Без рамки (HUD)'],
                     u'Рамка в ангаре', u'Стиль тактической рамки ангарной панели.'),
            'hangarPanel', True),
        visAll(slider(u'Скругление углов рамки (ангар)', 'vhRadius', 0, 14, 1, f0,
                      u'Скругление углов', u'Радиус скругления углов рамки в ангаре.'),
               (('hangarPanel', True), ('vhFrameStyle', [0, 1, 2]))),
        visAll(slider(u'Непрозрачность подложки (ангар)', 'vhBgOpacity', 0.0, 1.0, 0.02, f2,
                      u'Подложка в ангаре', u'Непрозрачность тёмного фона ангарной панели.'),
               (('hangarPanel', True), ('vhFrameStyle', [0, 1, 2]))),
        visAll(slider(u'Яркость угловых скобок (ангар)', 'vhCornerAlpha', 0.0, 1.0, 0.05, f2,
                      u'Угловые скобки', u'Яркость L-уголков по краям ангарной панели.'),
               (('hangarPanel', True), ('vhFrameStyle', [0, 1]))),
        visAll(slider(u'Непрозрачность контура (ангар)', 'vhBorderAlpha', 0.0, 1.0, 0.02, f2,
                      u'Контур рамки', u'Непрозрачность тонкой линии периметра ангарной панели.'),
               (('hangarPanel', True), ('vhFrameStyle', [0, 2]))),
        vis(dropdown(u'Расположение звёзд (ангар)', 'vhStarsPos',
                     [u'Сверху (горизонтально)', u'Снизу (горизонтально)',
                      u'Слева (вертикально)', u'Справа (вертикально)',
                      u'В шапке (рядом с %)', u'Скрыть'],
                     u'Звёзды в ангаре', u'Позиция звёзд отметок на ангарной панели.'),
            'hangarPanel', True),
        visAll(dropdown(u'Стиль звёзд (ангар)', 'vhStarsStyle',
                        [u'Белые / контур', u'Белые / серые залитые', u'Золотые / контур'],
                        u'Стиль звёзд в ангаре', u'Оформление полученных и неполученных звёзд.'),
               (('hangarPanel', True), ('vhStarsPos', 5, '!='))),
        visAll(check(u'Вертикальный разделитель | (без рамки, ангар)', 'vhStarsDivider',
                     u'Разделитель звёзд', u'Тонкая вертикальная линия при боковых звёздах без рамки.'),
               (('hangarPanel', True), ('vhFrameStyle', 3), ('vhStarsPos', [2, 3]))),
        visAll(slider(u'Размер звёзд (ангар)', 'vhStarsSize', 10, 22, 1, f0,
                      u'Размер звёзд', u'Диаметр одной звезды в ангаре.'),
               (('hangarPanel', True), ('vhStarsPos', 5, '!='))),
        visAll(slider(u'Расстояние между звёздами (ангар)', 'vhStarsGap', 2, 14, 1, f0,
                      u'Отступ звёзд', u'Зазор между звёздами в ангаре.'),
               (('hangarPanel', True), ('vhStarsPos', 5, '!='))),
        visAll(check(u'Мягкое свечение полученных звёзд (ангар)', 'vhStarsGlow',
                     u'Свечение звёзд', u'Мягкий ореол вокруг заработанных звёзд в ангаре.'),
               (('hangarPanel', True), ('vhStarsPos', 5, '!='))),
        vis(label(u'<b>Полоска и данные (65 / 85 / 95 / 100%)</b>'), 'hangarPanel', True),
        vis(dropdown(u'Точность процента (ангар)', 'vhPctDecimals',
                     [u'Целые (79%)', u'2 знака (78.94%)'],
                     u'Точность процента', u'Количество знаков после запятой в ангаре.'),
            'hangarPanel', True),
        vis(dropdown(u'Стиль полоски (ангар)', 'vhBarStyle',
                     [u'Тактическая (трек + курсор)',
                      u'Пороги 65 / 85 / 95 / 100%',
                      u'Сплошная',
                      u'Без полоски',
                      u'Свой текст (с заполнением)'],
                     u'Стиль полоски в ангаре', u'Вид полоски прогресса или заполняемого текста на ангарной панели.'),
            'hangarPanel', True),
        visAll(textInput(u'Текст вместо полоски (ангар)', 'vhBarCustomText',
                         u'Свой текст полоски в ангаре',
                         u'Текст, который заполняется цветом прогресса отметки в ангаре (до 24 символов).'),
               (('hangarPanel', True), ('vhBarStyle', 4))),
        visAll(slider(u'Размер текста полоски (px, ангар)', 'vhBarTextSize', 10, 26, 1, f0,
                      u'Размер текста полоски', u'Размер шрифта заполняемого текста в ангаре.'),
               (('hangarPanel', True), ('vhBarStyle', 4))),
        visAll(dropdown(u'Масштаб полоски (ангар)', 'vhBarScale',
                        [u'0 — 100%', u'До следующей отметки'],
                        u'Шкала полоски в ангаре', u'Полная шкала 0–100% или прогресс внутри текущего интервала.'),
               (('hangarPanel', True), ('vhBarStyle', 3, '!='))),
        visAll(slider(u'Высота заполненной полоски (px, ангар)', 'vhBarHeight', 2, 10, 1, f0,
                      u'Высота полоски', u'Толщина заполненной части полоски в ангаре.'),
               (('hangarPanel', True), ('vhBarStyle', [0, 1, 2]))),
        visAll(slider(u'Толщина незаполненной полоски (px, ангар)', 'vhBarTrackHeight', 1, 10, 1, f0,
                      u'Толщина белой полоски', u'Толщина пустой белой части полоски в ангаре.'),
               (('hangarPanel', True), ('vhBarStyle', [0, 1, 2]))),
        visAll(check(u'Крайние засечки | — | (ангар)', 'vhBarEndTicks',
                     u'Засечки по краям', u'Вертикальные ограничители в начале и конце полоски.'),
               (('hangarPanel', True), ('vhBarStyle', [0, 2]))),
        visAll(check(u'Вертикальный курсор на значении (ангар)', 'vhBarCursor',
                     u'Курсор полоски', u'Яркая вертикальная риска на текущем проценте.'),
               (('hangarPanel', True), ('vhBarStyle', [0, 1, 2]))),
        visAll(check(u'Риски порогов 65 / 85 / 95% (ангар)', 'vhBarMarks',
                     u'Деления порогов', u'Тонкие деления 65 / 85 / 95% на полоске в ангаре.'),
               (('hangarPanel', True), ('vhBarStyle', [0, 2]), ('vhBarScale', 0))),
        vis(check(u'Показывать строку «Ср. урон»', 'vhShowEma',
                  u'Текущий средний урон', u'Показывает текущее скользящее среднее суммарного урона танка.'),
            'hangarPanel', True),
        vis(check(u'Показывать пороги отметок (65 / 85 / 95 / 100%)', 'vhShowThresholds',
                  u'Таблица порогов в ангаре', u'Показывает требуемый средний урон для 65%, 85%, 95% и 100%.'),
            'hangarPanel', True),
        vis(dropdown(u'Разделитель тысяч (ангар)', 'vhThousandsSep',
                     [u'Пробел (3 308)', u'Запятая (3,308)', u'Без разделителя (3308)'],
                     u'Формат чисел в ангаре', u'Разделитель тысяч для среднего урона и порогов в ангаре.'),
            'hangarPanel', True),
        vis(label(u'<b>Цвета панели в ангаре</b>'), 'hangarPanel', True),
        vis(color(u'Цвет полоски и акцента (ангар)', 'vhBarColor',
                  u'Цвет заполненной полоски, числа «Ср. урон» и уже выполненных порогов отметок.'),
            'hangarPanel', True),
        vis(color(u'Основной текст (процент и пороги, ангар)', 'vhTextMain',
                  u'Цвет крупного процента и значений порогов 65 / 85 / 95 / 100%.'),
            'hangarPanel', True),
        vis(color(u'Приглушённый текст (подписи, ангар)', 'vhTextMuted',
                  u'Цвет подписей «Ср. урон» и «65% / 85% / 95% / 100%».'),
            'hangarPanel', True),
        vis(color(u'Угловые скобки и контур рамки (ангар)', 'vhCornerColor',
                  u'Цвет L-уголков, тонкой рамки и разделительной линии в ангаре.'),
            'hangarPanel', True),
        vis(color(u'Подложка фона (ангар)', 'vhBgColor',
                  u'Цвет тёмной подложки ангарной панели.'),
            'hangarPanel', True),
        vis(color(u'Полученная звезда (ангар)', 'vhStarOnColor',
                  u'Цвет заработанных звёзд в ангаре.'),
            'hangarPanel', True),
        vis(color(u'Неполученная звезда (ангар)', 'vhStarOffColor',
                  u'Цвет контура или заливки неполученных звёзд в ангаре.'),
            'hangarPanel', True),
    ]

    if showV3:
        tabColors = tabColorsV3 + tabColorsLegacy
        col1 = (tab(u'Основное', tabMain) +
                tab(u'Рамка и звёзды', tabFrameStars) +
                tab(u'Шапка и полоска', tabHeaderBar) +
                tab(u'Урон и ассист', tabDmgAssist) +
                tab(u'Цвета', tabColors) +
                tab(u'Ангар', tabHangar))
    else:
        tabColors = tabColorsLegacy
        col1 = (tab(u'Основное', tabMain) +
                tab(u'Цвета', tabColors) +
                tab(u'Ангар', tabHangar))

    previewSource, _bw, _bh, previewW, previewH = _menuPreviewRender()
    _PREVIEW['source'] = previewSource
    _PREVIEW['key'] = (previewSource, previewW, previewH)
    col2 = [
        label(u'<b>Предпросмотр панели</b>'),
        {'type': 'Image', 'varName': 'marksLivePreview',
         'source': previewSource,
         'width': previewW, 'height': previewH,
         'align': 'center', 'valign': 'center',
         'containerWidth': _PREVIEW_CONTAINER_W,
         'containerHeight': _PREVIEW_CONTAINER_H},
        radio(u'<b>Режим предпросмотра</b>', 'previewTarget',
              [u'Боевая панель', u'Панель в ангаре'],
              u'Что показывать на превью',
              u'Переключает картинку предпросмотра между боевой панелью и панелью в ангаре (с порогами 65 / 85 / 95 / 100%).',
              inline=True),
        radio(u'<b>Состояние отметки (превью)</b>', 'previewState',
              [u'Плюс (+)', u'Минус (−)', u'Ноль (0)', u'Большой +'],
              u'Состояние для предпросмотра',
              u'Переключает пример (0 / 1 / 2 / 3 звезды: 43.28% / 70.64% / 85.47% / 97.83%) на картинке выше.',
              inline=True),
    ]
    if showV3:
        col2.append(
            vis(radio(u'<b>Клавиша Alt (превью)</b>', 'previewAlt',
                      [u'Без Alt (обычный вид)', u'Зажат Alt'],
                      u'Проверка нажатия Alt',
                      u'Позволяет прямо на превью выше посмотреть, как выглядит боевая панель без Alt и при нажатом Alt (также можно просто зажать Alt на клавиатуре).',
                      inline=True),
                'battlePanelVariant', 0))
    col2.append(
        radio(u'<b>Вариант боевой панели</b>', 'battlePanelVariant',
              [u'Вариант 1 — Киберспорт',
               u'Вариант 2 — Отметка Корбена'],
              u'Вариант боевой панели',
              u'Вариант 1 (Киберспорт): тактическая рамка, звёзды, гибкие полоски, ассист и темп. '
              u'Вариант 2 (Отметка Корбена): минималистичный крупный % и строка «набито / нужно».',
              inline=False))
    if showV3:
        col2.append(
            vis(actionBtn('v3ResetPreset', u'Сбросить Вариант 1', u'Эталон «Киберспорт»',
                          u'Сброс настроек Варианта 1',
                          u'Возвращает все визуальные настройки боевой панели «Киберспорт» к виду по умолчанию.'),
                'battlePanelVariant', 0))
    col2.extend([
        actionBtn('vhResetPreset', u'Сбросить ангар', u'Эталон панели в ангаре',
                  u'Сброс настроек ангарной панели',
                  u'Возвращает все визуальные настройки панели в ангаре к виду по умолчанию.'),
        actionBtn('resetPosition', u'Сбросить позицию', u'Позиция панели в бою',
                  u'Сброс боевой позиции',
                  u'Возвращает боевую панель на стандартные координаты на экране.'),
        actionBtn('resetHangarPosition', u'Сбросить позицию', u'Позиция панели в ангаре',
                  u'Сброс позиции в ангаре',
                  u'Возвращает ангарную панель на стандартные координаты на экране.'),
    ])
    return {'modDisplayName': u'Три отметки на стволе',
            'modVersion': MOD_VERSION,
            'column1': col1, 'column2': col2}


def _menuSwapPanel():
    """Меню есть - встроенная страница настроек не нужна (кнопка скрывается)."""
    try:
        panel = g_hangar._panel
        if panel is not None and panel.settings is not None:
            panel.closeSettings()
            panel.settings = None
    except Exception:
        _logError('menu swap')


def _registerMenu():
    """Один раз зарегистрироваться в Mod Menu. Можно звать сколько угодно:
    повторяет попытки редко и не более шести раз."""
    if _MENU['ok'] or _MENU['busy']:
        return _MENU['ok']
    now = time.time()
    if now < _MENU['next'] or _MENU['tries'] >= 6:
        return False
    _MENU['tries'] += 1
    _MENU['next'] = now + 5.0
    _MENU['busy'] = True
    try:
        api, tpl = _menuImport()
        if api is None or tpl is None:
            _logOnce('menu-none', 'Mod Menu / ModsSettingsAPI not found: the built-in settings page is used')
            return False
        try:
            ver = tuple(api.getVersionTuple())
        except Exception:
            ver = (1, 0, 0)
        template = _menuTemplate(tpl, ver, showV3=True)
        try:
            saved = api.setModTemplate(_MENU_LINKAGE, template, _onMenuApplied, _onMenuButton)
        except TypeError:
            saved = api.setModTemplate(_MENU_LINKAGE, template, _onMenuApplied)
            try:
                evBtn = getattr(api, 'onButtonClicked', None)
                if evBtn is not None:
                    evBtn += _onMenuButton
            except Exception:
                _logError('menu button register')
        _MENU.update(api=api, tpl=tpl, ver=ver, template=template,
                     fullTemplate=template, tplV3=True, ok=True)
        try:
            api.setModDefaults(_MENU_LINKAGE, _menuDefaults())
        except Exception:
            _logError('menu defaults')
        try:
            api.registerLiveSettingsChange(_MENU_LINKAGE, _onMenuLive, True)
        except Exception:
            _logError('menu live register')
        try:
            api.onWindowClosed += _onMenuClosed
        except Exception:
            _logError('menu closed register')
        try:
            api.onWindowOpened += _onMenuOpened
        except Exception:
            _logOnce('noopened', 'Mod Menu has no onWindowOpened: the preview starts with the first change')
        _log('Mod Menu: registered (API %s, %s)' % (
            '.'.join(str(v) for v in ver), type(api).__module__))
        try:
            _log('Mod Menu: first values %r' % dict(
                (k, saved[k]) for k in ('battlePanelVariant', 'colorPlus', 'uiScale', 'glow') if k in saved))
        except Exception:
            pass
        # значения, сохранённые самим меню, главнее config.json
        _applyMenuSettings(saved, True)
        _syncMenuTabs()
        _PREVIEW['key'] = None
        _menuPreviewRefresh()
        _menuSwapPanel()
        return True
    except Exception:
        _logError('mod menu register')
        return False
    finally:
        _MENU['busy'] = False


def _unregisterMenu():
    api = _MENU['api']
    if api is None:
        return
    try:
        api.unregisterLiveSettingsChange(_MENU_LINKAGE, _onMenuLive)
    except Exception:
        pass
    try:
        evBtn = getattr(api, 'onButtonClicked', None)
        if evBtn is not None:
            evBtn -= _onMenuButton
    except Exception:
        pass
    try:
        api.onWindowClosed -= _onMenuClosed
    except Exception:
        pass
    try:
        api.onWindowOpened -= _onMenuOpened
    except Exception:
        pass


_DEAD_MODES = ('postmortem', 'deathfreecam', 'killcam', 'deathcam')


def _ctrlModeName():
    """Имя текущего режима камеры/управления (пустое, если неизвестно). Каждое
    новое имя пишется в журнал один раз."""
    try:
        player = BigWorld.player()
        handler = getattr(player, 'inputHandler', None) if player is not None else None
        name = str(getattr(handler, 'ctrlModeName', '') or '')
    except Exception:
        return ''
    if name:
        _logOnce(('ctrlmode', name), 'battle control mode: %s' % name)
    return name


def _introActive():
    """(идёт ли вступление «В центре внимания» перед боем, чем определено).
    У вступления свой режим камеры: prebattleHighlights (виден в журнале)."""
    name = _ctrlModeName()
    if name and 'prebattle' in name.replace('_', '').lower():
        return True, 'control mode %s' % name
    return False, ''


def _killcamActive():
    """(идёт ли просмотр выстрела, чем определено). Это отдельный режим
    камеры, в который игра переключает после гибели; затем наблюдение
    (postmortem). Имя режима в клиенте мне неизвестно наверняка, поэтому
    узнаём по частям 'kill' / 'death' (кроме свободной камеры); все режимы
    пишутся в журнал."""
    name = _ctrlModeName()
    if not name:
        return False, ''
    low = name.replace('_', '').lower()
    if 'kill' in low or ('death' in low and low != 'deathfreecam'):
        return True, 'control mode %s' % name
    return False, ''


def _playerDead():
    """(уничтожена ли машина игрока, чем определено). Несколько независимых
    признаков: ни один из них я не мог проверить в клиенте, поэтому работает
    любой; режим камеры пишется в журнал, чтобы список можно было уточнить."""
    try:
        state = _sessionProvider.shared.vehicleState
        if state is not None and getattr(state, 'isInPostmortem', False):
            return True, 'vehicleState.isInPostmortem'
    except Exception:
        pass
    player = BigWorld.player()
    if player is None:
        return False, ''
    try:
        if getattr(player, 'isVehicleAlive', None) is False:
            return True, 'avatar.isVehicleAlive'
    except Exception:
        pass
    try:
        handler = getattr(player, 'inputHandler', None)
        name = str(getattr(handler, 'ctrlModeName', '') or '')
        if name:
            _logOnce(('ctrlmode', name), 'battle control mode: %s' % name)
            if name.replace('_', '').lower() in _DEAD_MODES:
                return True, 'control mode %s' % name
    except Exception:
        pass
    return False, ''


def _panelDragPoll(owner, panel, minKey):
    """Ctrl+ЛКМ: перетаскивание; клик по кнопке -/+ сворачивает панель."""
    if not g_config.get('dragEnabled', True) or panel is None:
        return
    if getattr(panel, '_dim', False):
        owner._drag = None
        return
    try:
        mc = GUI.mcursor()
        if not getattr(mc, 'visible', False):
            owner._drag = None
            return
        pos = mc.position
        px, py = float(pos[0]), float(pos[1])
        down = BigWorld.isKeyDown(Keys.KEY_LEFTMOUSE)
        ctrl = (BigWorld.isKeyDown(Keys.KEY_LCONTROL) or
                BigWorld.isKeyDown(Keys.KEY_RCONTROL))
        st = getattr(panel, 'settings', None)
        if st is not None and _settingsPoll(owner, panel, st, px, py, down, ctrl):
            return
        if down:
            if owner._drag is None and not getattr(owner, '_btnPress', False):
                if ctrl and panel.contains((px, py)):
                    owner._drag = (px - panel.x, py - panel.y)
                    owner._dragFrom = (px, py)
                    owner._dragMoved = False
                elif minKey is not None and _panelInButton(panel, px, py):
                    # клик по кнопке работает и без Ctrl
                    owner._btnPress = True
            elif owner._drag is not None:
                if not getattr(owner, '_dragMoved', False):
                    fx, fy = getattr(owner, '_dragFrom', (px, py))
                    if abs(px - fx) > _pxW(5) or abs(py - fy) > _pxH(5):
                        owner._dragMoved = True
                if getattr(owner, '_dragMoved', False):
                    panel.moveTo(px - owner._drag[0], py - owner._drag[1])
        elif getattr(owner, '_btnPress', False):
            owner._btnPress = False
            if minKey is not None and _panelInButton(panel, px, py):
                g_config[minKey] = not g_config.get(minKey, False)
                owner._needRefresh = True
                _saveJson(CONFIG_PATH, g_config)
        elif owner._drag is not None:
            owner._drag = None
            if getattr(owner, '_dragMoved', False):
                g_config[panel.keyX] = round(panel.x, 4)
                g_config[panel.keyY] = round(panel.y, 4)
                _saveJson(CONFIG_PATH, g_config)
            elif minKey is not None and \
                    _panelInButton(panel, *getattr(owner, '_dragFrom', (px, py))):
                g_config[minKey] = not g_config.get(minKey, False)
                owner._needRefresh = True
                _saveJson(CONFIG_PATH, g_config)
    except Exception:
        owner._drag = None


# ==========================================================================
# HTML-панель (Gameface)

if _GF_OK:

    class _TmModel(ViewModel):

        def __init__(self, payload):
            self.__payload = payload
            super(_TmModel, self).__init__(properties=1, commands=1)

        def _initialize(self):
            super(_TmModel, self)._initialize()
            self._addStringProperty('payload', self.__payload)
            self.onReady = self._addCommand('onReady')

        def setPayload(self, value):
            self._setString(0, value)


    class _TmView(ViewImpl):

        def __init__(self, owner):
            self.__owner = owner
            model = _TmModel(owner.payload)
            owner.model = model
            settings = ViewSettings(layoutID=_GF_LAYOUT(),
                                    flags=ViewFlags.VIEW, model=model)
            super(_TmView, self).__init__(settings)

        def _getEvents(self):
            model = self.getViewModel()
            return ((model.onReady, self.__onReady),)

        @args2params(str)
        def __onReady(self, message):
            self.__owner.onJsReady()

        def _finalize(self):
            self.__owner.model = None
            super(_TmView, self)._finalize()


    class _TmWindow(WindowImpl):

        def __init__(self, content, parent):
            # слой WINDOW - как у панелей GUIFlash: меню и диалоги рисуются выше
            super(_TmWindow, self).__init__(
                WindowFlags.WINDOW, content=content,
                layer=WindowLayer.WINDOW, name='ThreeMarksPanel',
                parent=parent)

        def _onReady(self):
            # Like the reference overlay, do not take battle keyboard focus.
            self.show(False)


    def _windowAlive(window):
        try:
            return (window is not None and window.proxy is not None and
                    window.windowStatus not in _GONE_WINDOW_STATUSES)
        except Exception:
            return False


    def _battleIsCovered(ownWindow):
        """Detect battle overlays/scoreboard and modal views like app.gunmarks."""
        try:
            windowsManager = dependency.instance(IGuiLoader).windowsManager
            windows = []
            seenIDs = set()

            def addWindow(window):
                if window is None:
                    return
                try:
                    uniqueID = window.uniqueID
                except Exception:
                    return
                if uniqueID not in seenIDs:
                    seenIDs.add(uniqueID)
                    windows.append(window)

            try:
                for window in windowsManager.findWindows(lambda item: True) or ():
                    addWindow(window)
            except Exception:
                pass
            try:
                for view in windowsManager.findViews(lambda item: True) or ():
                    try:
                        addWindow(view.getParentWindow())
                    except Exception:
                        pass
            except Exception:
                pass

            for window in windows:
                if window is ownWindow:
                    continue
                try:
                    if (window.layer in _COVERING_LAYERS and
                            window.windowStatus == WindowStatus.LOADED and
                            not bool(window.isHidden())):
                        return True
                except Exception:
                    pass

            # Some battle views (including unparented client overlays) are
            # Scaleform views and are not returned by windowsManager.
            try:
                from skeletons.gui.app_loader import IAppLoader
                app = dependency.instance(IAppLoader).getDefBattleApp()
                containerManager = getattr(app, 'containerManager', None) \
                    if app is not None else None
                if containerManager is not None:
                    for layer in _COVERING_LAYERS:
                        container = containerManager.getContainer(layer)
                        if container is not None and container.getViewCount():
                            return True
                    if containerManager.isModalViewsIsExists():
                        return True
            except Exception:
                pass
        except Exception:
            pass
        return False


    class _GfPanel(object):

        def __init__(self, mode='b', keyX='x', keyY='y',
                     wPx=_WINDOW_W, hPx=_WINDOW_H):
            self.mode = mode
            self.keyX = keyX
            self.keyY = keyY
            self.x = float(g_config[keyX])
            self.y = float(g_config[keyY])
            self._baseW = float(wPx)
            self._baseH = float(hPx)
            self.ui = 1.0
            self.settings = None
            self._geoKey = None
            self._restoreY = None
            self.wPx = float(wPx)
            self.hPx = float(hPx)
            self.payload = '{}'
            self.mini = False
            self.model = None
            self.window = None
            self._token = 0
            self._ready = False
            self._lastMove = None
            self._destroyed = False
            self._covered = False
            self._visible = True
            self._dim = False

        def build(self):
            self._destroyed = False
            if self.window is not None:
                return
            self._token += 1
            token = self._token
            # Resource declarations are loaded by the WG client before this
            # Python module is initialized, so no res_map validation/restart
            # phase is required on 2.4.1 and newer.
            self._load(token)

        def _load(self, token, retry=0):
            if token != self._token or self._destroyed:
                return
            parent = dependency.instance(IGuiLoader).windowsManager.getMainWindow()
            if parent is None or parent.proxy is None or \
                    parent.windowStatus != WindowStatus.LOADED:
                if retry < 100:
                    BigWorld.callback(0.1, lambda: self._load(token, retry + 1))
                else:
                    _logOnce('nomainwindow', 'panel: main window never became ready')
                return
            try:
                self.window = _TmWindow(_TmView(self), parent)
                self.window.load()
            except Exception:
                _logError('panel window')

        def onJsReady(self):
            self._ready = True
            self._publish(force=True)
            self._move(force=True)

        def push(self, data):
            st = self.settings
            editing = st is not None and st.open
            if editing:
                data = {'set': st.items, 'setH': _SET_H}
                data['mode'] = 's'
            else:
                data['mode'] = self.mode
            data['dim'] = bool(self._dim) and not editing
            data['cfg'] = self.settings is not None
            data['ui'] = _uiPayload()
            if editing:
                data['ui']['s'] = 1.0       # страница настроек не масштабируется
            battleView = not editing and data.get('mode') == 'b'
            hangarView = not editing and data.get('mode') == 'h'
            preset = int(data['ui'].get('preset', 0)) if battleView else 0
            if (battleView and preset == 0) or hangarView:
                v3d = data.get('v3d') or _PREVIEW_SAMPLES_V3['plus']
                if hangarView:
                    v3d = dict(v3d)
                    v3d['isHangar'] = True
                    mCfg = _vhToV3Cfg(g_config)
                    uiScaleVal = float(data['ui'].get('hs', data['ui']['s']))
                    anchor = 0
                else:
                    mCfg = g_config
                    uiScaleVal = float(data['ui']['s'])
                    anchor = _cfgInt('v3Anchor', 0, 5)
                m = _v3Metrics(mCfg, v3d, alt=bool(v3d.get('alt', False)))
                data['v3m'] = [m['winW'], m['winH']]
                geo = (uiScaleVal, editing, 'vh' if hangarView else 'v3', m['winW'], m['winH'])
                if geo != self._geoKey:
                    prevGeo = self._geoKey
                    self._geoKey = geo
                    self.ui = uiScaleVal
                    newW = float(m['winW']) * self.ui
                    newH = float(m['winH']) * self.ui
                    dx, dy = 0.0, 0.0
                    if prevGeo is not None and (self.wPx, self.hPx) != (newW, newH):
                        dW = _pxW(newW - self.wPx)
                        dH = _pxH(newH - self.hPx)
                        dx = 0.0 if anchor in (0, 3) else (-0.5 * dW if anchor in (1, 4) else -dW)
                        dy = 0.0 if anchor in (0, 1, 2) else dH
                    self.wPx = newW
                    self.hPx = newH
                    self.moveTo(self.x + dx, self.y + dy)
            else:
                pctOnly = battleView and bool(data['ui'].get('onlyPct', True))
                ast = ((not editing) and self.mode == 'b' and
                       ('ast' in data) and not pctOnly)
                geo = (data['ui']['s'], editing, ast, pctOnly)
                if geo != self._geoKey:
                    self._geoKey = geo
                    self.ui = data['ui']['s']
                    baseH = (_SET_H + 24.0) if editing else (
                            (_PCT_WINDOW_H if pctOnly else self._baseH) +
                            (22.0 if ast else 0.0))
                    baseW = _PCT_WINDOW_W if pctOnly else self._baseW
                    self.wPx = baseW * self.ui
                    self.hPx = baseH * self.ui
                    self.moveTo(self.x, self.y)
            payload = json.dumps(data, ensure_ascii=True)
            if payload != self.payload:
                self.payload = payload
                self._publish()
            self._move()

        def render(self, shownPct, barPct, delta, dmg, projEma, marks,
                   glowing, hasRating, big=False, assist=None, v3d=None):
            if hasRating:
                pctTxt = u'%.2f%%' % shownPct
                if delta is None:
                    deltaTxt = u''
                else:
                    sign = u'+' if delta >= 0 else u''
                    deltaTxt = u'%s%.2f%%' % (sign, delta)
            else:
                pctTxt = u'--.--%'
                deltaTxt = u''
            data = self._battleData(pctTxt, deltaTxt, barPct, glowing, big, dmg,
                                    projEma, marks, assist, v3d)
            self.push(data)

        def _battleData(self, pctTxt, deltaTxt, barPct, glowing, big, dmg,
                        projEma, marks, assist, v3d=None):
            data = {
                'min': False,
                'pct': pctTxt,
                'delta': deltaTxt,
                'bar': round(max(0.0, min(100.0, barPct)), 2),
                'glow': bool(glowing),
                'big': bool(big),
                'dmg': _fmt(dmg),
                'proj': _fmt(projEma) if projEma > 0 else u'—',
                'marks': int(marks),
                'dmgTitle': g_config.get('textDamageTitle', u'Сум. урон:'),
            }
            if assist is not None and (assist[0] is not None or assist[1] is not None):
                # [засвет, гусеница]; None - этот показ выключен
                data['ast'] = [None if v is None else int(v) for v in assist]
            if v3d is not None:
                data['v3d'] = v3d
            return data

        def _publish(self, force=False):
            if self.model is None or not (self._ready or force):
                return
            try:
                with self.model.transaction() as model:
                    model.setPayload(self.payload)
            except Exception:
                pass

        def contains(self, pos):
            try:
                px, py = float(pos[0]), float(pos[1])
            except Exception:
                return False
            editing = self.settings is not None and self.settings.open
            if self.mini and self.mode == 'h' and not editing:
                wp, hp = self.wPx, 98.0 * self.ui
            else:
                wp, hp = self.wPx, self.hPx
            w = _pxW(wp)
            h = _pxH(hp)
            return (self.x <= px <= self.x + w) and (self.y - h <= py <= self.y)

        def openSettings(self):
            st = self.settings
            if st is None or st.open:
                return
            st.open = True
            st.target = 0
            st.pick = None
            st.active = None
            st.pressed = False
            st.build()
            self._restoreY = self.y
            _SETTINGS_OPEN[0] = True
            _log('settings opened')

        def closeSettings(self):
            st = self.settings
            if st is None or not st.open:
                return
            st.save()
            st.open = False
            st.active = None
            st.pressed = False
            _SETTINGS_OPEN[0] = False
            if self._restoreY is not None:
                self.y = self._restoreY
                self._restoreY = None
            _cfgStamp[0] = _mtime(CONFIG_PATH)
            _log('settings closed')

        def moveTo(self, x, y):
            w = _pxW(self.wPx)
            h = _pxH(self.hPx)
            self.x = max(-1.0, min(1.0 - w, x))
            self.y = max(-1.0 + h, min(1.0, y))
            self._move()

        def _move(self, force=False):
            if not _windowAlive(self.window) or not self._ready:
                return
            try:
                sw, sh = _screen()
                px = int(round((self.x + 1.0) * 0.5 * sw))
                py = int(round((1.0 - self.y) * 0.5 * sh))
                if not force and self._lastMove == (px, py):
                    return
                self.window.move(px, py)
                self._lastMove = (px, py)
            except Exception:
                pass

        def updateVisibility(self, hidden=False):
            """hidden - спрятать совсем (Tab, скрытый интерфейс). Меню Esc,
            диалоги и полноэкранные окна панель не прячут, а затемняют: она
            остаётся на месте, как будто ушла под слой."""
            if not _windowAlive(self.window):
                return
            behaviour = str(g_config.get('battleMenu', 'show')).lower()
            covered = False
            if behaviour in ('dim', 'hide'):
                covered = bool(_battleIsCovered(self.window))
            hidden = bool(hidden) or (behaviour == 'hide' and covered)
            dim = (not hidden) and behaviour == 'dim' and covered
            if dim != self._dim:
                self._dim = dim
                try:
                    data = json.loads(self.payload)
                    data['dim'] = dim
                    self.payload = json.dumps(data, ensure_ascii=True)
                    self._publish()
                except Exception:
                    pass
            if hidden == self._covered:
                return
            self._covered = hidden
            try:
                if hidden:
                    self.window.hide()
                else:
                    self.window.show(False)
                self._visible = not hidden
            except Exception:
                # The client may destroy its battle window before our stop hook.
                if not _windowAlive(self.window):
                    self.window = None

        def destroy(self):
            self._destroyed = True
            self._token += 1
            try:
                self.closeSettings()
            except Exception:
                _logError('close settings')
            if self.window is not None:
                try:
                    self.window.destroy()
                except Exception:
                    pass
                self.window = None
            self.model = None
            self._ready = False
            self._lastMove = None
            self._covered = False
            self._visible = True
            self._dim = False
            self.payload = '{}'


# ==========================================================================
# боевой контроллер

def _altIsDown():
    try:
        for name in ('KEY_LALT', 'KEY_RALT'):
            key = getattr(Keys, name, None)
            if key is not None and bool(BigWorld.isKeyDown(key)):
                return True
    except Exception:
        pass
    return False


def _sniperActive():
    try:
        return _ctrlModeName().lower() == 'sniper'
    except Exception:
        return False


_V3_THR_CACHE = {'key': None, 'val': (0, 0, 0, 0)}


def _v3Thresholds(intCD, mark, rating, ema):
    """(t65, t85, t95, t100) средний суммарный урон на 65 / 85 / 95 / 100%."""
    try:
        if mark is None or rating <= 0 or ema <= 0:
            return (0, 0, 0, 0)
        key = (int(intCD or 0), int(round(float(mark.avg))), int(round(float(mark.percent) * 100)),
               int(round(float(rating) * 100)), int(round(float(ema))), _calcVersion[0])
        if _V3_THR_CACHE['key'] == key:
            return _V3_THR_CACHE['val']
        res = [0, 0, 0, 0]
        curve = _curveFor(intCD)
        if curve and mark.avg > 0:
            limits = _serverCurve(mark, curve)[0].thresholds()
            if limits:
                for i in range(min(4, len(limits))):
                    v = limits[i]
                    if v is not None and 0 < v < 30000:
                        res[i] = int(math.ceil(v))
        if not any(res):
            stats = _calcStatistics(float(rating), float(ema))
            for i, k in enumerate((65, 85, 95)):
                v = stats.get(k)
                if v and 0 < v < 30000:
                    res[i] = int(math.ceil(v))
            if res[2] > 0:
                res[3] = min(30000, int(math.ceil(res[2] * (100.0 / 95.0) / 10.0) * 10))
        out = tuple(res)
        _V3_THR_CACHE['key'] = key
        _V3_THR_CACHE['val'] = out
        return out
    except Exception:
        return (0, 0, 0, 0)


class _BattleController(object):

    TICK = 0.05

    def __init__(self):
        self._panel = None
        self._tracker = None
        self._active = False
        self._cbID = None
        self._dragCbID = None
        self._intCD = None
        self._rating = 0.0
        self._ema = 0.0
        self._marks = 0
        self._isSpg = False
        self._lastAlt = False
        self._lastSniper = False
        self._shownPct = 0.0
        self._shownBar = 0.0
        self._glowUntil = 0.0
        self._lastTarget = 0.0
        self._lastVisibilityCheck = 0.0
        self._drag = None
        self._uiHidden = False
        self._statsShown = False
        self._visibilityListeners = []
        self._pendingForecast = None
        self._mark = None
        self._fcKey = None
        self._fc = None

    def start(self):
        if not _GF_OK:
            return
        try:
            player = BigWorld.player()
            if player is None:
                return
            vd = player.vehicleTypeDescriptor.type
            if vd.level < int(g_config.get('minVehicleLevel', 5)):
                return
            if g_config.get('onlyRandomBattles', True):
                if player.arena.bonusType != ARENA_BONUS_TYPE.REGULAR:
                    return
            self._intCD = vd.compactDescr
            try:
                self._isSpg = ('SPG' in (getattr(vd, 'tags', ()) or ()))
            except Exception:
                self._isSpg = False
            self._lastAlt = False
            self._lastSniper = False
            self._pendingForecast = None
            self._fcKey = self._fc = None
            _snapshotVehicle(self._intCD)
            self._mark = _markFor(self._intCD)
            if self._mark is not None:
                self._rating = self._mark.percent
                self._ema = self._mark.avg
                self._marks = self._mark.marks
            else:
                self._rating = self._ema = 0.0
                self._marks = 0
            if self._rating > 0 and self._intCD is not None:
                _SESSION_BASE.setdefault(self._intCD, self._rating)
            _requestCalc(self._intCD)
            _log('battle start tank=%s percent=%.2f avg=%d written=%s' % (
                self._intCD, self._rating, self._ema,
                self._mark.written if self._mark else None))

            self._shownPct = self._rating
            self._shownBar = self._rating
            self._lastTarget = self._rating
            self._tracker = _DamageTracker(self._onBattleEvent)
            self._panel = _GfPanel()
            self._panel.build()
            self._tracker.start()
            self._bindVisibilityEvents()
            self._active = True
            self._tick()
            self._dragTick()
        except Exception:
            _logError('battle start')

    def stop(self):
        self._active = False
        if self._intCD is not None and self._pendingForecast is not None:
            try:
                entry = g_cache.setdefault(_vehKey(self._intCD), {})
                entry['pendingForecast'] = self._pendingForecast
                _saveJson(CACHE_PATH, g_cache)
            except Exception:
                pass
        self._unbindVisibilityEvents()
        if self._cbID is not None:
            try:
                BigWorld.cancelCallback(self._cbID)
            except Exception:
                pass
            self._cbID = None
        if self._dragCbID is not None:
            try:
                BigWorld.cancelCallback(self._dragCbID)
            except Exception:
                pass
            self._dragCbID = None
        if self._tracker is not None:
            self._tracker.stop()
            self._tracker = None
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        self._drag = None

    def _bindVisibilityEvents(self):
        if not _EB_OK or self._visibilityListeners:
            return
        try:
            entries = (
                (gui_events.GameEvent.GUI_VISIBILITY, self._onGuiVisibility),
                (gui_events.GameEvent.FULL_STATS, self._onFullStats),
                (gui_events.GameEvent.FULL_STATS_QUEST_PROGRESS,
                 self._onFullStats),
                (gui_events.GameEvent.FULL_STATS_PERSONAL_RESERVES,
                 self._onFullStats),
            )
            for event, handler in entries:
                g_eventBus.addListener(event, handler,
                                       scope=EVENT_BUS_SCOPE.BATTLE)
                self._visibilityListeners.append((event, handler))
        except Exception:
            self._unbindVisibilityEvents()

    def _unbindVisibilityEvents(self):
        if _EB_OK:
            for event, handler in self._visibilityListeners:
                try:
                    g_eventBus.removeListener(
                        event, handler, scope=EVENT_BUS_SCOPE.BATTLE)
                except Exception:
                    pass
        self._visibilityListeners = []

    def _onGuiVisibility(self, event):
        try:
            ctx = getattr(event, 'ctx', {}) or {}
            if 'visible' in ctx:
                self._uiHidden = not bool(ctx['visible'])
                self._syncPanelVisibility()
        except Exception:
            pass

    def _onFullStats(self, event):
        try:
            ctx = getattr(event, 'ctx', {}) or {}
            if 'isDown' in ctx:
                self._statsShown = bool(ctx['isDown'])
                self._syncPanelVisibility()
        except Exception:
            pass

    def _hidden(self):
        """Прятать ли панель совсем: Tab, скрытый интерфейс, посмертие."""
        if self._uiHidden or self._statsShown or self._tabIsDown():
            return True
        if g_config.get('hideInIntro', True):
            intro, how = _introActive()
            if intro:
                _logOnce(('intro', how), 'panel hidden during the intro (%s)' % how)
                return True
        if g_config.get('hideAfterDeath', False):
            dead, how = _playerDead()
            if dead:
                _logOnce(('dead', how), 'panel hidden: player vehicle destroyed (%s)' % how)
                return True
        if g_config.get('hideInKillcam', True):
            kill, how = _killcamActive()
            if kill:
                _logOnce(('killcam', how), 'panel hidden during the shot replay (%s)' % how)
                return True
        if _cfgInt('battlePreset', 0, 1) == 0:
            if bool(g_config.get('v3HideInSniper', False)) and _sniperActive():
                return True
        return False

    def _syncPanelVisibility(self):
        if self._panel is None:
            return
        self._panel.updateVisibility(self._hidden())

    def _tabIsDown(self):
        try:
            key = getattr(Keys, 'KEY_TAB', None)
            return key is not None and bool(BigWorld.isKeyDown(key))
        except Exception:
            return False

    def onSummary(self, summary):
        if self._active and self._tracker is not None:
            self._tracker.onSummary(summary)

    def _onBattleEvent(self):
        if self._active:
            try:
                self._update()
            except Exception:
                _logError('battle event')

    def _pollDrag(self):
        _panelDragPoll(self, self._panel, None)

    def _dragTick(self):
        """Перетаскивание опрашивается покадрово, пока виден курсор."""
        if not self._active:
            return
        interval = 0.2
        try:
            mc = GUI.mcursor()
            if getattr(mc, 'visible', False):
                self._pollDrag()
                interval = 0.0
            elif self._drag is not None:
                self._drag = None
        except Exception:
            pass
        self._dragCbID = BigWorld.callback(interval, self._dragTick)

    def _tick(self):
        if not self._active:
            return
        try:
            _pump()
            _pollConfig()
            altChanged = False
            if _cfgInt('battlePreset', 0, 1) == 0:
                altNow = _altIsDown()
                sniperNow = _sniperActive()
                if altNow != self._lastAlt or sniperNow != self._lastSniper:
                    self._lastAlt = altNow
                    self._lastSniper = sniperNow
                    altChanged = True
            self._update()
            now = BigWorld.time()
            if altChanged or now - self._lastVisibilityCheck >= 0.25:
                self._lastVisibilityCheck = now
                if self._panel is not None:
                    self._panel.updateVisibility(self._hidden())
        except Exception:
            _logError('battle tick')
        self._cbID = BigWorld.callback(self.TICK, self._tick)

    def _parts(self):
        try:
            return self._tracker.parts()
        except Exception:
            return None

    def _plan(self, mark, dmg):
        """(процент после боя, изменение, среднее после боя, сутки кривой)
        или None, если кривой пока нет. Результат кэшируется: пересчёт - при
        новом уроне, новых данных или раз в полминуты."""
        curve = _curveFor(self._intCD)
        if not curve:
            return None
        stamp = (int(dmg), _calcVersion[0], int(_serverNow() // 30))
        if self._fcKey == stamp:
            return self._fc
        plan = None
        try:
            _epoch.witness(_vehKey(self._intCD), mark.avg, mark.percent,
                           mark.written)
            after, delta, whole, _projected = _forecast(mark, dmg, curve)
            server = _serverCurve(mark, curve)[0]
            bigAt = 0.0
            if g_config.get('bigByDamage', True):
                # порог большого плюса: во сколько раз урон больше среднего,
                # нужного на bigBasePercent (например, на 95%)
                bigAt = (server.damageOf(_cfgNumber('bigBasePercent', 1.0, 100.0)) *
                         _cfgNumber('bigDamageFactor', 0.5, 20.0))
            plan = (after, delta, int(whole), server.day, bigAt)
        except Exception:
            _logError('forecast')
        self._fcKey, self._fc = stamp, plan
        return plan

    def _update(self):
        if self._panel is None:
            return
        dmg = self._tracker.combined() if self._tracker else 0
        mark = self._mark
        hasRating = mark is not None and self._rating > 0 and self._ema > 0

        target, delta = self._rating, None
        big = False
        projEma = int(_nextAverage(self._ema, dmg)[0]) if hasRating else 0
        if hasRating:
            plan = self._plan(mark, dmg)
            if plan is not None:
                target, delta, projEma, curveDay, bigAt = plan
                big = bool(bigAt > 0 and dmg >= bigAt and delta >= 0)
                self._pendingForecast = {
                    'at': time.time(), 'before': self._rating,
                    'average': self._ema, 'predicted': target,
                    'combined': int(dmg), 'curveDay': curveDay,
                    'parts': self._parts(),
                }

        now = BigWorld.time()
        if target > self._lastTarget + 1e-6:
            self._glowUntil = now + 0.7
        self._lastTarget = target

        self._shownPct = target
        self._shownBar += (target - self._shownBar) * 0.15
        if abs(target - self._shownBar) < 0.002:
            self._shownBar = target

        preset = _cfgInt('battlePreset', 0, 1)
        v3d = None
        assist = None
        parts = self._parts() or {}
        if preset == 0:
            tHold = int(round(projEma))
            t65, t85, t95, t100 = _v3Thresholds(self._intCD, mark, self._shownPct, self._ema) if hasRating else (0, 0, 0, 0)
            if self._shownPct < 65.0:
                tNextPct, tNext = 65, t65
            elif self._shownPct < 85.0:
                tNextPct, tNext = 85, t85
            elif self._shownPct < 95.0:
                tNextPct, tNext = 95, t95
            else:
                tNextPct, tNext = 100, t100
            if parts.get('src') == 'feedback':
                own = int(parts.get('damage', 0) or 0)
                spot = int(parts.get('radio', 0) or 0)
                track = int(parts.get('track', 0) or 0)
                stun = int(parts.get('stun', 0) or 0)
            else:
                own = int(parts.get('effDamage', 0) or 0)
                spot = int(parts.get('effAssist', 0) or 0)
                track = 0
                stun = int(parts.get('effStun', 0) or 0)
            sBase = _SESSION_BASE.get(self._intCD, self._rating)
            sDelta = (self._shownPct - sBase) if hasRating else None
            v3d = {
                'pct': round(self._shownPct, 2),
                'bar': round(self._shownBar, 2),
                'delta': round(delta, 2) if delta is not None else None,
                'sDelta': round(sDelta, 2) if sDelta is not None else None,
                'dmg': int(dmg),
                'tHold': int(tHold),
                'tMark': 0,
                'tPlus1': 0,
                'tNextPct': int(tNextPct),
                'tNext': int(tNext),
                't95': int(t95),
                'own': max(0, own),
                'spot': max(0, spot),
                'track': max(0, track),
                'stun': max(0, stun),
                'marks': int(self._marks),
                'big': bool(big),
                'isSpg': bool(self._isSpg),
                'alt': bool(self._lastAlt),
                'hasRating': bool(hasRating),
            }
        else:
            showSpot = bool(g_config.get('showSpot', True))
            showTrack = bool(g_config.get('showTrack', True))
            if showSpot or showTrack:
                assist = (parts.get('radio', 0) if showSpot else None,
                          parts.get('track', 0) if showTrack else None)
        self._panel.render(self._shownPct, self._shownBar, delta, dmg,
                           int(round(projEma)), self._marks,
                           now < self._glowUntil, hasRating, big, assist, v3d=v3d)


g_controller = _BattleController()


# ==========================================================================
# требования среднего урона на пороги (порт spoter calcStatistics)

_LEVELS = (2.0, 20.0, 40.0, 55.0, 65.0, 85.0, 95.0, 100.0)


def _calcPercent(ema, start, end, d, p):
    """Аналитический эквивалент цикла спотера (шаг 0.1 до 30000)."""
    if not (start <= end < 100.001) or ema >= 30000:
        return ema
    need = end * d / p
    result = max(ema, need) + 0.1
    return min(result, 30000.0)


def _calcStatistics(p, d):
    """-> {65: ema, 85: ema, 95: ema} - требования среднего урона."""
    pC = math.floor(p) + 1
    dC = _calcPercent(d, p, pC, d, p)
    data = [2,
            _calcPercent(0, 0.0, 20.0, d, p),
            _calcPercent(0, 0.0, 40.0, d, p),
            _calcPercent(0, 0.0, 55.0, d, p),
            _calcPercent(0, 0.0, 65.0, d, p),
            _calcPercent(0, 0.0, 85.0, d, p),
            _calcPercent(0, 0.0, 95.0, d, p),
            _calcPercent(0, 0.0, 100.0, d, p)]
    idx = [x for x in _LEVELS if x >= p][0]
    check = _LEVELS.index(idx)
    limit1 = dC
    limit2 = data[check]
    delta = limit2 - limit1
    for value in xrange(len(data)):
        if data[value] == limit1 or data[value] == limit2:
            continue
        if value > check:
            data[value] = int(math.ceil(math.ceil((data[value] + delta) / 10.0)) * 10)

    return {65: data[4], 85: data[5], 95: data[6]}


# ==========================================================================
# ангарная панель: текущий %, средний урон, требования на 65/85/95

_HIDE_VIEW_KEYWORDS = ('techtree', 'research', 'vehiclehub', 'upgrade',
                       'moduleset', 'blueprint', 'shop', 'barracks',
                       'profile', 'exchange', 'personalmissions')

# Экран оснащения (слоты оборудования, снаряжение, боекомплект) открывается
# поверх ангара. Узнаём его по классам открытых окон (модуль.Класс) и по
# маршруту; всё увиденное пишется в журнал, чтобы список можно было уточнить.
_SETUP_VIEW_KEYWORDS = ('tank_setup', 'tanksetup', 'ammunition_setup',
                        'ammunitionsetup')
_SETUP_ROUTE_KEYWORDS = _SETUP_VIEW_KEYWORDS + ('/setup',)


_HANGAR_STATE_IDS = ('subScope/subLayer/hangar', 'subScope/subLayer/hangar/{root}',
                      'subScope/subLayer/legacyHangar')


def _hangarState():
    """(показан ли ангар, id видимого состояния). Ангар в 2.4 - это состояние
    лобби-автомата; экран оснащения, исследования и т.п. - другие состояния.
    (None, '') - автомат недоступен, тогда решают прочие признаки."""
    try:
        from gui.Scaleform.lobby_entry import getLobbyStateMachine
        machine = getLobbyStateMachine()
    except Exception:
        return (None, '')
    if machine is None:
        return (None, '')
    stateID = ''
    try:
        state = machine.visibleState
        stateID = str(state.getStateID()) if state is not None else ''
    except Exception:
        pass
    try:
        from gui.lobby_state_machine.states import isHangarState
        return (bool(isHangarState(machine.visibleState)), stateID)
    except Exception:
        pass
    if stateID:
        return (stateID in _HANGAR_STATE_IDS, stateID)
    return (None, '')


def _hangarMode():
    """(случайный ли бой выбран в ангаре, описание). None - определить не
    удалось: тогда панель не прячется. Тип очереди даёт текущая сущность
    лобби; её класс пишется в журнал, чтобы список режимов можно было уточнить."""
    queueType = None
    desc = ''
    path = ''
    try:
        from gui.prb_control.dispatcher import g_prbLoader
        dispatcher = g_prbLoader.getDispatcher()
        entity = dispatcher.getEntity() if dispatcher is not None else None
        if entity is not None:
            cls = type(entity)
            path = '%s.%s' % (cls.__module__, cls.__name__)
            desc = path
            getter = getattr(entity, 'getQueueType', None)
            if getter is not None:
                queueType = getter()
    except Exception:
        pass
    if not queueType:
        try:
            from gui.prb_control import prb_getters
            queueType = prb_getters.getQueueType()
        except Exception:
            pass
    low = path.lower()
    # взвод в случайных боях и сам случайный бой узнаём и по классу сущности
    if '.random.' in low or low.endswith('squad.entity.squadentity'):
        return (True, '%s queue=%s' % (desc, queueType))
    if not queueType:
        return (None, desc)
    try:
        from constants import QUEUE_TYPE
        return (queueType == QUEUE_TYPE.RANDOMS, '%s queue=%s' % (desc, queueType))
    except Exception:
        return (None, desc)


def _hangarCovered(ownWindow):
    """Поверх ангара лежит крупное окно (диалог, промо, настройки)?"""
    try:
        from frameworks.wulf import WindowFlags
        windowsManager = dependency.instance(IGuiLoader).windowsManager
        layers = [getattr(WindowLayer, name, None) for name in
                  ('TOP_SUB_VIEW', 'WINDOW', 'FULLSCREEN_WINDOW', 'TOP_WINDOW',
                   'OVERLAY')]
        layers = [layer for layer in layers if layer is not None]

        def predicate(window):
            try:
                if window is ownWindow or window.layer not in layers:
                    return False
                if window.windowStatus not in (WindowStatus.LOADING,
                                               WindowStatus.LOADED):
                    return False
                if window.typeFlag in (WindowFlags.TOOLTIP,
                                       WindowFlags.CONTEXT_MENU):
                    return False
                if window.isHidden():
                    return False
                size = window.size
                return size[0] > 1000 and size[1] > 600
            except Exception:
                return False

        return bool(windowsManager.findWindows(predicate))
    except Exception:
        return False


def _viewClassNames():
    """Классы всех открытых Gameface-окон (строки 'модуль.Класс') или None."""
    try:
        windowsManager = dependency.instance(IGuiLoader).windowsManager
        names = set()
        for view in windowsManager.findViews(lambda item: True) or ():
            cls = type(view)
            names.add('%s.%s' % (cls.__module__, cls.__name__))
        return names
    except Exception:
        return None


class _HangarController(object):

    THRESHOLDS = (65.0, 85.0, 95.0)

    def __init__(self):
        self._panel = None
        self._cbID = None
        self._dragCbID = None
        self._drag = None
        self._inLobby = False
        self._blocked = False
        self._watchCbID = None
        self._statKey = None
        self._statCache = None
        self._setupOpen = False
        self._lastPayload = None
        self._stateID = None
        self._modeDesc = None
        self._viewNames = set()
        self._viewLogLines = 0

    # -- видимость -----------------------------------------------------------

    def onLobby(self):
        self._inLobby = True
        self._blocked = False
        self._ensure()
        self._startWatch()

    def _startWatch(self):
        if self._watchCbID is None:
            self._watchTick()

    def _watchTick(self):
        if not self._inLobby:
            self._watchCbID = None
            return
        try:
            if not _MENU['ok']:
                _registerMenu()
            else:
                hwAlt = _altIsDown()
                if hwAlt != _PREVIEW.get('hwAlt', False):
                    _PREVIEW['hwAlt'] = hwAlt
                    _menuPreviewRefresh()
            self._scanViews()
            if self._panel is None and not self._blocked:
                self._ensure()
        except Exception:
            _logError('hangar watch')
        self._watchCbID = BigWorld.callback(0.3, self._watchTick)

    def _scanViews(self):
        """Решает, надо ли прятать панель: не ангар (экран оснащения и пр.),
        крупное окно поверх, либо опознанный по классу экран оснащения."""
        reason = ''
        shown, stateID = _hangarState()
        if stateID != self._stateID:
            self._stateID = stateID
            _log('lobby state: %s (hangar=%s)' % (stateID, shown))
        if shown is False:
            reason = 'state %s' % stateID
        elif g_config.get('hideUnderWindows', False) and _GF_OK and \
                _hangarCovered(getattr(self._panel, 'window', None)):
            reason = 'big window'
        random, modeDesc = _hangarMode()
        if modeDesc != self._modeDesc:
            self._modeDesc = modeDesc
            _log('hangar mode: %s random=%s' % (modeDesc, random))
        if not reason and random is False and g_config.get('hangarOnlyRandom', True):
            reason = 'not a random battle'
        names = _viewClassNames()
        if names is not None:
            if names != self._viewNames and self._viewLogLines < 400:
                added = sorted(names - self._viewNames)
                removed = sorted(self._viewNames - names)
                self._viewLogLines += 1
                _log('hangar views +%s -%s' % (added, removed))
            self._viewNames = names
            if not reason and any(k in n.lower() for n in names
                                  for k in _SETUP_VIEW_KEYWORDS):
                reason = 'setup view'
        cover = bool(reason)
        if cover != self._setupOpen:
            self._setupOpen = cover
            _log('hangar panel %s (%s)' % ('hidden' if cover else 'shown', reason or 'ok'))
            if cover:
                self._hide()
            else:
                self._ensure()

    def onLeaveLobby(self):
        self._inLobby = False
        if self._watchCbID is not None:
            try:
                BigWorld.cancelCallback(self._watchCbID)
            except Exception:
                pass
            self._watchCbID = None
        self._hide()

    def setBlocked(self, blocked):
        self._blocked = bool(blocked)
        if self._blocked:
            self._hide()
        else:
            self._ensure()

    def onViewLoaded(self, event):
        try:
            alias = unicode(getattr(event, 'alias', '') or '').lower()
        except Exception:
            return
        if not alias:
            return
        _logOnce(('alias', alias), 'lobby view alias: %s' % alias)
        if any(k in alias for k in _HIDE_VIEW_KEYWORDS + _SETUP_VIEW_KEYWORDS):
            self._blocked = True
            self._hide()
        elif 'hangar' in alias:
            self._blocked = False
            self._ensure()

    def refresh(self, *args, **kwargs):
        if self._panel is not None:
            self._update()
        else:
            self._ensure()

    def _ensure(self):
        if not _GF_OK or not g_config.get('hangarPanel', True):
            return
        if not self._inLobby or self._blocked or self._setupOpen:
            return
        try:
            if not g_currentVehicle.isPresent():
                return
            item = g_currentVehicle.item
            if item is None or getattr(item, 'level', 10) < \
                    int(g_config.get('minVehicleLevel', 5)):
                return
        except Exception:
            return
        if self._panel is None:
            self._panel = _GfPanel(mode='h', keyX='hx', keyY='hy',
                                   wPx=_HWINDOW_W, hPx=_HWINDOW_H)
            self._panel.settings = None if _MENU['ok'] else _SettingsUI()
            self._panel.build()
            self._tick()
            self._dragTick()
        self._update()

    def _hide(self):
        if self._cbID is not None:
            try:
                BigWorld.cancelCallback(self._cbID)
            except Exception:
                pass
            self._cbID = None
        if self._dragCbID is not None:
            try:
                BigWorld.cancelCallback(self._dragCbID)
            except Exception:
                pass
            self._dragCbID = None
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        self._drag = None

    # -- данные ---------------------------------------------------------------

    def _update(self):
        if self._panel is None:
            return
        if not g_config.get('hangarPanel', True):
            self._hide()
            return
        try:
            st = getattr(self._panel, 'settings', None)
            if st is not None and st.open:
                # страница настроек не зависит от досье и кривых: только
                # отправить готовый список (иначе на каждый кадр перетаскивания
                # читалось бы досье и считались кривые)
                self._panel.push({})
                return
            if not g_currentVehicle.isPresent():
                return
            item = g_currentVehicle.item
            if item is None:
                return
            if getattr(item, 'level', 10) < \
                    int(g_config.get('minVehicleLevel', 5)):
                self._hide()
                return
            intCD = item.intCD
            mark = _markFor(intCD)
            if mark is None:
                return
            _requestCalc(intCD)
            rating, ema, marks = mark.percent, mark.avg, mark.marks
            curve = _curveFor(intCD)
            limits = None
            if curve and rating > 0 and ema > 0:
                try:
                    _epoch.witness(_vehKey(intCD), mark.avg, mark.percent,
                                   mark.written)
                    rating = _currentPercent(mark, curve)[0]
                    limits = _serverCurve(mark, curve)[0].thresholds()
                except Exception:
                    _logError('hangar curve')
            hasRating = bool(rating > 0 and ema > 0)
            t65, t85, t95, t100 = _v3Thresholds(intCD, mark, rating, ema) if hasRating else (0, 0, 0, 0)
            self._panel.mini = False
            payload = {
                'min': False,
                'nodata': not hasRating,
                'pct': (u'%.2f%%' % rating) if rating > 0 else u'--.--%',
                'bar': round(max(0.0, min(100.0, rating)), 2),
                'marks': int(marks),
                'ema': _fmt(ema) if ema > 0 else u'—',
                't65': _fmt(t65) if (hasRating and 0 < t65 < 30000) else u'—',
                't85': _fmt(t85) if (hasRating and 0 < t85 < 30000) else u'—',
                't95': _fmt(t95) if (hasRating and 0 < t95 < 30000) else u'—',
                't100': _fmt(t100) if (hasRating and 0 < t100 < 30000) else u'—',
                'v3d': {
                    'isHangar': True,
                    'mini': False,
                    'pct': round(rating, 2) if hasRating else 0.0,
                    'bar': round(max(0.0, min(100.0, rating)), 2) if hasRating else 0.0,
                    'delta': None,
                    'sDelta': None,
                    'dmg': int(round(ema)) if hasRating else 0,
                    'tHold': 0,
                    'tMark': 0,
                    'tPlus1': 0,
                    't65': int(t65),
                    't85': int(t85),
                    't95': int(t95),
                    't100': int(t100),
                    'marks': int(marks),
                    'big': False,
                    'isSpg': False,
                    'alt': False,
                    'hasRating': hasRating,
                },
            }
            self._lastPayload = dict(payload)
            self._panel.push(payload)
        except Exception:
            _logError('hangar update')

    # -- циклы ---------------------------------------------------------------

    def _tick(self):
        if self._panel is None:
            return
        try:
            _pump()
            _pollConfig()
            self._update()
        except Exception:
            _logError('hangar tick')
        self._cbID = BigWorld.callback(1.0, self._tick)

    def _dragTick(self):
        if self._panel is None:
            return
        interval = 0.2
        try:
            mc = GUI.mcursor()
            if getattr(mc, 'visible', False):
                self._pollDrag()
                interval = 0.0
            elif self._drag is not None:
                self._drag = None
        except Exception:
            pass
        self._dragCbID = BigWorld.callback(interval, self._dragTick)

    def _pollDrag(self):
        _panelDragPoll(self, self._panel, None)
        if getattr(self, '_needRefresh', False):
            self._needRefresh = False
            self._update()


g_hangar = _HangarController()


class _RouteTap(logging.Handler):
    """Слушает lobby_state_machine: маршрут с /hangar - показать,
    любой другой (исследования, очередь) - скрыть."""

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return
        if 'Visible route changed' not in msg:
            return
        try:
            low = msg.lower()
            _logOnce(('route', low[:240]), 'route: %s' % msg[:240])
            if any(k in low for k in _SETUP_ROUTE_KEYWORDS):
                g_hangar.setBlocked(True)
            elif '/hangar' in low:
                g_hangar.setBlocked(False)
            else:
                g_hangar.setBlocked(True)
        except Exception:
            pass


_routeTap = _RouteTap()


# ==========================================================================
# hook серверной сводки

def _patchedSummary(self, summary):
    if _ORIG_SUMMARY is not None:
        _ORIG_SUMMARY(self, summary)
    try:
        g_controller.onSummary(summary)
    except Exception:
        pass


def _installHooks():
    try:
        if _ORIG_SUMMARY is not None:
            feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary = _patchedSummary
    except Exception:
        pass


def _removeHooks():
    try:
        cur = feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary
        if _ORIG_SUMMARY is not None and \
                getattr(cur, '__func__', cur) is _patchedSummary:
            feedback_adaptor.BattleFeedbackAdaptor.handleBattleEventsSummary = _ORIG_SUMMARY
    except Exception:
        pass


# ==========================================================================
# события и вход/выход

def _onHangarVehicleChanged(*args, **kwargs):
    try:
        if g_currentVehicle.isPresent():
            item = g_currentVehicle.item
            if item is not None:
                _snapshotVehicle(item.intCD)
        g_hangar.refresh()
    except Exception:
        pass


def _onAccountShowGUI(*args, **kwargs):
    g_hangar.onLobby()


def _onAvatarBecomePlayer(*args, **kwargs):
    g_hangar.onLeaveLobby()


def _onLoadView(event):
    g_hangar.onViewLoaded(event)


def _onSyncCompleted(*args, **kwargs):
    _onHangarVehicleChanged()


def _onAvatarReady(*args, **kwargs):
    g_controller.start()


def _onAvatarBecomeNonPlayer(*args, **kwargs):
    g_controller.stop()


def init():
    try:
        _loadConfig()
        _loadCache()
        _writeConfigHelp()
        _log('init, version %s, gameface ok=%s, event bus ok=%s' % (
            MOD_VERSION, _GF_OK, _EB_OK))
        if not _GF_OK:
            _log('gameface import failed, no panel will be shown:\n%s' % _GF_ERR)
        _installHooks()
        _registerMenu()
        g_playerEvents.onAvatarReady += _onAvatarReady
        g_playerEvents.onAvatarBecomeNonPlayer += _onAvatarBecomeNonPlayer
        g_playerEvents.onAccountShowGUI += _onAccountShowGUI
        g_playerEvents.onAvatarBecomePlayer += _onAvatarBecomePlayer
        g_currentVehicle.onChanged += _onHangarVehicleChanged
        _itemsCache.onSyncCompleted += _onSyncCompleted
        if _EB_OK:
            try:
                g_eventBus.addListener(gui_events.ViewEventType.LOAD_VIEW,
                                       _onLoadView)
            except Exception:
                pass
        try:
            logging.getLogger('gui.lobby_state_machine').addHandler(_routeTap)
        except Exception:
            pass
    except Exception:
        _logError('init')


def fini():
    try:
        g_controller.stop()
        g_hangar.onLeaveLobby()
        _unregisterMenu()
        _removeHooks()
        g_playerEvents.onAvatarReady -= _onAvatarReady
        g_playerEvents.onAvatarBecomeNonPlayer -= _onAvatarBecomeNonPlayer
        g_playerEvents.onAccountShowGUI -= _onAccountShowGUI
        g_playerEvents.onAvatarBecomePlayer -= _onAvatarBecomePlayer
        g_currentVehicle.onChanged -= _onHangarVehicleChanged
        _itemsCache.onSyncCompleted -= _onSyncCompleted
        if _EB_OK:
            try:
                g_eventBus.removeListener(gui_events.ViewEventType.LOAD_VIEW,
                                          _onLoadView)
            except Exception:
                pass
        try:
            logging.getLogger('gui.lobby_state_machine').removeHandler(_routeTap)
        except Exception:
            pass
        _saveJson(CACHE_PATH, g_cache)
    except Exception:
        pass
