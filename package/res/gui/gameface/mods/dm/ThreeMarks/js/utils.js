(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var B64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

    function num(v, d) {
        v = Number(v);
        return isFinite(v) ? v : d;
    }

    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    function fmtInt(n) {
        var t = String(Math.round(Number(n) || 0)), out = '';
        while (t.length > 3) {
            out = ' ' + t.slice(-3) + out;
            t = t.slice(0, -3);
        }
        return t + out;
    }

    function readUi(raw) {
        var u = {}, def = ns.DEF_UI;
        raw = raw || {};
        for (var k in def) {
            if (Object.prototype.hasOwnProperty.call(def, k)) {
                u[k] = (raw[k] === undefined || raw[k] === null) ? def[k] : raw[k];
            }
        }
        return u;
    }

    function readV3Ui(raw) {
        var v = {}, def = ns.DEF_V3;
        raw = raw || {};
        for (var k in def) {
            if (Object.prototype.hasOwnProperty.call(def, k)) {
                v[k] = (raw[k] === undefined || raw[k] === null) ? def[k] : raw[k];
            }
        }
        return v;
    }

    function v3Int(v, k, lo, hi) {
        return Math.round(clamp(num(v[k], ns.DEF_V3[k]), lo, hi));
    }

    function rgbOf(hex) {
        var m = /^#([0-9a-fA-F]{6})$/.exec(hex || '');
        if (!m) return [255, 255, 255];
        var n = parseInt(m[1], 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }

    function mixRgb(a, b, t) {
        return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    }

    function cssRgb(c) {
        return 'rgb(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' + Math.round(c[2]) + ')';
    }

    function cssRgba(c, a) {
        return 'rgba(' + Math.round(c[0]) + ',' + Math.round(c[1]) + ',' + Math.round(c[2]) + ',' + a + ')';
    }

    function kindOf(value, band, bigFrom) {
        if (bigFrom > 0 && value >= bigFrom) return 'g';
        if (Math.abs(value) <= band) return 'z';
        return value < 0 ? 'n' : 'p';
    }

    function encodeB64Ascii(str) {
        if (typeof root.btoa === 'function') {
            return root.btoa(str);
        }
        var out = '', i = 0, c1, c2, c3;
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
            out += B64_CHARS.charAt(c1 >> 2) +
                B64_CHARS.charAt(((c1 & 3) << 4) | (c2 >> 4)) +
                B64_CHARS.charAt(((c2 & 15) << 2) | (c3 >> 6)) +
                B64_CHARS.charAt(c3 & 63);
        }
        return out;
    }

    function svgUri(svg) {
        return 'data:image/svg+xml;base64,' + encodeB64Ascii(svg);
    }

    var EXTRA_WIDE_UPPER = '\u0416\u0428\u0429\u042e\u042b\u0424\u0414MW';
    var EXTRA_WIDE_LOWER = '\u0436\u0448\u0449\u044e\u044b\u0444\u0434\u043cmw';
    var NARROW_GLYPHS = 'Iiljtf!|\u0406\u0456\u0407\u0457';

    function v3Advance(text, size, scale) {
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
            else if (EXTRA_WIDE_UPPER.indexOf(ch) >= 0) w += 0.90 * s;
            else if (EXTRA_WIDE_LOWER.indexOf(ch) >= 0) w += 0.78 * s;
            else if (NARROW_GLYPHS.indexOf(ch) >= 0) w += 0.34 * s;
            else if ((ch >= 'A' && ch <= 'Z') || (ch >= '\u0410' && ch <= '\u042f') || ch === '\u0401') w += 0.64 * s;
            else w += 0.54 * s;
        }
        var sc = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        return w * sc;
    }

    function v3FmtNum(n, sepMode) {
        var val = Math.round(Number(n) || 0);
        var neg = val < 0;
        var s = String(Math.abs(val)), res;
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

    function v3BgGradient(hex, a) {
        var c = rgbOf(hex);
        var top = mixRgb(c, [255, 255, 255], 0.08);
        var bot = mixRgb(c, [0, 0, 0], 0.16);
        return 'linear-gradient(180deg,' + cssRgba(top, a) + ',' + cssRgba(bot, clamp(a * 1.12, 0, 1).toFixed(3)) + ')';
    }

    function v3BarGradient(hex) {
        var c = rgbOf(hex);
        var lo = mixRgb(c, [0, 0, 0], 0.18);
        var hi = mixRgb(c, [255, 255, 255], 0.16);
        return 'linear-gradient(90deg,' + cssRgb(lo) + ',' + cssRgb(hi) + ')';
    }

    ns.utils = {
        num: num, clamp: clamp, fmtInt: fmtInt,
        readUi: readUi, readV3Ui: readV3Ui, v3Int: v3Int,
        rgbOf: rgbOf, mixRgb: mixRgb, cssRgb: cssRgb, cssRgba: cssRgba,
        v3BgGradient: v3BgGradient, v3BarGradient: v3BarGradient,
        kindOf: kindOf, svgUri: svgUri, v3Advance: v3Advance, v3FmtNum: v3FmtNum
    };
}(window));
