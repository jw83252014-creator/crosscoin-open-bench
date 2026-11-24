#!/usr/bin/env python3
"""
Slug-Rollover & Queue-Clearance Guard for Prediction-Market Shadow Simulators.

Prevents the classic shadow-simulator phantom-win bug where a WebSocket order book
rolls to the *next* 5m/15m window's 50c opening quote right around round close,
falsely triggering a take-profit exit on an expiring losing position.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ShadowPosition:
    slug: str
    side: str            # "YES" or "NO"
    entry_cents: float
    tp_delta_cents: float
    close_ts: float      # Unix timestamp (seconds) when this market window closes


def check_shadow_tp_fill(
    pos: ShadowPosition,
    current_slug: Optional[str],
    best_bid_cents: Optional[float],
    now_ts: float,
    pre_bell_buffer_sec: float = 1.5,
    queue_clearance_cents: float = 1.0,
) -> bool:
    """
    Return True ONLY when:
      1. The live feed's active slug matches the open position's exact slug,
      2. We are strictly before `close_ts - pre_bell_buffer_sec`, and
      3. The live best bid has traded *through* our resting maker target by at
         least `queue_clearance_cents` (default +1.0c).
    """
    if not current_slug or current_slug != pos.slug:
        return False
    if now_ts >= (pos.close_ts - pre_bell_buffer_sec):
        return False
    if best_bid_cents is None:
        return False
    tp_target = pos.entry_cents + pos.tp_delta_cents
    return best_bid_cents >= (tp_target + queue_clearance_cents)
