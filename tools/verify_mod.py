# -*- coding: utf-8 -*-
from __future__ import absolute_import

import argparse
import base64
import hashlib
import json
import marshal
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from wot_stubs import build_strict_wot_env, install_modules, restore_modules

PY27_MAGIC = '\x03\xf3\r\n'
NODE_FALLBACK = r'C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe'


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().upper()


def _find_node():
    for candidate in ('node', NODE_FALLBACK):
        try:
            proc = subprocess.Popen([candidate, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _err = proc.communicate()
            if proc.returncode == 0 and out.strip():
                return candidate
        except OSError:
            pass
    return None


def _read_mod_version():
    meta_path = os.path.join(REPO_ROOT, 'package', 'meta.xml')
    root = ET.parse(meta_path).getroot()
    ver = (root.findtext('version') or '').strip()
    if not ver:
        raise RuntimeError('Missing <version> in %s' % meta_path)
    return ver


def stage_unit_tests():
    proc = subprocess.Popen(
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = proc.communicate()
    if proc.returncode != 0:
        print(out)
        raise RuntimeError('Unit/Contract/Architecture test suite failed (rc=%d)' % proc.returncode)
    m = re.search(r'Ran (\d+) tests?', out)
    count = int(m.group(1)) if m else 0
    return 'All %d tests passed (math, UI contracts, frontend, architecture)' % count


def stage_package_audit(wot_dir, mod_subdir, mod_ext, check_install):
    ver = _read_mod_version()
    dist_wotmod = os.path.join(REPO_ROOT, 'dist', 'dm.threemarks_%s%s' % (ver, mod_ext))
    if not os.path.isfile(dist_wotmod):
        raise RuntimeError('Built archive not found: %s' % dist_wotmod)

    zv = zipfile.ZipFile(dist_wotmod, 'r')
    try:
        infos = zv.infolist()
        arcs = set()
        pyc_count = 0
        for info in infos:
            if info.compress_type != zipfile.ZIP_STORED:
                raise RuntimeError('Entry %s is compressed (%d), expected ZIP_STORED' % (info.filename, info.compress_type))
            if info.filename.endswith('.py') or info.filename.endswith('.tmp'):
                raise RuntimeError('Forbidden source/temp file in archive: %s' % info.filename)
            arcs.add(info.filename)
            if info.filename.endswith('.pyc'):
                pyc_count += 1
                data = zv.read(info.filename)
                if data[:4] != PY27_MAGIC:
                    raise RuntimeError('Bad Python 2.7 magic in %s' % info.filename)
                marshal.loads(data[8:])

        entry_pyc = 'res/scripts/client/gui/mods/mod_three_marks.pyc'
        if entry_pyc not in arcs:
            raise RuntimeError('Missing entrypoint: %s' % entry_pyc)
        entry_code = marshal.loads(zv.read(entry_pyc)[8:])
        for fn_name in ('init', 'fini'):
            if fn_name not in entry_code.co_names and fn_name not in entry_code.co_varnames:
                raise RuntimeError('Entrypoint %s missing %s()' % (entry_pyc, fn_name))

        gen_path = 'res/gui/gen_resources/dm_threemarks.json'
        if gen_path not in arcs:
            raise RuntimeError('Missing %s' % gen_path)
        gen_items = json.loads(zv.read(gen_path).decode('utf-8'))
        for item in gen_items:
            rel_ui = item['path'].replace('coui://', 'res/')
            if rel_ui not in arcs:
                raise RuntimeError('Missing layout resource in archive: %s' % rel_ui)
            html = zv.read(rel_ui).decode('utf-8')
            base_dir = os.path.dirname(rel_ui)
            for tag_ref in re.findall(r'(?:src|href)="([^"]+)"', html):
                ref_arc = (base_dir + '/' + tag_ref).replace('\\', '/')
                if ref_arc not in arcs:
                    raise RuntimeError('Missing asset referenced by HTML: %s' % ref_arc)

        res_map_path = 'res/mods/configs/res_map/dm_threemarks.json'
        if res_map_path not in arcs:
            raise RuntimeError('Missing Lesta OpenWG layout config: %s' % res_map_path)
        res_map_items = json.loads(zv.read(res_map_path).decode('utf-8'))
        for item in res_map_items:
            rel_ui = item['path'].replace('coui://', 'res/')
            if rel_ui not in arcs:
                raise RuntimeError('Missing layout referenced by res_map: %s' % rel_ui)

        css_arc = 'res/gui/gameface/mods/dm/ThreeMarks/ThreeMarks.css'
        css_txt = zv.read(css_arc).decode('utf-8')
        for img_ref in re.findall(r'img://([^)\s"\']+)', css_txt):
            img_arc = 'res/' + img_ref
            if img_arc not in arcs:
                raise RuntimeError('Missing image referenced by CSS: %s' % img_arc)
        for mod_asset in re.findall(r'coui://(gui/gameface/mods/dm/ThreeMarks/[^)\s"\']+)', css_txt):
            asset_arc = 'res/' + mod_asset
            if asset_arc not in arcs:
                raise RuntimeError('Missing mod asset referenced by CSS: %s' % asset_arc)
            if asset_arc.lower().endswith('.ttf'):
                hdr = zv.read(asset_arc)[:4]
                if hdr not in ('\x00\x01\x00\x00', 'OTTO', 'true'):
                    raise RuntimeError('Invalid TTF/OTF header in %s: %r' % (asset_arc, hdr))

        src_py_count = sum(1 for _r, _d, fs in os.walk(os.path.join(REPO_ROOT, 'src')) for fn in fs if fn.endswith('.py'))
        if pyc_count != src_py_count:
            raise RuntimeError('PYC count mismatch: archive=%d vs src=%d' % (pyc_count, src_py_count))
    finally:
        zv.close()

    node_exe = _find_node()
    if node_exe is None:
        raise RuntimeError('Node.js not found for ES5 syntax verification')
    ui_dir = os.path.join(REPO_ROOT, 'package', 'res', 'gui', 'gameface', 'mods', 'dm', 'ThreeMarks')
    js_count = 0
    for root_dir, _dirs, files in os.walk(ui_dir):
        for fn in sorted(files):
            if fn.endswith('.js'):
                js_count += 1
                p = os.path.join(root_dir, fn)
                proc = subprocess.Popen([node_exe, '--check', p], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _o, err = proc.communicate()
                if proc.returncode != 0:
                    raise RuntimeError('Node syntax error in %s: %s' % (p, err))

    dist_sha = _sha256(dist_wotmod)
    msg = '%d entries (%d PYC, %d JS OK), SHA256=%s' % (len(arcs), pyc_count, js_count, dist_sha[:12])
    if check_install:
        installed = os.path.join(wot_dir, 'mods', mod_subdir, os.path.basename(dist_wotmod))
        if not os.path.isfile(installed):
            raise RuntimeError('Installed archive missing: %s' % installed)
        inst_sha = _sha256(installed)
        if inst_sha != dist_sha:
            raise RuntimeError('Installed SHA256 mismatch: game=%s vs dist=%s' % (inst_sha, dist_sha))
        msg += ' (installed SHA256 match)'
    return msg, dist_wotmod


def stage_compiled_runtime(wotmod_path):
    tmp_dir = tempfile.mkdtemp(prefix='tm_verify_rt_')
    mods_dir = os.path.join(tmp_dir, 'extracted')
    work_dir = os.path.join(tmp_dir, 'work')
    os.makedirs(mods_dir)
    os.makedirs(work_dir)
    orig_cwd = os.getcwd()
    orig_path = list(sys.path)
    env = build_strict_wot_env()
    saved_mods = None
    try:
        zv = zipfile.ZipFile(wotmod_path, 'r')
        try:
            prefix = 'res/scripts/client/gui/mods/'
            for info in zv.infolist():
                if info.filename.startswith(prefix) and not info.filename.endswith('/'):
                    rel = info.filename[len(prefix):]
                    out_path = os.path.join(mods_dir, rel.replace('/', os.sep))
                    out_parent = os.path.dirname(out_path)
                    if not os.path.isdir(out_parent):
                        os.makedirs(out_parent)
                    with open(out_path, 'wb') as f:
                        f.write(zv.read(info.filename))
        finally:
            zv.close()

        for mod_name in list(sys.modules):
            if mod_name == 'mod_three_marks' or mod_name.startswith('dm_threemarks'):
                sys.modules.pop(mod_name, None)

        sys.path.insert(0, mods_dir)
        os.chdir(work_dir)
        saved_mods = install_modules(env['modules'])

        import mod_three_marks
        if not mod_three_marks.__file__.lower().endswith('.pyc'):
            raise RuntimeError('Expected compiled .pyc entrypoint, loaded %s' % mod_three_marks.__file__)

        mod_three_marks.init()
        app = mod_three_marks._app
        if app is None:
            raise RuntimeError('mod_three_marks._app is None after init()')

        api = env['api']
        tpl = env['tpl']
        reg_tpl = api.templates.get('dm.threemarks')
        if not reg_tpl:
            raise RuntimeError('Mod Menu template was not registered')
        if tpl.tabs_created != [u'Боевая панель', u'Ангар', u'Боевая панель', u'Ангар']:
            raise RuntimeError('Expected 2 top tabs [Боевая панель, Ангар] in col1 & col2, got %r' % (tpl.tabs_created,))
        col2_tabs = dict((t.get('title'), t.get('items') or ()) for t in (reg_tpl.get('column2') or ()) if t.get('type') == 'Tab')
        if not any(c.get('varName') == 'marksLivePreview' for c in col2_tabs.get(u'Боевая панель', ())) or \
                not any(c.get('varName') == 'marksLivePreviewHangar' for c in col2_tabs.get(u'Ангар', ())):
            raise RuntimeError('Expected tab-scoped Battle/Hangar preview images in column2: %r' % (col2_tabs.keys(),))
        tabs_by_title = dict((t.get('title'), t.get('items') or ()) for t in (reg_tpl.get('column1') or ()) if t.get('type') == 'Tab')
        b_nav = [c for c in tabs_by_title.get(u'Боевая панель', ()) if c.get('varName') == 'battleSection']
        if not b_nav or len(b_nav[0].get('options') or ()) != 5 or 'span' in b_nav[0]:
            raise RuntimeError('Expected 5-button battleSection switcher inside Боевая панель tab, got %r' % (b_nav,))
        h_nav = [c for c in tabs_by_title.get(u'Ангар', ()) if c.get('varName') == 'hangarSection']
        if not h_nav or len(h_nav[0].get('options') or ()) != 4 or 'span' in h_nav[0]:
            raise RuntimeError('Expected 4-button hangarSection switcher inside Ангар tab, got %r' % (h_nav,))
        if 'dm.threemarks' not in api.defaults:
            raise RuntimeError('setModDefaults() was not called')
        if api.live_cb is None or api.button_cb is None:
            raise RuntimeError('Live settings or button callback not registered')
        flat_tpl = json.dumps(api.templates['dm.threemarks'], ensure_ascii=False)
        if u'Тактическая (трек + курсор)' in flat_tpl:
            raise RuntimeError('Removed bar style still present in registered menu template')

        # Hangar entry + Gameface view/window load + onReady -> payload verification
        env['pe'].onAccountShowGUI.emit()
        env['flush_callbacks']()
        if not env['windows']:
            raise RuntimeError('Hangar TmWindow was not created')
        h_win = env['windows'][-1]
        if not h_win.hidden:
            raise RuntimeError('Hangar TmWindow became visible prematurely before JS onReady')
        h_init_payload = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if h_init_payload.get('mode') != 'h':
            raise RuntimeError('Hangar TmModel missing initial mode=h payload before onReady: %r' % (h_init_payload,))
        h_win.content.getViewModel()._cmds['onReady'].emit('ready')
        if h_win.hidden:
            raise RuntimeError('Hangar TmWindow remained hidden after both _onReady and JS onReady')
        h_payload = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if h_payload.get('mode') != 'h' or 'v3d' not in h_payload or 'v3m' not in h_payload:
            raise RuntimeError('Invalid hangar Gameface payload: %r' % (h_payload,))

        # Client onSyncCompleted passes 2 args (reason, diff)
        env['items_cache'].onSyncCompleted.emit(1, {'vehicles': {}})
        env['cv'].onChanged.emit()

        # Live Hangar UI change must update active Hangar window immediately without switching tank
        api.live_cb('dm.threemarks', {'vhBgOpacity': 0.90})
        h_payload_live = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if abs(float(h_payload_live.get('ui', {}).get('vh', {}).get('bgo', 0.0)) - 0.90) > 0.01:
            raise RuntimeError('Hangar panel payload did not update live on menu change without vehicle switch')

        # Switching tank in hangar must update panel even if g_currentVehicle.onChanged did not fire
        env['cv'].item.intCD = 62273
        env['flush_callbacks'](limit=2)
        if app._c.hangar_service._last_int_cd != 62273:
            raise RuntimeError('Hangar panel did not detect tank switch to 62273 without onChanged')
        h_payload_sw = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if app._c.curve_sync.is_pending(62273):
            if h_payload_sw.get('pct') != u'--.--%':
                raise RuntimeError('Expected loading placeholder --.--% while curve pending: %r' % (h_payload_sw.get('pct'),))
            app._c.curve_sync._apply_curve('62273', {}, 0, 'offline')
            app._c.curve_sync._apply_history('62273', {}, False, 'offline')
            app._c.hangar_service.refresh()
            h_payload_sw = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if h_payload_sw.get('pct') != u'44.11%':
            raise RuntimeError('Hangar panel did not update on tank switch without onChanged: %r' % (h_payload_sw.get('pct'),))

        # Interactive Aslain menu checks: tab switching, live preview SVG, action buttons
        reloads_before = len(api.reloaded)
        api.live_cb('dm.threemarks', {'battlePanelVariant': 1})
        api.live_cb('dm.threemarks', {'battlePanelVariant': 0})
        if len(api.reloaded) < reloads_before + 2:
            raise RuntimeError('reloadModTemplate did not switch tabs cleanly')

        imgs_before = len(api.images)
        api.live_cb('dm.threemarks', {'vhBarStyle': 3, 'vhScale': 1.15, 'previewTarget': 1, 'previewAlt': 1})
        env['flush_callbacks'](limit=1)
        if len(api.images) <= imgs_before:
            raise RuntimeError('updateImage did not emit new SVG on live setting change')
        svg_uri = api.images[-1][2]
        if not svg_uri.startswith('data:image/svg+xml;base64,'):
            raise RuntimeError('Unexpected preview image URI: %s' % svg_uri[:40])
        svg_xml = base64.b64decode(svg_uri.split(',', 1)[1]).decode('utf-8')
        if '<svg' not in svg_xml or 'KIBERSPORT' not in svg_xml:
            raise RuntimeError('Decoded preview SVG missing expected content')
        if '@font-face' in svg_xml:
            raise RuntimeError('Preview SVG must not embed @font-face')

        if api.input_previews:
            raise RuntimeError('Unexpected registerInputPreview keys (small preview box removed): %r' % (sorted(api.input_previews.keys()),))

        # Update tab-scoped Battle & Hangar previews independently on TextInput edits and sync twin previewState
        api.live_cb('dm.threemarks', {'v3DamageLabel': 1, 'v3DamageCustomLabel': u'Тест 22 323'})
        env['flush_callbacks'](limit=1)
        battle_imgs = [img for img in api.images if img[1] == 'marksLivePreview']
        dmg_svg = base64.b64decode(battle_imgs[-1][2].split(',', 1)[1]).decode('utf-8')
        if u'Тест 22 323' not in dmg_svg:
            raise RuntimeError('Battle preview SVG missing updated v3DamageCustomLabel')

        api.live_cb('dm.threemarks', {'v3BarStyle': 3, 'v3BarCustomText': u'LIVE BAR'})
        env['flush_callbacks'](limit=1)
        battle_imgs = [img for img in api.images if img[1] == 'marksLivePreview']
        bar_svg = base64.b64decode(battle_imgs[-1][2].split(',', 1)[1]).decode('utf-8')
        if u'LIVE BAR' not in bar_svg:
            raise RuntimeError('Battle preview SVG missing live typed v3BarCustomText')

        api.live_cb('dm.threemarks', {'vhBarCustomText': u'HANGAR LIVE'})
        env['flush_callbacks'](limit=1)
        hangar_imgs = [img for img in api.images if img[1] == 'marksLivePreviewHangar']
        h_live_svg = base64.b64decode(hangar_imgs[-1][2].split(',', 1)[1]).decode('utf-8')
        if u'HANGAR LIVE' not in h_live_svg:
            raise RuntimeError('Hangar preview SVG missing updated vhBarCustomText')
        h_payload_txt = json.loads(h_win.content.getViewModel()._props.get('payload', '{}'))
        if h_payload_txt.get('ui', {}).get('vh', {}).get('bt') != 'HANGAR LIVE':
            raise RuntimeError('Hangar panel payload did not update live on vhBarCustomText edit')

        ctl_before_s = len(api.control_values)
        api.live_cb('dm.threemarks', {'previewStateHangar': 1})
        if ('dm.threemarks', 'previewState', 1) not in api.control_values[ctl_before_s:]:
            raise RuntimeError('Expected previewState twin sync on previewStateHangar=1')

        for btn_name in ('v3ResetPreset', 'vhResetPreset', 'resetPosition', 'resetHangarPosition'):
            api.button_cb('dm.threemarks', btn_name, btn_name)

        # Leave lobby -> Battle -> FeedbackSummary hook -> Exit battle -> fini()
        env['pe'].onAvatarBecomePlayer.emit()
        env['pe'].onAvatarReady.emit()
        env['flush_callbacks']()
        if len(env['windows']) < 2:
            raise RuntimeError('Battle TmWindow was not created')
        b_win = env['windows'][-1]
        if not b_win.hidden:
            raise RuntimeError('Battle TmWindow became visible prematurely before JS onReady')
        b_init_payload = json.loads(b_win.content.getViewModel()._props.get('payload', '{}'))
        if b_init_payload.get('mode') != 'b':
            raise RuntimeError('Battle TmModel missing initial mode=b payload before onReady: %r' % (b_init_payload,))
        b_win.content.getViewModel()._cmds['onReady'].emit('ready')
        if b_win.hidden:
            raise RuntimeError('Battle TmWindow remained hidden after both _onReady and JS onReady')
        b_payload = json.loads(b_win.content.getViewModel()._props.get('payload', '{}'))
        if b_payload.get('mode') != 'b' or 'v3d' not in b_payload or 'v3m' not in b_payload:
            raise RuntimeError('Invalid battle Gameface payload: %r' % (b_payload,))

        env['FeedbackAdaptor']().handleBattleEventsSummary({})
        env['pe'].onAvatarBecomeNonPlayer.emit()
        mod_three_marks.fini()

        if mod_three_marks._app is not None:
            raise RuntimeError('mod_three_marks._app not cleared by fini()')
        if not api.unregistered_live:
            raise RuntimeError('unregisterLiveSettingsChange was not called on fini()')
        if api.input_previews or api.unregistered_previews:
            raise RuntimeError('Unexpected input preview hooks registered/unregistered: %r' % (api.input_previews,))
        if env['FeedbackAdaptor'].handleBattleEventsSummary != env['orig_feedback']:
            raise RuntimeError('BattleFeedbackAdaptor hook not restored on fini()')

        log_path = os.path.join(work_dir, 'mods', 'configs', 'three_marks', 'three_marks.log')
        if not os.path.isfile(log_path):
            raise RuntimeError('Runtime log was not written: %s' % log_path)
        log_txt = open(log_path, 'rb').read().decode('utf-8', 'replace')
        if 'registered in Mod Menu 2.1.15' not in log_txt:
            raise RuntimeError('Log missing Mod Menu 2.1.15 registration confirmation')
        err_lines = [ln for ln in log_txt.splitlines() if 'ERROR' in ln or 'Traceback' in ln]
        if err_lines:
            raise RuntimeError('Errors detected in simulated runtime log:\n' + '\n'.join(err_lines))
        _run_lesta_sim(mods_dir, work_dir)
        return 'Compiled .pyc E2E simulation OK (EU + Lesta RU Scaleform/OpenWG/Izeberg, 0 log errors)'
    finally:
        try:
            os.chdir(orig_cwd)
        except Exception:
            pass
        sys.path[:] = orig_path
        if saved_mods is not None:
            restore_modules(saved_mods)
        for mod_name in list(sys.modules):
            if mod_name == 'mod_three_marks' or mod_name.startswith('dm_threemarks'):
                sys.modules.pop(mod_name, None)
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_lesta_sim(mods_dir, parent_work_dir):
    lesta_work = os.path.join(parent_work_dir, 'lesta_work')
    os.makedirs(lesta_work)
    env = build_strict_wot_env()
    mods = env['modules']
    mods['constants'].CURRENT_REALM = 'RU'
    delattr(mods['constants'], 'AUTH_REALM')
    mods.pop('gui.lobby_state_machine', None)
    mods.pop('gui.lobby_state_machine.states', None)
    mods['gui.Scaleform.lobby_entry'] = object()

    class _LestaR(object):
        pass

    mods['gui.impl.gen'].R = _LestaR()

    class _FakeModDynAccessor(object):
        def __init__(self, mod_id):
            self.mod_id = mod_id

        def __call__(self):
            return 19

    owg_mod = type(sys)('openwg_gameface')
    owg_mod.ModDynAccessor = _FakeModDynAccessor
    mods['openwg_gameface'] = owg_mod

    hangar_alias = ['hangar']

    def _get_view(layer):
        if layer == 2:
            return type('V', (object,), {'alias': hangar_alias[0]})()
        return None

    lobby_app = type('L', (object,), {'containerManager': type('CM', (object,), {'getView': staticmethod(_get_view)})()})()
    mods['skeletons.gui.app_loader'].IAppLoader = 'IAppLoader'
    env['modules']['gui.Scaleform'].lobby_entry = mods['gui.Scaleform.lobby_entry']
    mods['gui.Scaleform.lobby_entry'] = mods['gui.Scaleform.lobby_entry']
    # Reuse deps_map inside instance closure by overriding helpers.dependency.instance
    orig_instance = mods['helpers.dependency'].instance
    mods['helpers.dependency'].instance = lambda cls: (
        type('AL', (object,), {'getDefBattleApp': lambda s: None, 'getDefLobbyApp': lambda s: lobby_app})()
        if cls == 'IAppLoader' else orig_instance(cls)
    )

    orig_cwd = os.getcwd()
    saved_mods = None
    try:
        for mod_name in list(sys.modules):
            if mod_name == 'mod_three_marks' or mod_name.startswith('dm_threemarks') or mod_name in (
                'openwg_gameface', 'gui.lobby_state_machine', 'gui.lobby_state_machine.states',
            ):
                sys.modules.pop(mod_name, None)
        os.chdir(lesta_work)
        saved_mods = install_modules(mods)
        import mod_three_marks
        mod_three_marks.init()
        app = mod_three_marks._app
        if app._c.realm_domain != 'ru':
            raise RuntimeError('Lesta sim expected realm_domain=="ru", got %r' % (app._c.realm_domain,))
        if abs(app._c.epoch._server_hour - 3.0) > 1e-6:
            raise RuntimeError('Lesta sim expected epoch hour 3.0, got %r' % (app._c.epoch._server_hour,))
        env['pe'].onAccountShowGUI.emit()
        env['flush_callbacks']()
        if not env['windows']:
            raise RuntimeError('Lesta Hangar TmWindow was not created via ModDynAccessor')
        h_win = env['windows'][-1]
        if h_win.content._settings.layoutID != 19:
            raise RuntimeError('Lesta TmView did not use ModDynAccessor layoutID 19')
        hangar_alias[0] = 'techtree'
        shown, st_id = app._c.hangar_env.hangar_state()
        if shown is not False or st_id != 'techtree':
            raise RuntimeError('Lesta Scaleform hangar_state fallback failed on non-hangar alias: %r %r' % (shown, st_id))
        env['pe'].onAvatarBecomePlayer.emit()
        env['pe'].onAvatarReady.emit()
        env['flush_callbacks']()
        if len(env['windows']) < 2:
            raise RuntimeError('Lesta Battle TmWindow was not created')
        env['pe'].onAvatarBecomeNonPlayer.emit()
        mod_three_marks.fini()
        log_path = os.path.join(lesta_work, 'mods', 'configs', 'three_marks', 'three_marks.log')
        log_txt = open(log_path, 'rb').read().decode('utf-8', 'replace')
        if 'realm=ru' not in log_txt:
            raise RuntimeError('Lesta sim log missing realm=ru')
        err_lines = [ln for ln in log_txt.splitlines() if 'ERROR' in ln or 'Traceback' in ln]
        if err_lines:
            raise RuntimeError('Errors detected in Lesta simulated runtime log:\n' + '\n'.join(err_lines))
    finally:
        try:
            os.chdir(orig_cwd)
        except Exception:
            pass
        if saved_mods is not None:
            restore_modules(saved_mods)
        for mod_name in list(sys.modules):
            if mod_name == 'mod_three_marks' or mod_name.startswith('dm_threemarks') or mod_name == 'openwg_gameface':
                sys.modules.pop(mod_name, None)


def stage_live_game_log(wot_dir):
    log_path = os.path.join(wot_dir, 'mods', 'configs', 'three_marks', 'three_marks.log')
    if not os.path.isfile(log_path):
        return True, 'No game log yet at %s' % log_path
    lines = open(log_path, 'rb').read().decode('utf-8', 'replace').splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if 'init, version ' in line:
            start_idx = i
    session = lines[start_idx:]
    issues = [ln for ln in session if ('ERROR' in ln or 'Traceback' in ln or 'registered in Mod Menu 1.0.0' in ln)]
    if issues:
        return False, 'Latest WoT session (%d lines) has %d issue(s):\n  %s' % (
            len(session), len(issues), '\n  '.join(issues[:10]),
        )
    return True, 'Latest WoT session (%d lines) clean (0 errors)' % len(session)


def main():
    parser = argparse.ArgumentParser(description='Self-verification harness for dm.threemarks')
    parser.add_argument('--wot-dir', default=r'F:\game\TankiEU\World_of_Tanks_EU')
    parser.add_argument('--mod-subdir', default='2.4.2.0')
    parser.add_argument('--mod-ext', default='.wotmod')
    parser.add_argument('--client', default='EU')
    parser.add_argument('--no-install-check', action='store_true')
    parser.add_argument('--check-game-log', action='store_true')
    args = parser.parse_args()

    try:
        msg1 = stage_unit_tests()
        print('[PASS] Stage 1 (Tests): %s' % msg1)
        msg2, wotmod_path = stage_package_audit(args.wot_dir, args.mod_subdir, args.mod_ext, not args.no_install_check)
        print('[PASS] Stage 2 (Archive): %s' % msg2)
        msg3 = stage_compiled_runtime(wotmod_path)
        print('[PASS] Stage 3 (Runtime): %s' % msg3)
        ok_log, msg4 = stage_live_game_log(args.wot_dir)
        tag = 'PASS' if ok_log else ('FAIL' if args.check_game_log else 'INFO')
        print('[%s] Stage 4 (GameLog): %s' % (tag, msg4))
        if args.check_game_log and not ok_log:
            return 1
        return 0
    except Exception as exc:
        print('[FAIL] %s' % exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
