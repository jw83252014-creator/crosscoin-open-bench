#!/usr/bin/env python3
"""
L2 fill-decay verifier (standard library only).

Question it answers: if an order had been sent at time t, would its limit price
still have been available at t + latency? It reports, for each latency offset,
the share of intended orders whose price was still there ("survival rate").

What it does NOT do: it does not model queue position, partial fills, fees,
or market impact. It only checks the top of book against the order's limit
price and size. Results are only as good as the snapshots you feed it, and
nothing here is a measured result until you run it on your own recorded data.

Inputs (JSONL or CSV, chosen by file extension):
  book   : timestamp_ms, best_bid, best_ask, ask_size [, bid_size]
           prices in cents; one row per L2 top-of-book snapshot
  orders : timestamp_ms, side, limit_price_cents, size
           side is "buy" (takes the ask) or "sell" (hits the bid)

Rule per order and latency L:
  look up the latest book snapshot at or before timestamp_ms + L.
  buy  survives if best_ask <= limit_price_cents and ask_size >= size
  sell survives if best_bid >= limit_price_cents and (bid_size >= size,
       or bid_size is missing, in which case size is not checked)
  if there is no snapshot at or before that time, the order is "no_data"
  and is left out of the survival rate.

Usage:
  python3 scripts/l2_fill_decay_verifier.py --book examples/example_book.jsonl \
      --orders examples/example_orders.csv [--latencies 0,150,300,900] [--json]
"""
import argparse
import bisect
import csv
import json
import os
import sys

DEFAULT_LATENCIES = (0, 150, 300, 900)


def _read_rows(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, newline="") as fh:
        if ext in (".jsonl", ".ndjson"):
            return [json.loads(line) for line in fh if line.strip()]
        if ext == ".csv":
            return list(csv.DictReader(fh))
    raise ValueError("unsupported file type (use .jsonl or .csv): %s" % path)


def _num(v):
    if v is None or v == "":
        return None
    return float(v)


def load_book(path):
    snaps = []
    for r in _read_rows(path):
        snaps.append({
            "t": int(float(r["timestamp_ms"])),
            "bid": _num(r.get("best_bid")),
            "ask": _num(r.get("best_ask")),
            "ask_size": _num(r.get("ask_size")),
            "bid_size": _num(r.get("bid_size")),
        })
    snaps.sort(key=lambda s: s["t"])
    return snaps


def load_orders(path):
    orders = []
    for r in _read_rows(path):
        side = str(r["side"]).strip().lower()
        if side not in ("buy", "sell"):
            raise ValueError("side must be buy or sell, got %r" % r["side"])
        orders.append({
            "t": int(float(r["timestamp_ms"])),
            "side": side,
            "limit": float(r["limit_price_cents"]),
            "size": float(r["size"]),
        })
    return orders


def snapshot_at(snaps, times, t):
    """Latest snapshot with timestamp <= t, or None."""
    i = bisect.bisect_right(times, t) - 1
    return snaps[i] if i >= 0 else None


def survives(order, snap):
    if snap is None:
        return None
    if order["side"] == "buy":
        if snap["ask"] is None or snap["ask_size"] is None:
            return None
        return snap["ask"] <= order["limit"] and snap["ask_size"] >= order["size"]
    if snap["bid"] is None:
        return None
    size_ok = snap["bid_size"] is None or snap["bid_size"] >= order["size"]
    return snap["bid"] >= order["limit"] and size_ok


def verify(snaps, orders, latencies=DEFAULT_LATENCIES):
    times = [s["t"] for s in snaps]
    out = []
    for lat in latencies:
        alive = dead = nodata = 0
        for o in orders:
            res = survives(o, snapshot_at(snaps, times, o["t"] + lat))
            if res is None:
                nodata += 1
            elif res:
                alive += 1
            else:
                dead += 1
        n = alive + dead
        out.append({
            "latency_ms": lat,
            "n_scored": n,
            "survived": alive,
            "gone": dead,
            "no_data": nodata,
            "survival_rate": round(alive / n, 4) if n else None,
        })
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--book", required=True)
    p.add_argument("--orders", required=True)
    p.add_argument("--latencies", default=",".join(map(str, DEFAULT_LATENCIES)))
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = p.parse_args(argv)
    lats = [int(x) for x in a.latencies.split(",") if x.strip()]
    rows = verify(load_book(a.book), load_orders(a.orders), lats)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    print("latency_ms  n_scored  survived  gone  no_data  survival_rate")
    for r in rows:
        rate = "n/a" if r["survival_rate"] is None else "%.1f%%" % (100 * r["survival_rate"])
        print("%10d  %8d  %8d  %4d  %7d  %13s" % (
            r["latency_ms"], r["n_scored"], r["survived"], r["gone"], r["no_data"], rate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
