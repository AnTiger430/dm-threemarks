(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};
    var U = ns.utils;

    function v3ResolveAssist(v, d) {
        var spot = Math.max(0, Math.round(U.num(d.spot, 0)));
        var track = Math.max(0, Math.round(U.num(d.track, 0)));
        var maxAst = Math.max(spot, track);
        var activeCh = (spot > track) ? 'spot' : ((track > spot) ? 'track' : null);
        var alt = !!d.alt;
        var showMode = U.v3Int(v, 'ash', 0, 3);
        var rawMode = U.v3Int(v, 'am', 0, 1);
        if (showMode === 3 || (showMode === 1 && !alt) || (showMode === 2 && alt)) {
            return { items: [], activeCh: activeCh, maxAst: maxAst, altExp: false };
        }
        var rows = (rawMode === 0) ? [['spot', spot], ['track', track]] : [[activeCh || 'spot', maxAst]];
        if (v.ahz) {
            var filtered = [];
            for (var i = 0; i < rows.length; i += 1) {
                if (rows[i][1] > 0) filtered.push(rows[i]);
            }
            rows = filtered;
        }
        var sep = U.v3Int(v, 'sep', 0, 2);
        var items = [];
        for (var j = 0; j < rows.length; j += 1) {
            var ch = rows[j][0], val = rows[j][1];
            items.push({ ch: ch, val: val, active: (ch === activeCh && val > 0), text: U.v3FmtNum(val, sep) });
        }
        return { items: items, activeCh: activeCh, maxAst: maxAst, altExp: false };
    }

    function v3ResolveTempo(v, d) {
        var alt = !!d.alt;
        var showMode = U.v3Int(v, 'tsh', 0, 3);
        var rawMode = U.v3Int(v, 'tmm', 0, 2);
        if (showMode === 3 || (showMode === 1 && !alt) || (showMode === 2 && alt)) {
            return [];
        }
        var pct = U.num(d.pct, 0);
        var tNextPct = Math.round(U.num(d.tNextPct, 0)) || (pct < 65 ? 65 : (pct < 85 ? 85 : (pct < 95 ? 95 : 100)));
        var tNext = Math.max(0, Math.round(U.num(d.tNext, 0)));
        var t95 = Math.max(0, Math.round(U.num(d.t95, 0)));
        var dmg = Math.max(0, Math.round(U.num(d.dmg, 0)));
        var pairs;
        if (rawMode === 1) pairs = [[tNextPct, tNext]];
        else if (rawMode === 2) pairs = [[95, t95]];
        else if (tNextPct === 95) pairs = [[95, t95 > 0 ? t95 : tNext]];
        else if (tNextPct < 95) pairs = [[tNextPct, tNext], [95, t95]];
        else pairs = [[95, t95], [100, tNext]];

        var sep = U.v3Int(v, 'sep', 0, 2);
        var items = [];
        for (var i = 0; i < pairs.length; i += 1) {
            var pLbl = pairs[i][0], val = pairs[i][1];
            var valStr = val > 0 ? U.v3FmtNum(val, sep) : '\u2014';
            var lbl = pLbl + '%';
            items.push({ pct: pLbl, val: val, done: (val > 0 && dmg >= val), lbl: lbl, valStr: valStr, text: lbl + ' ' + valStr });
        }
        return items;
    }

    function v3ResolveHangarRows(v, d) {
        if (!d.isHangar || d.mini || v.hThr === false) return [];
        var sep = U.v3Int(v, 'sep', 0, 2);
        var hasRating = (d.hasRating !== false);
        var pct = U.num(d.pct, 0);
        var marks = Math.max(0, Math.round(U.num(d.marks, 0)));
        function mkCell(pLbl, key, reqMarks) {
            var val = Math.max(0, Math.round(U.num(d[key], 0)));
            var valStr = (hasRating && val > 0 && val < 30000) ? U.v3FmtNum(val, sep) : '\u2014';
            var lbl = pLbl + '%';
            var done = (reqMarks > 0 && hasRating && val > 0 && (marks >= reqMarks || pct >= pLbl));
            return { pct: pLbl, val: val, done: done, lbl: lbl, valStr: valStr, text: lbl + ' ' + valStr };
        }
        return [[mkCell(65, 't65', 1), mkCell(85, 't85', 2)], [mkCell(95, 't95', 3), mkCell(100, 't100', 0)]];
    }

    function v3DeltaInfo(v, d, u) {
        var hasRating = (d.hasRating !== false);
        var pct = U.num(d.pct, 0);
        var dec = (U.v3Int(v, 'dec', 0, 1) === 0) ? 0 : 2;
        if (!hasRating) {
            return { pctText: dec === 0 ? '--%' : '--.--%', deltaText: '', kind: 'zero', accent: v.zr, showDelta: false, down: false };
        }
        var pctText = pct.toFixed(dec) + '%';
        var rawDelta = d.delta;
        if (rawDelta === undefined || rawDelta === null || !isFinite(Number(rawDelta))) {
            return { pctText: pctText, deltaText: '', kind: 'zero', accent: v.zr, showDelta: false, down: false };
        }
        var val = Number(rawDelta);
        var zeroBand = U.num(u.band, 0.02);
        var bigByDmg = !!u.bigDmg;
        var bigFrom = U.num(u.bigFrom, 4);
        var kind;
        if (bigByDmg && d.big && val >= 0) kind = 'big';
        else if (!bigByDmg && bigFrom > 0 && val >= bigFrom) kind = 'big';
        else if (Math.abs(val) <= zeroBand) kind = 'zero';
        else if (val < 0) kind = 'minus';
        else kind = 'plus';
        var accents = { plus: v.up, minus: v.dn, zero: v.zr, big: v.big };
        var nearZero = Math.abs(val) < (dec === 0 ? 0.5 : 0.005);
        var dispVal = nearZero ? 0 : val;
        var sign = (nearZero || val < 0) ? '' : '+';
        var dir = (kind === 'minus') ? 'down' : ((kind === 'zero') ? 'zero' : 'up');
        return {
            pctText: pctText,
            deltaText: sign + dispVal.toFixed(dec) + '%',
            kind: kind,
            dir: dir,
            accent: accents[kind],
            showDelta: (U.v3Int(v, 'di', 0, 3) !== 3),
            down: (val < 0)
        };
    }

    function v3TargetInfo(v, d) {
        var dmg = Math.max(0, Math.round(U.num(d.dmg, 0)));
        var tgt = Math.max(0, Math.round(U.num(d.tHold, 0)));
        var sep = U.v3Int(v, 'sep', 0, 2);
        return {
            dmg: dmg, tgt: tgt,
            dmgStr: U.v3FmtNum(dmg, sep),
            tgtStr: tgt > 0 ? U.v3FmtNum(tgt, sep) : '\u2014',
            remStr: tgt > 0 ? U.v3FmtNum(Math.max(0, tgt - dmg), sep) : '\u2014'
        };
    }

    function v3BarRatio(v, d) {
        var pct = U.clamp(U.num(d.bar !== undefined ? d.bar : d.pct, 0), 0, 100);
        if (U.v3Int(v, 'bsc', 0, 1) === 1) {
            if (pct < 65) return pct / 65;
            if (pct < 85) return (pct - 65) / 20;
            if (pct < 95) return (pct - 85) / 10;
            return (pct - 95) / 5;
        }
        return pct / 100;
    }

    function v3BarColor(v, deltaAccent) {
        var mode = U.v3Int(v, 'bcm', 0, 2);
        if (mode === 1) return deltaAccent;
        if (mode === 2) return v.bcc;
        return v.up;
    }

    function v3ComputeMetrics(v, d, u) {
        var isHangar = !!d.isHangar;
        var fnt = U.v3Int(v, 'fnt', 0, 7);
        var fScale = (ns.V3_FONT_SCALES && ns.V3_FONT_SCALES[fnt]) || 1.0;
        var den = U.v3Int(v, 'den', 0, 2);
        var spec = [[10, 7, 4, 24, 14, 13, 13], [12, 9, 6, 26, 15, 14, 14], [15, 11, 8, 28, 16, 15, 15]][den];
        var padX = spec[0], padY = spec[1], gapRow = spec[2];
        var pctSize = spec[3], deltaSize = spec[4], dmgSize = spec[5], astSize = spec[6];

        var dInfo = v3DeltaInfo(v, d, u);
        if (isHangar) dInfo.showDelta = false;
        var tInfo = v3TargetInfo(v, d);
        if (isHangar && !(d.hasRating !== false && tInfo.dmg > 0)) tInfo.dmgStr = '\u2014';

        var ast = isHangar ? { items: [], activeCh: null, maxAst: 0, altExp: false } : v3ResolveAssist(v, d);
        var thr = isHangar ? [] : v3ResolveTempo(v, d);
        var hRows = isHangar ? v3ResolveHangarRows(v, d) : [];

        var frameStyle = U.v3Int(v, 'fs', 0, 3);
        var starsPos = U.v3Int(v, 'sp', 0, 5);
        var starsDiv = !!v.sd;
        var starSize = U.v3Int(v, 'sz', 10, 22);
        var starGap = U.v3Int(v, 'sg', 2, 14);
        var starsSpan = 3 * starSize + 2 * starGap;

        var di = U.v3Int(v, 'di', 0, 3);
        var deltaIconW = (dInfo.showDelta && (di === 0 || di === 1)) ? 12 : 0;
        var pctW = U.v3Advance(dInfo.pctText, pctSize, fScale);
        var headerPctW = pctW;
        if (isHangar) {
            var pctDec = (U.v3Int(v, 'dec', 0, 1) === 0) ? 0 : 2;
            headerPctW = Math.max(pctW, U.v3Advance(pctDec === 0 ? '100%' : '100.00%', pctSize, fScale));
        }
        var deltaW = dInfo.showDelta ? (U.v3Advance(dInfo.deltaText, deltaSize, fScale) + (deltaIconW > 0 ? deltaIconW + 5 : 0)) : 0;
        var headerMinW = headerPctW + deltaW + ((dInfo.showDelta && pctW > 0) ? 14 : 0) + ((starsPos === 4) ? (starsSpan + 10) : 0);

        var showDmg = !!v.dmgOn;
        var dmgLblMode = U.v3Int(v, 'dl', 0, 3);
        var dmgLblText = isHangar ? '\u0421\u0443\u043c\u043c\u0430\u0440\u043d\u044b\u0439 \u0443\u0440\u043e\u043d' : (dmgLblMode === 0 ? '\u0421\u0443\u043c. \u0443\u0440\u043e\u043d' : (dmgLblMode === 1 ? String(v.dlc || '').replace(/[\r\n]/g, ' ').slice(0, 24) : ''));
        var dmgValStr = isHangar ? tInfo.dmgStr : (tInfo.dmgStr + ' / ' + tInfo.tgtStr);
        var barMinW = [156, 178, 200][den];
        var maxAutoTextW = barMinW + 80;
        var rawLblW = dmgLblText ? U.v3Advance(dmgLblText, dmgSize, fScale) : 0;
        var hSep = U.v3Int(v, 'sep', 0, 2);
        var hSampleNum = isHangar ? U.v3FmtNum(9999, hSep) : '';
        var dmgValW = showDmg ? U.v3Advance(dmgValStr, dmgSize, fScale) : 0;
        if (isHangar && showDmg) {
            dmgValW = Math.max(dmgValW, U.v3Advance(hSampleNum, dmgSize, fScale));
        }
        var rawDmgRowW = showDmg ? (rawLblW + (rawLblW > 0 ? 12 : 0) + dmgValW) : 0;
        var dmgRowMinW = (showDmg && !isHangar && dmgLblMode === 1) ? Math.min(rawDmgRowW, maxAutoTextW) : rawDmgRowW;

        var astInside = (U.v3Int(v, 'ap', 0, 1) === 0);
        var astItemGap = ast.items.length <= 2 ? 18 : 11;
        var thrInside = (U.v3Int(v, 'tp', 0, 1) === 0);
        var thrItemGap = 14;
        var baseAst = astSize;
        var baseThr = Math.max(11, baseAst - 1);

        var barStyle = U.v3Int(v, 'bs', 0, 3);
        var barH = U.v3Int(v, 'bh', 2, 10);
        var trackH = U.v3Int(v, 'bth', 1, 10);
        var barText = (barStyle === 3) ? (String(v.bt || '').replace(/[\r\n]/g, ' ').slice(0, 24) || 'KIBERSPORT') : '';
        var reqBarTextSize = U.v3Int(v, 'bts', 10, 26);
        var rawBarTextW = (barStyle === 3) ? U.v3Advance(barText, reqBarTextSize, fScale) : 0;
        var barTextMinW = (barStyle === 3) ? Math.ceil(Math.min(rawBarTextW + 8, maxAutoTextW)) : 0;

        var hCol0W = 0, hCol1W = 0, hColGap = 16;
        if (hRows && hRows.length >= 2) {
            var hValMinW = U.v3Advance(hSampleNum, baseThr, fScale);
            hCol0W = Math.ceil(U.v3Advance('95%', baseThr, fScale)) + 8 + Math.ceil(Math.max(hValMinW, U.v3Advance(hRows[0][0].valStr, baseThr, fScale), U.v3Advance(hRows[1][0].valStr, baseThr, fScale)));
            hCol1W = Math.ceil(U.v3Advance('100%', baseThr, fScale)) + 8 + Math.ceil(Math.max(hValMinW, U.v3Advance(hRows[0][1].valStr, baseThr, fScale), U.v3Advance(hRows[1][1].valStr, baseThr, fScale)));
        }
        var hGridMinW = (hRows && hRows.length >= 2) ? (hCol0W + hColGap + hCol1W) : 0;

        var extraW = U.v3Int(v, 'minW', 0, 200);
        var minBracket = Math.max(12, U.v3Int(v, 'rad', 0, 14) + 8);
        var starsMinFrameW = ((starsPos === 0 || starsPos === 1) && frameStyle !== 3) ? (starsSpan + 12 + 2 * minBracket) : ((starsPos === 0 || starsPos === 1) ? (starsSpan + 8) : 0);
        var baseCw = Math.ceil(Math.max(barMinW, barTextMinW, headerMinW, dmgRowMinW, hGridMinW, starsMinFrameW - 2 * padX));
        var cw = baseCw + extraW;

        var barTextSize = reqBarTextSize, barTextW = rawBarTextW;
        if (barStyle === 3) {
            var availBarW = Math.max(20, cw - 6);
            if (barTextW > availBarW) {
                barTextSize = Math.max(8, Math.floor(reqBarTextSize * (availBarW / barTextW)));
                barTextW = U.v3Advance(barText, barTextSize, fScale);
                while (barTextSize > 8 && barTextW > availBarW) {
                    barTextSize -= 1;
                    barTextW = U.v3Advance(barText, barTextSize, fScale);
                }
            }
        }
        var dmgLblSize = dmgSize;
        if (showDmg && dmgLblText) {
            var availLblW = Math.max(20, cw - dmgValW - 10);
            if (rawLblW > availLblW) {
                dmgLblSize = Math.max(8, Math.floor(dmgSize * (availLblW / rawLblW)));
                while (dmgLblSize > 8 && U.v3Advance(dmgLblText, dmgLblSize, fScale) > availLblW) {
                    dmgLblSize -= 1;
                }
            }
        }

        var widthScale = Math.max(1.0, Math.min(1.65, cw / barMinW));
        var rawAst = U.v3Int(v, 'asz', 0, 24);
        if (rawAst > 0) {
            astSize = Math.max(10, Math.min(24, rawAst));
        } else {
            astSize = Math.round(baseAst * widthScale);
            if (ast.items.length && astInside) {
                while (astSize > baseAst) {
                    var icoS = Math.max(12, astSize + 1), sumCheck = 0;
                    for (var ci = 0; ci < ast.items.length; ci += 1) sumCheck += icoS + 5 + U.v3Advance(ast.items[ci].text, astSize, fScale);
                    if (sumCheck + Math.max(0, ast.items.length - 1) * astItemGap <= cw) break;
                    astSize -= 1;
                }
            }
        }
        var astIconSize = Math.max(12, astSize + 1);
        var astWidths = [], sumAstW = 0;
        for (var ai = 0; ai < ast.items.length; ai += 1) {
            var aw = astIconSize + 5 + U.v3Advance(ast.items[ai].text, astSize, fScale);
            astWidths.push(aw);
            sumAstW += aw;
        }
        var astRowMinW = astWidths.length ? (sumAstW + Math.max(0, astWidths.length - 1) * astItemGap) : 0;

        var thrSize;
        if (isHangar) {
            thrSize = baseThr;
        } else {
            var rawThr = U.v3Int(v, 'tsz', 0, 24);
            if (rawThr > 0) {
                thrSize = Math.max(10, Math.min(24, rawThr));
            } else {
                thrSize = Math.round(baseThr * widthScale);
                if (thr.length && thrInside) {
                    while (thrSize > baseThr) {
                        var tSumCheck = 0;
                        for (var tci = 0; tci < thr.length; tci += 1) tSumCheck += U.v3Advance(thr[tci].text, thrSize, fScale);
                        if (tSumCheck + Math.max(0, thr.length - 1) * thrItemGap <= cw) break;
                        thrSize -= 1;
                    }
                }
            }
        }
        var thrWidths = [], sumThrW = 0;
        for (var ti = 0; ti < thr.length; ti += 1) {
            var tw = U.v3Advance(thr[ti].text, thrSize, fScale);
            thrWidths.push(tw);
            sumThrW += tw;
        }
        var thrRowMinW = thrWidths.length ? (sumThrW + Math.max(0, thrWidths.length - 1) * thrItemGap) : 0;

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

        var effBarH = Math.max(barH, trackH), barY = null, barBlockH = 0;
        if (barStyle === 3) {
            y += gapRow;
            barY = y;
            barBlockH = Math.round(barTextSize * 1.18);
            y += barBlockH;
        } else if (barStyle !== 2) {
            y += gapRow;
            barY = y;
            barBlockH = Math.max(effBarH, v.bcur ? 10 : effBarH, (barStyle === 0 && v.bet) ? 8 : effBarH);
            y += barBlockH;
        }

        var dmgY = null, dmgH = Math.round(dmgSize * 1.25);
        if (showDmg) { y += gapRow; dmgY = y; y += dmgH; }

        var astY = null, astH = Math.max(astSize + 2, astIconSize);
        if (ast.items.length && astInside) { y += gapRow + 1; astY = y; y += astH; }

        var thrY = null, thrH = thrSize + 2;
        if (thr.length && thrInside) { y += (astY !== null) ? gapRow : (gapRow + 1); thrY = y; y += thrH; }

        var hSepY = null, hRow1Y = null, hRow2Y = null;
        if (hRows.length) { y += gapRow + 1; hSepY = y; y += gapRow; hRow1Y = y; y += thrH + 2; hRow2Y = y; y += thrH; }

        var fh = y + padY + extraBot;
        if (starsPos === 2 || starsPos === 3) {
            var minSideH = starsSpan + (sideBorderStars ? 2 * (minBracket + 8) : 8);
            if (fh < minSideH) {
                var ds = Math.floor((minSideH - fh) / 2);
                fh = minSideH;
                headerY += ds;
                if (barY !== null) barY += ds;
                if (dmgY !== null) dmgY += ds;
                if (astY !== null) astY += ds;
                if (thrY !== null) thrY += ds;
                if (hSepY !== null) hSepY += ds;
                if (hRow1Y !== null) hRow1Y += ds;
                if (hRow2Y !== null) hRow2Y += ds;
            }
        }

        var fw = cw + 2 * padX + extraLeft + extraRight;
        var margin = 6;
        var fx = margin + ((sideBorderStars && starsPos === 2) ? halfStar : ((sideOutsideStars && starsPos === 2) ? (starSize + (starsDiv ? 14 : 8)) : 0));
        var fy = margin + (starsPos === 0 ? halfStar : 0);
        var cx = fx + padX + extraLeft;

        var starsCoords = [], divLine = null, si, sx0, sy0, scx;
        if (starsPos === 0 || starsPos === 1) {
            sx0 = fx + fw * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            var syFix = (starsPos === 0) ? fy : (fy + fh);
            for (si = 0; si < 3; si += 1) starsCoords.push([sx0 + si * (starSize + starGap), syFix]);
        } else if (starsPos === 2 || starsPos === 3) {
            sy0 = fy + fh * 0.5 - starsSpan * 0.5 + starSize * 0.5;
            if (starsPos === 2) {
                scx = sideBorderStars ? fx : (margin + starSize * 0.5);
                if (sideOutsideStars && starsDiv) divLine = [fx - 7, fy + 3, fx - 7, fy + fh - 3];
            } else {
                scx = sideBorderStars ? (fx + fw) : (fx + fw + (starsDiv ? 14 : 8) + starSize * 0.5);
                if (sideOutsideStars && starsDiv) divLine = [fx + fw + 7, fy + 3, fx + fw + 7, fy + fh - 3];
            }
            for (si = 0; si < 3; si += 1) starsCoords.push([scx, sy0 + si * (starSize + starGap)]);
        }

        var rightExtend = (sideBorderStars && starsPos === 3) ? halfStar : ((sideOutsideStars && starsPos === 3) ? ((starsDiv ? 14 : 8) + starSize) : 0);
        var winW = Math.ceil(fx + fw + rightExtend + margin);
        var curBelowY = fy + fh + (starsPos === 1 ? halfStar + 6 : 6);
        var astBelowY = null, thrBelowY = null;
        if (ast.items.length && !astInside) { astBelowY = curBelowY; curBelowY += astH + 4; }
        if (thr.length && !thrInside) { thrBelowY = curBelowY; curBelowY += thrH + 4; }
        var winH = (astBelowY !== null || thrBelowY !== null) ? Math.ceil(curBelowY - 4 + margin) : Math.ceil(fy + fh + (starsPos === 1 ? halfStar : 0) + margin);

        return {
            winW: winW, winH: winH, fx: fx, fy: fy, fw: fw, fh: fh, cx: cx, cw: cw,
            headerY: fy + headerY, headerH: headerH, pctSize: pctSize, deltaSize: deltaSize,
            dInfo: dInfo, tInfo: tInfo, ast: ast, thr: thr, isHangar: isHangar, hRows: hRows,
            hCol0W: hCol0W, hCol1W: hCol1W, hColGap: hColGap,
            hSepY: hSepY !== null ? (fy + hSepY) : null,
            hRow1Y: hRow1Y !== null ? (fy + hRow1Y) : null,
            hRow2Y: hRow2Y !== null ? (fy + hRow2Y) : null,
            barStyle: barStyle, barY: barY !== null ? (fy + barY) : null, barH: barH, trackH: trackH,
            barBlockH: barBlockH, barText: barText, barTextSize: barTextSize, barTextW: barTextW,
            dmgY: dmgY !== null ? (fy + dmgY) : null, dmgH: dmgH, dmgSize: dmgSize, dmgLblSize: dmgLblSize, dmgLblText: dmgLblText, dmgLblMode: dmgLblMode,
            astY: astInside ? (astY !== null ? (fy + astY) : null) : astBelowY,
            astH: astH, astSize: astSize, astIconSize: astIconSize, astItemGap: astItemGap, astRowMinW: astRowMinW, astInside: astInside,
            thrY: thrInside ? (thrY !== null ? (fy + thrY) : null) : thrBelowY,
            thrH: thrH, thrSize: thrSize, thrItemGap: thrItemGap,
            starsCoords: starsCoords, starSize: starSize, starGap: starGap, starsSpan: starsSpan,
            starsPos: starsPos, sideBorderStars: sideBorderStars, divLine: divLine
        };
    }

    ns.v3Metrics = {
        v3BarRatio: v3BarRatio,
        v3BarColor: v3BarColor,
        v3ComputeMetrics: v3ComputeMetrics
    };
}(window));
