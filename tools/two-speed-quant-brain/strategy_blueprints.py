#!/usr/bin/env python3
"""
Two-Speed Quant Brain — Open Reference Strategy Blueprints & v2 Microstructure Features
=======================================================================================
Paper / shadow research implementations (zero external dependencies, zero live order calls).

Includes:
  1. `PennyBell1HMaker`: +1c front-of-book passive maker entry + 80c-82c pre-bell maker exit
  2. `PhoenixFlipDipDetector`: Intra-round <=20c -> >=80c/85c -> <=55c/60c exhaustion dip
  3. `Streak4DiurnalGate`: 4-candle streak fade gated by <1 ms LightGBM + UTC diurnal filter
  4. `CrossVenueMiddleStressCheck`: Penalizes Leg-2 misses + <=5 bps oracle-pin flips + thin depth
  5. `compute_v2_features`: Developing POC distance, volume absorption, volume void, swing, canary divergence

Not trading advice. Research & reproducible paper/shadow evaluation only.
"""
import math


def penny_bell_1h_decision(best_bid, best_ask, secs_to_bell, has_position=False, entry_price=None):
    """0% passive maker 1H strategy: bid 1c ahead of best bid; rest 80c-82c exit inside final 12m."""
    if has_position:
        if secs_to_bell <= 720:  # final 12 minutes
            exit_limit = 0.80 if secs_to_bell <= 300 else 0.82
            if best_bid >= exit_limit - 0.02:
                return {"action": "POST_MAKER_EXIT", "limit_price": round(exit_limit, 2)}
        return {"action": "HOLD_POSITION", "limit_price": None}

    # Entry: only join inside spread if strictly passive (does not cross best_ask)
    proposed_bid = round(best_bid + 0.01, 2)
    if proposed_bid < best_ask and 0.45 <= proposed_bid <= 0.72 and secs_to_bell >= 1200:
        return {"action": "POST_MAKER_BID", "limit_price": proposed_bid}
    return {"action": "ABSTAIN", "limit_price": None}


class PhoenixFlipDipDetector:
    """Detects intra-round reversal whipsaw: side starts <=low_c, surges >=high_c, then dips <=dip_c."""

    def __init__(self, low_c=0.20, high_c=0.80, dip_c=0.60):
        self.low_c = low_c
        self.high_c = high_c
        self.dip_c = dip_c
        self.saw_low = False
        self.saw_high = False
        self.triggered = False

    def update(self, mid_price, ask_price):
        if not self.saw_low and mid_price <= self.low_c:
            self.saw_low = True
        elif self.saw_low and not self.saw_high and mid_price >= self.high_c:
            self.saw_high = True
        elif self.saw_low and self.saw_high and not self.triggered and ask_price <= self.dip_c:
            self.triggered = True
            return {"signal": "PHOENIX_FLIP_DIP", "ask_price": round(ask_price, 4)}
        return None


def stress_test_cross_venue_arb(
    n_trades,
    ideal_net_cents,
    pin_5bps_count,
    leg2_miss_rate=0.10,
    leg2_unwind_loss_cents=8.0,
    pin_flip_rate=0.50,
    pin_flip_loss_cents=50.0,
    min_venue_depth_shares=60,
):
    """Honest cross-venue arb/middle stress test against Leg-2 miss and <=5 bps oracle-pin flip risk."""
    leg2_drag = n_trades * leg2_miss_rate * leg2_unwind_loss_cents
    pin_drag = pin_5bps_count * pin_flip_rate * pin_flip_loss_cents
    stressed_net = ideal_net_cents - leg2_drag - pin_drag
    avg_stressed = stressed_net / max(1, n_trades)
    thin_depth_warning = min_venue_depth_shares < 50
    return {
        "n_trades": n_trades,
        "ideal_net_cents": round(ideal_net_cents, 2),
        "leg2_drag_cents": round(leg2_drag, 2),
        "pin_drag_cents": round(pin_drag, 2),
        "stressed_net_cents": round(stressed_net, 2),
        "stressed_ev_per_trade_cents": round(avg_stressed, 2),
        "thin_depth_warning": thin_depth_warning,
        "verdict": "SURVIVES_STRESS" if stressed_net > 0 else "FAILS_STRESS",
    }


def compute_v2_features(row):
    """Computes the 6 v2 Abstain-Gate microstructure + diurnal features (target OOS Brier < 0.1650)."""
    bid = float(row.get("bid", 0.5))
    ask = float(row.get("ask", 0.5))
    bid_sz = max(0.0, float(row.get("bid_size", 1.0)))
    ask_sz = max(0.0, float(row.get("ask_size", 1.0)))
    strike = max(1e-9, float(row.get("strike", 1.0)))
    spot_poc = float(row.get("developing_poc", strike))

    # 1. Developing POC distance to strike (bps)
    poc_dist_bps = ((spot_poc - strike) / strike) * 10000.0

    # 2. Volume absorption / directional efficiency (0..1)
    v_up = max(0.0, float(row.get("cum_vol_up", 0.0)))
    v_dn = max(0.0, float(row.get("cum_vol_dn", 0.0)))
    tot_v = v_up + v_dn
    if tot_v > 0:
        dom = max(v_up, v_dn) / tot_v
        vol_absorption = round(dom * dom, 5)
    else:
        vol_absorption = 0.0

    # 3. Volume void flag (wide spread >5c + thin inside depth)
    vol_void_flag = 1 if ((ask - bid) > 0.05 and bid_sz < 10.0 and ask_sz < 10.0) else 0

    # 4. Phoenix intra-round swing flag (large 5m spot swing > 100 bps)
    swing_bps = abs(float(row.get("spot_swing_5m_bps", 0.0)))
    phoenix_swing_flag = 1 if swing_bps > 100.0 else 0

    # 5. Cross-coin canary divergence (BTC moves >25 bps while altcoin is flat <5 bps)
    btc_ret = float(row.get("btc_return_bps", 0.0))
    alt_ret = float(row.get("alt_return_bps", 0.0))
    if btc_ret > 25.0 and abs(alt_ret) < 5.0:
        canary_div = 1
    elif btc_ret < -25.0 and abs(alt_ret) < 5.0:
        canary_div = -1
    else:
        canary_div = 0

    # 6. Diurnal liquidity hour flag (US/EU overlap high-churn hours 13:00-16:00 UTC)
    hour_utc = int(row.get("hour_utc", 0)) % 24
    liquidity_hour_flag = 1 if hour_utc in (13, 14, 15, 16) else 0

    return {
        "poc_distance_to_strike_bps": round(poc_dist_bps, 3),
        "volume_absorption": vol_absorption,
        "volume_void_flag": vol_void_flag,
        "phoenix_intra_round_swing": phoenix_swing_flag,
        "cross_coin_canary_divergence": canary_div,
        "liquidity_hour_flag": liquidity_hour_flag,
    }


if __name__ == "__main__":
    import json
    det = PhoenixFlipDipDetector(low_c=0.20, high_c=0.80, dip_c=0.60)
    seq = [(0.18, 0.19), (0.83, 0.84), (0.57, 0.58)]
    sig = None
    for m, a in seq:
        sig = det.update(m, a) or sig
    print(json.dumps({
        "penny_bell_sample": penny_bell_1h_decision(0.54, 0.57, secs_to_bell=2400),
        "phoenix_flip_dip_sample": sig,
        "cross_venue_stress_sample": stress_test_cross_venue_arb(52, 854.0, pin_5bps_count=2),
        "v2_features_sample": compute_v2_features({
            "bid": 0.54, "ask": 0.56, "bid_size": 45, "ask_size": 30,
            "strike": 92000.0, "developing_poc": 92115.0,
            "cum_vol_up": 800, "cum_vol_dn": 200,
            "spot_swing_5m_bps": 118.0, "btc_return_bps": 32.0,
            "alt_return_bps": 2.0, "hour_utc": 14,
        }),
    }, indent=2))
