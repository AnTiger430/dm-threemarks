(function (root) {
    'use strict';
    var ns = root.DmThreeMarks;
    var U = ns.utils;

    function collectDom() {
        return {
            v3: document.getElementById('tm-v3'),
            panel: document.getElementById('tm-panel'),
            pct: document.getElementById('tm-pct'),
            arrow: document.getElementById('tm-arrow'),
            delta: document.getElementById('tm-delta'),
            fill: document.getElementById('tm-fill'),
            tick: document.getElementById('tm-tick'),
            val: document.getElementById('tm-val'),
            need: document.getElementById('tm-need'),
            valWrap: document.getElementById('tm-valwrap'),
            stars: [
                document.getElementById('tm-star1'),
                document.getElementById('tm-star2'),
                document.getElementById('tm-star3')
            ],
            emaV: document.getElementById('tm-hema-v'),
            thr: {
                l65: document.getElementById('tm-h65l'), v65: document.getElementById('tm-h65v'),
                l85: document.getElementById('tm-h85l'), v85: document.getElementById('tm-h85v'),
                l95: document.getElementById('tm-h95l'), v95: document.getElementById('tm-h95v')
            },
            btn: document.getElementById('tm-btn'),
            track: document.getElementById('tm-track'),
            set: document.getElementById('tm-set'),
            cfg: document.getElementById('tm-cfg'),
            ast: document.getElementById('tm-ast'),
            astR: document.getElementById('tm-ast-r'),
            astT: document.getElementById('tm-ast-t'),
            astRv: document.getElementById('tm-ast-rv'),
            astTv: document.getElementById('tm-ast-tv'),
            astRi: document.getElementById('tm-ast-ri'),
            astTi: document.getElementById('tm-ast-ti'),
            btoggle: document.getElementById('tm-btoggle'),
            btH: document.getElementById('tm-bt-h'),
            btV: document.getElementById('tm-bt-v')
        };
    }

    function ThreeMarksApp() {
        var self = this;
        this._dom = collectDom();
        this._bridge = new ns.GamefaceBridge();
        this._v3 = new ns.V3Renderer(this._dom.v3);
        this._classic = new ns.ClassicRenderer(this._dom, function () { return self._bridge.curScale; });
        this._settings = new ns.SettingsRenderer(this._dom.set, this._dom.cfg, function (c, t, col) {
            return self._classic.drawText(c, t, col);
        });
        this._curMode = '';
        this._lastPayload = '';
        this._lastSetH = 0;
        this._lastV3Key = '';
    }

    ThreeMarksApp.prototype._renderBattleToggle = function (show, isPlus, scale, ctrlDown, winW) {
        var el = this._dom.btoggle;
        if (!el) return;
        if (!show) {
            el.style.display = 'none';
            return;
        }
        var s = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        var box = Math.max(16, Math.round(22 * s));
        var barL = Math.max(6, Math.round(10 * s));
        var barT = Math.max(1.5, Math.round(2 * s));
        var leftPx = Math.max(0, Math.round(winW * s) - box);
        var topPx = Math.round(4 * s);
        el.className = isPlus ? 'plus' : 'minus';
        el.style.display = 'block';
        el.style.left = leftPx + 'px';
        el.style.top = topPx + 'px';
        el.style.width = box + 'px';
        el.style.height = box + 'px';
        el.style.borderRadius = Math.max(4, Math.round(6 * s)) + 'px';
        el.style.opacity = '0.92';
        if (this._dom.btH) {
            this._dom.btH.style.width = barL + 'px';
            this._dom.btH.style.height = barT + 'px';
        }
        if (this._dom.btV) {
            this._dom.btV.style.width = barT + 'px';
            this._dom.btV.style.height = barL + 'px';
            this._dom.btV.style.display = isPlus ? 'block' : 'none';
        }
    };

    ThreeMarksApp.prototype.refresh = function () {
        var raw = this._bridge.readPayload();
        if (!raw || raw === this._lastPayload) return;
        this._lastPayload = raw;
        var p;
        try { p = JSON.parse(raw); } catch (e) { return; }
        if (!p || (p.mode !== 'h' && p.mode !== 'b' && p.mode !== 's')) {
            this._dom.v3.style.display = 'none';
            this._dom.panel.style.display = 'none';
            this._renderBattleToggle(false, false, 1, false, 0);
            return;
        }

        var u = U.readUi(p.ui);
        var alpha = U.clamp(U.num(u.alpha, 1), 0, 1);
        var isHangarMode = (p.mode === 'h');
        var isBattleMode = (p.mode === 'b');
        var ui = (p.mode === 's') ? 1 : U.clamp(U.num(isHangarMode ? (u.hs !== undefined ? u.hs : u.s) : u.s, 1), 0.5, 2.5);
        var uiChanged = (ui !== this._bridge.curUi);
        if (uiChanged) {
            this._bridge.curUi = ui;
        }

        if (p.mode === 's') {
            this._renderBattleToggle(false, false, 1, false, 0);
            this._dom.v3.style.display = 'none';
            this._dom.panel.style.display = 'block';
            this._dom.panel.style.opacity = (alpha * (p.dim ? 0.4 : 1)).toFixed(3);
            this._classic.applyPanelStyle(u);
            this._dom.cfg.style.display = (p.cfg === false) ? 'none' : '';
            var setH = U.clamp(U.num(p.setH, 318), 100, 800);
            ns.SIZES.s = [244, setH + 24];
            if (this._curMode !== 's' || this._dom.panel.className !== 'settings' || this._lastSetH !== setH || uiChanged) {
                this._curMode = 's';
                this._classic.curMode = 's';
                this._lastSetH = setH;
                this._dom.panel.className = 'settings';
                this._bridge.doResize('s');
            }
            this._dom.panel.style.height = setH + 'px';
            this._dom.tick.style.display = 'none';
            this._dom.arrow.style.display = 'none';
            this._dom.ast.style.display = 'none';
            this._settings.render(p.set || []);
            return;
        }

        if (isHangarMode || Number(u.preset) === 0 || Number(u.preset) === 2) {
            this._dom.panel.style.display = 'none';
            var effScale = this._bridge.getEffectiveScale();
            if (isBattleMode && p.bmin) {
                this._dom.v3.style.display = 'none';
                var bminDims = (p.v3m && p.v3m[0] && p.v3m[1])
                    ? [Math.max(1, Math.round(p.v3m[0])), Math.max(1, Math.round(p.v3m[1]))]
                    : (ns.SIZES.v3 || [214, 96]);
                var bminKey = bminDims[0] + 'x' + bminDims[1] + '@' + effScale.toFixed(3);
                ns.SIZES.v3 = bminDims;
                if (this._curMode !== 'v3' || this._lastV3Key !== bminKey) {
                    this._curMode = 'v3';
                    this._lastV3Key = bminKey;
                    this._bridge.doResize('v3');
                }
                this._renderBattleToggle(!!p.ctrl, true, effScale, !!p.ctrl, bminDims[0]);
                return;
            }
            this._dom.v3.style.display = 'block';
            var effAlpha = alpha * (p.dim ? 0.4 : 1);
            this._dom.v3.style.opacity = (effAlpha < 0.999) ? effAlpha.toFixed(3) : '';
            var v3Dims = this._v3.render(p, u, isHangarMode, effScale);
            if (isBattleMode && p.ctrl) {
                this._dom.v3.className += ' tm-ctrl-drag';
            }
            var v3Key = v3Dims[0] + 'x' + v3Dims[1] + '@' + effScale.toFixed(3);
            ns.SIZES.v3 = v3Dims;
            if (this._curMode !== 'v3' || this._lastV3Key !== v3Key) {
                this._curMode = 'v3';
                this._lastV3Key = v3Key;
                this._bridge.doResize('v3');
            }
            this._renderBattleToggle(isBattleMode && !!p.ctrl, false, effScale, !!p.ctrl, v3Dims[0]);
            return;
        }

        this._dom.v3.style.display = 'none';
        var cEffScale = this._bridge.getEffectiveScale();
        if (isBattleMode && p.bmin) {
            this._dom.panel.style.display = 'none';
            var cMode = u.onlyPct ? 'bp' : ((p.ast && (u.spot || u.track)) ? 'ba' : 'b');
            if (this._curMode !== cMode || uiChanged) {
                this._curMode = cMode;
                this._classic.curMode = cMode;
                this._bridge.doResize(cMode);
            }
            var cMinDims = ns.SIZES[this._curMode] || ns.SIZES.b;
            this._renderBattleToggle(!!p.ctrl, true, u.onlyPct ? cEffScale : 1, !!p.ctrl, (cMinDims && cMinDims[0]) || (u.onlyPct ? 220 : 244));
            return;
        }
        this._dom.panel.style.display = 'block';
        this._dom.panel.style.opacity = (alpha * (p.dim ? 0.4 : 1)).toFixed(3);
        var self = this;
        var didResize = false;
        this._classic.render(p, u, function (modeKey) {
            self._curMode = modeKey;
            self._bridge.doResize(modeKey);
            didResize = true;
        }, cEffScale);
        if (uiChanged && !didResize && this._curMode) {
            this._bridge.doResize(this._curMode);
        }
        var cDims = ns.SIZES[this._curMode] || ns.SIZES.b;
        this._renderBattleToggle(isBattleMode && !!p.ctrl, false, u.onlyPct ? cEffScale : 1, !!p.ctrl, (cDims && cDims[0]) || (u.onlyPct ? 220 : 244));
    };

    ThreeMarksApp.prototype.layoutAll = function () {
        if (this._curMode === 'v3' || this._curMode === 's' || !this._curMode) return;
        this._classic.layoutAll();
    };

    ThreeMarksApp.prototype.start = function () {
        var self = this;
        this.refresh();
        var info = this._curMode
            ? this._bridge.doResize(this._curMode)
            : { scale: this._bridge.getEffectiveScale(), width: 0, height: 0, resized: false };
        this._bridge.subscribe(
            function () { self.refresh(); },
            function () {
                if (self._curMode) self._bridge.doResize(self._curMode, true);
                self._lastPayload = '';
                self.refresh();
            }
        );
        root.setInterval(function () { self.refresh(); }, 100);
        root.setInterval(function () { self.layoutAll(); }, 100);
        this._bridge.reportReady(info);
        var tries = 0, lastScale = info.scale;
        var timer = root.setInterval(function () {
            tries += 1;
            var curScale = self._bridge.getEffectiveScale();
            if (curScale !== lastScale) {
                lastScale = curScale;
                if (self._curMode) self._bridge.doResize(self._curMode, true);
                self._lastPayload = '';
                self.refresh();
            }
            if (tries >= 5) root.clearInterval(timer);
        }, 700);
    };

    ns.BridgeClass = ns.GamefaceBridge;
    ns.app = new ThreeMarksApp();
    ns.GamefaceBridge.prototype.whenReady.call(null, function () { ns.app.start(); });
}(window));
