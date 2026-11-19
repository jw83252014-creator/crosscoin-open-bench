#!/usr/bin/env python3
"""
CLEAN EXACT-TICKER Walk-Forward Dynamically Weighted Probability & Peak-Lock Study (v2)
- Groups strictly by exact Kalshi ticker `tk` (no window-rollover strike bleed!)
- Settles strictly by true market settlement (final yb>=95 -> YES, ya<=5 -> NO; skips ambiguous)
- Tests BOTH:
  (A) Passive Maker fill (strict ask<=bid) vs Immediate Taker fill (at ask, exact Poly US 9.5%*p*(1-p) fee)
  (B) Trader Peak-Lock / Close-to-Strike Protection rule (80c/85c/90c/92c)
  (C) Walk-Forward Dynamically Weighted Probability (Static Expanding vs Online Regime-Adaptive EWA)
"""
import json, math, os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_DIR = os.environ.get("OPEN_BENCH_DATA_DIR", "./data")
SNAP_PATH = os.path.join(DATA_DIR, "seven_coin_sync_snapshots.jsonl")
PREROUND_PATH = os.path.join(DATA_DIR, "ledger_preround_v22.jsonl")
ET = ZoneInfo("America/New_York")

def poly_taker_fee_cents(p_cents):
    p = max(0.01, min(0.99, p_cents / 100.0))
    return 9.5 * p * (1.0 - p)

def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-min(x, 40.0)))
    z = math.exp(max(x, -40.0))
    return z / (1.0 + z)

preround_by_tk = {}
if os.path.exists(PREROUND_PATH):
    with open(PREROUND_PATH) as f:
        for line in f:
            try:
                r = json.loads(line)
                tk = r.get("ticker")
                if not tk: continue
                flow = float(r.get("flow") or 0)
                med = float(r.get("med1hFlow") or 1)
                preround_by_tk[tk] = {"side": r.get("side"), "ratio": min(abs(flow)/max(med,1.0), 5.0)}
            except: pass

# Group strictly by exact BTC ticker `tk`
by_tk = {}
with open(SNAP_PATH) as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        ts = float(d.get("ts") or 0)
        t15 = d.get("t15")
        c = d.get("c") or {}
        btc = c.get("BTC")
        if not btc or ts <= 0 or t15 is None: continue
        tk = btc.get("tk")
        sp, st, yb, ya = btc.get("sp"), btc.get("st"), btc.get("yb"), btc.get("ya")
        if not tk or None in (sp, st, yb, ya) or st <= 0: continue
        w = by_tk.get(tk)
        if w is None:
            w = {"tk": tk, "first_ts": ts, "last_ts": ts, "st": float(st), "ticks": [], "last_yb": int(yb), "last_ya": int(ya), "last_sp": float(sp), "min_t15": float(t15), "max_t15": float(t15)}
            by_tk[tk] = w
        w["last_ts"] = ts
        w["st"] = float(st)  # settled/final strike for this exact ticker
        w["last_yb"] = int(yb); w["last_ya"] = int(ya); w["last_sp"] = float(sp)
        if float(t15) < w["min_t15"]: w["min_t15"] = float(t15)
        if float(t15) > w["max_t15"]: w["max_t15"] = float(t15)

        b3y = b3n = ay = an = 0
        coins = list(c.keys())
        for cn in coins:
            ci = c.get(cn) or {}
            cyb, cya = ci.get("yb"), ci.get("ya")
            if cyb is None or cya is None: continue
            mid = 0.5*(cyb + cya)
            if mid >= 52:
                ay += 1
                if cn in ("BTC","ETH","SOL"): b3y += 1
            elif mid <= 48:
                an += 1
                if cn in ("BTC","ETH","SOL"): b3n += 1
        d30 = float(btc.get("d30") or 0.0)
        el = 900.0 - float(t15)
        if el <= 180 or not w["ticks"] or (ts - w["ticks"][-1][0]) >= 1.5 or float(t15) <= 30:
            w["ticks"].append((ts, float(t15), int(yb), int(ya), float(sp), float(st), d30, b3y, b3n, ay, an, len(coins)))

# Filter to clean settled tickers: started near open (max_t15 >= 850), reached bell (min_t15 <= 15), unambiguous settlement
valid = []
ambiguous = 0
for tk, w in sorted(by_tk.items(), key=lambda kv: kv[1]["first_ts"]):
    if w["max_t15"] < 850 or w["min_t15"] > 15:
        continue
    # True settlement: check final tick(s)
    if w["last_yb"] >= 90:
        yes_won = 1
    elif w["last_ya"] <= 10:
        yes_won = 0
    else:
        ambiguous += 1
        continue
    w["yes_won"] = yes_won
    valid.append(w)

print(f"EXACT-TICKER CLEAN SETTLED WINDOWS: n={len(valid)} (skipped {ambiguous} non-90/10 ambiguous bell ticks)")

# ==============================================================================
# PART 1: TRUE PEAK-LOCK / CLOSE-TO-STRIKE FLIP ANALYSIS (EXACT SETTLEMENT!)
# ==============================================================================
print("\n=== PART 1: TRUE EXACT-SETTLED PEAK-LOCK / CLOSE-TO-STRIKE ANALYSIS ===")
for thresh in [75, 80, 85, 90, 92, 95]:
    hits = []
    for w in valid:
        yes_won = w["yes_won"]
        for ts, t15, yb, ya, sp, st, d30, b3y, b3n, ay, an, nc in w["ticks"]:
            if t15 > 870 or t15 < 15: continue
            nb = 100 - ya
            if yb >= thresh:
                hits.append(("YES", t15, abs(sp-st)/st*10000.0, yb, 100-yb, yes_won)); break
            if nb >= thresh:
                hits.append(("NO", t15, abs(sp-st)/st*10000.0, nb, 100-nb, 1-yes_won)); break
    n = len(hits)
    fl = sum(1 for h in hits if h[5] == 0)
    print(f"\nFIRST TOUCH >={thresh}c: n={n}, Won={n-fl} ({100*(n-fl)/max(1,n):.1f}%), FLIPPED={fl} ({100*fl/max(1,n):.1f}%) | Market implied flip <= {100-thresh}%")
    for lbl, pred in [
        ("t_left > 300s (early)", lambda h: h[1] > 300),
        ("t_left 120..300s (mid)", lambda h: 120 < h[1] <= 300),
        ("t_left 15..120s (last 2m)", lambda h: h[1] <= 120),
        ("dist < 15 bps (close)", lambda h: h[2] < 15),
        ("dist 15..30 bps", lambda h: 15 <= h[2] < 30),
        ("dist >= 30 bps (far)", lambda h: h[2] >= 30),
        ("CLOSE(<15bps) & t_left>60s", lambda h: h[2] < 15 and h[1] > 60),
    ]:
        sub = [h for h in hits if pred(h)]
        if len(sub) < 5: continue
        sfl = sum(1 for h in sub if h[5] == 0)
        avg_bid = sum(h[3] for h in sub)/len(sub)
        cash_vs_hold = avg_bid - (1.0 - sfl/len(sub))*100.0
        print(f"  {lbl:28s}: n={len(sub):3d} | TrueFlip={100*sfl/len(sub):5.1f}% (avgPx={avg_bid:.1f}c) | CashOut vs Hold: {cash_vs_hold:+5.2f}c")

# ==============================================================================
# PART 2: ADVERSE SELECTION CHECK (PASSIVE MAKER FILL vs IMMEDIATE TAKER vs ALL SIGNALS!)
# ==============================================================================
print("\n=== PART 2: PASSIVE MAKER ADVERSE SELECTION vs TAKER vs SIGNAL TRUTH (EXACT SETTLEMENT) ===")
prev_strikes = []
prev_rets = []
signals = []

for w in valid:
    st = w["st"]
    dt_et = datetime.fromtimestamp(w["first_ts"], ET)
    is_ny = 1.0 if (8 <= dt_et.hour < 16) else 0.0
    trend4h_bps = (st - prev_strikes[-16])/prev_strikes[-16]*10000.0 if len(prev_strikes) >= 16 else 0.0
    sigma_bps = max(10.0, math.sqrt(sum(r*r for r in prev_rets[-16:])/len(prev_rets[-16:]))) if len(prev_rets) >= 6 else 25.0
    pr = preround_by_tk.get(w["tk"])

    entry = None
    for idx_t, tk_row in enumerate(w["ticks"]):
        ts, t15, yb, ya, sp, st_cur, d30, b3y, b3n, ay, an, nc = tk_row
        el = 900.0 - t15
        if el < 2.0 or el > 120.0: continue
        spread = max(0, ya - yb)
        if spread > 5: continue
        nb = 100 - ya; na = 100 - yb
        side = None; trig = None
        if pr and el <= 30.0:
            ps = pr["side"]
            sb, sa = (yb, ya) if ps == "YES" else (nb, na)
            if 42 <= sb <= 62 and sa <= 64:
                side, trig = ps, "PREROUND"
        if side is None and el >= 15.0:
            if 48 <= yb <= 62 and ya <= 64 and b3y == 3: side, trig = "YES", "BIG3"
            elif 48 <= nb <= 62 and na <= 64 and b3n == 3: side, trig = "NO", "BIG3"
            elif 50 <= yb <= 62 and ya <= 64 and b3y >= 2: side, trig = "YES", "SOFT2"
            elif 50 <= nb <= 62 and na <= 64 and b3n >= 2: side, trig = "NO", "SOFT2"
        if side is not None:
            sb, sa = (yb, ya) if side == "YES" else (nb, na)
            sign = 1.0 if side == "YES" else -1.0
            dist_bps = sign * (sp - st_cur) / st_cur * 10000.0
            entry = {
                "idx_t": idx_t, "el": el, "side": side, "trig": trig,
                "bid": sb, "ask": sa, "spread": spread,
                "b3_agree": 1.0 if ((side=="YES" and b3y==3) or (side=="NO" and b3n==3)) else 0.0,
                "breadth": (ay if side=="YES" else an)/max(1.0, float(nc)),
                "z_dist": max(-3.0, min(3.0, dist_bps/sigma_bps)),
                "d30_bps": max(-20.0, min(20.0, sign*(d30/sp)*10000.0))/10.0,
                "trend_align": 1.0 if sign*trend4h_bps > 15 else (-1.0 if sign*trend4h_bps < -15 else 0.0),
                "is_ny": is_ny,
                "pr_align": (pr["ratio"] if pr["side"]==side else -pr["ratio"]) if pr else 0.0,
                "won_bell": 1 if ((side=="YES" and w["yes_won"]==1) or (side=="NO" and w["yes_won"]==0)) else 0,
            }
            break

    prev_strikes.append(st)
    prev_rets.append((w["last_sp"] - st)/st*10000.0)
    if not entry: continue

    # Evaluate BOTH (1) Immediate fill at ask (Taker) and (2) Passive Maker fill at bid (ask<=bid within 60s)
    side = entry["side"]
    maker_filled = False
    hit_tp_from_taker = {68:False, 70:False, 74:False, 85:False, 90:False}
    hit_tp_from_maker = {68:False, 70:False, 74:False, 85:False, 90:False}
    for tk_row in w["ticks"][entry["idx_t"]+1:]:
        ts, t15, yb, ya, sp, st_cur, d30, b3y, b3n, ay, an, nc = tk_row
        el = 900.0 - t15
        sb = yb if side=="YES" else (100 - ya)
        sa = ya if side=="YES" else (100 - yb)
        for lv in hit_tp_from_taker:
            if not hit_tp_from_taker[lv] and sb >= lv + 1:
                hit_tp_from_taker[lv] = True
        if not maker_filled:
            if el <= entry["el"] + 60.0 and (sa <= entry["bid"] or sb < entry["bid"]):
                maker_filled = True
        else:
            for lv in hit_tp_from_maker:
                if not hit_tp_from_maker[lv] and sb >= lv + 1:
                    hit_tp_from_maker[lv] = True

    entry["maker_filled"] = maker_filled
    entry["hit_tp_taker"] = hit_tp_from_taker
    entry["hit_tp_maker"] = hit_tp_from_maker
    signals.append(entry)

def show_group(name, sub):
    if not sub: return
    n = len(sub)
    mf = [r for r in sub if r["maker_filled"]]
    uf = [r for r in sub if not r["maker_filled"]]
    # 1. All signals at ask (Taker entry + Poly fee -> Bell or Maker TP70)
    ev_tak_bell = sum(((100 if r["won_bell"] else 0) - r["ask"] - poly_taker_fee_cents(r["ask"])) for r in sub)/n
    ev_tak_tp70 = sum(((70 if r["hit_tp_taker"][70] else (100 if r["won_bell"] else 0)) - r["ask"] - poly_taker_fee_cents(r["ask"])) for r in sub)/n
    # 2. All signals zero-fee mid/bid (ideal frictionless edge of signal!)
    ev_ideal_bell = sum(((100 if r["won_bell"] else 0) - r["bid"]) for r in sub)/n
    # 3. Passive Maker Filled ONLY (real adverse selection!)
    ev_mkr_bell = sum(((100 if r["won_bell"] else 0) - r["bid"]) for r in mf)/max(1,len(mf))
    ev_mkr_tp70 = sum(((70 if r["hit_tp_maker"][70] else (100 if r["won_bell"] else 0)) - r["bid"]) for r in mf)/max(1,len(mf))
    # 4. Unfilled signals (what ran away from our passive bid!)
    uf_wr = 100.0*sum(r["won_bell"] for r in uf)/max(1,len(uf))
    mf_wr = 100.0*sum(r["won_bell"] for r in mf)/max(1,len(mf))
    print(f"\n[{name}] total={n} | MakerFilled={len(mf)} ({100*len(mf)/n:.0f}%, BellWR={mf_wr:.1f}%) | UnfilledRunaways={len(uf)} (BellWR={uf_wr:.1f}%)")
    print(f"   Signal Ideal (0% fee @bid -> Bell): {ev_ideal_bell:+5.2f}c/sh | Taker(w/fee)->Bell: {ev_tak_bell:+5.2f}c | Taker(w/fee)->TP70: {ev_tak_tp70:+5.2f}c")
    print(f"   Passive Maker Filled -> Bell:       {ev_mkr_bell:+5.2f}c/sh | Passive Maker -> TP70: {ev_mkr_tp70:+5.2f}c/sh")

show_group("ALL SIGNALS", signals)
show_group("PREROUND TRIGGER ONLY", [r for r in signals if r["trig"]=="PREROUND"])
show_group("BIG3 TRIGGER ONLY", [r for r in signals if r["trig"]=="BIG3"])
show_group("NY + BIG3 AGREE", [r for r in signals if r["is_ny"]==1.0 and r["b3_agree"]==1.0])
show_group("NY + TREND ALIGNED + BIG3", [r for r in signals if r["is_ny"]==1.0 and r["b3_agree"]==1.0 and r["trend_align"]>0])
show_group("z_dist > +0.25 sigma", [r for r in signals if r["z_dist"] > 0.25])

# ==============================================================================
# PART 3: WALK-FORWARD DYNAMICALLY WEIGHTED PROBABILITY ON TRUE SIGNAL EDGE!
# ==============================================================================
print("\n=== PART 3: WALK-FORWARD DYNAMICALLY WEIGHTED PROBABILITY (EXACT SETTLEMENT, ALL SIGNALS) ===")
FEAT = ["bias","b3_agree","breadth","z_dist","d30_bps","trend_align","is_ny","pr_align","px_rel"]
def gx(r):
    return [1.0, r["b3_agree"], r["breadth"]-0.5, r["z_dist"], r["d30_bps"], r["trend_align"], r["is_ny"], max(-2.0,min(3.0,r["pr_align"])), (r["bid"]-55.0)/10.0]

# Run Online Dynamic Adaptive Logistic (predicting true P_bell) on ALL signals
w_dyn = [0.0]*len(FEAT)
oos = []
warmup = 80
for i, r in enumerate(signals):
    x = gx(r)
    p = sigmoid(sum(wi*xi for wi,xi in zip(w_dyn, x)))
    y = float(r["won_bell"])
    if i >= warmup:
        oos.append((r, p, y))
    err = y - p
    for j in range(len(w_dyn)):
        reg = 0.05*w_dyn[j] if j>0 else 0.0
        w_dyn[j] = (w_dyn[j]*(0.99 if j>0 else 1.0)) + 0.08*(err*x[j] - reg)

b_mkt = sum((r["bid"]/100.0 - y)**2 for r,_,y in oos)/len(oos)
b_dyn = sum((p - y)**2 for _,p,y in oos)/len(oos)
print(f"OOS Signals (n={len(oos)}): Market Brier={b_mkt:.4f} | Dynamic Adaptive Brier={b_dyn:.4f} (diff={b_dyn-b_mkt:+.4f})")
print("Final Dynamic Weights (Bell Win):", ", ".join(f"{f}={v:+.3f}" for f,v in zip(FEAT, w_dyn)))

# Check EV by Dynamic Edge Bucket (p_dyn*100 - ask - taker_fee) AND Passive Maker Fill!
for thresh_c in [-99, 0.0, 2.0, 4.0, 6.0]:
    sub_tak = [x for x in oos if (x[1]*100.0 - x[0]["ask"] - poly_taker_fee_cents(x[0]["ask"])) > thresh_c]
    sub_mkr = [x for x in oos if x[0]["maker_filled"] and (x[1]*100.0 - x[0]["bid"]) > thresh_c]
    if sub_tak:
        ev_t = sum(((100 if r["won_bell"] else 0) - r["ask"] - poly_taker_fee_cents(r["ask"])) for r,_,_ in sub_tak)/len(sub_tak)
        wr_t = 100.0*sum(r["won_bell"] for r,_,_ in sub_tak)/len(sub_tak)
        print(f"  Taker Gate (predEV>{thresh_c:+4.1f}c): n={len(sub_tak):3d} | WR={wr_t:5.1f}% | Realized EV={ev_t:+5.2f}c/sh")
    if sub_mkr:
        ev_m = sum(((100 if r["won_bell"] else 0) - r["bid"]) for r,_,_ in sub_mkr)/len(sub_mkr)
        ev_m70 = sum(((70 if r["hit_tp_maker"][70] else (100 if r["won_bell"] else 0)) - r["bid"]) for r,_,_ in sub_mkr)/len(sub_mkr)
        wr_m = 100.0*sum(r["won_bell"] for r,_,_ in sub_mkr)/len(sub_mkr)
        print(f"  Maker Gate (predEV>{thresh_c:+4.1f}c): n={len(sub_mkr):3d} | BellWR={wr_m:5.1f}% | BellEV={ev_m:+5.2f}c | TP70EV={ev_m70:+5.2f}c")
