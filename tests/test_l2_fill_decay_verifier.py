#!/usr/bin/env python3
"""Tests for scripts/l2_fill_decay_verifier.py using the SYNTHETIC example files."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import l2_fill_decay_verifier as v  # noqa: E402

BOOK = os.path.join(ROOT, "examples", "example_book.jsonl")
ORDERS = os.path.join(ROOT, "examples", "example_orders.csv")


class VerifierTest(unittest.TestCase):
    def setUp(self):
        rows = v.verify(v.load_book(BOOK), v.load_orders(ORDERS))
        self.by_lat = {r["latency_ms"]: r for r in rows}

    def test_no_data_order_excluded(self):
        # order at t=500 + 0/150/300 ms is before the first snapshot
        self.assertEqual(self.by_lat[0]["no_data"], 1)
        self.assertEqual(self.by_lat[900]["no_data"], 0)

    def test_survival_by_latency(self):
        # t+0: buy51x50 ok, buy52x20 ok, sell60x20 ok            -> 3/3
        self.assertEqual((self.by_lat[0]["survived"], self.by_lat[0]["n_scored"]), (3, 3))
        # t+150: buy51x50 fails (size 40), buy52 ok, sell ok      -> 2/3
        self.assertEqual((self.by_lat[150]["survived"], self.by_lat[150]["n_scored"]), (2, 3))
        # t+300: ask 53 > both buys, sell ok (bid 60)              -> 1/3
        self.assertEqual((self.by_lat[300]["survived"], self.by_lat[300]["n_scored"]), (1, 3))
        # t+900: ask 55 kills buys incl. t=500 order (snap @1300 ask 53 > 51); bid 58 < 60 -> 0/4
        self.assertEqual((self.by_lat[900]["survived"], self.by_lat[900]["n_scored"]), (0, 4))

    def test_cli_runs(self):
        self.assertEqual(v.main(["--book", BOOK, "--orders", ORDERS, "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
