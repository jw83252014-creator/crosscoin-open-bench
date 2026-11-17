#!/usr/bin/env python3
"""Fetch settled Kalshi 15-minute crypto rounds and their 1-minute candles from the public API.
Read-only, no credentials. Writes files in the format the studies expect (see data/README.md)."""
import argparse, json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = ["KXBTC15M", "KXETH15M", "KXSOL15M"]

def get(path, **params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "crosscoin-open-bench"}), timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"giving up on {url}")

def ts(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())

def dollars(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--since", default="2026-09-09", help="earliest open date, YYYY-MM-DD")
    ap.add_argument("--max-markets", type=int, default=0, help="stop after N markets per series (0 = no limit)")
    ap.add_argument("--sleep", type=float, default=0.15)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    since = ts(a.since + "T00:00:00Z")
    candles_path = os.path.join(a.out, "full_candles.jsonl")
    with open(candles_path, "w") as cf:
        for series in SERIES:
            rows, cursor = [], None
            while True:
                p = dict(series_ticker=series, status="settled", limit=1000)
                if cursor:
                    p["cursor"] = cursor
                d = get("/markets", **p)
                for m in d.get("markets", []):
                    if m.get("result") in ("yes", "no") and ts(m["open_time"]) >= since:
                        rows.append({k: m.get(k) for k in ("ticker", "open_time", "close_time", "result", "floor_strike", "expiration_value")})
                cursor = d.get("cursor")
                if not cursor or not d.get("markets") or (a.max_markets and len(rows) >= a.max_markets):
                    break
                time.sleep(a.sleep)
            if a.max_markets:
                rows = rows[: a.max_markets]
            rows.sort(key=lambda r: r["open_time"])
            with open(os.path.join(a.out, f"{series}.jsonl"), "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            print(series, len(rows), "settled rounds")
            for r in rows:
                o, c = ts(r["open_time"]), ts(r["close_time"])
                d = get(f"/series/{series}/markets/{r['ticker']}/candlesticks", start_ts=o, end_ts=c, period_interval=1)
                cs = [[x["end_period_ts"], dollars(x["yes_bid"]["close_dollars"]), dollars(x["yes_ask"]["close_dollars"])]
                      for x in d.get("candlesticks", []) if x.get("yes_bid") and x.get("yes_ask")]
                cf.write(json.dumps({"t": r["ticker"], "c": cs}) + "\n")
                time.sleep(a.sleep)
    print("wrote", candles_path)

if __name__ == "__main__":
    main()
