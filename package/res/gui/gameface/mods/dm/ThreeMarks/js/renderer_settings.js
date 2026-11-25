(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var U = ns.utils;

    function SettingsRenderer(elSet, elCfg, drawTextFn) {
        this._elSet = elSet;
        this._elCfg = elCfg;
        this._drawText = drawTextFn;
        this._nodes = [];
        this._keys = [];
        this.buildCfg();
    }

    SettingsRenderer.prototype.buildCfg = function () {
        var colors = ['#FF6060', '#86EF6A', '#4FD8FF', '#FFD23C'];
        for (var i = 0; i < 4; i += 1) {
            var d = document.createElement('div');
            d.style.left = ((i % 2) * 9) + 'px';
            d.style.top = (Math.floor(i / 2) * 9) + 'px';
            d.style.background = colors[i];
            this._elCfg.appendChild(d);
        }
    };

    SettingsRenderer.prototype._drawArrow = function (box, color, down) {
        var rows = ns.ARROW_ROWS;
        box.style.width = '10px';
        box.style.height = '9px';
        if (down) box.style.transform = 'scaleY(-1)';
        for (var i = 0; i < rows.length; i += 1) {
            var w = rows[i];
            var r = document.createElement('div');
            r.style.left = ((10 - w) / 2) + 'px';
            r.style.top = i + 'px';
            r.style.width = w + 'px';
            r.style.height = (i < rows.length - 1 ? 2 : 1) + 'px';
            r.style.background = color;
            box.appendChild(r);
        }
    };

    SettingsRenderer.prototype._makeNode = function (it) {
        var d = document.createElement('div');
        d.__t = it.t;
        if (it.t === 'n') d.className = 'tm-run';
        else if (it.t === 'x') d.className = 'tm-live';
        return d;
    };

    SettingsRenderer.prototype._fillNode = function (d, it) {
        d.style.left = U.num(it.x, 0) + 'px';
        d.style.top = U.num(it.y, 0) + 'px';
        if (it.t === 'b') {
            d.style.width = U.num(it.w, 0) + 'px';
            d.style.height = U.num(it.h, 0) + 'px';
            d.style.background = it.bg || '';
            d.style.border = it.bd ? '1px solid ' + it.bd : '';
            d.style.borderRadius = it.r ? it.r + 'px' : '';
        } else if (it.t === 'i') {
            d.style.width = U.num(it.w, 0) + 'px';
            d.style.height = '17px';
            var url = 'url(' + ns.CONST.SET_IMG + it.n + '.png)';
            if (d.__img !== url) { d.__img = url; d.style.backgroundImage = url; }
            d.style.backgroundRepeat = 'no-repeat';
            d.style.opacity = (it.op === undefined) ? 1 : it.op;
        } else if (it.t === 'n') {
            this._drawText(d, String(it.s || ''), it.c || 'white');
        } else if (it.t === 'x') {
            d.textContent = String(it.s || '');
            d.style.color = it.c || '#EAEAEA';
            d.style.width = U.num(it.w, 120) + 'px';
            d.style.height = U.num(it.h, 17) + 'px';
            d.style.fontFamily = 'Warhelios';
            d.style.fontSize = '12px';
            d.style.lineHeight = U.num(it.h, 17) + 'px';
            d.style.whiteSpace = 'nowrap';
            d.style.overflow = 'hidden';
        } else if (it.t === 'a') {
            while (d.firstChild) d.removeChild(d.firstChild);
            d.style.transform = '';
            this._drawArrow(d, it.c || '#FFFFFF', !!it.d);
        }
    };

    SettingsRenderer.prototype.render = function (items) {
        while (this._nodes.length > items.length) {
            this._elSet.removeChild(this._nodes.pop());
            this._keys.pop();
        }
        for (var i = 0; i < items.length; i += 1) {
            var it = items[i];
            var key = JSON.stringify(it);
            if (this._keys[i] === key) continue;
            var d = this._nodes[i];
            if (!d || d.__t !== it.t) {
                var fresh = this._makeNode(it);
                if (d) this._elSet.replaceChild(fresh, d); else this._elSet.appendChild(fresh);
                this._nodes[i] = d = fresh;
            }
            this._fillNode(d, it);
            this._keys[i] = key;
        }
    };

    ns.SettingsRenderer = SettingsRenderer;
}(window));
