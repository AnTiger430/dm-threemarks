# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ...application.config.defaults import DEFAULT_CONFIG, MOD_VERSION
from .tab_definitions import (
    build_preview_column,
    build_preview_column_battle,
    build_preview_column_hangar,
    build_tab_colors_legacy,
    build_tab_colors_v3,
    build_tab_dmg_assist,
    build_tab_frame_stars,
    build_tab_hangar,
    build_tab_header_bar,
    build_tab_main,
)


BATTLE_SECTIONS_V3 = [u'Основное', u'Рамка и звёзды', u'Шапка и полоска', u'Урон и ассист', u'Цвета']
BATTLE_SECTIONS_LEGACY = [u'Основное', u'Цвета']


def _ctl(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except TypeError:
        return fn(*args)


class _WidgetDsl(object):
    """Small DSL helper wrapping Aslain/ModsSettingsAPI template calls with defaults & tooltips."""

    def __init__(self, tpl, ver, values):
        self.tpl = tpl
        self.new = tuple(ver) >= (2, 0, 0)
        self.values = values
        self.f2 = '%.2f' if self.new else '{{value}}'
        self.f1 = '%.1f' if self.new else '{{value}}'
        self.f0 = '%.0f' if self.new else '{{value}}'

    def _def_text(self, key, kind, dfmt=None, labels=None):
        val = DEFAULT_CONFIG.get(key)
        if kind == 'slider':
            try:
                fval = float(val)
            except Exception:
                return None
            if key in ('v3MinWidth', 'v3AssistSize', 'v3TempoSize') and int(round(fval)) == 0:
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
            elif key in ('previewState', 'previewStateHangar', 'previewAlt', 'previewTarget', 'battleSection', 'hangarSection'):
                idx = 0
            else:
                idx = int(val)
            if 0 <= idx < len(labels):
                return labels[idx]
        return None

    def tip(self, head, body, default_text=None):
        if self.new:
            extra = (u'<br><font color="#B8BDC4">По умолчанию:</font> <b>%s</b>' % default_text) if default_text is not None else u''
            return u'{HEADER}%s{/HEADER}{BODY}%s%s{/BODY}' % (head, body, extra)
        extra = (u' (по умолчанию: %s)' % default_text) if default_text is not None else u''
        return u'%s: %s%s' % (head, body, extra)

    def slider(self, text, key, low, high, step, fmt, head, body):
        dfmt = '%.0f' if fmt == self.f0 else ('%.1f' if fmt == self.f1 else '%.2f')
        return _ctl(self.tpl.createSlider, text, key, self.values[key], low, high, step,
                    format=fmt, tooltip=self.tip(head, body, self._def_text(key, 'slider', dfmt=dfmt)))

    def check(self, text, key, head, body):
        return _ctl(self.tpl.createCheckbox, text, key, self.values[key],
                    tooltip=self.tip(head, body, self._def_text(key, 'check')))

    def color(self, text, key, body):
        return _ctl(self.tpl.createColorChoice, text, key, self.values[key],
                    tooltip=self.tip(text, body, self._def_text(key, 'color')))

    def label(self, text):
        return _ctl(self.tpl.createLabel, text)

    def gated(self, control, master, value):
        fn = getattr(self.tpl, 'enableWhen', None)
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

    def vis(self, control, master, value, cond='==', indent=False):
        fn = getattr(self.tpl, 'visibleWhen', None)
        if fn is not None and not isinstance(value, (list, tuple)):
            try:
                return fn(control, master, value, indent=indent) if cond == '==' else fn(control, master, value, indent=indent, condition=cond)
            except TypeError:
                try:
                    if cond == '==':
                        return fn(control, master, value)
                except Exception:
                    pass
            except Exception:
                pass
        if self.new and isinstance(control, dict):
            control['masterVarName'] = master
            control['masterValue'] = list(value) if isinstance(value, tuple) else value
            if cond != '==':
                control['condition'] = cond
            control['gateHides'] = True
            control['masterIndent'] = bool(indent)
            return control
        return self.gated(control, master, value)

    def visAll(self, control, conds, indent=False):
        if self.new and isinstance(control, dict):
            built = []
            for item in conds:
                m, v = item[0], item[1]
                c = item[2] if len(item) >= 3 else '=='
                entry = {'masterVarName': m, 'masterValue': list(v) if isinstance(v, tuple) else v}
                if c != '==':
                    entry['condition'] = c
                built.append(entry)
            control['conditions'] = built
            control['conditionsLogic'] = 'AND'
            control['gateHides'] = True
            control['masterIndent'] = bool(indent)
            return control
        return self.gated(control, conds[-1][0], conds[-1][1])

    def radio(self, text, key, labels, head, body, inline=False):
        gen = getattr(self.tpl, 'generateOptions', None)
        opts = gen(list(labels)) if gen is not None else [{'label': s} for s in labels]
        t_text = self.tip(head, body, self._def_text(key, 'choice', labels=labels))
        try:
            return self.tpl.createRadioButtonGroup(text, key, opts, self.values[key], tooltip=t_text, inline=inline)
        except TypeError:
            return _ctl(self.tpl.createRadioButtonGroup, text, key, opts, self.values[key], tooltip=t_text)

    def dropdown(self, text, key, labels, head, body):
        fn = getattr(self.tpl, 'createDropdown', None)
        if fn is None:
            return self.radio(text, key, labels, head, body, inline=False)
        gen = getattr(self.tpl, 'generateOptions', None)
        opts = gen(list(labels)) if gen is not None else [{'label': s} for s in labels]
        t_text = self.tip(head, body, self._def_text(key, 'choice', labels=labels))
        try:
            return fn(text, key, opts, self.values[key], tooltip=t_text)
        except TypeError:
            try:
                return fn(text, key, opts, self.values[key])
            except Exception:
                return self.radio(text, key, labels, head, body, inline=False)
        except Exception:
            return self.radio(text, key, labels, head, body, inline=False)

    def textInput(self, text, key, head, body, max_len=24, width=240):
        t_text = self.tip(head, body, self._def_text(key, 'str'))
        fn = getattr(self.tpl, 'createInput', None) or getattr(self.tpl, 'createTextInput', None)
        ctl = _ctl(fn, text, key, self.values[key], tooltip=t_text) if fn is not None else {'type': 'TextInput', 'text': text, 'varName': key, 'value': self.values[key], 'tooltip': t_text}
        if isinstance(ctl, dict):
            ctl['maxLength'] = int(max_len)
            if width:
                ctl['width'] = int(width)
        return ctl

    def actionBtn(self, var_name, btn_text, label_text, head, body, width=148):
        fn = getattr(self.tpl, 'createActionButton', None)
        if fn is not None:
            try:
                return fn(var_name, btn_text, label=label_text, width=width, tooltip=self.tip(head, body))
            except TypeError:
                try:
                    return fn(var_name, btn_text, label=label_text, tooltip=self.tip(head, body))
                except Exception:
                    pass
            except Exception:
                pass
        if self.new:
            comp = {'type': 'Button', 'varName': var_name, 'text': label_text,
                    'button': {'name': var_name, 'text': btn_text, 'width': width, 'align': 'right'}}
            t = self.tip(head, body)
            if t:
                comp['tooltip'] = t
            return comp
        return self.label(label_text)

    def subsec(self, master_key, idx, title, items):
        if not self.new:
            return [self.label(u'<b>%s</b>' % title)] + list(items)
        out = []
        for ctl in items:
            if isinstance(ctl, dict):
                indent = bool(ctl.get('masterIndent', False))
                if 'conditions' in ctl:
                    conds = list(ctl['conditions'])
                elif 'masterVarName' in ctl:
                    entry = {
                        'masterVarName': ctl.pop('masterVarName'),
                        'masterValue': ctl.pop('masterValue'),
                    }
                    if 'condition' in ctl:
                        entry['condition'] = ctl.pop('condition')
                    conds = [entry]
                else:
                    conds = []
                conds = [{'masterVarName': master_key, 'masterValue': idx}] + conds
                if len(conds) == 1:
                    ctl['masterVarName'] = master_key
                    ctl['masterValue'] = idx
                    ctl['gateHides'] = True
                    ctl['masterIndent'] = indent
                else:
                    ctl['conditions'] = conds
                    ctl['conditionsLogic'] = 'AND'
                    ctl['gateHides'] = True
                    ctl['masterIndent'] = indent
            out.append(ctl)
        return out

    def tab(self, title, items):
        fn = getattr(self.tpl, 'createTab', None) if self.new else None
        if fn is not None:
            try:
                return fn(title, list(items))
            except Exception:
                pass
        return [self.label(u'<b>%s</b>' % title)] + list(items)


class MenuTemplateBuilder(object):
    """Builds the 2-column Aslain Mod Menu template."""

    def __init__(self, converter, preview_renderer, is_lesta=False):
        self._converter = converter
        self._preview = preview_renderer
        self._is_lesta = bool(is_lesta)

    def build(self, tpl, ver, show_v3=True):
        w = _WidgetDsl(tpl, ver, self._converter.current_values(self._preview.state))
        tab_main = build_tab_main(w, show_v3, is_lesta=self._is_lesta)
        tab_hangar = build_tab_hangar(w)
        tab_colors_legacy = build_tab_colors_legacy(w)
        b_secs = BATTLE_SECTIONS_V3 if show_v3 else BATTLE_SECTIONS_LEGACY
        if int(w.values.get('battleSection', 0) or 0) >= len(b_secs):
            w.values['battleSection'] = 0
        b_nav = [w.radio(
            u'<b>Раздел боевой панели</b>', 'battleSection', b_secs,
            u'Раздел боевой панели',
            u'Переключает подразделы настроек боевой панели кнопками.',
            inline=True,
        )] if w.new else []
        if show_v3:
            battle_items = (
                b_nav +
                w.subsec('battleSection', 0, u'Основное', tab_main) +
                w.subsec('battleSection', 1, u'Рамка и звёзды', build_tab_frame_stars(w)) +
                w.subsec('battleSection', 2, u'Шапка и полоска', build_tab_header_bar(w)) +
                w.subsec('battleSection', 3, u'Урон и ассист', build_tab_dmg_assist(w)) +
                w.subsec('battleSection', 4, u'Цвета', build_tab_colors_v3(w) + tab_colors_legacy)
            )
        else:
            battle_items = (
                b_nav +
                w.subsec('battleSection', 0, u'Основное', tab_main) +
                w.subsec('battleSection', 1, u'Цвета', tab_colors_legacy)
            )
        col1 = w.tab(u'Боевая панель', battle_items) + w.tab(u'Ангар', tab_hangar)

        if w.new:
            b_src, _bw, _bh, b_w, b_h = self._preview.render(target=0)
            h_src, _hw, _hh, h_w, h_h = self._preview.render(target=1)
            self._preview.state['source'] = h_src if int(self._preview.state.get('target', 0) or 0) == 1 else b_src
            self._preview.state['keyBattle'] = (b_src, b_w, b_h)
            self._preview.state['keyHangar'] = (h_src, h_w, h_h)
            self._preview.state['key'] = self._preview.state['keyHangar'] if int(self._preview.state.get('target', 0) or 0) == 1 else self._preview.state['keyBattle']
            col2 = (
                w.tab(u'Боевая панель', build_preview_column_battle(w, show_v3, b_src, b_w, b_h)) +
                w.tab(u'Ангар', build_preview_column_hangar(w, h_src, h_w, h_h))
            )
        else:
            preview_src, _bw, _bh, preview_w, preview_h = self._preview.render()
            self._preview.state['source'] = preview_src
            self._preview.state['key'] = (preview_src, preview_w, preview_h)
            col2 = build_preview_column(w, show_v3, preview_src, preview_w, preview_h)
        return {'modDisplayName': u'Три отметки на стволе', 'modVersion': MOD_VERSION, 'column1': col1, 'column2': col2}
