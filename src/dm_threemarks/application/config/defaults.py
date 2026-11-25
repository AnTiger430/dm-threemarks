# -*- coding: utf-8 -*-
from __future__ import absolute_import

MOD_VERSION = '10.12.45'

WINDOW_W, WINDOW_H = (244, 96)
HWINDOW_W, HWINDOW_H = (244, 144)
PCT_WINDOW_W, PCT_WINDOW_H = (220, 72)

WG_API_URL = 'https://api.worldoftanks.%s/wot/tanks/mastery/?application_id=%s&distribution=damage&percentile=%s&tank_id=%s'
LESTA_API_URL = 'https://api.tanki.su/wot/tanks/mastery/?application_id=%s&distribution=damage&percentile=%s&tank_id=%s'
WG_HISTORY_URL = 'https://poliroid.me/gunmarks/api/v2/data/%s/vehicle/%s/%s'

V3_DEFAULTS = {
    'v3Font': 2,
    'v3Density': 0,
    'v3MinWidth': 0,
    'v3Anchor': 1,
    'v3FrameStyle': 0,
    'v3Radius': 14,
    'v3CornerColor': '#FFFFFF',
    'v3CornerAlpha': 0.50,
    'v3BorderAlpha': 0.22,
    'v3BgColor': '#0B1016',
    'v3BgOpacity': 0.20,
    'v3StarsPos': 0,
    'v3StarsStyle': 0,
    'v3StarsDivider': False,
    'v3StarsSize': 16,
    'v3StarsGap': 7,
    'v3StarsGlow': True,
    'v3StarOnColor': '#FFFFFF',
    'v3StarOffColor': '#9AA3AE',
    'v3HeaderOrder': 2,
    'v3PctDecimals': 1,
    'v3DeltaIcon': 1,
    'v3DeltaColorMode': 0,
    'v3BarStyle': 0,
    'v3BarScale': 0,
    'v3BarHeight': 4,
    'v3BarTrackHeight': 2,
    'v3BarCustomText': u'KIBERSPORT',
    'v3BarTextSize': 15,
    'v3BarEndTicks': True,
    'v3BarCursor': True,
    'v3BarMarks': True,
    'v3BarColorMode': 0,
    'v3BarCustomColor': '#A7D080',
    'v3ShowDamage': True,
    'v3DamageLabel': 0,
    'v3DamageCustomLabel': u'Сум. урон',
    'v3ThousandsSep': 2,
    'v3DamageDynColor': True,
    'v3AssistShow': 0,
    'v3AssistMode': 0,
    'v3AssistPlace': 0,
    'v3AssistHideZero': False,
    'v3AssistSize': 15,
    'v3TempoShow': 1,
    'v3TempoMode': 0,
    'v3TempoPlace': 0,
    'v3TempoSize': 13,
    'v3AccentPlus': '#A7D080',
    'v3AccentMinus': '#E57373',
    'v3AccentZero': '#9AA3AE',
    'v3AccentBig': '#B07CFF',
    'v3TextMain': '#FFFFFF',
    'v3TextMuted': '#B8BDC4',
}

VH_DEFAULTS = {
    'vhFont': 2,
    'vhScale': 1.1,
    'vhDensity': 0,
    'vhFrameStyle': 2,
    'vhRadius': 5,
    'vhCornerColor': '#FFFFFF',
    'vhCornerAlpha': 0.0,
    'vhBorderAlpha': 0.20,
    'vhBgColor': '#131313',
    'vhBgOpacity': 0.60,
    'vhStarsPos': 0,
    'vhStarsStyle': 0,
    'vhStarsDivider': False,
    'vhStarsSize': 22,
    'vhStarsGap': 7,
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
    'vhBarMarks': True,
    'vhBarColor': '#A7D080',
    'vhShowEma': True,
    'vhShowThresholds': True,
    'vhThousandsSep': 2,
    'vhTextMain': '#FFFFFF',
    'vhTextMuted': '#B8BDC4',
}

DEFAULT_CONFIG = {
    'x': 0.3656,
    'y': -0.2334,
    'hx': 0.3355,
    'hy': 0.8278,
    'hangarPanel': True,
    'onlyRandomBattles': True,
    'minVehicleLevel': 5,
    'dragEnabled': True,
    'onlineHistory': True,
    'battleMenu': 'show',
    'battlePreset': 0,
    'battlePercentOnly': False,
    'barStyleVersion': 2,
    'hideUnderWindows': False,
    'hangarOnlyRandom': True,
    'hideInIntro': True,
    'hideInKillcam': True,
    'hideAfterDeath': False,
    'uiScale': 0.9,
    'bgOpacity': 0.82,
    'panelOpacity': 1.0,
    'colorPlus': '#86EF6A',
    'colorMinus': '#FF6060',
    'colorZero': '#EAEAEA',
    'barColorPlus': '#8FE37D',
    'barColorMinus': '#FF6060',
    'barColorZero': '#DDE6EE',
    'barColorHangar': '#F0F2F6',
    'barBySign': False,
    'barColorStandard': '#8FE37D',
    'trackOpacity': 0.10,
    'tickColor': '#FFFFFF',
    'pctColor': '#F4F4F4',
    'pctFollowsSign': False,
    'glow': True,
    'showSpot': False,
    'showTrack': False,
    'zeroBand': 0.02,
    'bigByDamage': True,
    'bigDamageFactor': 2.0,
    'bigBasePercent': 95.0,
    'bigFrom': 4.0,
    'colorBig': '#B07CFF',
    'barColorBig': '#B07CFF',
    'dmgFollowsSign': True,
    'colorDmg': '#86EF6A',
    'colorProj': '#EAEAEA',
    'minHangar': False,
    'minBattle': False,
    'textDamageTitle': u'Сум. урон:',
    'wgApiApplicationId': 'bce57ac20af6b67b08be09fd66847ed9',
    'lestaApiApplicationId': '',
}
DEFAULT_CONFIG.update(V3_DEFAULTS)
DEFAULT_CONFIG.update(VH_DEFAULTS)

CONFIG_HELP = u"""Три отметки на стволе - настройки внешнего вида (config.json)
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
hideAfterDeath   true - прятать панель после гибели насовсем, в том числе при наблюдении
hangarOnlyRandom true - панель ангара только в случайных боях
lestaApiApplicationId (для «Мир танков» / Lesta) необязательный application_id с developers.lesta.ru для прямых кривых api.tanki.su (при ошибке или отсутствии автоматически используется Poliroid)
"""
