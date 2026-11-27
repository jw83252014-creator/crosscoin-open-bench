import os
import sys
import unittest

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools",
    "two-speed-quant-brain",
)
sys.path.insert(0, TOOLS_DIR)

import abstain_gate_inference as gate  # noqa: E402
import jev_v4_lucys_book as jev  # noqa: E402
import strategy_blueprints as sb  # noqa: E402


class TestTwoSpeedQuantBrain(unittest.TestCase):
    def test_abstain_gate_loads_and_runs_fast(self):
        res = gate.run_synthetic_benchmark(50)
        self.assertTrue(res["ok"])
        self.assertEqual(res["trees"], 164)
        self.assertLess(res["p50_ms"], 10.0)
        sc = res["sample_streak4_score"]
        self.assertIn("pYesCal", sc)
        self.assertIn("pYesBlend", sc)
        self.assertIsNotNone(sc["streak4Gate"])
        self.assertEqual(sc["streak4Gate"]["fadeSide"], "NO")

    def test_jev_v4_lucys_book_self_test(self):
        out = jev.run_self_test()
        self.assertTrue(out["ok"])
        self.assertEqual(out["self_test"], "PASSED")
        self.assertEqual(out["recalled_verified"], 2)

    def test_strategy_blueprints(self):
        pb = sb.penny_bell_1h_decision(0.54, 0.57, secs_to_bell=2400)
        self.assertEqual(pb["action"], "POST_MAKER_BID")
        self.assertEqual(pb["limit_price"], 0.55)

        det = sb.PhoenixFlipDipDetector(low_c=0.20, high_c=0.80, dip_c=0.60)
        self.assertIsNone(det.update(0.18, 0.19))
        self.assertIsNone(det.update(0.84, 0.85))
        trig = det.update(0.57, 0.58)
        self.assertIsNotNone(trig)
        self.assertEqual(trig["signal"], "PHOENIX_FLIP_DIP")

        st = sb.stress_test_cross_venue_arb(52, 854.0, pin_5bps_count=2)
        self.assertEqual(st["verdict"], "SURVIVES_STRESS")

        feats = sb.compute_v2_features({
            "bid": 0.50, "ask": 0.58, "bid_size": 5, "ask_size": 5,
            "strike": 100.0, "developing_poc": 101.0,
            "cum_vol_up": 90, "cum_vol_dn": 10,
            "spot_swing_5m_bps": 125.0, "btc_return_bps": 30.0,
            "alt_return_bps": 1.0, "hour_utc": 14,
        })
        self.assertEqual(feats["volume_void_flag"], 1)
        self.assertEqual(feats["phoenix_intra_round_swing"], 1)
        self.assertEqual(feats["cross_coin_canary_divergence"], 1)
        self.assertEqual(feats["liquidity_hour_flag"], 1)


if __name__ == "__main__":
    unittest.main()
