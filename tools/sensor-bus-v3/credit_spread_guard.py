#!/usr/bin/env python3
"""
Zero-dependency HYG vs IEF Credit-Spread Crash Sensor ($0/mo via Yahoo Finance).

Detects systemic credit-market stress (high-yield junk bonds selling off while
7-10Y US Treasuries catch a flight-to-safety bid) so short-horizon crypto /
prediction-market bots can pause mean-reversion fading during macro risk-off cascades.

Usage:
    python3 tools/sensor-bus-v3/credit_spread_guard.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Dict, Any, Optional


def classify_credit_regime(hyg_chg_pct: float, ief_chg_pct: float) -> Dict[str, Any]:
    """Pure deterministic classifier for HYG (junk bonds) vs IEF (7-10Y Treasuries)."""
    spread_pct = round(hyg_chg_pct - ief_chg_pct, 3)
    if hyg_chg_pct <= -2.0:
        return {
            "state": "CREDIT_CRASH",
            "alert": True,
            "hygMinusIefPct": spread_pct,
            "hint": "Severe junk-bond selloff (HYG <= -2.0%): halt passive fade entries.",
        }
    if hyg_chg_pct <= -1.0 and ief_chg_pct >= -0.1:
        return {
            "state": "CREDIT_STRESS",
            "alert": True,
            "hygMinusIefPct": spread_pct,
            "hint": "Credit spread widening (HYG <= -1.0% while IEF holds): tighten sizing and drift guards.",
        }
    return {
        "state": "CALM",
        "alert": False,
        "hygMinusIefPct": spread_pct,
        "hint": "Credit spreads calm — no systemic junk-bond flight to Treasuries.",
    }


def fetch_yahoo_daily_change(symbol: str, timeout: float = 5.0) -> Optional[Dict[str, float]]:
    """Fetch latest price and daily % change from public Yahoo Finance chart JSON."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "crosscoin-open-bench/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    meta = payload["chart"]["result"][0]["meta"]
    px = float(meta["regularMarketPrice"])
    prev = float(meta.get("chartPreviousClose") or meta.get("previousClose"))
    chg_pct = round(((px - prev) / prev) * 100.0, 2) if prev > 0 else 0.0
    return {"px": round(px, 2), "prev": round(prev, 2), "chgPct": chg_pct}


def fetch_credit_spread_guard(timeout: float = 5.0) -> Dict[str, Any]:
    """Query HYG and IEF live and return structured credit-spread regime telemetry."""
    t0 = time.monotonic()
    hyg = fetch_yahoo_daily_change("HYG", timeout=timeout)
    ief = fetch_yahoo_daily_change("IEF", timeout=timeout)
    out = classify_credit_regime(hyg["chgPct"], ief["chgPct"])
    out.update({
        "hyg": hyg,
        "ief": ief,
        "rttMs": round((time.monotonic() - t0) * 1000.0, 1),
    })
    return out


if __name__ == "__main__":
    print(json.dumps(fetch_credit_spread_guard(), indent=2))
