import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "sensor-bus-v3")))

from credit_spread_guard import classify_credit_regime
from slug_rollover_guard import ShadowPosition, check_shadow_tp_fill


class TestSensorBusV3(unittest.TestCase):
    def test_credit_calm(self):
        res = classify_credit_regime(hyg_chg_pct=-0.01, ief_chg_pct=0.90)
        self.assertEqual(res["state"], "CALM")
        self.assertFalse(res["alert"])

    def test_credit_stress(self):
        res = classify_credit_regime(hyg_chg_pct=-1.25, ief_chg_pct=0.40)
        self.assertEqual(res["state"], "CREDIT_STRESS")
        self.assertTrue(res["alert"])

    def test_credit_crash(self):
        res = classify_credit_regime(hyg_chg_pct=-2.30, ief_chg_pct=-0.50)
        self.assertEqual(res["state"], "CREDIT_CRASH")
        self.assertTrue(res["alert"])

    def test_slug_rollover_blocks_phantom_win(self):
        pos = ShadowPosition(
            slug="btc-updown-5m-0500z",
            side="NO",
            entry_cents=31.0,
            tp_delta_cents=14.0,
            close_ts=1000.0,
        )
        # Next round's 50c quote arrives after rollover -> MUST return False
        self.assertFalse(
            check_shadow_tp_fill(pos, current_slug="btc-updown-5m-0505z", best_bid_cents=50.0, now_ts=995.0)
        )
        # Final 1.5s pre-bell buffer -> MUST return False
        self.assertFalse(
            check_shadow_tp_fill(pos, current_slug="btc-updown-5m-0500z", best_bid_cents=50.0, now_ts=999.0)
        )
        # Exact target touch without +1c queue clearance (45c) -> MUST return False
        self.assertFalse(
            check_shadow_tp_fill(pos, current_slug="btc-updown-5m-0500z", best_bid_cents=45.0, now_ts=900.0)
        )
        # Valid mid-round trade-through at 46c (+1c clearance) -> True
        self.assertTrue(
            check_shadow_tp_fill(pos, current_slug="btc-updown-5m-0500z", best_bid_cents=46.0, now_ts=900.0)
        )


if __name__ == "__main__":
    unittest.main()
