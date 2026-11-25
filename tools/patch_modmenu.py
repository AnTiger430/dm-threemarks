#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Idempotent patcher for Aslain Mod Menu (ModMenu.css + ModMenu.js):
1. Adds ThreeMarks @font-face definitions to ModMenu.css so previews render bundled TTFs.
2. Adds renderInlineDataSvg to ModMenu.js so data:image/svg+xml previews render via DOM+SVG with @font-face support.
3. Adds 0ms/25ms instant sendTextLive + Enter handling for TextInput and inline SVG fast-swap.
"""
from __future__ import absolute_import, print_function

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile

CSS_MARKER = '/* dm-threemarks-fonts */'
FONT_FACES_CSS = """
/* dm-threemarks-fonts */
@font-face { font-family: "ThreeMarksPFDINMax"; font-weight: 400; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/PFDINMax-CompressedRegular.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksPFDINMax"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/PFDINMax-CompressedBold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksDINRound"; font-weight: 400; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/DINRoundPro-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksDINRound"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/DINRoundPro-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksJura"; font-weight: 400; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Jura-Regular.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksJura"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Jura-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksExo2"; font-weight: 500; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Exo2-Medium.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksExo2"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Exo2-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksRubik"; font-weight: 500; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Rubik-Medium.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksRubik"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Rubik-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksFiraCond"; font-weight: 500; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/FiraSansCondensed-Medium.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksFiraCond"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/FiraSansCondensed-Bold.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksTektur"; font-weight: 500; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Tektur-Medium.ttf) format("truetype"); }
@font-face { font-family: "ThreeMarksTektur"; font-weight: 700; font-style: normal; src: url(coui://gui/gameface/mods/dm/ThreeMarks/fonts/Tektur-Bold.ttf) format("truetype"); }
"""

INLINE_SVG_HELPERS = """
var _MM_SVG_NS = 'http://www.w3.org/2000/svg';
function isDataSvgUrl(u) {
return String(u || '').indexOf('data:image/svg+xml;base64,') === 0;
}
function _mmDecodeB64Utf8(b64) {
var raw = '';
if (typeof window.atob === 'function') {
raw = window.atob(b64);
} else {
var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
var i = 0, clean = String(b64).replace(/[^A-Za-z0-9\\+\\/\\=]/g, '');
while (i < clean.length) {
var e1 = chars.indexOf(clean.charAt(i++)), e2 = chars.indexOf(clean.charAt(i++));
var e3 = chars.indexOf(clean.charAt(i++)), e4 = chars.indexOf(clean.charAt(i++));
var c1 = (e1 << 2) | (e2 >> 4), c2 = ((e2 & 15) << 4) | (e3 >> 2), c3 = ((e3 & 3) << 6) | e4;
raw += String.fromCharCode(c1);
if (e3 !== 64 && e3 >= 0) raw += String.fromCharCode(c2);
if (e4 !== 64 && e4 >= 0) raw += String.fromCharCode(c3);
}
}
var out = '', k = 0, n = raw.length;
while (k < n) {
var b0 = raw.charCodeAt(k++);
if (b0 < 128) { out += String.fromCharCode(b0); }
else if (b0 > 191 && b0 < 224 && k < n) {
var b1 = raw.charCodeAt(k++);
out += String.fromCharCode(((b0 & 31) << 6) | (b1 & 63));
} else if (b0 >= 224 && b0 < 240 && k + 1 < n) {
var c2a = raw.charCodeAt(k++), c2b = raw.charCodeAt(k++);
out += String.fromCharCode(((b0 & 15) << 12) | ((c2a & 63) << 6) | (c2b & 63));
} else if (k + 2 < n) {
var d1 = raw.charCodeAt(k++), d2 = raw.charCodeAt(k++), d3 = raw.charCodeAt(k++);
var cp = (((b0 & 7) << 18) | ((d1 & 63) << 12) | ((d2 & 63) << 6) | (d3 & 63)) - 0x10000;
out += String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF));
}
}
return out;
}
function _mmUnescapeXml(s) {
return String(s || '')
.replace(/&#(\\d+);/g, function (_, n) { return String.fromCharCode(parseInt(n, 10)); })
.replace(/&#x([0-9a-fA-F]+);/g, function (_, h) { return String.fromCharCode(parseInt(h, 16)); })
.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');
}
function _mmParseAttrs(s) {
var a = {}, re = /([A-Za-z_:][A-Za-z0-9_.:-]*)\\s*=\\s*(?:"([^"]*)"|'([^']*)')/g, m;
while ((m = re.exec(s)) !== null) {
a[m[1]] = _mmUnescapeXml(m[2] !== undefined ? m[2] : (m[3] || ''));
}
return a;
}
function _mmSvgEl(tag, attrs) {
var node = document.createElementNS ? document.createElementNS(_MM_SVG_NS, tag) : document.createElement(tag);
if (attrs && typeof node.setAttribute === 'function') {
for (var k in attrs) {
if (Object.prototype.hasOwnProperty.call(attrs, k)) node.setAttribute(k, String(attrs[k]));
}
}
return node;
}
function renderInlineDataSvg(frame, dataUri, wantW, wantH) {
var comma = String(dataUri || '').indexOf(',');
if (comma < 0) return null;
var svgText = '';
try { svgText = _mmDecodeB64Utf8(dataUri.slice(comma + 1)); } catch (e) { return null; }
var rootM = /<svg\\b([^>]*)>/i.exec(svgText);
var rootA = rootM ? _mmParseAttrs(rootM[1]) : {};
var vb = String(rootA.viewBox || '').trim().split(/[\\s,]+/);
var svgW = Number(rootA.width) || (vb.length === 4 ? Number(vb[2]) : 0) || 220;
var svgH = Number(rootA.height) || (vb.length === 4 ? Number(vb[3]) : 0) || 96;
var reqW = Number(wantW) || 0, reqH = Number(wantH) || 0;
var dispW = svgW, dispH = svgH;
if (reqW > 0 && reqH > 0) {
var sf = Math.min(reqW / svgW, reqH / svgH);
dispW = svgW * sf; dispH = svgH * sf;
} else if (reqW > 0) {
dispW = reqW; dispH = svgH * (reqW / svgW);
} else if (reqH > 0) {
dispH = reqH; dispW = svgW * (reqH / svgH);
}
var pxPerRem = (typeof getScale === 'function') ? Number(getScale()) : 1;
if (!isFinite(pxPerRem) || pxPerRem <= 0) pxPerRem = 1;
var scaleF = dispW / svgW;
var effPx = scaleF * pxPerRem;
var dispPxW = Math.max(1, Math.round(svgW * effPx));
var dispPxH = Math.max(1, Math.round(svgH * effPx));
var outer = el('div', 'mm-image', frame);
outer.style.position = 'relative';
outer.style.overflow = 'hidden';
outer.style.width = dispPxW + 'px';
outer.style.height = dispPxH + 'px';
var svgNode = _mmSvgEl('svg', {xmlns: _MM_SVG_NS, width: dispPxW, height: dispPxH, viewBox: '0 0 ' + svgW + ' ' + svgH});
svgNode.style.display = 'block';
svgNode.style.position = 'absolute';
svgNode.style.left = '0px';
svgNode.style.top = '0px';
svgNode.style.width = dispPxW + 'px';
svgNode.style.height = dispPxH + 'px';
outer.appendChild(svgNode);
var defsOpen = false, curClipId = '', clipMap = {}, gStack = [], clipBoxes = {};
var textOverlay = el('div', 'mm-svg-texts', outer);
textOverlay.style.position = 'absolute';
textOverlay.style.left = '0px';
textOverlay.style.top = '0px';
textOverlay.style.width = dispPxW + 'px';
textOverlay.style.height = dispPxH + 'px';
textOverlay.style.pointerEvents = 'none';
function curOpacity() {
var op = 1;
for (var gi = 0; gi < gStack.length; gi += 1) op *= gStack[gi].op;
return op;
}
function curClip() {
for (var gi = gStack.length - 1; gi >= 0; gi -= 1) {
if (gStack[gi].clip) return gStack[gi].clip;
}
return null;
}
var tagRe = /<\\/?([A-Za-z0-9:_-]+)([^>]*?)(\\/?)>/g, match;
while ((match = tagRe.exec(svgText)) !== null) {
var rawTag = match[0], name = match[1].toLowerCase(), attrStr = match[2] || '', selfClose = !!match[3];
var isClose = rawTag.charAt(1) === '/';
if (isClose) {
if (name === 'defs') defsOpen = false;
else if (name === 'clippath') curClipId = '';
else if (name === 'g' && gStack.length) gStack.pop();
continue;
}
var at = _mmParseAttrs(attrStr);
if (name === 'defs') { if (!selfClose) defsOpen = true; continue; }
if (name === 'clippath') { if (!selfClose && at.id) curClipId = at.id; continue; }
if (defsOpen || curClipId) {
if (curClipId && name === 'rect') {
clipMap[curClipId] = {x: Number(at.x) || 0, y: Number(at.y) || 0, w: Number(at.width) || svgW, h: Number(at.height) || svgH};
}
continue;
}
if (name === 'g') {
if (!selfClose) {
var gOp = (at.opacity !== undefined) ? Number(at.opacity) : 1;
if (!isFinite(gOp)) gOp = 1;
var cpMatch = /url\\(#([^)]+)\\)/.exec(String(at['clip-path'] || ''));
gStack.push({op: gOp, clip: (cpMatch && clipMap[cpMatch[1]]) ? {id: cpMatch[1], r: clipMap[cpMatch[1]]} : null});
}
continue;
}
if (name === 'svg') continue;
if (name === 'rect' || name === 'path' || name === 'line' || name === 'polygon' || name === 'polyline' || name === 'circle' || name === 'ellipse') {
if (curClip() && name === 'rect' && (Number(at['fill-opacity']) || 0) <= 0.02) continue;
var effOp = curOpacity();
var sa = {};
for (var ak in at) {
if (Object.prototype.hasOwnProperty.call(at, ak)) sa[ak] = at[ak];
}
if (effOp < 0.999) {
var baseOp = (sa.opacity !== undefined) ? Number(sa.opacity) : 1;
if (!isFinite(baseOp)) baseOp = 1;
sa.opacity = (baseOp * effOp).toFixed(3);
}
svgNode.appendChild(_mmSvgEl(name, sa));
continue;
}
if (name === 'text') {
var txtContent = '';
if (!selfClose) {
var closeIdx = svgText.indexOf('</text>', tagRe.lastIndex);
if (closeIdx >= 0) {
txtContent = _mmUnescapeXml(svgText.slice(tagRe.lastIndex, closeIdx));
tagRe.lastIndex = closeIdx + 7;
}
}
if (!txtContent) continue;
var tx = Number(at.x) || 0, ty = Number(at.y) || 0;
var fs = Math.max(6, Number(at['font-size']) || 14);
var fam = String(at['font-family'] || '');
var fw = String(at['font-weight'] || '700');
var col = String(at.fill || '#FFFFFF');
var ta = String(at['text-anchor'] || 'start');
var tOp = ((at['fill-opacity'] !== undefined) ? Number(at['fill-opacity']) : 1) *
((at.opacity !== undefined) ? Number(at.opacity) : 1) * curOpacity();
var cl = curClip();
var host = textOverlay, offX = 0, offY = 0, contW = svgW;
if (cl) {
if (!clipBoxes[cl.id]) {
var cb = el('div', 'mm-svg-clip', textOverlay);
cb.style.position = 'absolute';
cb.style.overflow = 'hidden';
cb.style.left = (cl.r.x * effPx).toFixed(1) + 'px';
cb.style.top = (cl.r.y * effPx).toFixed(1) + 'px';
cb.style.width = (cl.r.w * effPx).toFixed(1) + 'px';
cb.style.height = (cl.r.h * effPx).toFixed(1) + 'px';
clipBoxes[cl.id] = cb;
}
host = clipBoxes[cl.id];
offX = cl.r.x; offY = cl.r.y; contW = cl.r.w;
}
var fsPx = Math.max(6, Math.round(fs * effPx));
var tn = el('div', 'mm-svg-txt', host);
tn.textContent = txtContent;
tn.style.position = 'absolute';
tn.style.whiteSpace = 'nowrap';
tn.style.fontSize = fsPx + 'px';
tn.style.lineHeight = fsPx + 'px';
tn.style.fontFamily = fam ? (fam + ', Warhelios') : 'PFDINMax, Warhelios';
tn.style.fontWeight = fw;
tn.style.color = col;
if (isFinite(tOp) && tOp < 0.999) tn.style.opacity = Math.max(0, tOp).toFixed(3);
tn.style.top = ((ty - offY - fs * 0.80) * effPx).toFixed(1) + 'px';
var rx = tx - offX;
if (ta === 'middle') {
tn.style.left = (rx * effPx - 200 * effPx).toFixed(1) + 'px';
tn.style.width = Math.round(400 * effPx) + 'px';
tn.style.textAlign = 'center';
} else if (ta === 'end') {
tn.style.right = ((contW - rx) * effPx).toFixed(1) + 'px';
tn.style.textAlign = 'right';
} else {
tn.style.left = (rx * effPx).toFixed(1) + 'px';
tn.style.textAlign = 'left';
}
}
}
return outer;
}

"""

STOCK_TEXT_INPUT = """input.addEventListener('change', function () {
if (isGatedNode(wrap)) return;
values[linkage][comp.varName] = fromField(input.value);
onControlChanged(linkage, comp.varName, comp);
});
input.addEventListener('input', function () {
var typed = fromField(input.value);
if (valueEquals(values[linkage][comp.varName], typed)) return;
values[linkage][comp.varName] = typed;
onControlEdited(linkage, comp.varName);
});
if (multi) {
input.addEventListener('keydown', function (event) {
if (event.keyCode === 13) event.stopPropagation();
});
}"""

LEGACY_TIMER_INPUT = """var liveTimer = 0;
input.addEventListener('change', function () {
if (liveTimer) { window.clearTimeout(liveTimer); liveTimer = 0; }
if (isGatedNode(wrap)) return;
values[linkage][comp.varName] = fromField(input.value);
onControlChanged(linkage, comp.varName, comp);
});
input.addEventListener('input', function () {
var typed = fromField(input.value);
if (valueEquals(values[linkage][comp.varName], typed)) return;
values[linkage][comp.varName] = typed;
onControlEdited(linkage, comp.varName);
if (isGatedNode(wrap)) return;
if (liveTimer) window.clearTimeout(liveTimer);
liveTimer = window.setTimeout(function () {
liveTimer = 0;
if (!isGatedNode(wrap)) notifyLive(linkage);
}, 80);
});
if (multi) {
input.addEventListener('keydown', function (event) {
if (event.keyCode === 13) event.stopPropagation();
});
} else {
input.addEventListener('keydown', function (event) {
if (event.keyCode !== 13 || isGatedNode(wrap)) return;
if (liveTimer) { window.clearTimeout(liveTimer); liveTimer = 0; }
values[linkage][comp.varName] = fromField(input.value);
onControlChanged(linkage, comp.varName, comp);
});
}"""

INSTANT_TEXT_INPUT = """var liveTimer = 0;
var lastLiveAt = 0;
var sendTextLive = function () {
if (liveTimer) { window.clearTimeout(liveTimer); liveTimer = 0; }
if (isGatedNode(wrap)) return;
lastLiveAt = Date.now();
var env = {};
env[linkage] = values[linkage];
jsonCommand('componentChanged', env);
};
input.addEventListener('change', function () {
if (liveTimer) { window.clearTimeout(liveTimer); liveTimer = 0; }
if (isGatedNode(wrap)) return;
values[linkage][comp.varName] = fromField(input.value);
onControlChanged(linkage, comp.varName, comp);
});
input.addEventListener('input', function () {
var typed = fromField(input.value);
if (valueEquals(values[linkage][comp.varName], typed)) return;
values[linkage][comp.varName] = typed;
onControlEdited(linkage, comp.varName);
if (isGatedNode(wrap)) return;
var wait = 25 - (Date.now() - lastLiveAt);
if (wait <= 0) {
sendTextLive();
} else if (!liveTimer) {
liveTimer = window.setTimeout(sendTextLive, wait);
}
});
if (multi) {
input.addEventListener('keydown', function (event) {
if (event.keyCode === 13) event.stopPropagation();
});
} else {
input.addEventListener('keydown', function (event) {
if (event.keyCode !== 13 || isGatedNode(wrap)) return;
if (liveTimer) { window.clearTimeout(liveTimer); liveTimer = 0; }
values[linkage][comp.varName] = fromField(input.value);
onControlChanged(linkage, comp.varName, comp);
});
}"""

OLD_SWAP = """function swapImageWhenLoaded(linkage, varName, url, entry) {
var key = linkage + '|' + varName;
var swap = imageSwaps[key];
if (!swap || swap.entry !== entry) {"""

NEW_SWAP = """function swapImageWhenLoaded(linkage, varName, url, entry) {
var key = linkage + '|' + varName;
var swap = imageSwaps[key];
if (String(url || '').indexOf('data:image/svg+xml;base64,') === 0) {
if (!swap || swap.entry !== entry) {
swap = imageSwaps[key] = {entry: entry, started: Date.now(), token: 0, probes: []};
}
swap.token += 1;
swap.url = url;
finishImageSwap(linkage, varName, swap, 'inline svg');
return;
}
if (!swap || swap.entry !== entry) {"""


def _find_node():
    for cand in ('node', r'C:\Program Files\Adobe\Adobe Creative Cloud Experience\libs\node.exe'):
        try:
            subprocess.check_call([cand, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return cand
        except Exception:
            pass
    return None


def _patch_css(raw_css):
    if CSS_MARKER in raw_css:
        return raw_css
    nl = '\r\n' if '\r\n' in raw_css else '\n'
    norm = raw_css.replace('\r\n', '\n')
    patched = norm.rstrip() + '\n' + FONT_FACES_CSS.strip() + '\n'
    return patched.replace('\n', nl)


def _patch_js(raw_js):
    nl = '\r\n' if '\r\n' in raw_js else '\n'
    norm = raw_js.replace('\r\n', '\n')

    if 'var sendTextLive = function' not in norm:
        if LEGACY_TIMER_INPUT in norm:
            assert norm.count(LEGACY_TIMER_INPUT) == 1
            norm = norm.replace(LEGACY_TIMER_INPUT, INSTANT_TEXT_INPUT, 1)
        else:
            assert norm.count(STOCK_TEXT_INPUT) == 1, 'Expected 1 stock TextInput block'
            norm = norm.replace(STOCK_TEXT_INPUT, INSTANT_TEXT_INPUT, 1)

    if 'function renderInlineDataSvg' not in norm:
        img_anchor = 'function imageUrl(source) {'
        assert norm.count(img_anchor) == 1, 'Expected 1 imageUrl anchor'
        norm = norm.replace(img_anchor, INLINE_SVG_HELPERS + img_anchor, 1)

    branch_target = '} else if (isDataSvgUrl(url)) {\nrenderInlineDataSvg(frame, url, wantW, wantH);\n'
    if branch_target not in norm:
        atlas_anchor = 'stopAtlas = renderAtlas(frame, atlasAt(atlasFactor));\n} else {'
        assert norm.count(atlas_anchor) == 1, 'Expected 1 renderImage atlas branch anchor'
        norm = norm.replace(
            atlas_anchor,
            'stopAtlas = renderAtlas(frame, atlasAt(atlasFactor));\n' + branch_target + '} else {',
            1,
        )

    if 'isDataSvgUrl(url)' not in norm.split('function swapImageWhenLoaded', 1)[1][:450] and "indexOf('data:image/svg+xml;base64,')" not in norm.split('function swapImageWhenLoaded', 1)[1][:450]:
        assert norm.count(OLD_SWAP) == 1, 'Expected 1 swapImageWhenLoaded anchor'
        norm = norm.replace(OLD_SWAP, NEW_SWAP, 1)

    return norm.replace('\n', nl)


def patch_archive(src_path, dst_path=None):
    dst_path = dst_path or src_path
    css_entry = 'res/gui/gameface/mods/aslain/ModMenu/ModMenu.css'
    js_entry = 'res/gui/gameface/mods/aslain/ModMenu/ModMenu.js'

    with zipfile.ZipFile(src_path, 'r') as zin:
        patched_css = _patch_css(zin.read(css_entry).decode('utf-8')).encode('utf-8')
        patched_js = _patch_js(zin.read(js_entry).decode('utf-8')).encode('utf-8')

        node = _find_node()
        if node:
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as tf:
                tf.write(patched_js)
                tmp_js = tf.name
            try:
                subprocess.check_call([node, '--check', tmp_js])
            finally:
                if os.path.exists(tmp_js):
                    os.remove(tmp_js)

        tmp_zip = dst_path + '.tmp'
        parent = os.path.dirname(os.path.abspath(dst_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        try:
            with zipfile.ZipFile(tmp_zip, 'w', compression=zipfile.ZIP_STORED) as zout:
                for info in zin.infolist():
                    if info.filename == css_entry:
                        data = patched_css
                    elif info.filename == js_entry:
                        data = patched_js
                    else:
                        data = zin.read(info.filename)
                    zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    zi.compress_type = zipfile.ZIP_STORED
                    zi.external_attr = info.external_attr
                    zi.create_system = info.create_system
                    zout.writestr(zi, data)
        except Exception:
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
            raise

    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        os.replace(tmp_zip, dst_path) if hasattr(os, 'replace') else shutil.move(tmp_zip, dst_path)
    else:
        shutil.move(tmp_zip, dst_path)

    with zipfile.ZipFile(dst_path, 'r') as zchk:
        bad = zchk.testzip()
        assert bad is None, 'Corrupt archive entry: %s' % bad
        assert CSS_MARKER in zchk.read(css_entry).decode('utf-8')
        chk_js = zchk.read(js_entry).decode('utf-8')
        assert 'function renderInlineDataSvg' in chk_js
        assert 'var sendTextLive = function' in chk_js
    return dst_path


def main():
    parser = argparse.ArgumentParser(description='Patch Aslain ModMenu for ThreeMarks fonts & instant preview')
    parser.add_argument('--archive', required=True)
    parser.add_argument('--out', default='')
    args = parser.parse_args()
    out = patch_archive(args.archive, args.out or None)
    print('PATCH_MODMENU_OK:', out)


if __name__ == '__main__':
    main()
