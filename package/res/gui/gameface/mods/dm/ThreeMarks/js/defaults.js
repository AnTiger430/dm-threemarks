(function (root) {
    'use strict';
    var ns = root.DmThreeMarks = root.DmThreeMarks || {};

    ns.CONST = {
        MINI_W: 175,
        LABEL_EMA_W: 112,
        LABEL_TITLE_W: 62,
        PANEL_W: 220,
        TRACK_LEFT: 10,
        TRACK_W: 200,
        FONT_URL: 'img://gui/maps/three_marks/font_',
        SET_IMG: 'img://gui/maps/three_marks/set_'
    };

    ns.SIZES = { b: [244, 96], bp: [220, 72], h: [244, 144], hm: [244, 98], s: [244, 342], v3: [240, 120], bmin: [34, 34] };

    ns.DEF_UI = {
        s: 0.9, hs: 1.1, preset: 0, v3: null, vh: null, bg: 0.82, up: '#86EF6A', dn: '#FF6060', zr: '#EAEAEA',
        bUp: '#8FE37D', bDn: '#FF6060', bZr: '#DDE6EE', bH: '#F0F2F6',
        trk: 0.10, tick: '#FFFFFF', pct: '#F4F4F4', pctSign: false,
        glow: true, band: 0.02,
        big: '#B07CFF', bBig: '#B07CFF', bigFrom: 4,
        dmgSign: true, dmg: '#86EF6A', proj: '#EAEAEA',
        bSign: false, bStd: '#8FE37D', bigDmg: true,
        onlyPct: false, alpha: 1
    };

    ns.DEF_V3 = {
        fnt: 2, den: 0, minW: 0, anc: 1,
        fs: 0, rad: 14, cc: '#FFFFFF', ca: 0.50, ba: 0.22, bgc: '#0B1016', bgo: 0.20,
        sp: 0, ss: 0, sd: false, sz: 16, sg: 7, sgl: true, son: '#FFFFFF', sof: '#9AA3AE',
        ho: 2, dec: 1, di: 1, dc: 0,
        bs: 0, bsc: 0, bh: 4, bth: 2, bt: 'KIBERSPORT', bts: 15, bet: true, bcur: true, bmk: true, bcm: 0, bcc: '#A7D080',
        dmgOn: true, dl: 0, dlc: '\u0421\u0443\u043c. \u0443\u0440\u043e\u043d', sep: 2, ddyn: true,
        ash: 0, am: 0, ap: 0, ahz: false, asz: 15,
        tsh: 1, tmm: 0, tp: 0, tsz: 13,
        up: '#A7D080', dn: '#E57373', zr: '#9AA3AE', big: '#B07CFF', tm: '#FFFFFF', tmu: '#B8BDC4',
        hThr: true, h100: true
    };

    ns.V3_FONT_SCALES = [1.0, 1.08, 1.12, 1.30, 1.20, 1.28, 1.04, 1.30];
    ns.V3_FONT_FAMILIES = [
        '"ThreeMarksPFDINMax", PFDINMax, Warhelios',
        'Warhelios',
        '"ThreeMarksDINRound", DINRoundPro, Warhelios',
        '"ThreeMarksJura", Jura, Warhelios',
        '"ThreeMarksExo2", Warhelios',
        '"ThreeMarksRubik", Warhelios',
        '"ThreeMarksFiraCond", "ThreeMarksPFDINMax", PFDINMax, Warhelios',
        '"ThreeMarksTektur", Warhelios'
    ];

    ns.V3_TRACK_RUNS = [
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

    ns.ARROW_ROWS = [2, 2, 4, 4, 6, 6, 8, 8, 10];

    ns.METRICS = {
        h: 17,
        g: {
            '0': { x: 0, w: 8 }, '1': { x: 9, w: 6 }, '2': { x: 16, w: 8 },
            '3': { x: 25, w: 8 }, '4': { x: 34, w: 8 }, '5': { x: 43, w: 8 },
            '6': { x: 52, w: 8 }, '7': { x: 61, w: 8 }, '8': { x: 70, w: 8 },
            '9': { x: 79, w: 8 }, '.': { x: 88, w: 4 }, '/': { x: 93, w: 6 },
            '%': { x: 100, w: 10 }, '+': { x: 111, w: 8 }, '-': { x: 120, w: 6 },
            '\u2014': { x: 127, w: 10 }, '~': { x: 138, w: 8 }, ' ': { x: 147, w: 4 }
        }
    };
}(window));
