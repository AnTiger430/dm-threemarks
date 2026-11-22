(function () {
    'use strict';
    var SIZES = { b: [244, 96], h: [244, 144], hm: [244, 98], s: [244, 342], v3: [240, 120] };
    var lastAstOn = false;
    var lastSetH = 0;
    var lastV3Key = '';
    var curMode = 'b';
    var MINI_W = 175;
    var LABEL_EMA_W = 112;
    var LABEL_TITLE_W = 62;
    var PANEL_W = 220;
    var TRACK_LEFT = 10;
    var TRACK_W = 200;
    var curScale = 1;
    var curUi = 1;

    /* настройки внешнего вида приходят из config.json (p.ui) */
    var DEF_UI = {
        s: 1, hs: 1, preset: 0, v3: null, vh: null, bg: 0.82, up: '#86EF6A', dn: '#FF6060', zr: '#EAEAEA',
        bUp: '#8FE37D', bDn: '#FF6060', bZr: '#DDE6EE', bH: '#F0F2F6',
        trk: 0.18, tick: '#FFFFFF', pct: '#F4F4F4', pctSign: false,
        glow: true, band: 0.02,
        big: '#B07CFF', bBig: '#B07CFF', bigFrom: 4,
        dmgSign: true, dmg: '#86EF6A', proj: '#EAEAEA',
        bSign: true, bStd: '#8FE37D', bigDmg: true,
        onlyPct: false, alpha: 1
    };
    var DEF_V3 = {
        den: 1, minW: 0, anc: 0, hs: false,
        fs: 0, rad: 5, cc: '#FFFFFF', ca: 0.90, ba: 0.28, bgc: '#0B1016', bgo: 0.48,
        sp: 0, ss: 0, sd: false, sz: 15, sg: 6, sgl: true, son: '#FFFFFF', sof: '#9AA3AE',
        ho: 0, dec: 1, di: 0, dc: 0,
        bs: 0, bsc: 0, bh: 4, bth: 2, bt: 'KIBERSPORT', bts: 15, bet: true, bcur: true, bmk: false, bcm: 0, bcc: '#A7D080',
        dmgOn: true, dl: 0, dlc: '\u0421\u0443\u043c. \u0443\u0440\u043e\u043d', sep: 1, ddyn: true,
        ash: 0, am: 0, ap: 0, ahz: false,
        tsh: 0, tmm: 0, tp: 0,
        up: '#A7D080', dn: '#E57373', zr: '#9AA3AE', big: '#B07CFF', tm: '#FFFFFF', tmu: '#B8BDC4',
        hThr: true, h100: true
    };
    var V3_TRACK_RUNS = [
        [6, 1, 2, 2], [8, 1, 1, 1], [10, 1, 1, 1], [6, 2, 6, 2], [4, 3, 1, 1],
        [7, 3, 6, 2], [3, 4, 3, 2], [7, 4, 1, 2], [8, 4, 1, 1], [10, 4, 1, 1],
        [11, 4, 3, 2], [3, 5, 1, 1], [4, 5, 5, 2], [11, 5, 1, 1], [12, 5, 2, 2],
        [0, 6, 2, 1], [4, 6, 1, 1], [5, 6, 5, 2], [11, 6, 3, 2], [0, 7, 3, 2],
        [3, 7, 1, 1], [4, 7, 2, 2], [7, 7, 1, 1], [8, 7, 7, 2], [0, 8, 1, 1],
        [1, 8, 5, 2], [6, 8, 1, 1], [8, 8, 1, 1], [9, 8, 2, 2], [12, 8, 1, 1],
        [13, 8, 2, 2], [1, 9, 1, 1], [2, 9, 5, 2], [7, 9, 1, 1], [8, 9, 3, 2],
        [13, 9, 1, 1], [5, 10, 7, 2], [6, 11, 2, 2], [9, 11, 1, 1], [10, 11, 2, 2],
        [5, 12, 1, 1], [6, 12, 2, 2], [10, 12, 1, 1], [5, 13, 1, 1], [6, 13, 3, 2],
        [7, 14, 2, 2]
    ];
    var ARROW_ROWS = [2, 2, 4, 4, 6, 6, 8, 8, 10];

    var METRICS = {"h": 17, "g": {"0": {"x": 0, "w": 8}, "1": {"x": 9, "w": 6}, "2": {"x": 16, "w": 8}, "3": {"x": 25, "w": 8}, "4": {"x": 34, "w": 8}, "5": {"x": 43, "w": 8}, "6": {"x": 52, "w": 8}, "7": {"x": 61, "w": 8}, "8": {"x": 70, "w": 8}, "9": {"x": 79, "w": 8}, ".": {"x": 88, "w": 4}, "/": {"x": 93, "w": 6}, "%": {"x": 100, "w": 10}, "+": {"x": 111, "w": 8}, "-": {"x": 120, "w": 6}, "—": {"x": 127, "w": 10}, "~": {"x": 138, "w": 8}, " ": {"x": 147, "w": 4}}};
    var FONT_URL = 'img://gui/maps/three_marks/font_';

    var elV3 = document.getElementById('tm-v3');
    var elPct = document.getElementById('tm-pct');
    var elArrow = document.getElementById('tm-arrow');
    var elDelta = document.getElementById('tm-delta');
    var elFill = document.getElementById('tm-fill');
    var elTick = document.getElementById('tm-tick');
    var elVal = document.getElementById('tm-val');
    var elNeed = document.getElementById('tm-need');
    var elValWrap = document.getElementById('tm-valwrap');
    var stars = [document.getElementById('tm-star1'),
                 document.getElementById('tm-star2'),
                 document.getElementById('tm-star3')];
    var elPanel = document.getElementById('tm-panel');
    var elEmaV = document.getElementById('tm-hema-v');
    var thrEls = {
        l65: document.getElementById('tm-h65l'), v65: document.getElementById('tm-h65v'),
        l85: document.getElementById('tm-h85l'), v85: document.getElementById('tm-h85v'),
        l95: document.getElementById('tm-h95l'), v95: document.getElementById('tm-h95v')
    };
    var elBtn = document.getElementById('tm-btn');
    var elTrack = document.getElementById('tm-track');
    var elSet = document.getElementById('tm-set');
    var elCfg = document.getElementById('tm-cfg');
    var elAst = document.getElementById('tm-ast');
    var elAstR = document.getElementById('tm-ast-r');
    var elAstT = document.getElementById('tm-ast-t');
    var elAstRv = document.getElementById('tm-ast-rv');
    var elAstTv = document.getElementById('tm-ast-tv');
    var elAstRi = document.getElementById('tm-ast-ri');
    var elAstTi = document.getElementById('tm-ast-ti');
    function fmtInt(n) {
        var t = String(Math.round(Number(n) || 0)), out = '';
        while (t.length > 3) { out = ' ' + t.slice(-3) + out; t = t.slice(0, -3); }
        return t + out;
    }
    var SET_IMG = 'img://gui/maps/three_marks/set_';
    var arrowRows = [];
    var panelStyleKey = '';

    function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    function readUi(raw) {
        var u = {};
        raw = raw || {};
        for (var k in DEF_UI) {
            u[k] = (raw[k] === undefined || raw[k] === null) ? DEF_UI[k] : raw[k];
        }
        return u;
    }
    function rgbOf(hex) {
        var m = /^#([0-9a-fA-F]{6})$/.exec(hex || '');
        if (!m) return [255, 255, 255];
        var n = parseInt(m[1], 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    function mixRgb(a, b, t) {
        return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                a[2] + (b[2] - a[2]) * t];
    }
    function cssRgb(c) {
        return 'rgb(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' +
            Math.round(c[2]) + ')';
    }
    function cssRgba(c, a) {
        return 'rgba(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' +
            Math.round(c[2]) + ',' + a + ')';
    }
    /* 'p' - вырос, 'n' - упал, 'z' - около нуля */
    function kindOf(value, band, bigFrom) {
        if (bigFrom > 0 && value >= bigFrom) return 'g';    /* большой плюс */
        if (Math.abs(value) <= band) return 'z';
        return value < 0 ? 'n' : 'p';
    }

    /* фон панели, рамка, тень и пустая часть полоски */
    function applyPanelStyle(u) {
        var a = clamp(num(u.bg, 0.82), 0, 1);
        var trk = clamp(num(u.trk, 0.18), 0, 1);
        var key = a + '|' + trk;
        if (key === panelStyleKey) return;
        panelStyleKey = key;
        var k = Math.min(1, a / 0.8);   /* рамка и тень гаснут вместе с фоном */
        elPanel.style.background = 'linear-gradient(145deg, rgba(12,18,25,' +
            a.toFixed(3) + '), rgba(7,11,16,' + (a * 0.93).toFixed(3) + '))';
        elPanel.style.borderColor = 'rgba(186,210,229,' + (0.20 * k).toFixed(3) + ')';
        elPanel.style.boxShadow = '0 3px 10px rgba(0,0,0,' + (0.38 * k).toFixed(3) +
            '), inset 0 1px rgba(255,255,255,' + (0.035 * k).toFixed(3) + ')';
        elTrack.style.background = 'rgba(226,235,244,' + trk.toFixed(3) + ')';
    }

    /* стрелка собрана из полосок: цвет задаётся как у любого блока */
    /* кнопка настроек: четыре цветных квадрата (клик читает Python) */
    function buildCfg() {
        var colors = ['#FF6060', '#86EF6A', '#4FD8FF', '#FFD23C'];
        for (var i = 0; i < 4; i += 1) {
            var d = document.createElement('div');
            d.style.left = ((i % 2) * 9) + 'px';
            d.style.top = (Math.floor(i / 2) * 9) + 'px';
            d.style.background = colors[i];
            elCfg.appendChild(d);
        }
    }

    /* экран настроек: Python присылает готовый список элементов */
    function drawArrow(box, color, down) {
        box.style.width = '10px';
        box.style.height = '9px';
        if (down) box.style.transform = 'scaleY(-1)';
        for (var i = 0; i < ARROW_ROWS.length; i += 1) {
            var w = ARROW_ROWS[i];
            var r = document.createElement('div');
            r.style.left = ((10 - w) / 2) + 'px';
            r.style.top = i + 'px';
            r.style.width = w + 'px';
            r.style.height = (i < ARROW_ROWS.length - 1 ? 2 : 1) + 'px';
            r.style.background = color;
            box.appendChild(r);
        }
    }
    var setNodes = [];
    var setKeys = [];
    function makeNode(it) {
        var d = document.createElement('div');
        d.__t = it.t;
        if (it.t === 'n') d.className = 'tm-run';
        else if (it.t === 'x') d.className = 'tm-live';
        return d;
    }
    function fillNode(d, it) {
        d.style.left = num(it.x, 0) + 'px';
        d.style.top = num(it.y, 0) + 'px';
        if (it.t === 'b') {
            d.style.width = num(it.w, 0) + 'px';
            d.style.height = num(it.h, 0) + 'px';
            d.style.background = it.bg || '';
            d.style.border = it.bd ? '1px solid ' + it.bd : '';
            d.style.borderRadius = it.r ? it.r + 'px' : '';
        } else if (it.t === 'i') {
            d.style.width = num(it.w, 0) + 'px';
            d.style.height = '17px';
            var url = 'url(' + SET_IMG + it.n + '.png)';
            if (d.__img !== url) { d.__img = url; d.style.backgroundImage = url; }
            d.style.backgroundRepeat = 'no-repeat';
            d.style.opacity = (it.op === undefined) ? 1 : it.op;
        } else if (it.t === 'n') {
            drawText(d, String(it.s || ''), it.c || 'white');
        } else if (it.t === 'x') {
            d.textContent = String(it.s || '');
            d.style.color = it.c || '#EAEAEA';
            d.style.width = num(it.w, 120) + 'px';
            d.style.height = num(it.h, 17) + 'px';
            d.style.fontFamily = 'Warhelios, Arial, sans-serif';
            d.style.fontSize = '12px';
            d.style.lineHeight = num(it.h, 17) + 'px';
            d.style.whiteSpace = 'nowrap';
            d.style.overflow = 'hidden';
        } else if (it.t === 'a') {
            while (d.firstChild) d.removeChild(d.firstChild);
            d.style.transform = '';
            drawArrow(d, it.c || '#FFFFFF', !!it.d);
        }
    }
    /* Список приходит каждый раз целиком, но число и порядок элементов
       постоянны: обновляем только те, что изменились, и не пересоздаём
       узлы (иначе картинки подписей перезагружались бы на каждый кадр). */
    function renderSettings(items) {
        while (setNodes.length > items.length) {
            elSet.removeChild(setNodes.pop());
            setKeys.pop();
        }
        for (var i = 0; i < items.length; i += 1) {
            var it = items[i];
            var key = JSON.stringify(it);
            if (setKeys[i] === key) continue;
            var d = setNodes[i];
            if (!d || d.__t !== it.t) {
                var fresh = makeNode(it);
                if (d) elSet.replaceChild(fresh, d); else elSet.appendChild(fresh);
                setNodes[i] = d = fresh;
            }
            fillNode(d, it);
            setKeys[i] = key;
        }
    }

    /* Раскладка строки «процент + стрелка + изменение». Ширина текста известна
       движку не сразу после смены текста, поэтому её перемеряют каждый такт:
       первое измерение может быть устаревшим (числа наползали друг на друга). */
    var rowState = null;
    var dmgShown = false;
    var dmgScale = 1;
    function setLeft(el, value) {
        var v = value + 'px';
        if (el.__left !== v) { el.__left = v; el.style.left = v; }
    }
    function layoutRow() {
        if (!rowState) return;
        if (elPanel.className.indexOf('percent-only') >= 0) {
            setLeft(elPct, 0);
            return;
        }
        var wp = widthOf(elPct);
        if (rowState.hasDelta) {
            var left = (PANEL_W - wp) / 2;
            setLeft(elPct, left);
            setLeft(elArrow, left + wp + 9);
            setLeft(elDelta, left + wp + 9 + 10 + 6);
        } else {
            setLeft(elPct, Math.max(4, (PANEL_W - wp) / 2));
        }
    }

    /* Если «Х / Y» не помещается до первой звезды - сжимаем блок целиком.
       Меряем каждый такт (см. layoutRow); замер идёт с учётом текущего сжатия. */
    function layoutDamage() {
        if (!dmgShown) return;
        var total = (widthOf(elVal) + 4 + widthOf(elNeed)) / (dmgScale || 1);
        var onlyPct = elPanel.className.indexOf('percent-only') >= 0;
        var avail = onlyPct ? (PANEL_W - 12) : (PANEL_W - 38 - 14 - 73 - 6);
        var vs = total > avail ? Math.max(0.55, avail / total) : 1;
        if (Math.abs(vs - dmgScale) > 0.005) {
            dmgScale = vs;
            elValWrap.style.transform = vs < 1 ? 'scale(' + vs + ')' : '';
        }
    }
    function layoutAll() {
        if (curMode === 'v3') return;
        layoutRow();
        layoutDamage();
    }

    var v3Dom = null;
    var v3LastSvg = '';
    var v3IconCache = {};
    var B64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

    function encodeB64Ascii(str) {
        if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
            return window.btoa(str);
        }
        var out = '', i = 0, c1, c2, c3, e1, e2, e3, e4;
        while (i < str.length) {
            c1 = str.charCodeAt(i++) & 255;
            if (i === str.length) {
                out += B64_CHARS.charAt(c1 >> 2) + B64_CHARS.charAt((c1 & 3) << 4) + '==';
                break;
            }
            c2 = str.charCodeAt(i++) & 255;
            if (i === str.length) {
                out += B64_CHARS.charAt(c1 >> 2) +
                    B64_CHARS.charAt(((c1 & 3) << 4) | ((c2 & 240) >> 4)) +
                    B64_CHARS.charAt((c2 & 15) << 2) + '=';
                break;
            }
            c3 = str.charCodeAt(i++) & 255;
            e1 = c1 >> 2;
            e2 = ((c1 & 3) << 4) | (c2 >> 4);
            e3 = ((c2 & 15) << 2) | (c3 >> 6);
            e4 = c3 & 63;
            out += B64_CHARS.charAt(e1) + B64_CHARS.charAt(e2) +
                B64_CHARS.charAt(e3) + B64_CHARS.charAt(e4);
        }
        return out;
    }

    function svgUri(svg) {
        return 'data:image/svg+xml;base64,' + encodeB64Ascii(svg);
    }

    function readV3Ui(raw) {
        var v = {};
        raw = raw || {};
        for (var k in DEF_V3) {
            v[k] = (raw[k] === undefined || raw[k] === null) ? DEF_V3[k] : raw[k];
        }
        return v;
    }

    function v3Int(v, k, lo, hi) {
        return Math.round(clamp(num(v[k], DEF_V3[k]), lo, hi));
    }

    function v3Advance(text, size) {
        var t = String(text || '');
        var s = Number(size) || 14;
        var w = 0;
        for (var i = 0; i < t.length; i += 1) {
            var ch = t.charAt(i);
            if (ch >= '0' && ch <= '9') w += 0.50 * s;
            else if (ch === ' ') w += 0.24 * s;
            else if (ch === '/') w += 0.38 * s;
            else if (ch === '.' || ch === ',' || ch === ':') w += 0.26 * s;
            else if (ch === '+' || ch === '-' || ch === '\u2212') w += 0.48 * s;
            else if (ch === '%') w += 0.78 * s;
            else if (ch === '\u2014') w += 0.62 * s;
            else w += 0.52 * s;
        }
        return w;
    }

    function v3FmtNum(n, sepMode) {
        var val = Math.round(Number(n) || 0);
        var neg = val < 0;
        var s = String(Math.abs(val));
        var res;
        if (sepMode === 2) {
            res = s;
        } else {
            var sep = (sepMode === 0) ? ' ' : ',';
            var out = '';
            while (s.length > 3) {
                out = sep + s.slice(-3) + out;
                s = s.slice(0, -3);
            }
            res = s + out;
        }
        return neg ? ('-' + res) : res;
    }

    function v3ResolveAssist(v, d) {
        var spot = Math.max(0, Math.round(num(d.spot, 0)));
        var track = Math.max(0, Math.round(num(d.track, 0)));
        var maxAst = Math.max(spot, track);
        var activeCh = null;
        if (maxAst > 0) {
            activeCh = (spot >= track) ? 'spot' : 'track';
        }
        var alt = !!d.alt;
        var showMode = v3Int(v, 'ash', 0, 3);
        var rawMode = v3Int(v, 'am', 0, 1);
        if (showMode === 3 || (showMode === 1 && !alt) || (showMode === 2 && alt)) {
            return { items: [], activeCh: activeCh, maxAst: maxAst, altExp: false };
        }
        var rows;
        if (rawMode === 0) {
            rows = [['spot', spot], ['track', track]];
        } else {
            rows = [[activeCh || 'spot', maxAst]];
        }
        if (v.ahz) {
            var filtered = [];
            for (var fi = 0; fi < rows.length; fi += 1) {
                if (rows[fi][1] > 0) filtered.push(rows[fi]);
            }
            rows = filtered;
        }
        var sep = v3Int(v, 'sep', 0, 2);
        var items = [];
        for (var i = 0; i < rows.length; i += 1) {
            var ch = rows[i][0];
            var val = rows[i][1];
            var isAct = (ch === activeCh && val > 0);
            items.push({ ch: ch, val: val, active: isAct, text: v3FmtNum(val, sep) });
        }
        return { items: items, activeCh: activeCh, maxAst: maxAst, altExp: false };
    }

    function v3ResolveTempo(v, d) {
        var alt = !!d.alt;
        var showMode = v3Int(v, 'tsh', 0, 3);
        var rawMode = v3Int(v, 'tmm', 0, 2);
        if (showMode === 3 || (showMode === 1 && !alt) || (showMode === 2 && alt)) {
            return [];
        }
        var pct = num(d.pct, 0);
        var tNextPct = Math.round(num(d.tNextPct, 0)) || (pct < 65 ? 65 : (pct < 85 ? 85 : (pct < 95 ? 95 : 100)));
        var tNext = Math.max(0, Math.round(num(d.tNext, 0)));
        var t95 = Math.max(0, Math.round(num(d.t95, 0)));
        var dmg = Math.max(0, Math.round(num(d.dmg, 0)));
        var mode = rawMode;
        var pairs;
        if (mode === 1) {
            pairs = [[tNextPct, tNext]];
        } else if (mode === 2) {
            pairs = [[95, t95]];
        } else {
            if (tNextPct === 95) {
                pairs = [[95, t95 > 0 ? t95 : tNext]];
            } else if (tNextPct < 95) {
                pairs = [[tNextPct, tNext], [95, t95]];
            } else {
                pairs = [[95, t95], [100, tNext]];
            }
        }
        var sep = v3Int(v, 'sep', 0, 2);
        var items = [];
        for (var i = 0; i < pairs.length; i += 1) {
            var pLbl = pairs[i][0];
            var val = pairs[i][1];
            var valStr = val > 0 ? v3FmtNum(val, sep) : '\u2014';
            var lbl = pLbl + '%';
            var text = lbl + ' ' + valStr;
            var done = (val > 0 && dmg >= val);
            items.push({ pct: pLbl, val: val, done: done, lbl: lbl, valStr: valStr, text: text });
        }
        return items;
    }

    function v3ResolveHangarRows(v, d) {
        if (!d.isHangar || d.mini || v.hThr === false) return [];
        var sep = v3Int(v, 'sep', 0, 2);
        var hasRating = (d.hasRating !== false);
        var pct = num(d.pct, 0);
        function mkCell(pLbl, key) {
            var val = Math.max(0, Math.round(num(d[key], 0)));
            var valStr = (hasRating && val > 0 && val < 30000) ? v3FmtNum(val, sep) : '\u2014';
            var lbl = pLbl + '%';
            var done = (hasRating && val > 0 && pct >= pLbl);
            return { pct: pLbl, val: val, done: done, lbl: lbl, valStr: valStr, text: lbl + ' ' + valStr };
        }
        return [
            [mkCell(65, 't65'), mkCell(85, 't85')],
            [mkCell(95, 't95'), mkCell(100, 't100')]
        ];
    }

    function v3DeltaInfo(v, d, u) {
        var hasRating = (d.hasRating !== false);
        var pct = num(d.pct, 0);
        var decIdx = v3Int(v, 'dec', 0, 1);
        var dec = (decIdx === 0) ? 0 : 2;
        if (!hasRating) {
            return {
                pctText: dec === 0 ? '--%' : '--.--%',
                deltaText: '',
                kind: 'zero',
                accent: v.zr,
                showDelta: false,
                down: false
            };
        }
        var pctText = pct.toFixed(dec) + '%';
        var rawDelta = d.delta;
        if (rawDelta === undefined || rawDelta === null || !isFinite(Number(rawDelta))) {
            return {
                pctText: pctText,
                deltaText: '',
                kind: 'zero',
                accent: v.zr,
                showDelta: false,
                down: false
            };
        }
        var val = Number(rawDelta);
        var zeroBand = num(u.band, 0.02);
        var bigByDmg = !!u.bigDmg;
        var bigFrom = num(u.bigFrom, 4);
        var kind;
        if (bigByDmg && d.big && val >= 0) kind = 'big';
        else if (!bigByDmg && bigFrom > 0 && val >= bigFrom) kind = 'big';
        else if (Math.abs(val) <= zeroBand) kind = 'zero';
        else if (val < 0) kind = 'minus';
        else kind = 'plus';
        var accents = { plus: v.up, minus: v.dn, zero: v.zr, big: v.big };
        var deltaText = (val >= 0 ? '+' : '') + val.toFixed(dec) + '%';
        var showDelta = (v3Int(v, 'di', 0, 3) !== 3);
        return {
            pctText: pctText,
            deltaText: deltaText,
            kind: kind,
            accent: accents[kind],
            showDelta: showDelta,
            down: (val < 0)
        };
    }

    function v3TargetInfo(v, d) {
        var dmg = Math.max(0, Math.round(num(d.dmg, 0)));
        var tgt = Math.max(0, Math.round(num(d.tHold, 0)));
        var sep = v3Int(v, 'sep', 0, 2);
        var dmgStr = v3FmtNum(dmg, sep);
        var tgtStr = tgt > 0 ? v3FmtNum(tgt, sep) : '\u2014';
        var remVal = tgt > 0 ? Math.max(0, tgt - dmg) : 0;
        var remStr = tgt > 0 ? v3FmtNum(remVal, sep) : '\u2014';
        return { dmg: dmg, tgt: tgt, dmgStr: dmgStr, tgtStr: tgtStr, remStr: remStr };
    }

    function v3BarRatio(v, d, dmg, tgt) {
        var pct = clamp(num(d.bar !== undefined ? d.bar : d.pct, 0), 0, 100);
        var scale = v3Int(v, 'bsc', 0, 1);
        if (scale === 1) {
            if (pct < 65) return pct / 65;
            if (pct < 85) return (pct - 65) / 20;
            if (pct < 95) return (pct - 85) / 10;
            return (pct - 95) / 5;
        }
        return pct / 100;
    }

    function v3FramePath(x, y, w, h, r, gapSide, g0, g1) {
        r = Math.max(0, Math.min(r, Math.min(w, h) * 0.45));
        var x0 = x, y0 = y, x1 = x + w, y1 = y + h;
        function arc(ax, ay) {
            return r > 0.1 ? (' A ' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + ax.toFixed(1) + ' ' + ay.toFixed(1)) : '';
        }
        if (!gapSide) {
            if (r <= 0.1) return 'M ' + x0.toFixed(1) + ' ' + y0.toFixed(1) + ' H ' + x1.toFixed(1) + ' V ' + y1.toFixed(1) + ' H ' + x0.toFixed(1) + ' Z';
            return 'M ' + (x0 + r).toFixed(1) + ' ' + y0.toFixed(1) +
                ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
                ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
                ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) + ' Z';
        }
        if (gapSide === 'top') {
            g0 = Math.max(x0 + r + 2, Math.min(x1 - r - 4, g0));
            g1 = Math.max(g0 + 2, Math.min(x1 - r - 2, g1));
            return 'M ' + g1.toFixed(1) + ' ' + y0.toFixed(1) +
                ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
                ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
                ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) + ' H ' + g0.toFixed(1);
        }
        if (gapSide === 'bottom') {
            g0 = Math.max(x0 + r + 2, Math.min(x1 - r - 4, g0));
            g1 = Math.max(g0 + 2, Math.min(x1 - r - 2, g1));
            return 'M ' + g0.toFixed(1) + ' ' + y1.toFixed(1) +
                ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
                ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) +
                ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) + ' H ' + g1.toFixed(1);
        }
        if (gapSide === 'left') {
            g0 = Math.max(y0 + r + 2, Math.min(y1 - r - 4, g0));
            g1 = Math.max(g0 + 2, Math.min(y1 - r - 2, g1));
            return 'M ' + x0.toFixed(1) + ' ' + g0.toFixed(1) +
                ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) +
                ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
                ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) + ' V ' + g1.toFixed(1);
        }
        g0 = Math.max(y0 + r + 2, Math.min(y1 - r - 4, g0));
        g1 = Math.max(g0 + 2, Math.min(y1 - r - 2, g1));
        return 'M ' + x1.toFixed(1) + ' ' + g1.toFixed(1) +
            ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
            ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
            ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) +
            ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) + ' V ' + g0.toFixed(1);
    }

    function v3CornersPaths(x, y, w, h, r) {
        r = Math.max(0, Math.min(r, Math.min(w, h) * 0.45));
        var arm = Math.max(r + 4, Math.min(10, Math.min(w, h) * 0.22));
        var x0 = x, y0 = y, x1 = x + w, y1 = y + h;
        if (r <= 0.1) {
            return [
                'M ' + x0.toFixed(1) + ' ' + (y0 + arm).toFixed(1) + ' V ' + y0.toFixed(1) + ' H ' + (x0 + arm).toFixed(1),
                'M ' + (x1 - arm).toFixed(1) + ' ' + y0.toFixed(1) + ' H ' + x1.toFixed(1) + ' V ' + (y0 + arm).toFixed(1),
                'M ' + x1.toFixed(1) + ' ' + (y1 - arm).toFixed(1) + ' V ' + y1.toFixed(1) + ' H ' + (x1 - arm).toFixed(1),
                'M ' + (x0 + arm).toFixed(1) + ' ' + y1.toFixed(1) + ' H ' + x0.toFixed(1) + ' V ' + (y1 - arm).toFixed(1)
            ];
        }
        return [
            'M ' + x0.toFixed(1) + ' ' + (y0 + arm).toFixed(1) + ' V ' + (y0 + r).toFixed(1) + ' A ' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + (x0 + r).toFixed(1) + ' ' + y0.toFixed(1) + ' H ' + (x0 + arm).toFixed(1),
            'M ' + (x1 - arm).toFixed(1) + ' ' + y0.toFixed(1) + ' H ' + (x1 - r).toFixed(1) + ' A ' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + x1.toFixed(1) + ' ' + (y0 + r).toFixed(1) + ' V ' + (y0 + arm).toFixed(1),
            'M ' + x1.toFixed(1) + ' ' + (y1 - arm).toFixed(1) + ' V ' + (y1 - r).toFixed(1) + ' A ' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + (x1 - r).toFixed(1) + ' ' + y1.toFixed(1) + ' H ' + (x1 - arm).toFixed(1),
            'M ' + (x0 + arm).toFixed(1) + ' ' + y1.toFixed(1) + ' H ' + (x0 + r).toFixed(1) + ' A ' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + x0.toFixed(1) + ' ' + (y1 - r).toFixed(1) + ' V ' + (y1 - arm).toFixed(1)
        ];
    }

    function v3StarSvg(cx, cy, r, earned, style, onCol, offCol, glow) {
        var pts = [], inner = r * 0.43;
        for (var i = 0; i < 10; i += 1) {
            var ang = -Math.PI * 0.5 + i * Math.PI * 0.2;
            var rad = (i % 2 === 0) ? r : inner;
            pts.push((cx + rad * Math.cos(ang)).toFixed(2) + ',' + (cy + rad * Math.sin(ang)).toFixed(2));
        }
        var pstr = pts.join(' ');
        if (earned) {
            var fill = (style === 2) ? '#FFD23C' : onCol;
            var s = glow ? ('<polygon points="' + pstr + '" fill="' + fill + '" fill-opacity="0.24" stroke="' + fill + '" stroke-width="2.0" stroke-opacity="0.22"/>') : '';
            return s + '<polygon points="' + pstr + '" fill="' + fill + '" fill-opacity="0.96"/>';
        }
        if (style === 1) {
            return '<polygon points="' + pstr + '" fill="' + offCol + '" fill-opacity="0.50"/>';
        }
        return '<polygon points="' + pstr + '" fill="' + offCol + '" fill-opacity="0.10" stroke="' + offCol + '" stroke-width="1.15" stroke-opacity="0.55"/>';
    }

    function v3DeltaIconUri(kind, down, color) {
        var key = 'd|' + kind + '|' + (down ? 1 : 0) + '|' + color;
        if (v3IconCache[key]) return v3IconCache[key];
        var body = '';
        if (kind === 0) {
            var pts = down ? '0,1 10,1 5,10' : '5,1 10,10 0,10';
            body = '<polygon points="' + pts + '" fill="' + color + '"/>';
        } else if (kind === 1) {
            if (down) {
                body = '<path d="M 1.5 1.5 L 9.5 9.5 M 4.5 9.5 L 9.5 9.5 L 9.5 4.5" fill="none" stroke="' + color + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>';
            } else {
                body = '<path d="M 1.5 9.5 L 9.5 1.5 M 4.5 1.5 L 9.5 1.5 L 9.5 6.5" fill="none" stroke="' + color + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>';
            }
        }
        v3IconCache[key] = svgUri('<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 11 11">' + body + '</svg>');
        return v3IconCache[key];
    }

    function v3AssistIconInner(ch, ox, oy, size, color, opacity) {
        var s = size / 16.0;
        var cx = ox + size * 0.5, cy = oy + size * 0.5;
        if (ch === 'spot') {
            var r1 = 3.5 * s, dx1 = 2.68 * s, dy1 = 2.25 * s;
            var r2 = 5.8 * s, dx2 = 4.31 * s, dy2 = 3.88 * s;
            var sw = 1.25 * s;
            return '<circle cx="' + cx.toFixed(2) + '" cy="' + cy.toFixed(2) + '" r="' + (1.45 * s).toFixed(2) + '" fill="' + color + '" fill-opacity="' + opacity.toFixed(2) + '"/>' +
                '<path d="M ' + (cx - dx1).toFixed(2) + ' ' + (cy - dy1).toFixed(2) + ' A ' + r1.toFixed(2) + ' ' + r1.toFixed(2) + ' 0 0 0 ' + (cx - dx1).toFixed(2) + ' ' + (cy + dy1).toFixed(2) +
                ' M ' + (cx - dx2).toFixed(2) + ' ' + (cy - dy2).toFixed(2) + ' A ' + r2.toFixed(2) + ' ' + r2.toFixed(2) + ' 0 0 0 ' + (cx - dx2).toFixed(2) + ' ' + (cy + dy2).toFixed(2) +
                ' M ' + (cx + dx1).toFixed(2) + ' ' + (cy - dy1).toFixed(2) + ' A ' + r1.toFixed(2) + ' ' + r1.toFixed(2) + ' 0 0 1 ' + (cx + dx1).toFixed(2) + ' ' + (cy + dy1).toFixed(2) +
                ' M ' + (cx + dx2).toFixed(2) + ' ' + (cy - dy2).toFixed(2) + ' A ' + r2.toFixed(2) + ' ' + r2.toFixed(2) + ' 0 0 1 ' + (cx + dx2).toFixed(2) + ' ' + (cy + dy2).toFixed(2) +
                '" fill="none" stroke="' + color + '" stroke-width="' + sw.toFixed(2) + '" stroke-linecap="round" stroke-opacity="' + opacity.toFixed(2) + '"/>';
        }
        if (ch === 'track') {
            var ca = Math.cos(-35.0 * Math.PI / 180.0);
            var sa = Math.sin(-35.0 * Math.PI / 180.0);
            function rot(dx, dy) {
                return [cx + (dx * ca - dy * sa) * s, cy + (dx * sa + dy * ca) * s];
            }
            var rxs = [-2.1, 2.1], rails = [];
            for (var ri = 0; ri < rxs.length; ri += 1) {
                var p0 = rot(rxs[ri], -3.8), p1 = rot(rxs[ri], 3.8);
                rails.push('M ' + p0[0].toFixed(2) + ' ' + p0[1].toFixed(2) + ' L ' + p1[0].toFixed(2) + ' ' + p1[1].toFixed(2));
            }
            var tys = [-3.8, 0.0, 3.8], treads = [];
            for (var ti = 0; ti < tys.length; ti += 1) {
                var t0 = rot(-4.0, tys[ti]), t1 = rot(4.0, tys[ti]);
                treads.push('M ' + t0[0].toFixed(2) + ' ' + t0[1].toFixed(2) + ' L ' + t1[0].toFixed(2) + ' ' + t1[1].toFixed(2));
            }
            return '<path d="' + rails.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="' + (1.15 * s).toFixed(2) + '" stroke-linecap="round" stroke-opacity="' + (opacity * 0.85).toFixed(2) + '"/>' +
                '<path d="' + treads.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="' + (1.3 * s).toFixed(2) + '" stroke-linecap="round" stroke-opacity="' + opacity.toFixed(2) + '"/>';
        }
        return '';
    }

    function v3AssistIconUri(ch, size, color, opacity) {
        var s = Math.round(size);
        var key = 'a|' + ch + '|' + s + '|' + color + '|' + opacity.toFixed(2);
        if (v3IconCache[key]) return v3IconCache[key];
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + s + '" height="' + s + '" viewBox="0 0 ' + s + ' ' + s + '">' +
            v3AssistIconInner(ch, 0, 0, s, color, opacity) + '</svg>';
        v3IconCache[key] = svgUri(svg);
        return v3IconCache[key];
    }

    function v3TempoStarUri(size, color, opacity) {
        var s = Math.round(size);
        var key = 'ts|' + s + '|' + color + '|' + opacity.toFixed(2);
        if (v3IconCache[key]) return v3IconCache[key];
        var cx = s * 0.5, cy = s * 0.5, r = s * 0.42, inner = r * 0.42;
        var pts = [];
        for (var i = 0; i < 10; i += 1) {
            var ang = -Math.PI * 0.5 + i * Math.PI * 0.2;
            var rad = (i % 2 === 0) ? r : inner;
            pts.push((cx + rad * Math.cos(ang)).toFixed(2) + ',' + (cy + rad * Math.sin(ang)).toFixed(2));
        }
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + s + '" height="' + s + '" viewBox="0 0 ' + s + ' ' + s + '">' +
            '<polygon points="' + pts.join(' ') + '" fill="' + color + '" fill-opacity="' + opacity.toFixed(3) + '"/></svg>';
        v3IconCache[key] = svgUri(svg);
        return v3IconCache[key];
    }

    function v3BarColor(v, pct, deltaAccent) {
        var mode = v3Int(v, 'bcm', 0, 2);
        if (mode === 1) return deltaAccent;
        if (mode === 2) return v.bcc;
        return v.up;
    }

    function v3ComputeMetrics(v, d, u) {
        var isHangar = !!d.isHangar;
        var den = v3Int(v, 'den', 0, 2);
        var spec = [[10, 7, 4, 24, 14, 13, 13], [12, 9, 6, 26, 15, 14, 14], [15, 11, 8, 28, 16, 15, 15]][den];
        var padX = spec[0], padY = spec[1], gapRow = spec[2];
        var pctSize = spec[3], deltaSize = spec[4], dmgSize = spec[5], astSize = spec[6];

        var dInfo = v3DeltaInfo(v, d, u);
        if (isHangar) dInfo.showDelta = false;
        var tInfo = v3TargetInfo(v, d);
        if (isHangar && !(d.hasRating !== false && tInfo.dmg > 0)) {
            tInfo.dmgStr = '\u2014';
        }
        var ast = isHangar ? { items: [], activeCh: null, maxAst: 0, altExp: false } : v3ResolveAssist(v, d);
        var thr = isHangar ? [] : v3ResolveTempo(v, d);
        var hRows = isHangar ? v3ResolveHangarRows(v, d) : [];

        var frameStyle = v3Int(v, 'fs', 0, 3);
        var starsPos = v3Int(v, 'sp', 0, 5);
        var starsDiv = !!v.sd;
        var starSize = v3Int(v, 'sz', 10, 22);
        var starGap = v3Int(v, 'sg', 2, 14);
        var starsSpan = 3 * starSize + 2 * starGap;

        var di = v3Int(v, 'di', 0, 3);
        var deltaIconW = (dInfo.showDelta && (di === 0 || di === 1)) ? 12 : 0;
        var pctW = v3Advance(dInfo.pctText, pctSize);
        var deltaW = dInfo.showDelta ? (v3Advance(dInfo.deltaText, deltaSize) + (deltaIconW > 0 ? deltaIconW + 5 : 0)) : 0;
        var inlineStarsW = (starsPos === 4) ? (starsSpan + 10) : 0;
        var headerMinW = pctW + deltaW + ((dInfo.showDelta && pctW > 0) ? 14 : 0) + inlineStarsW;

        var showDmg = !!v.dmgOn;
        var dmgLblMode = v3Int(v, 'dl', 0, 2);
        var dmgLblText = '';
        var dmgValStr;
        if (isHangar) {
            dmgLblText = '\u0421\u0440. \u0443\u0440\u043e\u043d';
            dmgValStr = tInfo.dmgStr;
        } else {
            if (dmgLblMode === 0) {
                dmgLblText = '\u0421\u0443\u043c. \u0443\u0440\u043e\u043d';
            } else if (dmgLblMode === 1) {
                dmgLblText = String(v.dlc || '').replace(/[\r\n]/g, ' ').slice(0, 24);
            }
            dmgValStr = tInfo.dmgStr + ' / ' + tInfo.tgtStr;
        }
        var lblW = dmgLblText ? v3Advance(dmgLblText, dmgSize) : 0;
        var dmgRowMinW = showDmg ? (lblW + (lblW > 0 ? 12 : 0) + v3Advance(dmgValStr, dmgSize)) : 0;

        var astIconSize = Math.max(14, astSize + 1);
        var astItemGap = ast.items.length <= 2 ? 18 : 11;
        var astWidths = [];
        var sumAstW = 0;
        for (var ai = 0; ai < ast.items.length; ai += 1) {
            var aw = astIconSize + 5 + v3Advance(ast.items[ai].text, astSize);
            astWidths.push(aw);
            sumAstW += aw;
        }
        var astRowMinW = astWidths.length ? (sumAstW + Math.max(0, astWidths.length - 1) * astItemGap) : 0;
        var astInside = (v3Int(v, 'ap', 0, 1) === 0);

        var thrSize = Math.max(11, astSize - 1);
        var thrIconSize = 0;
        var thrItemGap = 14;
        var thrWidths = [];
        var sumThrW = 0;
        for (var ti = 0; ti < thr.length; ti += 1) {
            var tw = v3Advance(thr[ti].text, thrSize);
            thrWidths.push(tw);
            sumThrW += tw;
        }
        var thrRowMinW = thrWidths.length ? (sumThrW + Math.max(0, thrWidths.length - 1) * thrItemGap) : 0;
        var thrInside = (v3Int(v, 'tp', 0, 1) === 0);

        var barMinW = [156, 178, 200][den];
        var barStyle = v3Int(v, 'bs', 0, 4);
        var barH = v3Int(v, 'bh', 2, 10);
        var trackH = v3Int(v, 'bth', 1, 10);
        var barText = (barStyle === 4) ? (String(v.bt || '').replace(/[\r\n]/g, ' ').slice(0, 24) || 'KIBERSPORT') : '';
        var barTextSize = v3Int(v, 'bts', 10, 26);
        var barTextW = (barStyle === 4) ? v3Advance(barText, barTextSize) : 0;
        var barTextMinW = (barStyle === 4) ? Math.ceil(barTextW + 8) : 0;

        var hCol0W = 0, hCol1W = 0, hColGap = 16;
        if (hRows && hRows.length >= 2) {
            var lblW0 = Math.ceil(v3Advance('95%', thrSize)) + 5;
            var valW0 = Math.ceil(Math.max(v3Advance(hRows[0][0].valStr, thrSize), v3Advance(hRows[1][0].valStr, thrSize)));
            hCol0W = lblW0 + valW0;
            var lblW1 = Math.ceil(v3Advance('100%', thrSize)) + 5;
            var valW1 = Math.ceil(Math.max(v3Advance(hRows[0][1].valStr, thrSize), v3Advance(hRows[1][1].valStr, thrSize)));
            hCol1W = lblW1 + valW1;
        }

        var minWOpt = v3Int(v, 'minW', 0, 360);
        var minContentW = minWOpt > 0 ? Math.max(0, minWOpt - 2 * padX) : 0;
        var radius = v3Int(v, 'rad', 0, 14);
        var minBracket = Math.max(12, radius + 8);
        var starsMinFrameW = ((starsPos === 0 || starsPos === 1) && frameStyle !== 3)
            ? (starsSpan + 12 + 2 * minBracket)
            : ((starsPos === 0 || starsPos === 1) ? (starsSpan + 8) : 0);

        var cw = Math.ceil(Math.max(barMinW, barTextMinW, headerMinW, dmgRowMinW,
            minContentW, starsMinFrameW - 2 * padX));

        var framed = (frameStyle !== 3);
        var sideBorderStars = framed && (starsPos === 2 || starsPos === 3);
        var sideOutsideStars = !framed && (starsPos === 2 || starsPos === 3);
        var halfStar = Math.ceil(starSize * 0.5);

        var extraTop = (starsPos === 0) ? Math.max(0, halfStar + 5 - padY) : 0;
        var extraBot = (starsPos === 1) ? Math.max(0, halfStar + 5 - padY) : 0;
        var extraLeft = (sideBorderStars && starsPos === 2) ? Math.max(0, halfStar + 5 - padX) : 0;
        var extraRight = (sideBorderStars && starsPos === 3) ? Math.max(0, halfStar + 5 - padX) : 0;

        var y = padY + extraTop;
        var headerH = Math.round(pctSize * 1.15);
        if (starsPos === 4) headerH = Math.max(headerH, starSize + 2);
        var headerY = y;
        y += headerH;

        var effBarH = Math.max(barH, trackH);
        var barY = null, barBlockH = 0;
        if (barStyle === 4) {
            y += gapRow;
            barY = y;
            barBlockH = Math.round(barTextSize * 1.18);
            y += barBlockH;
        } else if (barStyle !== 3) {
            y += gapRow;
            barY = y;
            barBlockH = Math.max(effBarH, v.bcur ? 10 : effBarH,
                ((barStyle === 0 || barStyle === 2) && v.bet) ? 8 : effBarH);
            y += barBlockH;
        }

        var dmgY = null;
        var dmgH = Math.round(dmgSize * 1.25);
        if (showDmg) {
            y += gapRow;
            dmgY = y;
            y += dmgH;
        }

        var astY = null;
        var astH = Math.max(astSize + 2, astIconSize);
        if (ast.items.length && astInside) {
            y += gapRow + 1;
            astY = y;
            y += astH;
        }

        var thrY = null;
        var thrH = thrSize + 2;
        if (thr.length && thrInside) {
            y += (astY !== null) ? gapRow : (gapRow + 1);
            thrY = y;
            y += thrH;
        }

        var hSepY = null, hRow1Y = null, hRow2Y = null;
        if (hRows.length) {
            y += gapRow + 1;
            hSepY = y;
            y += gapRow;
            hRow1Y = y;
            y += thrH;
            y += 2;
            hRow2Y = y;
            y += thrH;
        }

        var fh = y + padY + extraBot;
        if (starsPos === 2 || starsPos === 3) {
            var minSideH = starsSpan + (sideBorderStars ? 2 * (minBracket + 8) : 8);
            if (fh < minSideH) {
                var diff = minSideH - fh;
                fh = minSideH;
                var deltaShift = Math.floor(diff / 2);
                headerY += deltaShift;
                if (barY !== null) barY += deltaShift;
                if (dmgY !== null) dmgY += deltaShift;
                if (astY !== null) astY += deltaShift;
                if (thrY !== null) thrY += deltaShift;
                if (hSepY !== null) hSepY += deltaShift;
                if (hRow1Y !== null) hRow1Y += deltaShift;
                if (hRow2Y !== null) hRow2Y += deltaShift;
            }
        }

        var fw = cw + 2 * padX + extraLeft + extraRight;
        var margin = 6;
        var fx = margin, fy = margin;
        if (starsPos === 0) fy = margin + halfStar;
        if (sideBorderStars && starsPos === 2) fx = margin + halfStar;
        if (sideOutsideStars && starsPos === 2) fx = margin + starSize + (starsDiv ? 14 : 8);

        var cx = fx + padX + extraLeft;
        var starsCoords = [];
        var divLine = null;
        var sx0, sy0, scx, si;
        if (starsPos === 0) {
            sx0 = fx + fw * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            for (si = 0; si < 3; si += 1) starsCoords.push([sx0 + si * (starSize + starGap), fy]);
        } else if (starsPos === 1) {
            sx0 = fx + fw * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            for (si = 0; si < 3; si += 1) starsCoords.push([sx0 + si * (starSize + starGap), fy + fh]);
        } else if (starsPos === 2) {
            sy0 = fy + fh * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            scx = sideBorderStars ? fx : (margin + starSize * 0.5);
            for (si = 0; si < 3; si += 1) starsCoords.push([scx, sy0 + si * (starSize + starGap)]);
            if (sideOutsideStars && starsDiv) divLine = [fx - 7, fy + 3, fx - 7, fy + fh - 3];
        } else if (starsPos === 3) {
            sy0 = fy + fh * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            scx = sideBorderStars ? (fx + fw) : (fx + fw + (starsDiv ? 14 : 8) + starSize * 0.5);
            for (si = 0; si < 3; si += 1) starsCoords.push([scx, sy0 + si * (starSize + starGap)]);
            if (sideOutsideStars && starsDiv) divLine = [fx + fw + 7, fy + 3, fx + fw + 7, fy + fh - 3];
        }

        var rightExtend = 0;
        if (sideBorderStars && starsPos === 3) rightExtend = halfStar;
        else if (sideOutsideStars && starsPos === 3) rightExtend = (starsDiv ? 14 : 8) + starSize;

        var winW = Math.ceil(fx + fw + rightExtend + margin);
        var botExtend = (starsPos === 1) ? halfStar : 0;
        var curBelowY = fy + fh + (starsPos === 1 ? halfStar + 6 : 6);
        var astBelowY = null, thrBelowY = null;
        if (ast.items.length && !astInside) {
            astBelowY = curBelowY;
            curBelowY += astH + 4;
        }
        if (thr.length && !thrInside) {
            thrBelowY = curBelowY;
            curBelowY += thrH + 4;
        }
        var winH;
        if (astBelowY !== null || thrBelowY !== null) {
            winH = Math.ceil(curBelowY - 4 + margin);
        } else {
            winH = Math.ceil(fy + fh + botExtend + margin);
        }

        return {
            winW: winW, winH: winH,
            fx: fx, fy: fy, fw: fw, fh: fh,
            cx: cx, cw: cw,
            headerY: fy + headerY, headerH: headerH,
            pctSize: pctSize, deltaSize: deltaSize,
            dInfo: dInfo, tInfo: tInfo, ast: ast, thr: thr,
            isHangar: isHangar, hRows: hRows,
            hCol0W: hCol0W, hCol1W: hCol1W, hColGap: hColGap,
            hSepY: hSepY !== null ? (fy + hSepY) : null,
            hRow1Y: hRow1Y !== null ? (fy + hRow1Y) : null,
            hRow2Y: hRow2Y !== null ? (fy + hRow2Y) : null,
            barStyle: barStyle, barY: barY !== null ? (fy + barY) : null, barH: barH, trackH: trackH, barBlockH: barBlockH,
            barText: barText, barTextSize: barTextSize, barTextW: barTextW,
            dmgY: dmgY !== null ? (fy + dmgY) : null, dmgH: dmgH, dmgSize: dmgSize,
            dmgLblText: dmgLblText, dmgLblMode: dmgLblMode,
            astY: astInside ? (astY !== null ? (fy + astY) : null) : astBelowY,
            astH: astH, astSize: astSize, astIconSize: astIconSize,
            astItemGap: astItemGap, astWidths: astWidths, astRowMinW: astRowMinW, astInside: astInside,
            thrY: thrInside ? (thrY !== null ? (fy + thrY) : null) : thrBelowY,
            thrH: thrH, thrSize: thrSize, thrIconSize: thrIconSize, thrItemGap: thrItemGap,
            thrWidths: thrWidths, thrRowMinW: thrRowMinW, thrInside: thrInside,
            starsCoords: starsCoords, starSize: starSize, starGap: starGap,
            starsSpan: starsSpan, starsPos: starsPos, sideBorderStars: sideBorderStars, divLine: divLine
        };
    }

    function ensureV3Dom() {
        if (v3Dom) return v3Dom;
        var bgImg = document.createElement('img');
        bgImg.className = 'v3-bgimg';
        elV3.appendChild(bgImg);

        var hdr = document.createElement('div');
        hdr.className = 'v3-hdr';
        var pctSpan = document.createElement('span');
        pctSpan.className = 'v3-pct';
        var delWrap = document.createElement('span');
        delWrap.className = 'v3-delwrap';
        var delIco = document.createElement('img');
        delIco.className = 'v3-delico';
        var delTxt = document.createElement('span');
        delTxt.className = 'v3-del';
        delWrap.appendChild(delIco);
        delWrap.appendChild(delTxt);
        hdr.appendChild(pctSpan);
        hdr.appendChild(delWrap);
        elV3.appendChild(hdr);

        var barWrap = document.createElement('div');
        barWrap.className = 'v3-barwrap';
        var barFill = document.createElement('div');
        barFill.className = 'v3-bar-fill';
        var barCur = document.createElement('div');
        barCur.className = 'v3-bar-cur';
        barWrap.appendChild(barFill);
        var segFills = [];
        for (var i = 0; i < 4; i += 1) {
            var sf = document.createElement('div');
            sf.className = 'v3-seg-fill';
            sf.style.display = 'none';
            barWrap.appendChild(sf);
            segFills.push(sf);
        }
        barWrap.appendChild(barCur);
        elV3.appendChild(barWrap);

        var barTxtWrap = document.createElement('div');
        barTxtWrap.className = 'v3-bartxt-wrap';
        barTxtWrap.style.display = 'none';
        var barTxtBox = document.createElement('div');
        barTxtBox.className = 'v3-bartxt-box';
        var barTxtBase = document.createElement('span');
        barTxtBase.className = 'v3-bartxt-base';
        var barTxtClip = document.createElement('div');
        barTxtClip.className = 'v3-bartxt-clip';
        var barTxtFill = document.createElement('span');
        barTxtFill.className = 'v3-bartxt-fill';
        barTxtClip.appendChild(barTxtFill);
        barTxtBox.appendChild(barTxtBase);
        barTxtBox.appendChild(barTxtClip);
        barTxtWrap.appendChild(barTxtBox);
        elV3.appendChild(barTxtWrap);

        var dmgRow = document.createElement('div');
        dmgRow.className = 'v3-dmg';
        var dmgLbl = document.createElement('span');
        dmgLbl.className = 'v3-dmglbl';
        var dmgVals = document.createElement('span');
        dmgVals.className = 'v3-dmgvals';
        var dmgMain = document.createElement('span');
        dmgMain.className = 'v3-dmgmain';
        var dmgSec = document.createElement('span');
        dmgSec.className = 'v3-dmgsec';
        dmgVals.appendChild(dmgMain);
        dmgVals.appendChild(dmgSec);
        dmgRow.appendChild(dmgLbl);
        dmgRow.appendChild(dmgVals);
        elV3.appendChild(dmgRow);

        var astRow = document.createElement('div');
        astRow.className = 'v3-astwrap';
        var astItems = [];
        for (var j = 0; j < 4; j += 1) {
            var box = document.createElement('div');
            box.className = 'v3-astitem';
            box.style.display = 'none';
            var ico = document.createElement('img');
            ico.className = 'v3-astico';
            var txt = document.createElement('span');
            txt.className = 'v3-asttxt';
            box.appendChild(ico);
            box.appendChild(txt);
            astRow.appendChild(box);
            astItems.push({ box: box, ico: ico, txt: txt });
        }
        elV3.appendChild(astRow);

        v3Dom = {
            bgImg: bgImg, hdr: hdr, pct: pctSpan, delWrap: delWrap, delIco: delIco, delTxt: delTxt,
            barWrap: barWrap, barFill: barFill, barCur: barCur, segFills: segFills,
            barTxtWrap: barTxtWrap, barTxtBox: barTxtBox, barTxtBase: barTxtBase, barTxtClip: barTxtClip, barTxtFill: barTxtFill,
            dmgRow: dmgRow, dmgLbl: dmgLbl, dmgMain: dmgMain, dmgSec: dmgSec,
            astRow: astRow, astItems: astItems
        };
        var thrRow = document.createElement('div');
        thrRow.className = 'v3-astwrap v3-thrwrap';
        var thrItems = [];
        for (var tj = 0; tj < 2; tj += 1) {
            var tbox = document.createElement('div');
            tbox.className = 'v3-astitem v3-thritem';
            tbox.style.display = 'none';
            var tico = document.createElement('img');
            tico.className = 'v3-astico v3-thrico';
            var tlbl = document.createElement('span');
            tlbl.className = 'v3-asttxt v3-thrlbl';
            var ttxt = document.createElement('span');
            ttxt.className = 'v3-asttxt v3-thrval';
            tbox.appendChild(tico);
            tbox.appendChild(tlbl);
            tbox.appendChild(ttxt);
            thrRow.appendChild(tbox);
            thrItems.push({ box: tbox, ico: tico, lbl: tlbl, txt: ttxt });
        }
        elV3.appendChild(thrRow);
        v3Dom.thrRow = thrRow;
        v3Dom.thrItems = thrItems;

        var thrRow2 = document.createElement('div');
        thrRow2.className = 'v3-astwrap v3-thrwrap v3-thrwrap2';
        var thrItems2 = [];
        for (var tj2 = 0; tj2 < 2; tj2 += 1) {
            var tbox2 = document.createElement('div');
            tbox2.className = 'v3-astitem v3-thritem';
            tbox2.style.display = 'none';
            var tico2 = document.createElement('img');
            tico2.className = 'v3-astico v3-thrico';
            tico2.style.display = 'none';
            var tlbl2 = document.createElement('span');
            tlbl2.className = 'v3-asttxt v3-thrlbl';
            var ttxt2 = document.createElement('span');
            ttxt2.className = 'v3-asttxt v3-thrval';
            tbox2.appendChild(tico2);
            tbox2.appendChild(tlbl2);
            tbox2.appendChild(ttxt2);
            thrRow2.appendChild(tbox2);
            thrItems2.push({ box: tbox2, ico: tico2, lbl: tlbl2, txt: ttxt2 });
        }
        elV3.appendChild(thrRow2);
        v3Dom.thrRow2 = thrRow2;
        v3Dom.thrItems2 = thrItems2;
        return v3Dom;
    }

    function renderV3(p, u, isHangar) {
        var dom = ensureV3Dom();
        var v = readV3Ui(isHangar ? (u.vh || u.v3) : u.v3);
        var d = p.v3d || {
            isHangar: !!isHangar,
            pct: parseFloat(p.pct) || 0,
            bar: p.bar || 0,
            delta: parseFloat(p.delta),
            sDelta: null,
            dmg: 0, tHold: 0, tMark: 0, tPlus1: 0,
            own: 0, spot: (p.ast && p.ast[0]) || 0, track: (p.ast && p.ast[1]) || 0, stun: 0,
            marks: p.marks || 0, big: !!p.big, isSpg: false, alt: false,
            hasRating: (p.pct && p.pct !== '--.--%')
        };
        if (isHangar) d.isHangar = true;
        var m = v3ComputeMetrics(v, d, u);
        var winW = (p.v3m && p.v3m[0]) ? Math.max(1, Math.round(p.v3m[0])) : m.winW;
        var winH = (p.v3m && p.v3m[1]) ? Math.max(1, Math.round(p.v3m[1])) : m.winH;
        elV3.style.width = winW + 'px';
        elV3.style.height = winH + 'px';
        dom.bgImg.style.width = winW + 'px';
        dom.bgImg.style.height = winH + 'px';

        var fs = v3Int(v, 'fs', 0, 3);
        var rad = v3Int(v, 'rad', 0, 14);
        var bga = clamp(num(v.bgo, 0.48), 0, 1);
        var ca = clamp(num(v.ca, 0.90), 0, 1);
        var ba = clamp(num(v.ba, 0.28), 0, 1);
        var sh = (fs === 3) ? 0.95 : 0.85;
        var txtShadow = '0 1px 2px rgba(0,0,0,' + sh.toFixed(2) + ')';

        var parts = [];
        if (fs !== 3) {
            if (bga > 0.01) {
                parts.push('<rect x="' + m.fx.toFixed(1) + '" y="' + m.fy.toFixed(1) + '" width="' + m.fw.toFixed(1) + '" height="' + m.fh.toFixed(1) + '" rx="' + rad + '" fill="' + v.bgc + '" fill-opacity="' + bga.toFixed(3) + '"/>');
            }
            if ((fs === 0 || fs === 2) && ba > 0.01) {
                var gapSide = null, g0 = 0, g1 = 0;
                if (fs === 0 || fs === 2) {
                    var halfGap = m.starsSpan * 0.5 + 6;
                    if (m.starsPos === 0) { gapSide = 'top'; g0 = m.fx + m.fw * 0.5 - halfGap; g1 = m.fx + m.fw * 0.5 + halfGap; }
                    else if (m.starsPos === 1) { gapSide = 'bottom'; g0 = m.fx + m.fw * 0.5 - halfGap; g1 = m.fx + m.fw * 0.5 + halfGap; }
                    else if (m.starsPos === 2 && m.sideBorderStars) { gapSide = 'left'; g0 = m.fy + m.fh * 0.5 - halfGap; g1 = m.fy + m.fh * 0.5 + halfGap; }
                    else if (m.starsPos === 3 && m.sideBorderStars) { gapSide = 'right'; g0 = m.fy + m.fh * 0.5 - halfGap; g1 = m.fy + m.fh * 0.5 + halfGap; }
                }
                parts.push('<path d="' + v3FramePath(m.fx, m.fy, m.fw, m.fh, rad, gapSide, g0, g1) + '" fill="none" stroke="' + v.cc + '" stroke-width="1.0" stroke-opacity="' + ba.toFixed(3) + '"/>');
            }
            if ((fs === 0 || fs === 1) && ca > 0.01) {
                var cps = v3CornersPaths(m.fx, m.fy, m.fw, m.fh, rad);
                for (var ci = 0; ci < cps.length; ci += 1) {
                    parts.push('<path d="' + cps[ci] + '" fill="none" stroke="' + v.cc + '" stroke-width="1.8" stroke-linecap="round" stroke-opacity="' + ca.toFixed(3) + '"/>');
                }
            }
        }
        if (m.divLine) {
            parts.push('<line x1="' + m.divLine[0].toFixed(1) + '" y1="' + m.divLine[1].toFixed(1) + '" x2="' + m.divLine[2].toFixed(1) + '" y2="' + m.divLine[3].toFixed(1) + '" stroke="' + v.cc + '" stroke-width="1.2" stroke-opacity="0.45"/>');
        }

        var marks = Math.round(num(d.marks, 0));
        var starStyle = v3Int(v, 'ss', 0, 2);
        var starR = m.starSize * 0.5;
        for (var si = 0; si < m.starsCoords.length; si += 1) {
            parts.push(v3StarSvg(m.starsCoords[si][0], m.starsCoords[si][1], starR, si < marks, starStyle, v.son, v.sof, !!v.sgl));
        }
        if (m.starsPos === 4) {
            var isx0 = m.cx + m.cw - m.starsSpan + starR;
            var iscy = m.headerY + m.headerH * 0.5;
            for (var ii = 0; ii < 3; ii += 1) {
                parts.push(v3StarSvg(isx0 + ii * (m.starSize + m.starGap), iscy, starR, ii < marks, starStyle, v.son, v.sof, !!v.sgl));
            }
        }

        /* Header DOM */
        var ho = v3Int(v, 'ho', 0, 2);
        var di = v3Int(v, 'di', 0, 3);
        var dc = v3Int(v, 'dc', 0, 1);
        var hdrW = m.cw - (m.starsPos === 4 ? (m.starsSpan + 8) : 0);
        dom.hdr.style.left = m.cx + 'px';
        dom.hdr.style.top = m.headerY + 'px';
        dom.hdr.style.width = Math.max(20, hdrW) + 'px';
        dom.hdr.style.height = m.headerH + 'px';
        dom.hdr.style.flexDirection = (ho === 1) ? 'row-reverse' : 'row';
        dom.hdr.style.justifyContent = (ho === 2) ? 'center' : 'space-between';

        dom.pct.textContent = m.dInfo.pctText;
        dom.pct.style.color = v.tm;
        dom.pct.style.fontSize = m.pctSize + 'px';
        dom.pct.style.textShadow = txtShadow;

        if (m.dInfo.showDelta) {
            var delIconCol = (dc === 0) ? m.dInfo.accent : v.tmu;
            var delTextCol = (dc === 0) ? m.dInfo.accent : v.tmu;
            dom.delWrap.style.display = 'flex';
            dom.delWrap.style.marginLeft = (ho === 2) ? '10px' : '0px';
            if (di === 0 || di === 1) {
                dom.delIco.style.display = 'block';
                dom.delIco.src = v3DeltaIconUri(di, m.dInfo.down, delIconCol);
            } else {
                dom.delIco.style.display = 'none';
            }
            dom.delTxt.textContent = m.dInfo.deltaText;
            dom.delTxt.style.color = delTextCol;
            dom.delTxt.style.fontSize = m.deltaSize + 'px';
            dom.delTxt.style.textShadow = txtShadow;
        } else {
            dom.delWrap.style.display = 'none';
        }

        /* Progress bar SVG background + HTML smooth fill */
        var barPctVal = clamp(num(d.pct, 0), 0, 100);
        var ratio = v3BarRatio(v, d, m.tInfo.dmg, m.tInfo.tgt);
        var barCol = v3BarColor(v, barPctVal, m.dInfo.accent);
        if (m.barStyle === 4 && m.barY !== null) {
            dom.barWrap.style.display = 'none';
            dom.barTxtWrap.style.display = 'flex';
            dom.barTxtWrap.style.left = m.cx + 'px';
            dom.barTxtWrap.style.top = m.barY + 'px';
            dom.barTxtWrap.style.width = m.cw + 'px';
            dom.barTxtWrap.style.height = m.barBlockH + 'px';
            dom.barTxtBase.textContent = m.barText;
            dom.barTxtBase.style.fontSize = m.barTextSize + 'px';
            dom.barTxtBase.style.lineHeight = m.barBlockH + 'px';
            dom.barTxtFill.textContent = m.barText;
            dom.barTxtFill.style.fontSize = m.barTextSize + 'px';
            dom.barTxtFill.style.lineHeight = m.barBlockH + 'px';
            dom.barTxtFill.style.color = barCol;
            dom.barTxtFill.style.textShadow = txtShadow;
            dom.barTxtClip.style.width = clamp(ratio * 100, 0, 100).toFixed(2) + '%';
        } else if (m.barStyle !== 3 && m.barY !== null) {
            dom.barTxtWrap.style.display = 'none';
            var bx = m.cx, bw = m.cw, bh = m.barH, trackH = m.trackH;
            var by = m.barY + (m.barBlockH - bh) * 0.5;
            var trackY = by + (bh - trackH) * 0.5;
            var effBH = Math.max(bh, trackH);
            dom.barWrap.style.display = 'block';
            dom.barWrap.style.left = bx + 'px';
            dom.barWrap.style.top = by + 'px';
            dom.barWrap.style.width = bw + 'px';
            dom.barWrap.style.height = bh + 'px';

            if (m.barStyle === 1) {
                dom.barFill.style.display = 'none';
                var segGap = 2;
                var spans = [[0, 65], [65, 85], [85, 95], [95, 100]];
                var weights = [0.65, 0.20, 0.10, 0.05];
                var usableW = bw - segGap * (spans.length - 1);
                var segX = bx;
                var curPct = clamp(ratio * 100, 0, 100);
                var curFillX = 0;
                for (var sIdx = 0; sIdx < spans.length; sIdx += 1) {
                    var sf = dom.segFills[sIdx];
                    var sw = usableW * weights[sIdx];
                    var s0 = spans[sIdx][0], s1 = spans[sIdx][1];
                    var segFill = clamp((curPct - s0) / Math.max(1e-6, s1 - s0), 0, 1);
                    parts.push('<rect x="' + segX.toFixed(1) + '" y="' + trackY.toFixed(1) + '" width="' + sw.toFixed(1) + '" height="' + trackH.toFixed(1) + '" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>');
                    if (segFill > 0.005) {
                        var sfw = Math.max(1, sw * segFill);
                        sf.style.display = 'block';
                        sf.style.left = (segX - bx).toFixed(1) + 'px';
                        sf.style.width = sfw.toFixed(1) + 'px';
                        sf.style.height = bh + 'px';
                        sf.style.backgroundColor = barCol;
                    } else {
                        sf.style.display = 'none';
                    }
                    if (curPct > s0) {
                        curFillX = (segX - bx) + sw * segFill;
                    }
                    segX += sw + segGap;
                }
                if (v.bcur) {
                    var segCurH = Math.max(10, effBH + 6);
                    var segCurX = clamp(curFillX - 1.25, 0, Math.max(0, bw - 2.5));
                    dom.barCur.style.display = 'block';
                    dom.barCur.style.left = segCurX.toFixed(1) + 'px';
                    dom.barCur.style.top = ((bh - segCurH) * 0.5).toFixed(1) + 'px';
                    dom.barCur.style.height = segCurH + 'px';
                } else {
                    dom.barCur.style.display = 'none';
                }
            } else {
                for (var hi = 0; hi < dom.segFills.length; hi += 1) dom.segFills[hi].style.display = 'none';
                parts.push('<rect x="' + bx.toFixed(1) + '" y="' + trackY.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + trackH.toFixed(1) + '" rx="1" fill="#FFFFFF" fill-opacity="0.22"/>');
                if (v.bet) {
                    var tickH = Math.max(8, effBH + 4);
                    var tickTop = by + (bh - tickH) * 0.5;
                    parts.push('<rect x="' + bx.toFixed(1) + '" y="' + tickTop.toFixed(1) + '" width="1.2" height="' + tickH.toFixed(1) + '" fill="#FFFFFF" fill-opacity="0.45"/>');
                    parts.push('<rect x="' + (bx + bw - 1.2).toFixed(1) + '" y="' + tickTop.toFixed(1) + '" width="1.2" height="' + tickH.toFixed(1) + '" fill="#FFFFFF" fill-opacity="0.45"/>');
                }
                if (v.bmk && v3Int(v, 'bsc', 0, 1) === 0) {
                    var markH = effBH + 3;
                    var markTop = by + (bh - markH) * 0.5;
                    var ths = [65, 85, 95];
                    for (var ti = 0; ti < ths.length; ti += 1) {
                        var tx = bx + bw * (ths[ti] / 100);
                        parts.push('<rect x="' + (tx - 0.5).toFixed(1) + '" y="' + markTop.toFixed(1) + '" width="1.0" height="' + markH.toFixed(1) + '" fill="#FFFFFF" fill-opacity="0.40"/>');
                    }
                }
                var fillW = clamp(bw * ratio, 0, bw);
                if (fillW > 0.5) {
                    dom.barFill.style.display = 'block';
                    dom.barFill.style.width = fillW.toFixed(1) + 'px';
                    dom.barFill.style.height = bh + 'px';
                    dom.barFill.style.backgroundColor = barCol;
                } else {
                    dom.barFill.style.display = 'none';
                }
                if (v.bcur) {
                    var curH = Math.max(10, effBH + 6);
                    var curRelX = clamp(fillW - 1.25, 0, Math.max(0, bw - 2.5));
                    dom.barCur.style.display = 'block';
                    dom.barCur.style.left = curRelX.toFixed(1) + 'px';
                    dom.barCur.style.top = ((bh - curH) * 0.5).toFixed(1) + 'px';
                    dom.barCur.style.height = curH + 'px';
                } else {
                    dom.barCur.style.display = 'none';
                }
            }
        } else {
            dom.barWrap.style.display = 'none';
            dom.barTxtWrap.style.display = 'none';
        }

        /* Damage row DOM */
        if (m.dmgY !== null) {
            dom.dmgRow.style.display = 'flex';
            dom.dmgRow.style.left = m.cx + 'px';
            dom.dmgRow.style.top = m.dmgY + 'px';
            dom.dmgRow.style.width = m.cw + 'px';
            dom.dmgRow.style.height = m.dmgH + 'px';
            if (m.dmgLblText) {
                dom.dmgLbl.style.display = 'block';
                dom.dmgLbl.textContent = m.dmgLblText;
                dom.dmgLbl.style.color = v.tmu;
                dom.dmgLbl.style.fontSize = m.dmgSize + 'px';
                dom.dmgLbl.style.textShadow = txtShadow;
            } else {
                dom.dmgLbl.style.display = 'none';
            }
            if (m.isHangar) {
                var emaCol = (d.hasRating !== false && m.tInfo.dmg > 0) ? v.up : v.tmu;
                dom.dmgMain.style.display = 'block';
                dom.dmgMain.textContent = m.tInfo.dmgStr;
                dom.dmgMain.style.color = emaCol;
                dom.dmgMain.style.fontSize = m.dmgSize + 'px';
                dom.dmgMain.style.textShadow = txtShadow;
                dom.dmgSec.style.display = 'none';
            } else {
                var dmgCol = v.ddyn
                    ? ((m.tInfo.tgt > 0 && m.tInfo.dmg >= m.tInfo.tgt) || m.dInfo.kind === 'plus' || m.dInfo.kind === 'big'
                        ? v.up : (m.dInfo.kind === 'minus' ? v.dn : v.tm))
                    : v.tm;
                dom.dmgMain.style.display = 'block';
                dom.dmgMain.textContent = m.tInfo.dmgStr;
                dom.dmgMain.style.color = dmgCol;
                dom.dmgMain.style.fontSize = m.dmgSize + 'px';
                dom.dmgMain.style.textShadow = txtShadow;
                dom.dmgSec.style.display = 'block';
                dom.dmgSec.style.marginLeft = '4px';
                dom.dmgSec.textContent = '/ ' + m.tInfo.tgtStr;
                dom.dmgSec.style.color = v.tmu;
                dom.dmgSec.style.fontSize = m.dmgSize + 'px';
                dom.dmgSec.style.textShadow = txtShadow;
            }
        } else {
            dom.dmgRow.style.display = 'none';
        }

        /* Assist row DOM */
        if (m.ast.items.length && m.astY !== null) {
            var baseX = m.astInside ? m.cx : (winW - Math.max(m.cw, m.astRowMinW)) * 0.5;
            var baseW = m.astInside ? m.cw : Math.max(m.cw, m.astRowMinW);
            dom.astRow.style.display = 'flex';
            dom.astRow.style.left = baseX.toFixed(1) + 'px';
            dom.astRow.style.top = m.astY + 'px';
            dom.astRow.style.width = baseW.toFixed(1) + 'px';
            dom.astRow.style.height = m.astH + 'px';
            dom.astRow.style.justifyContent = 'center';
            for (var ka = 0; ka < 4; ka += 1) {
                var itemDom = dom.astItems[ka];
                if (ka < m.ast.items.length) {
                    var it = m.ast.items[ka];
                    var col = it.active ? v.up : v.tmu;
                    var iop = it.active ? 1.0 : 0.82;
                    itemDom.box.style.display = 'flex';
                    itemDom.box.style.marginLeft = (ka > 0) ? (m.astItemGap + 'px') : '0px';
                    itemDom.ico.style.width = m.astIconSize + 'px';
                    itemDom.ico.style.height = m.astIconSize + 'px';
                    itemDom.ico.src = v3AssistIconUri(it.ch, m.astIconSize, col, iop);
                    itemDom.txt.textContent = it.text;
                    itemDom.txt.style.color = col;
                    itemDom.txt.style.fontSize = m.astSize + 'px';
                    itemDom.txt.style.textShadow = txtShadow;
                } else {
                    itemDom.box.style.display = 'none';
                }
            }
        } else {
            dom.astRow.style.display = 'none';
        }

        /* Tempo / Hangar Thresholds rows DOM (no star icons - % and value only) */
        var spacePx = Math.max(2, Math.round(0.24 * m.thrSize));
        if (m.hRows && m.hRows.length) {
            if (m.hSepY !== null) {
                parts.push('<line x1="' + m.cx.toFixed(1) + '" y1="' + m.hSepY.toFixed(1) + '" x2="' + (m.cx + m.cw).toFixed(1) + '" y2="' + m.hSepY.toFixed(1) + '" stroke="' + v.cc + '" stroke-width="1.0" stroke-opacity="0.18"/>');
            }
            var hDomRows = [
                { row: dom.thrRow, items: dom.thrItems, data: m.hRows[0] || [], y: m.hRow1Y },
                { row: dom.thrRow2, items: dom.thrItems2, data: m.hRows[1] || [], y: m.hRow2Y }
            ];
            for (var hr = 0; hr < hDomRows.length; hr += 1) {
                var hdr = hDomRows[hr];
                if (hdr.data.length && hdr.y !== null) {
                    hdr.row.style.display = 'flex';
                    hdr.row.style.left = m.cx.toFixed(1) + 'px';
                    hdr.row.style.top = hdr.y + 'px';
                    hdr.row.style.width = m.cw.toFixed(1) + 'px';
                    hdr.row.style.height = m.thrH + 'px';
                    hdr.row.style.justifyContent = 'center';
                    for (var hk = 0; hk < hdr.items.length; hk += 1) {
                        var hDom = hdr.items[hk];
                        if (hk < hdr.data.length) {
                            var hit = hdr.data[hk];
                            var hlCol = hit.done ? v.up : v.tmu;
                            var hvCol = hit.done ? v.up : v.tm;
                            var colW = (hk === 0) ? m.hCol0W : m.hCol1W;
                            hDom.box.style.display = 'flex';
                            hDom.box.style.width = colW + 'px';
                            hDom.box.style.justifyContent = 'space-between';
                            hDom.box.style.marginLeft = (hk > 0) ? (m.hColGap + 'px') : '0px';
                            hDom.ico.style.display = 'none';
                            hDom.lbl.textContent = hit.lbl;
                            hDom.lbl.style.color = hlCol;
                            hDom.lbl.style.fontSize = m.thrSize + 'px';
                            hDom.lbl.style.textShadow = txtShadow;
                            hDom.txt.textContent = hit.valStr;
                            hDom.txt.style.marginLeft = '4px';
                            hDom.txt.style.color = hvCol;
                            hDom.txt.style.fontSize = m.thrSize + 'px';
                            hDom.txt.style.textShadow = txtShadow;
                        } else {
                            hDom.box.style.display = 'none';
                        }
                    }
                } else {
                    hdr.row.style.display = 'none';
                }
            }
        } else if (m.thr && m.thr.length && m.thrY !== null) {
            dom.thrRow2.style.display = 'none';
            var tBaseW = m.cw;
            var tBaseX = m.cx;
            dom.thrRow.style.display = 'flex';
            dom.thrRow.style.left = tBaseX.toFixed(1) + 'px';
            dom.thrRow.style.top = m.thrY + 'px';
            dom.thrRow.style.width = tBaseW.toFixed(1) + 'px';
            dom.thrRow.style.height = m.thrH + 'px';
            dom.thrRow.style.justifyContent = 'center';
            for (var kt = 0; kt < dom.thrItems.length; kt += 1) {
                var tDom = dom.thrItems[kt];
                if (kt < m.thr.length) {
                    var tit = m.thr[kt];
                    var lCol = tit.done ? v.up : v.tmu;
                    var vCol = tit.done ? v.up : v.tm;
                    tDom.box.style.display = 'flex';
                    tDom.box.style.width = '';
                    tDom.box.style.justifyContent = '';
                    tDom.box.style.marginLeft = (kt > 0) ? (m.thrItemGap + 'px') : '0px';
                    tDom.ico.style.display = 'none';
                    tDom.lbl.textContent = tit.lbl;
                    tDom.lbl.style.color = lCol;
                    tDom.lbl.style.fontSize = m.thrSize + 'px';
                    tDom.lbl.style.textShadow = txtShadow;
                    tDom.txt.textContent = tit.valStr;
                    tDom.txt.style.marginLeft = spacePx + 'px';
                    tDom.txt.style.color = vCol;
                    tDom.txt.style.fontSize = m.thrSize + 'px';
                    tDom.txt.style.textShadow = txtShadow;
                } else {
                    tDom.box.style.display = 'none';
                }
            }
        } else {
            dom.thrRow.style.display = 'none';
            dom.thrRow2.style.display = 'none';
        }

        var svgStr = '<svg xmlns="http://www.w3.org/2000/svg" width="' + winW + '" height="' + winH + '" viewBox="0 0 ' + winW + ' ' + winH + '">' + parts.join('') + '</svg>';
        if (svgStr !== v3LastSvg) {
            v3LastSvg = svgStr;
            dom.bgImg.src = svgUri(svgStr);
        }
        return [winW, winH];
    }

    function buildArrow() {
        for (var i = 0; i < ARROW_ROWS.length; i += 1) {
            var w = ARROW_ROWS[i];
            var d = document.createElement('div');
            d.style.left = ((10 - w) / 2) + 'px';
            d.style.top = i + 'px';
            d.style.width = w + 'px';
            d.style.height = (i < ARROW_ROWS.length - 1 ? 2 : 1) + 'px';
            elArrow.appendChild(d);
            arrowRows.push(d);
        }
    }
    function paintArrow(color, down) {
        elArrow.style.transform = down ? 'scaleY(-1)' : '';
        for (var i = 0; i < arrowRows.length; i += 1) {
            arrowRows[i].style.background = color;
        }
    }
    var lastPayload = '';

    /* рисует строку PNG-глифами; возвращает ширину в px */
    function drawText(container, text, color) {
        var key = color + '|' + text;
        if (container.__key === key) return container.__w || 0;
        container.__key = key;
        while (container.firstChild) container.removeChild(container.firstChild);
        var x = 0;
        for (var i = 0; i < text.length; i += 1) {
            var g = METRICS.g[text.charAt(i)];
            if (!g) continue;
            if (text.charAt(i) !== ' ') {
                var d = document.createElement('div');
                d.style.left = x + 'px';
                d.style.width = g.w + 'px';
                d.style.backgroundImage = 'url(' + FONT_URL + color + '.png)';
                d.style.backgroundPosition = (-g.x) + 'px 0px';
                container.appendChild(d);
            }
            x += g.w + 1;
        }
        container.__w = x;
        return x;
    }

    function widthOf(el) {
        try {
            return el.getBoundingClientRect().width / (curScale || 1);
        } catch (e) {
            return 0;
        }
    }

    function refresh() {
        var raw = window.model && window.model.payload ? String(window.model.payload) : '';
        if (!raw || raw === lastPayload) return;
        lastPayload = raw;
        var p;
        try { p = JSON.parse(raw); } catch (e) { return; }

        var u = readUi(p.ui);
        // Непрозрачность всей панели настраивается отдельно от её фона.
        var alpha = clamp(num(u.alpha, 1), 0, 1);
        var isHangarMode = (p.mode === 'h');
        var ui = (p.mode === 's') ? 1 : clamp(num(isHangarMode ? (u.hs !== undefined ? u.hs : u.s) : u.s, 1), 0.5, 2.5);
        if (ui !== curUi) { curUi = ui; doResize(); }

        if (p.mode === 's') {
            elV3.style.display = 'none';
            elPanel.style.display = 'block';
            elPanel.style.opacity = (alpha * (p.dim ? 0.4 : 1)).toFixed(3);
            applyPanelStyle(u);
            elCfg.style.display = (p.cfg === false) ? 'none' : '';
            var setH = clamp(num(p.setH, 318), 100, 800);
            SIZES.s = [244, setH + 24];
            if (curMode !== 's' || elPanel.className !== 'settings' || lastSetH !== setH) {
                curMode = 's';
                lastSetH = setH;
                elPanel.className = 'settings';
                doResize();
            }
            elPanel.style.height = setH + 'px';
            elTick.style.display = 'none';
            elArrow.style.display = 'none';
            elAst.style.display = 'none';
            renderSettings(p.set || []);
            return;
        }

        if (isHangarMode || Number(u.preset) === 0 || Number(u.preset) === 2) {
            elPanel.style.display = 'none';
            elV3.style.display = 'block';
            elV3.style.opacity = (alpha * (p.dim ? 0.4 : 1)).toFixed(3);
            var v3Dims = renderV3(p, u, isHangarMode);
            var v3Key = v3Dims[0] + 'x' + v3Dims[1];
            SIZES.v3 = v3Dims;
            if (curMode !== 'v3' || lastV3Key !== v3Key) {
                curMode = 'v3';
                lastV3Key = v3Key;
                doResize();
            }
            return;
        }

        elV3.style.display = 'none';
        elPanel.style.display = 'block';
        elPanel.style.opacity = (alpha * (p.dim ? 0.4 : 1)).toFixed(3);
        applyPanelStyle(u);
        /* встроенная страница настроек нужна, только если нет Mod Menu */
        elCfg.style.display = (p.cfg === false) ? 'none' : '';
        elPanel.style.height = '';
        rowState = null;
        dmgShown = false;

        var mode = p.mode === 'h' ? 'h' : 'b';
        var mini = !!p.min;
        var mini2 = mini && mode === 'h';
        /* p.ast = [засвет, гусеница]; null - этот показ выключен в настройках */
        var astR = !!p.ast && p.ast[0] !== null && p.ast[0] !== undefined;
        var astT = !!p.ast && p.ast[1] !== null && p.ast[1] !== undefined;
        var pctOnly = (mode === 'b') && !!u.onlyPct;
        var astOn = (mode === 'b') && (astR || astT) && !pctOnly;
        SIZES.b = pctOnly ? [220, 72] : [244, astOn ? 118 : 96];
        elPanel.style.height = astOn ? '94px' : '';
        elAst.style.display = astOn ? 'flex' : 'none';
        var sizeKey = mini2 ? 'hm' : mode;
        var cls = (mode === 'h' ? 'hangar' : '') + (mini2 ? ' mini' : '') +
            (p.nodata ? ' nodata' : '') + (pctOnly ? ' percent-only' : '');
        if (sizeKey !== curMode || elPanel.className !== cls || astOn !== lastAstOn) {
            curMode = sizeKey;
            lastAstOn = astOn;
            elPanel.className = cls;
            dmgScale = 1;
            elValWrap.style.transform = '';
            doResize();
        }

        elPct.textContent = p.pct || '--.--%';
        elPct.style.color = u.pct;

        elBtn.style.backgroundImage = 'url(img://gui/maps/three_marks/' +
            (mini ? 'btn_max' : 'btn_min') + '.png)';

        if (mode === 'h') {
            elPct.style.left = '10px';
            var wbar = Math.max(0, Math.min(100, Number(p.bar) || 0));
            elFill.style.width = wbar + '%';
            elFill.className = '';
            elFill.style.background = u.bH;
            elFill.style.boxShadow = 'none';
            elTick.style.background = u.tick;
            if (wbar > 0 && p.pct && p.pct !== '--.--%') {
                elTick.style.display = 'block';
                elTick.style.left = (10 + (wbar / 100) * 200 - 1) + 'px';
            } else {
                elTick.style.display = 'none';
            }
            drawText(elEmaV, p.ema || '—', 'green');
            elEmaV.style.left = (10 + LABEL_EMA_W + 8) + 'px';
            drawText(thrEls.l65, '65%', 'gray');
            drawText(thrEls.v65, p.t65 || '—', 'white');
            drawText(thrEls.l85, '85%', 'gray');
            drawText(thrEls.v85, p.t85 || '—', 'white');
            var wl95 = drawText(thrEls.l95, '95%', 'gray');
            var wv95 = drawText(thrEls.v95, p.t95 || '—', 'white');
            var left95 = Math.max(10, (PANEL_W - wl95 - 6 - wv95) / 2);
            thrEls.l95.style.left = left95 + 'px';
            thrEls.v95.style.left = (left95 + wl95 + 6) + 'px';
            var marksH = Number(p.marks) || 0;
            for (var j = 0; j < stars.length; j += 1) {
                stars[j].className = j < marksH ? 'tm-star on' : 'tm-star';
            }
            return;
        }

        var hasDelta = !!p.delta;
        var negative = hasDelta && p.delta.charAt(0) === '-';
        var deltaValue = hasDelta ? parseFloat(p.delta) : 0;
        var kind = 'z';
        if (hasDelta) {
            if (u.bigDmg) {
                /* большой плюс по урону: решает Python (p.big), процент не важен */
                kind = (p.big && deltaValue >= 0) ? 'g' : kindOf(deltaValue, num(u.band, 0.02), 0);
            } else {
                kind = kindOf(deltaValue, num(u.band, 0.02), num(u.bigFrom, 4));
            }
        }
        var deltaColor = kind === 'g' ? u.big : (kind === 'p' ? u.up : (kind === 'n' ? u.dn : u.zr));
        if (hasDelta) {
            elDelta.textContent = p.delta;
            elDelta.style.color = deltaColor;
            elArrow.style.display = 'block';
            paintArrow(deltaColor, negative);
        } else {
            elDelta.textContent = '';
            elArrow.style.display = 'none';
        }
        if (pctOnly) {
            /* В режиме «только процент» его цвет всегда показывает знак изменения. */
            elPct.style.color = hasDelta ? deltaColor : u.pct;
        } else if (u.pctSign && hasDelta) {
            elPct.style.color = deltaColor;
        }

        rowState = { hasDelta: hasDelta };
        layoutRow();

        var w = Math.max(0, Math.min(100, Number(p.bar) || 0));
        elFill.style.width = w + '%';
        var glowOn = !!p.glow && !!u.glow;
        elFill.className = glowOn ? 'glow' : '';
        var barColor = u.bSign === false ? u.bStd :
            (kind === 'g' ? u.bBig : (kind === 'p' ? u.bUp : (kind === 'n' ? u.bDn : u.bZr)));
        var baseRgb = rgbOf(barColor);
        var c0 = glowOn ? baseRgb : mixRgb(baseRgb, [0, 0, 0], 0.42);
        var c1 = glowOn ? mixRgb(baseRgb, [255, 255, 255], 0.25) : baseRgb;
        elFill.style.background = 'linear-gradient(90deg,' + cssRgb(c0) + ',' + cssRgb(c1) + ')';
        elFill.style.boxShadow = glowOn ? '0 0 9px ' + cssRgba(baseRgb, 0.85) : 'none';
        elTick.style.background = u.tick;

        /* бегунок у края зелёной заливки, выступает над полосой */
        if (w > 0 && p.pct && p.pct !== '--.--%') {
            elTick.style.display = 'block';
            elTick.style.left = (TRACK_LEFT + (w / 100) * TRACK_W - 1) + 'px';
        } else {
            elTick.style.display = 'none';
        }

        elVal.textContent = p.dmg || '0';
        elVal.style.color = (u.dmgSign && hasDelta) ? deltaColor : u.dmg;
        elNeed.textContent = '/ ' + (p.proj || '—');
        elNeed.style.color = u.proj;

        dmgShown = true;
        layoutDamage();

        /* засвет / гусеница: большее - цвет изменения, меньшее - цвет большого % */
        if (astOn) {
            var rVal = astR ? (Number(p.ast[0]) || 0) : 0;
            var tVal = astT ? (Number(p.ast[1]) || 0) : 0;
            var mainColor = (u.pctSign && hasDelta) ? deltaColor : u.pct;
            elAstR.style.display = astR ? 'flex' : 'none';
            elAstT.style.display = astT ? 'flex' : 'none';
            elAstT.style.marginLeft = astR ? '28px' : '0px';
            elAstRv.textContent = fmtInt(rVal);
            elAstTv.textContent = fmtInt(tVal);
            /* выключенный показ считается нулём: с одним показом он подсвечен,
               пока там больше нуля */
            elAstRv.style.color = rVal > tVal ? deltaColor : mainColor;
            elAstTv.style.color = tVal > rVal ? deltaColor : mainColor;
            elAstRi.style.opacity = rVal > tVal ? '1' : '0.6';
            elAstTi.style.opacity = tVal > rVal ? '1' : '0.6';
        }

        var marks = Number(p.marks) || 0;
        for (var i = 0; i < stars.length; i += 1) {
            stars[i].className = i < marks ? 'tm-star on' : 'tm-star';
        }
    }

    function doResize() {
        var scale = 1;
        try { scale = Number(viewEnv.getScale()); } catch (e) {}
        if (!isFinite(scale) || scale <= 0) scale = 1;
        scale = scale * curUi;
        curScale = scale;
        var dims = SIZES[curMode] || SIZES.b;
        var width = Math.max(1, Math.round(dims[0] * scale));
        var height = Math.max(1, Math.round(dims[1] * scale));
        document.documentElement.style.width = width + 'px';
        document.documentElement.style.height = height + 'px';
        document.body.style.width = width + 'px';
        document.body.style.height = height + 'px';
        document.body.style.transform = 'scale(' + scale + ')';
        document.body.style.transformOrigin = '0 0';
        var ok = false;
        try { viewEnv.resizeViewPx(width, height); ok = true; } catch (e) {}
        return { scale: scale, width: width, height: height, resized: ok };
    }

    function report(info) {
        if (window.model && typeof window.model.onReady === 'function') {
            window.model.onReady({
                message: 'ready scale=' + info.scale + ' view=' + info.width +
                    'x' + info.height + ' resized=' + info.resized
            });
        }
    }

    function initialize() {
        elVal.className = 'tm-live';
        elNeed.className = 'tm-live';
        buildArrow();
        buildCfg();
        var info = doResize();
        refresh();
        if (window.engine) {
            window.engine.on('viewEnv.onDataChanged', refresh);
            window.engine.on('self.onScaleUpdated', function () {
                doResize();
                lastPayload = '';
                refresh();
            });
        }
        window.setInterval(refresh, 100);
        window.setInterval(layoutAll, 100);   /* раскладка устаревает позже текста */
        report(info);
        var tries = 0;
        var lastScale = info.scale;
        var timer = window.setInterval(function () {
            tries += 1;
            var r = doResize();
            if (r.scale !== lastScale) {
                lastScale = r.scale;
                lastPayload = '';
                refresh();
            }
            if (tries >= 5) window.clearInterval(timer);
        }, 700);
    }

    function afterTwoFrames(cb) {
        window.requestAnimationFrame(function () {
            window.requestAnimationFrame(cb);
        });
    }

    if (window.engine && window.engine.whenReady) {
        window.engine.whenReady.then(function () { afterTwoFrames(initialize); });
    } else {
        afterTwoFrames(initialize);
    }
}());
