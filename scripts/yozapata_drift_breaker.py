#!/usr/bin/env python3
"""
@yozapata's 0.3R Drift Circuit Breaker
Rule: If live R/trade drifts > 0.3R worse than paper expectation, automatically demote bot back to shadow/paper.
"""
import sys, json

def check_drift(paper_r_per_trade, live_r_per_trade, r_unit_usd=5.0):
    drift_r = paper_r_per_trade - live_r_per_trade
    demote_required = drift_r > 0.3
    return {
        "paper_r": paper_r_per_trade,
        "live_r": live_r_per_trade,
        "drift_r": round(drift_r, 3),
        "r_unit_usd": r_unit_usd,
        "drift_usd_per_trade": round(drift_r * r_unit_usd, 2),
        "demote_to_paper": demote_required,
        "rule_source": "@yozapata on X (Feb 2026)"
    }

if __name__ == "__main__":
    # Test example: paper makes +0.25R/trade, live makes -0.10R/trade -> drift = 0.35R (>0.3R)
    res = check_drift(0.25, -0.10, 5.0)
    print("Drift Breaker Test:", json.dumps(res, indent=2))
