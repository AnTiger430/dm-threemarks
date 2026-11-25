(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var U = ns.utils;

    function ClassicRenderer(domRefs, getScale) {
        this._el = domRefs;
        this._getScale = getScale;
        this._arrowRows = [];
        this._panelStyleKey = '';
        this._rowState = null;
        this._dmgShown = false;
        this._dmgScale = 1;
        this._lastAstOn = false;
        this._lastFontIdx = -1;
        this._nativeScale = 0;
        this.curMode = 'b';
        this.buildArrow();
        this._el.val.className = 'tm-live';
        this._el.need.className = 'tm-live';
    }

    ClassicRenderer.prototype.resetGeometryCache = function () {
        this._dmgScale = 1;
        this._el.valWrap.style.transform = '';
    };

    ClassicRenderer.prototype.applyPanelStyle = function (u) {
        var a = U.clamp(U.num(u.bg, 0.82), 0, 1);
        var trk = U.clamp(U.num(u.trk, 0.18), 0, 1);
        var key = a + '|' + trk;
        if (key === this._panelStyleKey) return;
        this._panelStyleKey = key;
        var k = Math.min(1, a / 0.8);
        this._el.panel.style.background = 'linear-gradient(145deg, rgba(12,18,25,' + a.toFixed(3) + '), rgba(7,11,16,' + (a * 0.93).toFixed(3) + '))';
        this._el.panel.style.borderColor = 'rgba(186,210,229,' + (0.20 * k).toFixed(3) + ')';
        this._el.panel.style.boxShadow = '0 3px 10px rgba(0,0,0,' + (0.38 * k).toFixed(3) + '), inset 0 1px rgba(255,255,255,' + (0.035 * k).toFixed(3) + ')';
        this._el.track.style.background = 'rgba(226,235,244,' + trk.toFixed(3) + ')';
    };

    ClassicRenderer.prototype.buildArrow = function () {
        var rows = ns.ARROW_ROWS;
        for (var i = 0; i < rows.length; i += 1) {
            var w = rows[i];
            var d = document.createElement('div');
            d.style.left = ((10 - w) / 2) + 'px';
            d.style.top = i + 'px';
            d.style.width = w + 'px';
            d.style.height = (i < rows.length - 1 ? 2 : 1) + 'px';
            this._el.arrow.appendChild(d);
            this._arrowRows.push(d);
        }
    };

    ClassicRenderer.prototype.paintArrow = function (color, down) {
        this._el.arrow.style.transform = down ? 'scaleY(-1)' : '';
        for (var i = 0; i < this._arrowRows.length; i += 1) {
            this._arrowRows[i].style.background = color;
        }
    };

    ClassicRenderer.prototype.drawText = function (container, text, color) {
        var key = color + '|' + text;
        if (container.__key === key) return container.__w || 0;
        container.__key = key;
        while (container.firstChild) container.removeChild(container.firstChild);
        var x = 0, metrics = ns.METRICS, fontUrl = ns.CONST.FONT_URL;
        for (var i = 0; i < text.length; i += 1) {
            var g = metrics.g[text.charAt(i)];
            if (!g) continue;
            if (text.charAt(i) !== ' ') {
                var d = document.createElement('div');
                d.style.left = x + 'px';
                d.style.width = g.w + 'px';
                d.style.backgroundImage = 'url(' + fontUrl + color + '.png)';
                d.style.backgroundPosition = (-g.x) + 'px 0px';
                container.appendChild(d);
            }
            x += g.w + 1;
        }
        container.__w = x;
        return x;
    };

    ClassicRenderer.prototype._widthOf = function (el) {
        try {
            return el.getBoundingClientRect().width / (this._getScale() || 1);
        } catch (e) {
            return 0;
        }
    };

    ClassicRenderer.prototype._setLeft = function (el, value) {
        var v = value + 'px';
        if (el.__left !== v) {
            el.__left = v;
            el.style.left = v;
        }
    };

    ClassicRenderer.prototype.layoutAll = function () {
        var C = ns.CONST;
        if (this._rowState) {
            if (this._el.panel.className.indexOf('percent-only') >= 0) {
                this._setLeft(this._el.pct, 0);
            } else {
                var wp = this._widthOf(this._el.pct);
                if (this._rowState.hasDelta) {
                    var left = (C.PANEL_W - wp) / 2;
                    this._setLeft(this._el.pct, left);
                    this._setLeft(this._el.arrow, left + wp + 9);
                    this._setLeft(this._el.delta, left + wp + 25);
                } else {
                    this._setLeft(this._el.pct, Math.max(4, (C.PANEL_W - wp) / 2));
                }
            }
        }
        if (this._dmgShown) {
            var nscl = this._nativeScale;
            var div = (nscl > 0) ? 1 : (this._getScale() || 1);
            var gapPx = (nscl > 0) ? Math.max(1, Math.round(4 * nscl)) : 4;
            var total = (this._widthOf(this._el.val) + gapPx + this._widthOf(this._el.need)) / (div * (this._dmgScale || 1));
            var onlyPct = this._el.panel.className.indexOf('percent-only') >= 0;
            var avail = onlyPct ? ((C.PANEL_W - 12) * (nscl > 0 ? nscl : 1)) : (C.PANEL_W - 131);
            var vs = total > avail ? Math.max(0.55, avail / total) : 1;
            if (Math.abs(vs - this._dmgScale) > 0.005) {
                this._dmgScale = vs;
                this._el.valWrap.style.transform = vs < 1 ? 'scale(' + vs + ')' : '';
            }
        }
    };

    ClassicRenderer.prototype._applyFont = function (u) {
        var fnt = (u && u.v3 && u.v3.fnt !== undefined && u.v3.fnt !== null) ? U.v3Int(u.v3, 'fnt', 0, 7) : 0;
        if (fnt === this._lastFontIdx) return;
        this._lastFontIdx = fnt;
        var fam = (ns.V3_FONT_FAMILIES && ns.V3_FONT_FAMILIES[fnt]) || ns.V3_FONT_FAMILIES[0];
        var targets = [this._el.pct, this._el.delta, this._el.val, this._el.need, this._el.astRv, this._el.astTv];
        for (var i = 0; i < targets.length; i += 1) {
            if (targets[i] && targets[i].style) targets[i].style.fontFamily = fam;
        }
    };

    ClassicRenderer.prototype.render = function (p, u, resizeFn, scale) {
        var C = ns.CONST;
        this.applyPanelStyle(u);
        this._applyFont(u);
        this._el.cfg.style.display = (p.cfg === false) ? 'none' : '';
        this._el.panel.style.height = '';
        this._rowState = null;
        this._dmgShown = false;

        var mode = p.mode === 'h' ? 'h' : 'b';
        var mini = !!p.min;
        var mini2 = mini && mode === 'h';
        var astR = !!p.ast && p.ast[0] !== null && p.ast[0] !== undefined;
        var astT = !!p.ast && p.ast[1] !== null && p.ast[1] !== undefined;
        var pctOnly = (mode === 'b') && !!u.onlyPct;
        var astOn = (mode === 'b') && (astR || astT) && !pctOnly;
        var natS = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : (this._getScale() || 1);
        ns.SIZES.b = pctOnly ? [220, 72] : [244, astOn ? 118 : 96];
        this._el.panel.style.height = astOn ? '94px' : '';
        this._el.ast.style.display = astOn ? 'flex' : 'none';
        var sizeKey = pctOnly ? 'bp' : (mini2 ? 'hm' : mode);
        if (pctOnly) {
            this._nativeScale = natS;
            var wP = Math.max(1, Math.round(220 * natS)) + 'px';
            var pctH = Math.max(12, Math.round(28 * natS)) + 'px';
            var rowH = Math.max(10, Math.round(20 * natS)) + 'px';
            var valFs = Math.max(8, Math.round(15 * natS)) + 'px';
            this._el.panel.style.width = wP;
            this._el.panel.style.height = Math.max(1, Math.round(72 * natS)) + 'px';
            this._el.pct.style.top = Math.round(10 * natS) + 'px';
            this._el.pct.style.width = wP;
            this._el.pct.style.height = pctH;
            this._el.pct.style.lineHeight = pctH;
            this._el.pct.style.fontSize = Math.max(10, Math.round(22 * natS)) + 'px';
            this._el.valWrap.style.top = Math.round(42 * natS) + 'px';
            this._el.valWrap.style.width = wP;
            this._el.valWrap.style.height = rowH;
            this._el.val.style.height = rowH; this._el.val.style.lineHeight = rowH; this._el.val.style.fontSize = valFs;
            this._el.need.style.height = rowH; this._el.need.style.lineHeight = rowH; this._el.need.style.fontSize = valFs;
            this._el.need.style.marginLeft = Math.max(1, Math.round(4 * natS)) + 'px';
        } else if (this._nativeScale > 0) {
            this._nativeScale = 0;
            this._el.panel.style.width = '';
            this._el.pct.style.top = ''; this._el.pct.style.width = ''; this._el.pct.style.height = '';
            this._el.pct.style.lineHeight = ''; this._el.pct.style.fontSize = '';
            this._el.valWrap.style.top = ''; this._el.valWrap.style.width = ''; this._el.valWrap.style.height = '';
            this._el.val.style.height = ''; this._el.val.style.lineHeight = ''; this._el.val.style.fontSize = '';
            this._el.need.style.height = ''; this._el.need.style.lineHeight = ''; this._el.need.style.fontSize = '';
            this._el.need.style.marginLeft = '';
        }
        var cls = (mode === 'h' ? 'hangar' : '') + (mini2 ? ' mini' : '') + (p.nodata ? ' nodata' : '') + (pctOnly ? ' percent-only' : '');
        if (sizeKey !== this.curMode || this._el.panel.className !== cls || astOn !== this._lastAstOn) {
            this.curMode = sizeKey;
            this._lastAstOn = astOn;
            this._el.panel.className = cls;
            this.resetGeometryCache();
            resizeFn(sizeKey);
        }

        this._el.pct.textContent = p.pct || '--.--%';
        this._el.pct.style.color = u.pct;
        this._el.btn.style.backgroundImage = 'url(img://gui/maps/three_marks/' + (mini ? 'btn_max' : 'btn_min') + '.png)';

        if (mode === 'h') {
            this._renderHangar(p, u);
            return;
        }

        var hasDelta = !!p.delta;
        var negative = hasDelta && p.delta.charAt(0) === '-';
        var deltaValue = hasDelta ? parseFloat(p.delta) : 0;
        var kind = 'z';
        if (hasDelta) {
            kind = u.bigDmg
                ? ((p.big && deltaValue >= 0) ? 'g' : U.kindOf(deltaValue, U.num(u.band, 0.02), 0))
                : U.kindOf(deltaValue, U.num(u.band, 0.02), U.num(u.bigFrom, 4));
        }
        var deltaColor = kind === 'g' ? u.big : (kind === 'p' ? u.up : (kind === 'n' ? u.dn : u.zr));
        if (hasDelta) {
            this._el.delta.textContent = p.delta;
            this._el.delta.style.color = deltaColor;
            this._el.arrow.style.display = 'block';
            this.paintArrow(deltaColor, negative);
        } else {
            this._el.delta.textContent = '';
            this._el.arrow.style.display = 'none';
        }
        if (pctOnly || (u.pctSign && hasDelta)) {
            this._el.pct.style.color = hasDelta ? deltaColor : u.pct;
        }

        this._rowState = { hasDelta: hasDelta };
        this.layoutAll();

        var w = Math.max(0, Math.min(100, Number(p.bar) || 0));
        this._el.fill.style.width = w + '%';
        var glowOn = !!p.glow && !!u.glow;
        this._el.fill.className = glowOn ? 'glow' : '';
        var barColor = u.bSign === false ? u.bStd : (kind === 'g' ? u.bBig : (kind === 'p' ? u.bUp : (kind === 'n' ? u.bDn : u.bZr)));
        var baseRgb = U.rgbOf(barColor);
        var c0 = glowOn ? baseRgb : U.mixRgb(baseRgb, [0, 0, 0], 0.42);
        var c1 = glowOn ? U.mixRgb(baseRgb, [255, 255, 255], 0.25) : baseRgb;
        this._el.fill.style.background = 'linear-gradient(90deg,' + U.cssRgb(c0) + ',' + U.cssRgb(c1) + ')';
        this._el.fill.style.boxShadow = glowOn ? '0 0 9px ' + U.cssRgba(baseRgb, 0.85) : 'none';
        this._el.tick.style.background = u.tick;

        if (w > 0 && p.pct && p.pct !== '--.--%') {
            this._el.tick.style.display = 'block';
            this._el.tick.style.left = (C.TRACK_LEFT + (w / 100) * C.TRACK_W - 1) + 'px';
        } else {
            this._el.tick.style.display = 'none';
        }

        this._el.val.textContent = p.dmg || '0';
        this._el.val.style.color = (u.dmgSign && hasDelta) ? deltaColor : u.dmg;
        this._el.need.textContent = '/ ' + (p.proj || '\u2014');
        this._el.need.style.color = u.proj;
        this._dmgShown = true;
        this.layoutAll();

        if (astOn) {
            var rVal = astR ? (Number(p.ast[0]) || 0) : 0, tVal = astT ? (Number(p.ast[1]) || 0) : 0;
            var mainColor = (u.pctSign && hasDelta) ? deltaColor : u.pct;
            this._el.astR.style.display = astR ? 'flex' : 'none';
            this._el.astT.style.display = astT ? 'flex' : 'none';
            this._el.astT.style.marginLeft = astR ? '28px' : '0px';
            this._el.astRv.textContent = U.fmtInt(rVal);
            this._el.astTv.textContent = U.fmtInt(tVal);
            this._el.astRv.style.color = rVal > tVal ? deltaColor : mainColor;
            this._el.astTv.style.color = tVal > rVal ? deltaColor : mainColor;
            this._el.astRi.style.opacity = rVal > tVal ? '1' : '0.6';
            this._el.astTi.style.opacity = tVal > rVal ? '1' : '0.6';
        }

        var marks = Number(p.marks) || 0;
        for (var i = 0; i < this._el.stars.length; i += 1) {
            this._el.stars[i].className = i < marks ? 'tm-star on' : 'tm-star';
        }
    };

    ClassicRenderer.prototype._renderHangar = function (p, u) {
        var C = ns.CONST;
        this._el.pct.style.left = '10px';
        var wbar = Math.max(0, Math.min(100, Number(p.bar) || 0));
        this._el.fill.style.width = wbar + '%';
        this._el.fill.className = '';
        this._el.fill.style.background = u.bH;
        this._el.fill.style.boxShadow = 'none';
        this._el.tick.style.background = u.tick;
        if (wbar > 0 && p.pct && p.pct !== '--.--%') {
            this._el.tick.style.display = 'block';
            this._el.tick.style.left = (10 + (wbar / 100) * 200 - 1) + 'px';
        } else {
            this._el.tick.style.display = 'none';
        }
        this.drawText(this._el.emaV, p.ema || '\u2014', 'green');
        this._el.emaV.style.left = (10 + C.LABEL_EMA_W + 8) + 'px';
        this.drawText(this._el.thr.l65, '65%', 'gray');
        this.drawText(this._el.thr.v65, p.t65 || '\u2014', 'white');
        this.drawText(this._el.thr.l85, '85%', 'gray');
        this.drawText(this._el.thr.v85, p.t85 || '\u2014', 'white');
        var wl95 = this.drawText(this._el.thr.l95, '95%', 'gray');
        var wv95 = this.drawText(this._el.thr.v95, p.t95 || '\u2014', 'white');
        var left95 = Math.max(10, (C.PANEL_W - wl95 - 6 - wv95) / 2);
        this._el.thr.l95.style.left = left95 + 'px';
        this._el.thr.v95.style.left = (left95 + wl95 + 6) + 'px';
        var marksH = Number(p.marks) || 0;
        for (var j = 0; j < this._el.stars.length; j += 1) {
            this._el.stars[j].className = j < marksH ? 'tm-star on' : 'tm-star';
        }
    };

    ns.ClassicRenderer = ClassicRenderer;
}(window));
