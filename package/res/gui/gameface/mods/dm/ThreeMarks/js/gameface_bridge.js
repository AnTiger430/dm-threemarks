(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};

    function GamefaceBridge() {
        this.curScale = 1;
        this.curUi = 1;
        this._lastPxW = 0;
        this._lastPxH = 0;
        this._lastTransform = null;
    }

    GamefaceBridge.prototype.readPayload = function () {
        return (root.model && root.model.payload) ? String(root.model.payload) : '';
    };

    GamefaceBridge.prototype.getEffectiveScale = function () {
        var scale = 1;
        try { scale = Number(viewEnv.getScale()); } catch (e) {}
        if (!isFinite(scale) || scale <= 0) scale = 1;
        return scale * this.curUi;
    };

    GamefaceBridge.prototype.doResize = function (modeKey, force) {
        var scale = this.getEffectiveScale();
        this.curScale = scale;
        var dims = ns.SIZES[modeKey] || ns.SIZES.b;
        var width = Math.max(1, Math.round(dims[0] * scale));
        var height = Math.max(1, Math.round(dims[1] * scale));
        var transform = (modeKey === 'v3' || modeKey === 'bmin' || modeKey === 'bp')
            ? 'none'
            : ((Math.abs(scale - 1) < 0.001) ? 'none' : ('scale(' + scale + ')'));
        if (force || transform !== this._lastTransform) {
            document.body.style.transform = transform;
            document.body.style.transformOrigin = '0 0';
            this._lastTransform = transform;
        }
        var ok = true;
        if (force || width !== this._lastPxW || height !== this._lastPxH) {
            document.documentElement.style.width = width + 'px';
            document.documentElement.style.height = height + 'px';
            document.body.style.width = width + 'px';
            document.body.style.height = height + 'px';
            ok = false;
            try { viewEnv.resizeViewPx(width, height); ok = true; } catch (e) {}
            if (ok) {
                this._lastPxW = width;
                this._lastPxH = height;
            }
        }
        return { scale: scale, width: width, height: height, resized: ok };
    };

    GamefaceBridge.prototype.reportReady = function (info) {
        if (root.model && typeof root.model.onReady === 'function') {
            root.model.onReady({
                message: 'ready scale=' + info.scale + ' view=' + info.width + 'x' + info.height + ' resized=' + info.resized
            });
        }
    };

    GamefaceBridge.prototype.subscribe = function (onDataChanged, onScaleUpdated) {
        if (root.engine) {
            root.engine.on('viewEnv.onDataChanged', onDataChanged);
            root.engine.on('self.onScaleUpdated', onScaleUpdated);
        }
    };

    GamefaceBridge.prototype.whenReady = function (cb) {
        function afterTwoFrames() {
            root.requestAnimationFrame(function () {
                root.requestAnimationFrame(cb);
            });
        }
        if (root.engine && root.engine.whenReady) {
            root.engine.whenReady.then(afterTwoFrames);
        } else {
            afterTwoFrames();
        }
    };

    ns.GamefaceBridge = GamefaceBridge;
}(window));
