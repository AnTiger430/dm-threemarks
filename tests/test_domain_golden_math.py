# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from dm_threemarks.domain.constants import ANCHORS, EPOCH_DAY
from dm_threemarks.domain.entities.curve import Curve
from dm_threemarks.domain.entities.mark_snapshot import MarkSnapshot
from dm_threemarks.domain.entities.server_epoch import ServerEpoch
from dm_threemarks.domain.services.forecast_engine import ForecastEngine, floor_pct, next_average
from dm_threemarks.domain.services.threshold_calculator import ThresholdCalculator, build_fallback_curve, calc_percent, calc_statistics


def _load_golden():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'golden_v10_12_7.json')
    with open(path, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


class TestGoldenDomainMath(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.golden = _load_golden()

    def _build_curves(self):
        knots = {20: 600, 40: 1100, 55: 1500, 65: 1850, 75: 2250, 85: 2700, 95: 3300, 100: 3800}
        raw_exact = {}
        kkeys = sorted(knots.keys())
        for i in range(len(kkeys) - 1):
            p0, p1 = kkeys[i], kkeys[i + 1]
            d0, d1 = knots[p0], knots[p1]
            for q in range(p0, p1 + 1):
                raw_exact[str(q)] = d0 + (d1 - d0) * (q - p0) // (p1 - p0)
        raw_non_exact = dict(raw_exact)
        raw_non_exact['41'] = raw_non_exact['41'] + 5
        row_values = [int(raw_exact[str(p)]) for p in ANCHORS]
        return {
            'curve_exact': Curve(raw_exact, day=739000),
            'curve_non_exact': Curve(raw_non_exact, day=739000),
            'curve_flat': Curve({'20': 1000, '30': 1000, '40': 1500, '55': 2000, '65': 2500, '75': 3000, '85': 3500, '95': 4000, '100': 4500}, day=739000),
            'curve_row': Curve.from_row(row_values, day=738999),
        }

    def test_curves_exact_parity(self):
        pcts = [0.0, 10.0, 20.0, 50.0, 65.0, 72.34, 85.0, 95.0, 99.5, 100.0]
        dmgs = [0, 300, 600, 1100, 1850, 2400, 2700, 3300, 3800, 4200]
        for name, c in self._build_curves().items():
            exp = self.golden[name]
            self.assertEqual(bool(c), exp['bool'])
            self.assertEqual(c.exact, exp['exact'])
            self.assertEqual(c.day, exp['day'])
            self.assertEqual([list(pt) for pt in c.points], exp['points'])
            self.assertEqual(list(c.thresholds()), exp['thresholds'])
            self.assertEqual([c.damage_of(p) for p in pcts], exp['damageOf'])
            self.assertEqual([c.percent_of(d) for d in dmgs], exp['percentOf'])
            self.assertEqual([c.cell(d) for d in dmgs], exp['cell'])
            self.assertEqual([c.whole_damage(p) for p in pcts], exp['wholeDamage'])
            self.assertEqual([c.explains(1850, 65.0), c.explains(1850, 65.01), c.explains(2700, 85.0), c.explains(2699, 84.99)], exp['explains'])

    def test_floor_pct_and_next_average(self):
        floor_inputs = [0.0, 64.999999, 65.0, 84.999999, 85.0, 94.9999999, 95.0, 99.99999, 100.0]
        self.assertEqual([floor_pct(x) for x in floor_inputs], self.golden['floorPct'])
        next_inputs = [(0.0, 0), (1500.0, 3000), (1850.0, 1850), (2700.0, 0), (3123.0, 4567)]
        self.assertEqual([list(next_average(a, b)) for a, b in next_inputs], self.golden['nextAverage'])

    def test_epoch_and_forecast_engine(self):
        curves = self._build_curves()
        ep = ServerEpoch()
        ep.seen_day = 739000
        ep.seen_at = (739000 - EPOCH_DAY) * 86400.0 + 36000.0
        self.assertEqual(ep.by_clock(1700000000.0 - 3600.0 * 10), self.golden['epoch']['byClock_before_9utc'])
        self.assertEqual(ep.by_clock(1700000000.0), self.golden['epoch']['byClock_after_9utc'])
        self.assertEqual(ep.holds(ep.seen_at, ep.seen_at + 1800.0), self.golden['epoch']['holds_fresh'])
        self.assertEqual(ep.holds(ep.seen_at - 10800.0, ep.seen_at), self.golden['epoch']['holds_expired'])
        self.assertEqual(ep.day(ep.seen_at + 3600.0), self.golden['epoch']['day_late_hold'])

        now_ts = (739000 - EPOCH_DAY) * 86400.0 + 12 * 3600.0
        day_map = {
            ('10529', 739000): curves['curve_exact'],
            ('10529', 738999): curves['curve_row'],
        }

        def day_curve_fn(key, num, newest=None):
            if newest is not None and newest.day == num:
                return newest
            return day_map.get((key, num))

        engine = ForecastEngine(ep)
        m_exact = MarkSnapshot(10529, 65.00, 1850.0, 120, 1, int(now_ts - 600))
        m_stale = MarkSnapshot(10529, 62.00, 1850.0, 120, 1, int(now_ts - 172800))
        m_non_exact = MarkSnapshot(10529, 65.10, 1850.0, 120, 1, int(now_ts - 600))
        m_zero_avg = MarkSnapshot(10529, 65.00, 0.0, 0, 1, 0)

        sc = engine.server_curve(m_exact, curves['curve_exact'], now_ts, day_curve_fn)
        self.assertEqual([sc[0].day, sc[1], sc[2]], self.golden['serverCurve']['exact'])
        self.assertEqual(list(engine.current_percent(m_stale, curves['curve_exact'], now_ts, day_curve_fn)), self.golden['currentPercent']['stale'])
        self.assertEqual(list(engine.forecast(m_exact, 3200, curves['curve_exact'], now_ts, day_curve_fn).as_tuple()), self.golden['forecast']['exact_3200'])
        self.assertEqual(list(engine.forecast(m_exact, 500, curves['curve_exact'], now_ts, day_curve_fn).as_tuple()), self.golden['forecast']['exact_500'])
        self.assertEqual(list(engine.forecast(m_non_exact, 2500, curves['curve_non_exact'], now_ts, day_curve_fn).as_tuple()), self.golden['forecast']['non_exact_2500'])
        self.assertEqual(list(engine.forecast(m_zero_avg, 2000, curves['curve_exact'], now_ts, day_curve_fn).as_tuple()), self.golden['forecast']['zero_avg_2000'])

        thr_calc = ThresholdCalculator(engine)
        self.assertEqual(
            list(thr_calc.compute_thresholds(m_exact, 65.0, 1850.0, curves['curve_exact'], now_ts, day_curve_fn, 0).as_tuple()),
            [1850, 2700, 3300, 3800],
        )
        m_fb = MarkSnapshot(999999, 72.5, 2400.0, 50, 1, 0)
        self.assertEqual(
            list(thr_calc.compute_thresholds(m_fb, 72.5, 2400.0, None, now_ts, day_curve_fn, 0).as_tuple()),
            [2152, 2814, 3550, 3740],
        )

    def test_calc_percent_and_statistics(self):
        self.assertEqual(
            [calc_percent(0, 0.0, 65.0, 2400.0, 72.5), calc_percent(2400.0, 72.5, 73.0, 2400.0, 72.5)],
            self.golden['calcPercent'],
        )
        for label, p, d in (('45.2_1200', 45.2, 1200.0), ('72.5_2400', 72.5, 2400.0), ('91.0_3100', 91.0, 3100.0)):
            res = calc_statistics(p, d)
            exp = dict((int(k), v) for k, v in self.golden['calcStatistics'][label].items())
            self.assertEqual(res, exp)

    def test_hold_damage_zero_battle_thresholds_and_fallback_curve(self):
        curves = self._build_curves()
        ep = ServerEpoch()
        engine = ForecastEngine(ep)
        thr_calc = ThresholdCalculator(engine)
        now_ts = (739000 - EPOCH_DAY) * 86400.0 + 12 * 3600.0

        def day_curve_fn(key, num, newest=None):
            return newest if (newest is not None and newest.day == num) else None

        # Exact dossier -> hold == ema
        m_exact = MarkSnapshot(10529, 65.00, 1850.0, 120, 1, int(now_ts - 600))
        self.assertEqual(engine.hold_damage(m_exact, curves['curve_exact'], now_ts, day_curve_fn), 1850)

        # Upward curve shift (stale dossier percent below curve) -> hold uses server curve whole_damage (> ema)
        m_stale = MarkSnapshot(10529, 62.00, 1850.0, 120, 1, int(now_ts - 172800))
        self.assertEqual(engine.hold_damage(m_stale, curves['curve_exact'], now_ts, day_curve_fn), 1850)

        # Slight upward curve movement (< STALE_GAP, stale dossier -> shift=0): hold uses server.whole_damage(base) > ema
        m_below = MarkSnapshot(10529, 64.99, 1849.0, 120, 1, int(now_ts - 86400))
        self.assertEqual(engine.hold_damage(m_below, curves['curve_exact'], now_ts, day_curve_fn), 1850)
        self.assertEqual(engine.hold_damage(m_exact, None, now_ts, day_curve_fn), 1850)

        # Zero battle: hold == 0, thresholds populated from curve, empty without curve
        m_zero = MarkSnapshot(10529, 0.0, 0.0, 0, 0, 0)
        self.assertEqual(engine.hold_damage(m_zero, curves['curve_exact'], now_ts, day_curve_fn), 0)
        self.assertEqual(
            list(thr_calc.compute_thresholds(m_zero, 0.0, 0.0, curves['curve_exact'], now_ts, day_curve_fn, 0).as_tuple()),
            [1850, 2700, 3300, 3800],
        )
        self.assertEqual(
            list(thr_calc.compute_thresholds(m_zero, 0.0, 0.0, None, now_ts, day_curve_fn, 0).as_tuple()),
            [0, 0, 0, 0],
        )

        # build_fallback_curve across representative percentages
        for p, d in ((15.0, 300.0), (45.2, 1200.0), (72.5, 2400.0), (88.0, 3100.0), (96.0, 4200.0)):
            fb = build_fallback_curve(p, d)
            self.assertIsNotNone(fb)
            self.assertFalse(fb.exact)
            self.assertIsNone(fb.day)
            self.assertTrue(all(a[0] < b[0] and a[1] < b[1] for a, b in zip(fb.points, fb.points[1:])))
            self.assertTrue(fb.explains(d, p))
            m_fb = MarkSnapshot(999999, p, d, 50, 1, 0)
            res_eq = engine.forecast(m_fb, d, fb, now_ts, day_curve_fn)
            res_hi = engine.forecast(m_fb, d + 1000, fb, now_ts, day_curve_fn)
            res_lo = engine.forecast(m_fb, max(0, d - 1000), fb, now_ts, day_curve_fn)
            self.assertEqual(res_eq.delta, 0.0)
            self.assertGreater(res_hi.delta, 0.0)
            self.assertLess(res_lo.delta, 0.0)


if __name__ == '__main__':
    unittest.main()
