(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var U = ns.utils;

    function framePath(x, y, w, h, r, gapSide, g0, g1, scale) {
        var sc = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        r = Math.max(0, Math.min(r, Math.min(w, h) * 0.45));
        var x0 = x, y0 = y, x1 = x + w, y1 = y + h, pad = 2 * sc;
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
        if (gapSide === 'top' || gapSide === 'bottom') {
            g0 = Math.max(x0 + r + pad, Math.min(x1 - r - pad * 2, g0));
            g1 = Math.max(g0 + pad, Math.min(x1 - r - pad, g1));
            if (gapSide === 'top') {
                return 'M ' + g1.toFixed(1) + ' ' + y0.toFixed(1) + ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                    ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) + ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
                    ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) + ' H ' + g0.toFixed(1);
            }
            return 'M ' + g0.toFixed(1) + ' ' + y1.toFixed(1) + ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) +
                ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) + ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) +
                ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) + ' H ' + g1.toFixed(1);
        }
        g0 = Math.max(y0 + r + pad, Math.min(y1 - r - pad * 2, g0));
        g1 = Math.max(g0 + pad, Math.min(y1 - r - pad, g1));
        if (gapSide === 'left') {
            return 'M ' + x0.toFixed(1) + ' ' + g0.toFixed(1) + ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) +
                ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) + ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
                ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) + ' V ' + g1.toFixed(1);
        }
        return 'M ' + x1.toFixed(1) + ' ' + g1.toFixed(1) + ' V ' + (y1 - r).toFixed(1) + arc(x1 - r, y1) +
            ' H ' + (x0 + r).toFixed(1) + arc(x0, y1 - r) + ' V ' + (y0 + r).toFixed(1) + arc(x0 + r, y0) +
            ' H ' + (x1 - r).toFixed(1) + arc(x1, y0 + r) + ' V ' + g0.toFixed(1);
    }

    function cornersPaths(x, y, w, h, r, scale) {
        var sc = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        r = Math.max(0, Math.min(r, Math.min(w, h) * 0.45));
        var arm = Math.max(r + 4 * sc, Math.min(10 * sc, Math.min(w, h) * 0.22));
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

    var SVG_NS = 'http://www.w3.org/2000/svg';

    function createSvgEl(tag, attrs) {
        var el = document.createElementNS ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
        if (attrs && typeof el.setAttribute === 'function') {
            for (var k in attrs) {
                if (Object.prototype.hasOwnProperty.call(attrs, k)) {
                    el.setAttribute(k, String(attrs[k]));
                }
            }
        }
        return el;
    }

    function mountSvg(container, widthPx, heightPx, vbW, vbH, specs) {
        while (container.firstChild) container.removeChild(container.firstChild);
        var svg = createSvgEl('svg', {
            xmlns: SVG_NS,
            width: widthPx,
            height: heightPx,
            viewBox: '0 0 ' + vbW + ' ' + vbH
        });
        if (svg.style) {
            svg.style.display = 'block';
            svg.style.width = widthPx + 'px';
            svg.style.height = heightPx + 'px';
        }
        for (var i = 0; i < specs.length; i += 1) {
            svg.appendChild(createSvgEl(specs[i].tag, specs[i].attrs));
        }
        container.appendChild(svg);
        return svg;
    }

    function specsToStr(specs) {
        var out = [], i, k, attrs;
        for (i = 0; i < specs.length; i += 1) {
            attrs = [];
            for (k in specs[i].attrs) {
                if (Object.prototype.hasOwnProperty.call(specs[i].attrs, k)) {
                    attrs.push(k + '="' + specs[i].attrs[k] + '"');
                }
            }
            out.push('<' + specs[i].tag + ' ' + attrs.join(' ') + '/>');
        }
        return out.join('');
    }

    var SS = 2;

    function getCanvasCtx(container, cssW, cssH) {
        try {
            var cv = (container.firstChild && container.firstChild.tagName && String(container.firstChild.tagName).toLowerCase() === 'canvas')
                ? container.firstChild : null;
            if (!cv) {
                cv = document.createElement('canvas');
                if (typeof cv.getContext !== 'function') return null;
            }
            var ctx = cv.getContext('2d');
            if (!ctx) return null;
            if (cv.parentNode !== container) {
                while (container.firstChild) container.removeChild(container.firstChild);
                container.appendChild(cv);
            }
            cv.width = Math.max(1, Math.round(cssW * SS));
            cv.height = Math.max(1, Math.round(cssH * SS));
            if (cv.style) {
                cv.style.display = 'block';
                cv.style.width = cssW + 'px';
                cv.style.height = cssH + 'px';
            }
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, cv.width, cv.height);
            return ctx;
        } catch (e) {
            return null;
        }
    }

    function starSpecs(cx, cy, r, earned, style, onCol, offCol, glow, scale) {
        var sc = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        var pts = [], inner = r * 0.43;
        for (var i = 0; i < 10; i += 1) {
            var ang = -Math.PI * 0.5 + i * Math.PI * 0.2;
            var rad = (i % 2 === 0) ? r : inner;
            pts.push((cx + rad * Math.cos(ang)).toFixed(2) + ',' + (cy + rad * Math.sin(ang)).toFixed(2));
        }
        var pstr = pts.join(' ');
        if (earned) {
            var fill = (style === 2) ? '#FFD23C' : onCol;
            var out = [];
            if (glow) {
                out.push({
                    tag: 'polygon',
                    attrs: { points: pstr, fill: fill, 'fill-opacity': '0.24', stroke: fill, 'stroke-width': (2.0 * sc).toFixed(2), 'stroke-opacity': '0.22', 'stroke-linejoin': 'round' }
                });
            }
            out.push({ tag: 'polygon', attrs: { points: pstr, fill: fill, 'fill-opacity': '0.96', 'stroke-linejoin': 'round' } });
            return out;
        }
        if (style === 1) {
            return [{ tag: 'polygon', attrs: { points: pstr, fill: offCol, 'fill-opacity': '0.50' } }];
        }
        return [{
            tag: 'polygon',
            attrs: { points: pstr, fill: offCol, 'fill-opacity': '0.10', stroke: offCol, 'stroke-width': (1.15 * sc).toFixed(2), 'stroke-opacity': '0.55', 'stroke-linejoin': 'round' }
        }];
    }

    function traceStar(ctx, cx, cy, r) {
        var inner = r * 0.43;
        ctx.beginPath();
        for (var i = 0; i < 10; i += 1) {
            var ang = -Math.PI * 0.5 + i * Math.PI * 0.2;
            var rad = (i % 2 === 0) ? r : inner;
            var px = cx + rad * Math.cos(ang), py = cy + rad * Math.sin(ang);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();
    }

    function mountStarsCanvas(container, starsList, rPx, style, onCol, offCol, glow, scale) {
        if (!container) return false;
        if (!starsList || !starsList.length) {
            if (container.style) container.style.display = 'none';
            return true;
        }
        var sc = (typeof scale === 'number' && isFinite(scale) && scale > 0) ? scale : 1;
        var pad = Math.ceil(rPx + 4 * sc), minX = starsList[0][0], maxX = minX, minY = starsList[0][1], maxY = minY;
        for (var i = 1; i < starsList.length; i += 1) {
            if (starsList[i][0] < minX) minX = starsList[i][0];
            if (starsList[i][0] > maxX) maxX = starsList[i][0];
            if (starsList[i][1] < minY) minY = starsList[i][1];
            if (starsList[i][1] > maxY) maxY = starsList[i][1];
        }
        var x0 = Math.floor(minX - pad), y0 = Math.floor(minY - pad);
        var boxW = Math.max(1, Math.ceil(maxX + pad) - x0), boxH = Math.max(1, Math.ceil(maxY + pad) - y0);
        var ctx = getCanvasCtx(container, boxW, boxH);
        if (!ctx) {
            if (container.style) container.style.display = 'none';
            return false;
        }
        if (container.style) {
            container.style.display = 'block';
            container.style.left = x0 + 'px';
            container.style.top = y0 + 'px';
            container.style.width = boxW + 'px';
            container.style.height = boxH + 'px';
        }
        ctx.save();
        ctx.scale(SS, SS);
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        for (var k = 0; k < starsList.length; k += 1) {
            var sx = starsList[k][0] - x0, sy = starsList[k][1] - y0, earned = !!starsList[k][2];
            traceStar(ctx, sx, sy, rPx);
            if (earned) {
                var fill = (style === 2) ? '#FFD23C' : onCol;
                if (glow) {
                    ctx.globalAlpha = 0.24; ctx.fillStyle = fill; ctx.fill();
                    ctx.globalAlpha = 0.22; ctx.strokeStyle = fill; ctx.lineWidth = 2.0 * sc; ctx.stroke();
                }
                ctx.globalAlpha = 0.96; ctx.fillStyle = fill; ctx.fill();
            } else if (style === 1) {
                ctx.globalAlpha = 0.50; ctx.fillStyle = offCol; ctx.fill();
            } else {
                ctx.globalAlpha = 0.10; ctx.fillStyle = offCol; ctx.fill();
                ctx.globalAlpha = 0.55; ctx.strokeStyle = offCol; ctx.lineWidth = 1.15 * sc; ctx.stroke();
            }
        }
        ctx.restore();
        return true;
    }

    function starSvg(cx, cy, r, earned, style, onCol, offCol, glow) {
        return specsToStr(starSpecs(cx, cy, r, earned, style, onCol, offCol, glow));
    }

    function deltaDir(state) {
        if (state === true || state === 'down') return 'down';
        if (state === 'zero') return 'zero';
        return 'up';
    }

    function deltaSpecs(kind, state, color) {
        var dir = deltaDir(state);
        if (kind === 0) {
            var pts = dir === 'zero' ? '5.5,1.5 9.5,5.5 5.5,9.5 1.5,5.5' : (dir === 'down' ? '0,1 10,1 5,10' : '5,1 10,10 0,10');
            return [{ tag: 'polygon', attrs: { points: pts, fill: color, 'stroke-linejoin': 'round' } }];
        }
        if (kind === 1) {
            var pathD = dir === 'zero'
                ? 'M 1.5 5.5 L 9.5 5.5 M 6.0 2.0 L 9.5 5.5 L 6.0 9.0'
                : (dir === 'down'
                    ? 'M 1.5 1.5 L 9.5 9.5 M 4.5 9.5 L 9.5 9.5 L 9.5 4.5'
                    : 'M 1.5 9.5 L 9.5 1.5 M 4.5 1.5 L 9.5 1.5 L 9.5 6.5');
            return [{
                tag: 'path',
                attrs: {
                    d: pathD,
                    fill: 'none', stroke: color, 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'
                }
            }];
        }
        return [];
    }

    function deltaIconUri(cache, kind, state, color) {
        var dir = deltaDir(state);
        var key = 'd|' + kind + '|' + dir + '|' + color;
        if (cache[key]) return cache[key];
        cache[key] = U.svgUri('<svg xmlns="' + SVG_NS + '" width="11" height="11" viewBox="0 0 11 11">' + specsToStr(deltaSpecs(kind, dir, color)) + '</svg>');
        return cache[key];
    }

    function mountDeltaIcon(container, kind, state, color, sizePx) {
        var s = Math.max(1, Math.round(sizePx || 11));
        var dir = deltaDir(state);
        var key = 'd|' + kind + '|' + dir + '|' + color + '|' + s;
        if (container._svgKey === key) return;
        container._svgKey = key;
        var ctx = getCanvasCtx(container, s, s);
        if (ctx) {
            ctx.save();
            ctx.scale(SS * s / 11.0, SS * s / 11.0);
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            if (kind === 0) {
                var poly = dir === 'zero' ? [[5.5, 1.5], [9.5, 5.5], [5.5, 9.5], [1.5, 5.5]]
                    : (dir === 'down' ? [[0, 1], [10, 1], [5, 10]] : [[5, 1], [10, 10], [0, 10]]);
                ctx.beginPath();
                for (var pi = 0; pi < poly.length; pi += 1) {
                    if (pi === 0) ctx.moveTo(poly[pi][0], poly[pi][1]);
                    else ctx.lineTo(poly[pi][0], poly[pi][1]);
                }
                ctx.closePath();
                ctx.fillStyle = color;
                ctx.fill();
            } else if (kind === 1) {
                ctx.beginPath();
                if (dir === 'zero') {
                    ctx.moveTo(1.5, 5.5); ctx.lineTo(9.5, 5.5);
                    ctx.moveTo(6.0, 2.0); ctx.lineTo(9.5, 5.5); ctx.lineTo(6.0, 9.0);
                } else if (dir === 'down') {
                    ctx.moveTo(1.5, 1.5); ctx.lineTo(9.5, 9.5);
                    ctx.moveTo(4.5, 9.5); ctx.lineTo(9.5, 9.5); ctx.lineTo(9.5, 4.5);
                } else {
                    ctx.moveTo(1.5, 9.5); ctx.lineTo(9.5, 1.5);
                    ctx.moveTo(4.5, 1.5); ctx.lineTo(9.5, 1.5); ctx.lineTo(9.5, 6.5);
                }
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.8;
                ctx.stroke();
            }
            ctx.restore();
            return;
        }
        mountSvg(container, s, s, 11, 11, deltaSpecs(kind, dir, color));
    }

    function assistSpecs(ch, s, color, opacity) {
        var sc = s / 16.0, cx = s * 0.5, cy = s * 0.5;
        if (ch === 'spot') {
            var r1 = 3.5 * sc, dx1 = 2.68 * sc, dy1 = 2.25 * sc;
            var r2 = 5.8 * sc, dx2 = 4.31 * sc, dy2 = 3.88 * sc;
            var arcD = 'M ' + (cx - dx1).toFixed(2) + ' ' + (cy - dy1).toFixed(2) + ' A ' + r1.toFixed(2) + ' ' + r1.toFixed(2) + ' 0 0 0 ' + (cx - dx1).toFixed(2) + ' ' + (cy + dy1).toFixed(2) +
                ' M ' + (cx - dx2).toFixed(2) + ' ' + (cy - dy2).toFixed(2) + ' A ' + r2.toFixed(2) + ' ' + r2.toFixed(2) + ' 0 0 0 ' + (cx - dx2).toFixed(2) + ' ' + (cy + dy2).toFixed(2) +
                ' M ' + (cx + dx1).toFixed(2) + ' ' + (cy - dy1).toFixed(2) + ' A ' + r1.toFixed(2) + ' ' + r1.toFixed(2) + ' 0 0 1 ' + (cx + dx1).toFixed(2) + ' ' + (cy + dy1).toFixed(2) +
                ' M ' + (cx + dx2).toFixed(2) + ' ' + (cy - dy2).toFixed(2) + ' A ' + r2.toFixed(2) + ' ' + r2.toFixed(2) + ' 0 0 1 ' + (cx + dx2).toFixed(2) + ' ' + (cy + dy2).toFixed(2);
            return [
                { tag: 'circle', attrs: { cx: cx.toFixed(2), cy: cy.toFixed(2), r: (1.45 * sc).toFixed(2), fill: color, 'fill-opacity': opacity.toFixed(2) } },
                { tag: 'path', attrs: { d: arcD, fill: 'none', stroke: color, 'stroke-width': (1.25 * sc).toFixed(2), 'stroke-linecap': 'round', 'stroke-opacity': opacity.toFixed(2) } }
            ];
        }
        if (ch === 'track') {
            var ca = Math.cos(Math.PI * 0.25), sa = Math.sin(Math.PI * 0.25);
            function rot(dx, dy) { return [cx + (dx * ca - dy * sa) * sc, cy + (dx * sa + dy * ca) * sc]; }
            var poly = [
                [-2.62, -1.65], [2.62, -1.65], [2.62, -0.36], [5.20, -0.36],
                [5.20, 1.42], [2.15, 1.42], [2.15, 0.05], [-2.15, 0.05],
                [-2.15, 1.42], [-5.20, 1.42], [-5.20, -0.36], [-2.62, -0.36]
            ];
            var offs = [-4.40, -0.40, 3.60];
            var parts = [], oi, vi, cmds, pt;
            for (oi = 0; oi < offs.length; oi += 1) {
                cmds = [];
                for (vi = 0; vi < poly.length; vi += 1) {
                    pt = rot(poly[vi][0], poly[vi][1] + offs[oi]);
                    cmds.push((vi === 0 ? 'M ' : 'L ') + pt[0].toFixed(2) + ' ' + pt[1].toFixed(2));
                }
                parts.push(cmds.join(' ') + ' Z');
            }
            return [{ tag: 'path', attrs: { d: parts.join(' '), fill: color, 'fill-opacity': opacity.toFixed(2) } }];
        }
        return [];
    }

    function assistIconUri(cache, ch, size, color, opacity) {
        var s = Math.round(size);
        var key = 'a|' + ch + '|' + s + '|' + color + '|' + opacity.toFixed(2);
        if (cache[key]) return cache[key];
        cache[key] = U.svgUri('<svg xmlns="' + SVG_NS + '" width="' + s + '" height="' + s + '" viewBox="0 0 ' + s + ' ' + s + '">' + specsToStr(assistSpecs(ch, s, color, opacity)) + '</svg>');
        return cache[key];
    }

    function mountAssistIcon(container, ch, sizePx, color, opacity) {
        var s = Math.max(1, Math.round(sizePx));
        var key = 'a|' + ch + '|' + s + '|' + color + '|' + opacity.toFixed(2);
        if (container._svgKey === key) return;
        container._svgKey = key;
        var ctx = getCanvasCtx(container, s, s);
        if (ctx) {
            var sc = s / 16.0, cx = s * 0.5, cy = s * 0.5;
            ctx.save();
            ctx.scale(SS, SS);
            ctx.globalAlpha = opacity;
            ctx.fillStyle = color;
            ctx.strokeStyle = color;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            if (ch === 'spot') {
                ctx.beginPath();
                ctx.arc(cx, cy, 1.45 * sc, 0, Math.PI * 2);
                ctx.fill();
                ctx.lineWidth = 1.25 * sc;
                var a0 = 0.698;
                ctx.beginPath();
                ctx.arc(cx, cy, 3.5 * sc, Math.PI - a0, Math.PI + a0);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(cx, cy, 5.8 * sc, Math.PI - a0, Math.PI + a0);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(cx, cy, 3.5 * sc, -a0, a0);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(cx, cy, 5.8 * sc, -a0, a0);
                ctx.stroke();
            } else if (ch === 'track') {
                var ca = Math.cos(Math.PI * 0.25), sa = Math.sin(Math.PI * 0.25);
                var poly = [
                    [-2.62, -1.65], [2.62, -1.65], [2.62, -0.36], [5.20, -0.36],
                    [5.20, 1.42], [2.15, 1.42], [2.15, 0.05], [-2.15, 0.05],
                    [-2.15, 1.42], [-5.20, 1.42], [-5.20, -0.36], [-2.62, -0.36]
                ];
                var offs = [-4.40, -0.40, 3.60];
                for (var oi = 0; oi < offs.length; oi += 1) {
                    ctx.beginPath();
                    for (var vi = 0; vi < poly.length; vi += 1) {
                        var px = cx + (poly[vi][0] * ca - (poly[vi][1] + offs[oi]) * sa) * sc;
                        var py = cy + (poly[vi][0] * sa + (poly[vi][1] + offs[oi]) * ca) * sc;
                        if (vi === 0) ctx.moveTo(px, py);
                        else ctx.lineTo(px, py);
                    }
                    ctx.closePath();
                    ctx.fill();
                }
            }
            ctx.restore();
            return;
        }
        mountSvg(container, s, s, s, s, assistSpecs(ch, s, color, opacity));
    }

    ns.v3Svg = {
        framePath: framePath,
        cornersPaths: cornersPaths,
        mountSvg: mountSvg,
        starSpecs: starSpecs,
        starSvg: starSvg,
        mountStarsCanvas: mountStarsCanvas,
        deltaIconUri: deltaIconUri,
        mountDeltaIcon: mountDeltaIcon,
        assistIconUri: assistIconUri,
        mountAssistIcon: mountAssistIcon
    };
}(window));
