#!/usr/bin/env python3
"""
Paper-to-live drift circuit breaker (ILLUSTRATION, standard library only).

Idea credit: @yozapata on X (reply to @JeffWhiting8338, Nov 17, 2026) described
his rule as: "Live: if R per trade drifts >0.3R from paper, back to paper."

This file is an illustration of that rule, not a tested or tuned component.
The 0.3R threshold is his stated rule, not a value we measured. The example
numbers in __main__ are made up to show how the check works.

R is your own risk unit per trade (for example, the dollar amount you risk).
Pass paper and live results already expressed in R per trade.
"""
import json
import sys


def check_drift(paper_r_per_trade, live_r_per_trade, threshold_r=0.3, worse_only=False):
    """Return whether live results have drifted more than threshold_r from paper.

    By default any drift larger than threshold_r (better or worse) demotes,
    matching the wording "drifts >0.3R from paper". Set worse_only=True to
    demote only when live is worse than paper.
    """
    drift_r = live_r_per_trade - paper_r_per_trade
    trigger = (-drift_r > threshold_r) if worse_only else (abs(drift_r) > threshold_r)
    return {
        "paper_r_per_trade": paper_r_per_trade,
        "live_r_per_trade": live_r_per_trade,
        "drift_r": round(drift_r, 4),
        "threshold_r": threshold_r,
        "worse_only": worse_only,
        "demote_to_paper": trigger,
    }


if __name__ == "__main__":
    # MADE-UP EXAMPLE, not real results: paper +0.25R/trade, live -0.10R/trade.
    print(json.dumps(check_drift(0.25, -0.10), indent=2))
    sys.exit(0)
