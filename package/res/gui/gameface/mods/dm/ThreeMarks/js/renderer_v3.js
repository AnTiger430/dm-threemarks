(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var U = ns.utils;
    var M = ns.v3Metrics;
    var S = ns.v3Svg;

    function px(val, s) { return (val * s).toFixed(1) + 'px'; }
    function pxi(val, s) { return Math.max(1, Math.round(val * s)) + 'px'; }
    function px0(val, s) { return Math.round(val * s) + 'px'; }

    function V3Renderer(elV3) {
        this._el = elV3;
        this._dom = null;
        this._lastSvg = '';
        this._lastStarsKey = '';
        this._starsMode = '';
    }

    V3Renderer.prototype._makeThrRow = function (cls) {
        var row = document.createElement('div');
        row.className = cls;
        var items = [];
        for (var i = 0; i < 2; i += 1) {
            var box = document.createElement('div');
            box.className = 'v3-astitem v3-thritem';
            box.style.display = 'none';
            var ico = document.createElement('div');
            ico.className = 'v3-astico v3-thrico';
            ico.style.display = 'none';
            var lbl = document.createElement('span');
            lbl.className = 'v3-asttxt v3-thrlbl';
            var txt = document.createElement('span');
            txt.className = 'v3-asttxt v3-thrval';
            box.appendChild(ico);
            box.appendChild(lbl);
            box.appendChild(txt);
            row.appendChild(box);
            items.push({ box: box, ico: ico, lbl: lbl, txt: txt });
        }
        this._el.appendChild(row);
        return { row: row, items: items };
    };

    V3Renderer.prototype.ensureDom = function () {
        if (this._dom) return this._dom;
        var bgFill = document.createElement('div');
        bgFill.className = 'v3-bgfill';
        this._el.appendChild(bgFill);

        var bgImg = document.createElement('div');
        bgImg.className = 'v3-bgimg';
        this._el.appendChild(bgImg);

        var starsLayer = document.createElement('div');
        starsLayer.className = 'v3-stars';
        this._el.appendChild(starsLayer);

        var hdr = document.createElement('div');
        hdr.className = 'v3-hdr';
        var pctSpan = document.createElement('span'); pctSpan.className = 'v3-pct';
        var delWrap = document.createElement('span'); delWrap.className = 'v3-delwrap';
        var delIco = document.createElement('div'); delIco.className = 'v3-delico';
        var delTxt = document.createElement('span'); delTxt.className = 'v3-del';
        delWrap.appendChild(delIco); delWrap.appendChild(delTxt);
        hdr.appendChild(pctSpan); hdr.appendChild(delWrap);
        this._el.appendChild(hdr);

        var barWrap = document.createElement('div'); barWrap.className = 'v3-barwrap';
        var barFill = document.createElement('div'); barFill.className = 'v3-bar-fill';
        var barCur = document.createElement('div'); barCur.className = 'v3-bar-cur';
        barWrap.appendChild(barFill);
        var segFills = [], barTicks = [];
        for (var i = 0; i < 4; i += 1) {
            var sf = document.createElement('div'); sf.className = 'v3-seg-fill'; sf.style.display = 'none';
            barWrap.appendChild(sf); segFills.push(sf);
        }
        for (var k = 0; k < 3; k += 1) {
            var bt = document.createElement('div'); bt.className = 'v3-bar-tick'; bt.style.display = 'none';
            barWrap.appendChild(bt); barTicks.push(bt);
        }
        barWrap.appendChild(barCur);
        this._el.appendChild(barWrap);

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
        this._el.appendChild(barTxtWrap);

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
        this._el.appendChild(dmgRow);

        var astRow = document.createElement('div');
        astRow.className = 'v3-astwrap';
        var astItems = [];
        for (var j = 0; j < 4; j += 1) {
            var box = document.createElement('div');
            box.className = 'v3-astitem';
            box.style.display = 'none';
            var ico = document.createElement('div');
            ico.className = 'v3-astico';
            var txt = document.createElement('span');
            txt.className = 'v3-asttxt';
            box.appendChild(ico);
            box.appendChild(txt);
            astRow.appendChild(box);
            astItems.push({ box: box, ico: ico, txt: txt });
        }
        this._el.appendChild(astRow);

        var thr1 = this._makeThrRow('v3-astwrap v3-thrwrap');
        var thr2 = this._makeThrRow('v3-astwrap v3-thrwrap v3-thrwrap2');

        this._dom = {
            bgFill: bgFill, bgImg: bgImg, starsLayer: starsLayer, hdr: hdr, pct: pctSpan, delWrap: delWrap, delIco: delIco, delTxt: delTxt,
            barWrap: barWrap, barFill: barFill, barCur: barCur, segFills: segFills, barTicks: barTicks,
            barTxtWrap: barTxtWrap, barTxtBox: barTxtBox, barTxtBase: barTxtBase, barTxtClip: barTxtClip, barTxtFill: barTxtFill,
            dmgRow: dmgRow, dmgLbl: dmgLbl, dmgVals: dmgVals, dmgMain: dmgMain, dmgSec: dmgSec,
            astRow: astRow, astItems: astItems,
            thrRow: thr1.row, thrItems: thr1.items,
            thrRow2: thr2.row, thrItems2: thr2.items
        };
        return this._dom;
    };

    V3Renderer.prototype.render = function (p, u, isHangar, scale) {
        var dom = this.ensureDom();
        var s = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        var v = U.readV3Ui(isHangar ? (u.vh || u.v3) : u.v3);
        var d = p.v3d || {
            isHangar: !!isHangar, pct: parseFloat(p.pct) || 0, bar: p.bar || 0, delta: parseFloat(p.delta),
            sDelta: null, dmg: 0, tHold: 0, tMark: 0, tPlus1: 0, own: 0,
            spot: (p.ast && p.ast[0]) || 0, track: (p.ast && p.ast[1]) || 0, stun: 0,
            marks: p.marks || 0, big: !!p.big, isSpg: false, alt: false, hasRating: (p.pct && p.pct !== '--.--%')
        };
        if (isHangar) d.isHangar = true;
        var fnt = U.v3Int(v, 'fnt', 0, 7);
        this._el.className = 'tm-font-' + fnt;
        var m = M.v3ComputeMetrics(v, d, u);
        var winW = (p.v3m && p.v3m[0]) ? Math.max(1, Math.round(p.v3m[0])) : m.winW;
        var winH = (p.v3m && p.v3m[1]) ? Math.max(1, Math.round(p.v3m[1])) : m.winH;
        var winWpx = Math.max(1, Math.round(winW * s));
        var winHpx = Math.max(1, Math.round(winH * s));
        this._el.style.width = winWpx + 'px';
        this._el.style.height = winHpx + 'px';
        dom.bgImg.style.width = winWpx + 'px';
        dom.bgImg.style.height = winHpx + 'px';

        var fs = U.v3Int(v, 'fs', 0, 3), rad = U.v3Int(v, 'rad', 0, 14);
        var bga = U.clamp(U.num(v.bgo, 0.48), 0, 1), ca = U.clamp(U.num(v.ca, 0.90), 0, 1), ba = U.clamp(U.num(v.ba, 0.28), 0, 1);
        var shA = (fs === 3) ? 0.85 : ((bga < 0.55) ? (0.85 * (1 - bga / 0.55)) : 0);
        var txtShadow = (shA >= 0.05) ? ('0 1px 0 rgba(0,0,0,' + shA.toFixed(2) + ')') : 'none';
        var fxP = Math.round(m.fx * s), fyP = Math.round(m.fy * s);
        var fwP = Math.max(1, Math.round(m.fw * s)), fhP = Math.max(1, Math.round(m.fh * s)), radP = Math.round(rad * s);
        var specs = [];
        if (fs !== 3 && bga > 0.01) {
            dom.bgFill.style.display = 'block';
            dom.bgFill.style.left = fxP + 'px'; dom.bgFill.style.top = fyP + 'px';
            dom.bgFill.style.width = fwP + 'px'; dom.bgFill.style.height = fhP + 'px';
            dom.bgFill.style.borderRadius = radP + 'px';
            dom.bgFill.style.backgroundColor = U.cssRgba(U.rgbOf(v.bgc), bga);
            dom.bgFill.style.background = U.v3BgGradient(v.bgc, bga);
            dom.bgFill.style.boxShadow = (ba > 0.01) ? 'inset 0 1px 0 rgba(255,255,255,0.06)' : 'none';
        } else { dom.bgFill.style.display = 'none'; }
        if (fs !== 3) {
            var sx = fxP + 0.5, sy = fyP + 0.5, sw = Math.max(1, fwP - 1), sh = Math.max(1, fhP - 1), sr = Math.max(0, radP - 0.5);
            if ((fs === 0 || fs === 2) && ba > 0.01) {
                var gapSide = null, g0 = 0, g1 = 0, halfGap = m.starsSpan * 0.5 + 6;
                if (m.starsPos === 0) { gapSide = 'top'; g0 = m.fx + m.fw * 0.5 - halfGap; g1 = m.fx + m.fw * 0.5 + halfGap; }
                else if (m.starsPos === 1) { gapSide = 'bottom'; g0 = m.fx + m.fw * 0.5 - halfGap; g1 = m.fx + m.fw * 0.5 + halfGap; }
                else if (m.starsPos === 2 && m.sideBorderStars) { gapSide = 'left'; g0 = m.fy + m.fh * 0.5 - halfGap; g1 = m.fy + m.fh * 0.5 + halfGap; }
                else if (m.starsPos === 3 && m.sideBorderStars) { gapSide = 'right'; g0 = m.fy + m.fh * 0.5 - halfGap; g1 = m.fy + m.fh * 0.5 + halfGap; }
                specs.push({ tag: 'path', attrs: { d: S.framePath(sx, sy, sw, sh, sr, gapSide, Math.round(g0 * s) + 0.5, Math.round(g1 * s) + 0.5, s), fill: 'none', stroke: v.cc, 'stroke-width': '1', 'stroke-opacity': ba.toFixed(3) } });
            }
            if ((fs === 0 || fs === 1) && ca > 0.01) {
                var cps = S.cornersPaths(sx, sy, sw, sh, sr, s), cwPx = Math.max(1.5, Math.round(1.8 * s * 2) / 2).toFixed(1);
                for (var ci = 0; ci < cps.length; ci += 1) {
                    specs.push({ tag: 'path', attrs: { d: cps[ci], fill: 'none', stroke: v.cc, 'stroke-width': cwPx, 'stroke-linecap': 'round', 'stroke-opacity': ca.toFixed(3) } });
                }
            }
        }
        if (m.divLine) {
            specs.push({ tag: 'line', attrs: { x1: (Math.round(m.divLine[0] * s) + 0.5).toFixed(1), y1: String(Math.round(m.divLine[1] * s)), x2: (Math.round(m.divLine[2] * s) + 0.5).toFixed(1), y2: String(Math.round(m.divLine[3] * s)), stroke: v.cc, 'stroke-width': '1', 'stroke-opacity': '0.45' } });
        }

        var marks = Math.round(U.num(d.marks, 0)), starStyle = U.v3Int(v, 'ss', 0, 2), starRPx = m.starSize * 0.5 * s, starPts = [];
        for (var si = 0; si < m.starsCoords.length; si += 1) {
            starPts.push([Math.round(m.starsCoords[si][0] * s), Math.round(m.starsCoords[si][1] * s), si < marks]);
        }
        if (m.starsPos === 4) {
            var isx0 = m.cx + m.cw - m.starsSpan + m.starSize * 0.5, iscy = m.headerY + m.headerH * 0.5;
            for (var ii = 0; ii < 3; ii += 1) {
                starPts.push([Math.round((isx0 + ii * (m.starSize + m.starGap)) * s), Math.round(iscy * s), ii < marks]);
            }
        }
        var starsKey = s.toFixed(3) + '|' + starStyle + '|' + v.son + '|' + v.sof + '|' + (v.sgl ? 1 : 0) + '|' + starRPx.toFixed(2) + '|' + JSON.stringify(starPts);
        if (starsKey !== this._lastStarsKey) {
            this._lastStarsKey = starsKey;
            this._starsMode = S.mountStarsCanvas(dom.starsLayer, starPts, starRPx, starStyle, v.son, v.sof, !!v.sgl, s) ? 'canvas' : 'svg';
        }
        if (this._starsMode !== 'canvas') {
            for (var sp = 0; sp < starPts.length; sp += 1) {
                Array.prototype.push.apply(specs, S.starSpecs(starPts[sp][0], starPts[sp][1], starRPx, starPts[sp][2], starStyle, v.son, v.sof, !!v.sgl, s));
            }
        }

        var ho = U.v3Int(v, 'ho', 0, 2), di = U.v3Int(v, 'di', 0, 3), dc = U.v3Int(v, 'dc', 0, 1);
        dom.hdr.style.left = px0(m.cx, s);
        dom.hdr.style.top = px0(m.headerY, s);
        dom.hdr.style.width = pxi(Math.max(20, m.cw - (m.starsPos === 4 ? (m.starsSpan + 8) : 0)), s);
        dom.hdr.style.height = pxi(m.headerH, s);
        dom.hdr.style.flexDirection = (ho === 1) ? 'row-reverse' : 'row';
        dom.hdr.style.justifyContent = (ho === 2) ? 'center' : 'space-between';
        dom.pct.textContent = m.dInfo.pctText;
        dom.pct.style.opacity = (d.hasRating === false) ? '0.62' : '';
        dom.pct.style.color = v.tm; dom.pct.style.fontSize = pxi(m.pctSize, s); dom.pct.style.textShadow = txtShadow;

        if (m.dInfo.showDelta) {
            var delCol = (dc === 0) ? m.dInfo.accent : v.tmu;
            dom.delWrap.style.display = 'flex';
            dom.delWrap.style.marginLeft = (ho === 2) ? px0(10, s) : '0px';
            if (di === 0 || di === 1) {
                var delPx = Math.max(1, Math.round(11 * s));
                dom.delIco.style.display = 'block';
                dom.delIco.style.width = delPx + 'px';
                dom.delIco.style.height = delPx + 'px';
                dom.delIco.style.marginRight = px0(4, s);
                S.mountDeltaIcon(dom.delIco, di, m.dInfo.dir || (m.dInfo.down ? 'down' : 'up'), delCol, delPx);
            } else { dom.delIco.style.display = 'none'; }
            dom.delTxt.textContent = m.dInfo.deltaText;
            dom.delTxt.style.color = delCol;
            dom.delTxt.style.fontSize = pxi(m.deltaSize, s);
            dom.delTxt.style.textShadow = txtShadow;
        } else {
            dom.delWrap.style.display = 'none';
        }

        this._renderBar(dom, m, v, d, txtShadow, specs, s);
        this._renderDamageAndBottom(dom, m, v, d, winW, txtShadow, specs, s);

        var svgKey = winWpx + 'x' + winHpx + '|' + JSON.stringify(specs);
        if (svgKey !== this._lastSvg) {
            this._lastSvg = svgKey;
            S.mountSvg(dom.bgImg, winWpx, winHpx, winWpx, winHpx, specs);
        }
        return [winW, winH];
    };

    V3Renderer.prototype._renderBar = function (dom, m, v, d, txtShadow, specs, s) {
        var ratio = M.v3BarRatio(v, d);
        var barCol = M.v3BarColor(v, m.dInfo.accent);
        if (m.barStyle === 3 && m.barY !== null) {
            dom.barWrap.style.display = 'none';
            dom.barTxtWrap.style.display = 'flex';
            dom.barTxtWrap.style.left = px0(m.cx, s);
            dom.barTxtWrap.style.top = px0(m.barY, s);
            dom.barTxtWrap.style.width = pxi(m.cw, s);
            dom.barTxtWrap.style.height = pxi(m.barBlockH, s);
            dom.barTxtBase.textContent = m.barText;
            dom.barTxtBase.style.fontSize = pxi(m.barTextSize, s);
            dom.barTxtBase.style.lineHeight = pxi(m.barBlockH, s);
            dom.barTxtFill.textContent = m.barText;
            dom.barTxtFill.style.fontSize = pxi(m.barTextSize, s);
            dom.barTxtFill.style.lineHeight = pxi(m.barBlockH, s);
            dom.barTxtFill.style.color = barCol;
            dom.barTxtFill.style.textShadow = txtShadow;
            dom.barTxtClip.style.width = U.clamp(ratio * 100, 0, 100).toFixed(2) + '%';
            dom.barTxtBox.style.transform = '';
            if (typeof dom.barTxtBox.getBoundingClientRect === 'function') {
                try {
                    var bwPx = dom.barTxtBox.getBoundingClientRect().width;
                    var maxPx = Math.max(10, (m.cw - 4) * s);
                    if (bwPx > maxPx && bwPx > 0) {
                        dom.barTxtBox.style.transform = 'scale(' + (maxPx / bwPx).toFixed(4) + ')';
                    }
                } catch (e) {}
            }
            return;
        }
        dom.barTxtWrap.style.display = 'none';
        if (m.barStyle === 2 || m.barY === null) { dom.barWrap.style.display = 'none'; return; }

        var bxP = Math.round(m.cx * s), bwP = Math.max(1, Math.round(m.cw * s)), bhP = Math.max(1, Math.round(m.barH * s)), trackHP = Math.max(1, Math.round(m.trackH * s));
        var byP = Math.round((m.barY + (m.barBlockH - m.barH) * 0.5) * s), trackYP = byP + Math.round((bhP - trackHP) * 0.5), effBHp = Math.max(bhP, trackHP);
        dom.barWrap.style.display = 'block';
        dom.barWrap.style.left = bxP + 'px'; dom.barWrap.style.top = byP + 'px';
        dom.barWrap.style.width = bwP + 'px'; dom.barWrap.style.height = bhP + 'px';
        var curW = Math.max(2, Math.round(2.5 * s)), curH = Math.max(10, effBHp + Math.round(6 * s)), curTop = Math.round((bhP - curH) * 0.5);

        var barGrad = U.v3BarGradient(barCol);
        if (m.barStyle === 1) {
            dom.barFill.style.display = 'none';
            for (var tk = 0; tk < 3; tk += 1) dom.barTicks[tk].style.display = 'none';
            var spans = [[0, 65], [65, 85], [85, 95], [95, 100]], weights = [0.65, 0.20, 0.10, 0.05];
            var gapP = Math.max(1, Math.round(2 * s)), usableWP = Math.max(4, bwP - 3 * gapP), segXP = bxP, curPct = U.clamp(ratio * 100, 0, 100), curFillXP = 0;
            for (var sIdx = 0; sIdx < 4; sIdx += 1) {
                var sf = dom.segFills[sIdx], swP = Math.max(1, Math.round(usableWP * weights[sIdx])), s0 = spans[sIdx][0];
                var segFill = U.clamp((curPct - s0) / Math.max(1e-6, spans[sIdx][1] - s0), 0, 1);
                specs.push({ tag: 'rect', attrs: { x: segXP, y: trackYP, width: swP, height: trackHP, rx: '1', fill: '#FFFFFF', 'fill-opacity': '0.22' } });
                if (segFill > 0.005) {
                    sf.style.display = 'block'; sf.style.left = (segXP - bxP) + 'px'; sf.style.width = Math.max(1, Math.round(swP * segFill)) + 'px';
                    sf.style.height = bhP + 'px'; sf.style.backgroundColor = barCol; sf.style.background = barGrad;
                } else { sf.style.display = 'none'; }
                if (curPct > s0) curFillXP = (segXP - bxP) + swP * segFill;
                segXP += swP + gapP;
            }
            if (v.bcur) {
                dom.barCur.style.display = 'block'; dom.barCur.style.width = curW + 'px';
                dom.barCur.style.left = Math.round(U.clamp(curFillXP - curW * 0.5, 0, Math.max(0, bwP - curW))) + 'px';
                dom.barCur.style.top = curTop + 'px'; dom.barCur.style.height = curH + 'px';
            } else { dom.barCur.style.display = 'none'; }
            return;
        }
        for (var hi = 0; hi < 4; hi += 1) dom.segFills[hi].style.display = 'none';
        specs.push({ tag: 'rect', attrs: { x: bxP, y: trackYP, width: bwP, height: trackHP, rx: '1', fill: '#FFFFFF', 'fill-opacity': '0.22' } });
        if (v.bet) {
            var tickH = Math.max(8, effBHp + Math.round(4 * s)), tickTop = byP + Math.round((bhP - tickH) * 0.5);
            specs.push({ tag: 'rect', attrs: { x: bxP, y: tickTop, width: 1, height: tickH, fill: '#FFFFFF', 'fill-opacity': '0.45' } });
            specs.push({ tag: 'rect', attrs: { x: bxP + bwP - 1, y: tickTop, width: 1, height: tickH, fill: '#FFFFFF', 'fill-opacity': '0.45' } });
        }
        var showMarks = (v.bmk && U.v3Int(v, 'bsc', 0, 1) === 0);
        var markH = effBHp + Math.round(3 * s), markRelTop = Math.round((bhP - markH) * 0.5), ths = [65, 85, 95], pct100 = U.clamp(ratio * 100, 0, 100);
        for (var ti = 0; ti < 3; ti += 1) {
            var mt = dom.barTicks[ti];
            if (showMarks) {
                mt.style.display = 'block';
                mt.style.left = Math.round(bwP * (ths[ti] / 100)) + 'px';
                mt.style.top = markRelTop + 'px';
                mt.style.height = markH + 'px';
                mt.style.backgroundColor = (pct100 >= ths[ti]) ? 'rgba(255,255,255,0.62)' : 'rgba(255,255,255,0.36)';
            } else { mt.style.display = 'none'; }
        }
        var fillWP = Math.round(U.clamp(bwP * ratio, 0, bwP));
        if (fillWP > 0) {
            dom.barFill.style.display = 'block'; dom.barFill.style.width = fillWP + 'px';
            dom.barFill.style.height = bhP + 'px'; dom.barFill.style.backgroundColor = barCol; dom.barFill.style.background = barGrad;
        } else { dom.barFill.style.display = 'none'; }
        if (v.bcur) {
            dom.barCur.style.display = 'block'; dom.barCur.style.width = curW + 'px';
            dom.barCur.style.left = Math.round(U.clamp(fillWP - curW * 0.5, 0, Math.max(0, bwP - curW))) + 'px';
            dom.barCur.style.top = curTop + 'px'; dom.barCur.style.height = curH + 'px';
        } else { dom.barCur.style.display = 'none'; }
    };

    V3Renderer.prototype._renderDamageAndBottom = function (dom, m, v, d, winW, txtShadow, specs, s) {
        if (m.dmgY !== null) {
            var centerDmg = (!m.isHangar && m.dmgLblMode === 3);
            dom.dmgRow.style.display = 'flex'; dom.dmgRow.style.left = px0(m.cx, s);
            dom.dmgRow.style.top = px0(m.dmgY, s); dom.dmgRow.style.width = pxi(m.cw, s); dom.dmgRow.style.height = pxi(m.dmgH, s);
            dom.dmgRow.style.justifyContent = centerDmg ? 'center' : 'space-between';
            dom.dmgVals.style.marginLeft = centerDmg ? '0px' : 'auto';
            if (m.dmgLblText) {
                dom.dmgLbl.style.display = 'block'; dom.dmgLbl.textContent = m.dmgLblText;
                dom.dmgLbl.style.color = v.tmu; dom.dmgLbl.style.fontSize = pxi(m.dmgLblSize || m.dmgSize, s); dom.dmgLbl.style.textShadow = txtShadow;
            } else { dom.dmgLbl.style.display = 'none'; }
            if (m.isHangar) {
                dom.dmgMain.style.display = 'block'; dom.dmgMain.textContent = m.tInfo.dmgStr;
                dom.dmgMain.style.color = (d.hasRating !== false && m.tInfo.dmg > 0) ? v.up : v.tmu;
                dom.dmgMain.style.opacity = (m.tInfo.dmgStr === '\u2014') ? '0.55' : '';
                dom.dmgMain.style.fontSize = pxi(m.dmgSize, s); dom.dmgMain.style.textShadow = txtShadow;
                dom.dmgSec.style.display = 'none';
            } else {
                dom.dmgMain.style.opacity = '';
                var dmgCol = v.ddyn ? m.dInfo.accent : v.tm;
                dom.dmgMain.style.display = 'block'; dom.dmgMain.textContent = m.tInfo.dmgStr;
                dom.dmgMain.style.color = dmgCol; dom.dmgMain.style.fontSize = pxi(m.dmgSize, s); dom.dmgMain.style.textShadow = txtShadow;
                dom.dmgSec.style.display = 'block'; dom.dmgSec.style.marginLeft = px0(4, s);
                dom.dmgSec.textContent = '/ ' + m.tInfo.tgtStr; dom.dmgSec.style.color = v.tmu;
                dom.dmgSec.style.fontSize = pxi(m.dmgSize, s); dom.dmgSec.style.textShadow = txtShadow;
            }
            dom.dmgLbl.style.transform = '';
            if (m.dmgLblText && dom.dmgVals && typeof dom.dmgLbl.getBoundingClientRect === 'function') {
                try {
                    var lblPx = dom.dmgLbl.getBoundingClientRect().width;
                    var valsPx = dom.dmgVals.getBoundingClientRect().width;
                    var availLblPx = Math.max(10, m.cw * s - valsPx - 8 * s);
                    if (lblPx > availLblPx && lblPx > 0) {
                        dom.dmgLbl.style.transform = 'scale(' + (availLblPx / lblPx).toFixed(4) + ')';
                    }
                } catch (e) {}
            }
        } else { dom.dmgRow.style.display = 'none'; }

        if (m.ast.items.length && m.astY !== null) {
            var baseX = m.astInside ? m.cx : (winW - Math.max(m.cw, m.astRowMinW)) * 0.5;
            var baseW = m.astInside ? m.cw : Math.max(m.cw, m.astRowMinW);
            dom.astRow.style.display = 'flex'; dom.astRow.style.left = px0(baseX, s); dom.astRow.style.top = px0(m.astY, s);
            dom.astRow.style.width = pxi(baseW, s); dom.astRow.style.height = pxi(m.astH, s); dom.astRow.style.justifyContent = 'center';
            for (var ka = 0; ka < 4; ka += 1) {
                var itemDom = dom.astItems[ka];
                if (ka < m.ast.items.length) {
                    var it = m.ast.items[ka], col = it.active ? v.up : v.tmu;
                    itemDom.box.style.display = 'flex'; itemDom.box.style.marginLeft = (ka > 0) ? px0(m.astItemGap, s) : '0px';
                    var astPx = Math.max(1, Math.round(m.astIconSize * s));
                    itemDom.ico.style.width = astPx + 'px'; itemDom.ico.style.height = astPx + 'px'; itemDom.ico.style.marginRight = px0(5, s);
                    S.mountAssistIcon(itemDom.ico, it.ch, astPx, col, it.active ? 1.0 : 0.82);
                    itemDom.txt.textContent = it.text; itemDom.txt.style.color = col;
                    itemDom.txt.style.fontSize = pxi(m.astSize, s); itemDom.txt.style.textShadow = txtShadow;
                } else { itemDom.box.style.display = 'none'; }
            }
        } else { dom.astRow.style.display = 'none'; }

        var spacePx = Math.max(2, Math.round(0.24 * m.thrSize));
        if (m.hRows && m.hRows.length) {
            if (m.hSepY !== null) {
                specs.push({ tag: 'line', attrs: { x1: String(Math.round(m.cx * s)), y1: (Math.round(m.hSepY * s) + 0.5).toFixed(1), x2: String(Math.round((m.cx + m.cw) * s)), y2: (Math.round(m.hSepY * s) + 0.5).toFixed(1), stroke: v.cc, 'stroke-width': '1', 'stroke-opacity': '0.18' } });
            }
            var hDomRows = [{ row: dom.thrRow, items: dom.thrItems, data: m.hRows[0] || [], y: m.hRow1Y }, { row: dom.thrRow2, items: dom.thrItems2, data: m.hRows[1] || [], y: m.hRow2Y }];
            for (var hr = 0; hr < 2; hr += 1) {
                var hdr = hDomRows[hr];
                if (hdr.data.length && hdr.y !== null) {
                    hdr.row.style.display = 'flex'; hdr.row.style.left = px0(m.cx, s); hdr.row.style.top = px0(hdr.y, s);
                    hdr.row.style.width = pxi(m.cw, s); hdr.row.style.height = pxi(m.thrH, s); hdr.row.style.justifyContent = 'center';
                    for (var hk = 0; hk < 2; hk += 1) {
                        var hDom = hdr.items[hk];
                        if (hk < hdr.data.length) {
                            var hit = hdr.data[hk];
                            hDom.box.style.display = 'flex'; hDom.box.style.width = pxi((hk === 0) ? m.hCol0W : m.hCol1W, s); hDom.box.style.minWidth = '';
                            hDom.box.style.justifyContent = 'space-between'; hDom.box.style.marginLeft = (hk > 0) ? px0(m.hColGap, s) : '0px';
                            hDom.ico.style.display = 'none';
                            hDom.lbl.textContent = hit.lbl; hDom.lbl.style.color = hit.done ? v.up : v.tmu; hDom.lbl.style.fontSize = pxi(m.thrSize, s); hDom.lbl.style.textShadow = txtShadow;
                            hDom.txt.textContent = hit.valStr; hDom.txt.style.marginLeft = px0(4, s); hDom.txt.style.color = hit.done ? v.up : v.tm; hDom.txt.style.fontSize = pxi(m.thrSize, s); hDom.txt.style.textShadow = txtShadow;
                            hDom.txt.style.opacity = (hit.valStr === '\u2014') ? '0.55' : ((hit.pct === 100 && Math.round(U.num(d.marks, 0)) < 3) ? '0.82' : '');
                        } else { hDom.box.style.display = 'none'; }
                    }
                } else { hdr.row.style.display = 'none'; }
            }
        } else if (m.thr && m.thr.length && m.thrY !== null) {
            dom.thrRow2.style.display = 'none';
            dom.thrRow.style.display = 'flex'; dom.thrRow.style.left = px0(m.cx, s); dom.thrRow.style.top = px0(m.thrY, s);
            dom.thrRow.style.width = pxi(m.cw, s); dom.thrRow.style.height = pxi(m.thrH, s); dom.thrRow.style.justifyContent = 'center';
            for (var kt = 0; kt < 2; kt += 1) {
                var tDom = dom.thrItems[kt];
                if (kt < m.thr.length) {
                    var tit = m.thr[kt];
                    tDom.box.style.display = 'flex'; tDom.box.style.width = ''; tDom.box.style.minWidth = ''; tDom.box.style.justifyContent = '';
                    tDom.box.style.marginLeft = (kt > 0) ? px0(m.thrItemGap, s) : '0px'; tDom.ico.style.display = 'none';
                    tDom.lbl.textContent = tit.lbl; tDom.lbl.style.color = v.tmu; tDom.lbl.style.fontSize = pxi(m.thrSize, s); tDom.lbl.style.textShadow = txtShadow;
                    tDom.txt.textContent = tit.valStr; tDom.txt.style.marginLeft = px0(spacePx, s); tDom.txt.style.color = v.tm; tDom.txt.style.fontSize = pxi(m.thrSize, s); tDom.txt.style.textShadow = txtShadow;
                } else { tDom.box.style.display = 'none'; }
            }
        } else { dom.thrRow.style.display = 'none'; dom.thrRow2.style.display = 'none'; }
    };

    ns.V3Renderer = V3Renderer;
}(window));
