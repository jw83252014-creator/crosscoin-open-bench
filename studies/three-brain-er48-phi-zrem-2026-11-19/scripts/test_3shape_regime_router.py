#!/usr/bin/env python3
"""
Strict Zero-Leakage 7-Day Test of the 3-Shape Regime Router (Nov 12-19, 2026)
- Groups strictly by exact Kalshi ticker `tk` with exact 90/10 settlement.
- Strictly causal ER48 (last 48 completed 15m bells), 2h/4h strike trend, causal 4h sigma.
- Conservative passive maker fill (ask <= bid or bid < bid within 60s) and exact Poly US taker fee curve for IOC exits.
- Tests EVERY shape independently AND combined day-by-day across all 7 days:
  * SHAPE A (Smooth Trend: 0.15 <= ER48 <= 0.35)
  * SHAPE B (Pure Chop: ER48 < 0.15) — tests TP69, Passive Maker Fade @ 20-28c -> +14c TP, Passive Maker Fade -> Bell, and Sit-Out
  * SHAPE C (Exhausted Run: ER48 > 0.35) — tests Capped <=56c Trend+PhiZ, Fade Exhaustion, and Sit-Out
"""
import json, math, os
from datetime import datetime
from zoneinfo import ZoneInfo

SNAP_PATH = os.path.join(os.environ.get("OPEN_BENCH_DATA_DIR", "./data"), "seven_coin_sync_snapshots.jsonl")
ET = ZoneInfo("America/New_York")

def norm_cdf(z): return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
def poly_fee_c(pc): p = max(0.01, min(0.99, pc / 100.0)); return 9.5 * p * (1.0 - p)

by_tk = {}
with open(SNAP_PATH) as f:
    for line in f:
        try: d = json.loads(line)
        except: continue
        ts = float(d.get("ts") or 0); t15 = d.get("t15")
        c = d.get("c") or {}; btc = c.get("BTC")
        if not btc or ts <= 0 or t15 is None: continue
        tk = btc.get("tk")
        sp, st, yb, ya = btc.get("sp"), btc.get("st"), btc.get("yb"), btc.get("ya")
        if not tk or None in (sp, st, yb, ya) or st <= 0: continue
        w = by_tk.get(tk)
        if w is None:
            w = {"tk": tk, "first_ts": ts, "st": float(st), "ticks": [], "last_yb": int(yb), "last_ya": int(ya), "last_sp": float(sp), "min_t15": float(t15), "max_t15": float(t15)}
            by_tk[tk] = w
        w["st"] = float(st); w["last_yb"] = int(yb); w["last_ya"] = int(ya); w["last_sp"] = float(sp)
        w["min_t15"] = min(w["min_t15"], float(t15)); w["max_t15"] = max(w["max_t15"], float(t15))
        b3y = b3n = ay = an = 0
        for cn, ci in c.items():
            cyb, cya = (ci or {}).get("yb"), (ci or {}).get("ya")
            if cyb is None or cya is None: continue
            mid = 0.5 * (cyb + cya)
            if mid >= 52:
                ay += 1
                if cn in ("BTC", "ETH", "SOL"): b3y += 1
            elif mid <= 48:
                an += 1
                if cn in ("BTC", "ETH", "SOL"): b3n += 1
        el = 900.0 - float(t15)
        if el <= 180 or not w["ticks"] or (ts - w["ticks"][-1][0]) >= 1.5 or float(t15) <= 30:
            w["ticks"].append((ts, float(t15), int(yb), int(ya), float(sp), float(st), b3y, b3n, ay, an, len(c)))

valid = []
for tk, w in sorted(by_tk.items(), key=lambda kv: kv[1]["first_ts"]):
    if w["max_t15"] < 850 or w["min_t15"] > 15: continue
    if w["last_yb"] >= 90: yes_won = 1
    elif w["last_ya"] <= 10: yes_won = 0
    else: continue
    w["yes_won"] = yes_won
    valid.append(w)

print(f"Total clean exact-settled BTC 15m windows: n={len(valid)}")

strikes = []; log_rets = []; rets_bps = []
win_records = []

for w in valid:
    st = w["st"]
    dt_et = datetime.fromtimestamp(w["first_ts"], ET)
    day = dt_et.strftime("%Y-%m-%d")
    is_ny = 1 if (8 <= dt_et.hour < 16) else 0

    tr2 = (st - strikes[-8]) / strikes[-8] * 10000.0 if len(strikes) >= 8 else 0.0
    tr4 = (st - strikes[-16]) / strikes[-16] * 10000.0 if len(strikes) >= 16 else 0.0
    if len(log_rets) >= 12:
        u = log_rets[-48:]
        denom = sum(abs(x) for x in u)
        er48 = abs(sum(u)) / denom if denom > 1e-12 else 0.0
    else:
        er48 = 0.0
    sigma_bps = max(10.0, math.sqrt(sum(r*r for r in rets_bps[-16:]) / len(rets_bps[-16:]))) if len(rets_bps) >= 6 else 25.0

    if er48 < 0.15:
        shape = "B_CHOP(<0.15)"
    elif er48 <= 0.35:
        shape = "A_TREND(0.15-0.35)"
    else:
        shape = "C_EXHAUST(>0.35)"

    # 1) BIG-3 PASSIVE MAKER (BTC-only, elapsed 15..75s, bid 48..58c)
    big3 = None
    for idx_t, row in enumerate(w["ticks"]):
        ts, t15, yb, ya, sp, st_c, b3y, b3n, ay, an, nc = row
        el = 900.0 - t15
        if el < 15.0 or el > 75.0 or (ya - yb) > 4: continue
        nb, na = 100 - ya, 100 - yb
        side = "YES" if (b3y == 3 and 48 <= yb <= 58 and ya <= 60) else ("NO" if (b3n == 3 and 48 <= nb <= 58 and na <= 60) else None)
        if side:
            sb, sa = (yb, ya) if side == "YES" else (nb, na)
            sign = 1.0 if side == "YES" else -1.0
            T2 = 1 if sign * tr2 > 10.0 else 0
            T4 = 1 if sign * tr4 > 15.0 else 0
            won_bell = 1 if ((side == "YES" and w["yes_won"] == 1) or (side == "NO" and w["yes_won"] == 0)) else 0
            mf = False; hit69 = False; phiz_px = None; phiz_fee = 0.0
            for r2 in w["ticks"][idx_t+1:]:
                ts2, t15_2, yb2, ya2, sp2, st2, *_ = r2
                el2 = 900.0 - t15_2
                sb2 = yb2 if side == "YES" else (100 - ya2)
                sa2 = ya2 if side == "YES" else (100 - yb2)
                if not mf:
                    if el2 <= el + 60.0 and (sa2 <= sb or sb2 < sb):
                        mf = True
                else:
                    if not hit69 and sb2 >= 70:
                        hit69 = True
                    if phiz_px is None and sb2 >= 85 and 15.0 <= t15_2 <= 180.0:
                        signed_bps = sign * (sp2 - st2) / st2 * 10000.0
                        z_rem = signed_bps / max(1.0, sigma_bps * math.sqrt(t15_2 / 900.0))
                        phi_c = norm_cdf(z_rem) * 100.0
                        fc = poly_fee_c(sb2)
                        if (sb2 - fc) - phi_c >= 14.0:
                            phiz_px = float(sb2); phiz_fee = fc
            if mf:
                pnl_tp69 = (69.0 if hit69 else (100.0 if won_bell else 0.0)) - sb
                pnl_bell = (100.0 if won_bell else 0.0) - sb
                pnl_phiz = ((phiz_px - phiz_fee) if phiz_px is not None else (100.0 if won_bell else 0.0)) - sb
                big3 = {"side": side, "bid": sb, "T2": T2, "T4": T4, "dual": (T2==1 and T4==1), "anyT": (T2==1 or T4==1), "won_bell": won_bell, "pnl_tp69": pnl_tp69, "pnl_bell": pnl_bell, "pnl_phiz": pnl_phiz}
            break

    # 2) CHOP PASSIVE MAKER FADE (minute 1..8: leader spikes >=72c -> passive bid cheap side 20..28c -> +14c Maker TP or Bell!)
    fade = None
    for idx_t, row in enumerate(w["ticks"]):
        ts, t15, yb, ya, sp, st_c, b3y, b3n, ay, an, nc = row
        el = 900.0 - t15
        if el < 60.0 or el > 480.0 or (ya - yb) > 4: continue
        nb, na = 100 - ya, 100 - yb
        f_side = "NO" if (yb >= 72 and 20 <= nb <= 28) else ("YES" if (nb >= 72 and 20 <= yb <= 28) else None)
        if f_side:
            sb = yb if f_side == "YES" else nb
            won_bell = 1 if ((f_side == "YES" and w["yes_won"] == 1) or (f_side == "NO" and w["yes_won"] == 0)) else 0
            mf = False; hit_tp = False; tp_lv = sb + 14
            for r2 in w["ticks"][idx_t+1:]:
                ts2, t15_2, yb2, ya2, *_ = r2
                el2 = 900.0 - t15_2
                sb2 = yb2 if f_side == "YES" else (100 - ya2)
                sa2 = ya2 if f_side == "YES" else (100 - yb2)
                if not mf:
                    if el2 <= el + 90.0 and (sa2 <= sb or sb2 < sb):
                        mf = True
                else:
                    if not hit_tp and sb2 >= tp_lv + 1:
                        hit_tp = True
            if mf:
                pnl_fade_tp = (float(tp_lv) if hit_tp else (100.0 if won_bell else 0.0)) - sb
                pnl_fade_bell = (100.0 if won_bell else 0.0) - sb
                fade = {"side": f_side, "bid": sb, "pnl_tp": pnl_fade_tp, "pnl_bell": pnl_fade_bell, "won_tp": pnl_fade_tp > 0, "won_bell": won_bell}
            break

    win_records.append({"day": day, "shape": shape, "er48": er48, "is_ny": is_ny, "big3": big3, "fade": fade})

    if strikes: log_rets.append(math.log(st / strikes[-1]))
    strikes.append(st)
    rets_bps.append((w["last_sp"] - st) / st * 10000.0)

recs = win_records[48:]
print(f"Post-warmup windows (ER48 populated): n={len(recs)}")
for sh in ("B_CHOP(<0.15)", "A_TREND(0.15-0.35)", "C_EXHAUST(>0.35)"):
    cnt = sum(1 for r in recs if r["shape"] == sh)
    print(f"  Shape {sh:20s}: {cnt:3d} windows ({100*cnt/len(recs):.1f}%)")

def summarize(label, pnls):
    n = len(pnls)
    if n == 0:
        print(f"  {label:38s}: n=  0")
        return
    w = sum(1 for x in pnls if x > 0)
    tot = sum(pnls)
    avg = tot / n
    eq = 0.0; pk = 0.0; dd = 0.0
    for x in pnls:
        eq += x
        if eq > pk: pk = eq
        if pk - eq > dd: dd = pk - eq
    print(f"  {label:38s}: n={n:3d} | {w:3d}W-{n-w:3d}L ({100*w/n:5.1f}%) | EV={avg:+6.2f}c/sh | Total={tot:+7.1f}c | MaxDD={dd:5.1f}c")

print("\n=== PERFORMANCE BY MARKET SHAPE (WHICH WEAPON WINS EACH SHAPE?) ===")
for sh in ("B_CHOP(<0.15)", "A_TREND(0.15-0.35)", "C_EXHAUST(>0.35)"):
    sub = [r for r in recs if r["shape"] == sh]
    print(f"\n--- {sh} (windows={len(sub)}) ---")
    summarize("Big3 Unfiltered -> TP69", [r["big3"]["pnl_tp69"] for r in sub if r["big3"]])
    summarize("Big3 Any-Trend -> Bell", [r["big3"]["pnl_bell"] for r in sub if r["big3"] and r["big3"]["anyT"]])
    summarize("Big3 Any-Trend -> Bell+Phi(z_rem)", [r["big3"]["pnl_phiz"] for r in sub if r["big3"] and r["big3"]["anyT"]])
    summarize("Big3 Dual-Trend -> Bell", [r["big3"]["pnl_bell"] for r in sub if r["big3"] and r["big3"]["dual"]])
    summarize("Big3 Dual-Trend -> Bell+Phi(z_rem)", [r["big3"]["pnl_phiz"] for r in sub if r["big3"] and r["big3"]["dual"]])
    summarize("Big3 Dual-Trend (bid<=56c) -> PhiZ", [r["big3"]["pnl_phiz"] for r in sub if r["big3"] and r["big3"]["dual"] and r["big3"]["bid"]<=56])
    summarize("Passive Fade (20-28c -> +14c TP)", [r["fade"]["pnl_tp"] for r in sub if r["fade"]])
    summarize("Passive Fade (20-28c -> Bell)", [r["fade"]["pnl_bell"] for r in sub if r["fade"]])

print("\n=== FULL 7-DAY COMPARISON: STATIC BOTS vs 3-SHAPE REGIME ROUTERS ===")
def router_pnls(mode):
    out = []; by_day = {}
    for r in recs:
        p = None; sh = r["shape"]; b = r["big3"]; f = r["fade"]
        if mode == "STATIC_TP69":
            if b: p = b["pnl_tp69"]
        elif mode == "STATIC_ANYT_PHIZ":
            if b and b["anyT"]: p = b["pnl_phiz"]
        elif mode == "STATIC_DUALT_PHIZ":
            if b and b["dual"]: p = b["pnl_phiz"]
        elif mode == "ROUTER_V1_TREND_PHIZ_CHOP_SITOUT":
            if sh == "A_TREND(0.15-0.35)" and b and b["dual"]: p = b["pnl_phiz"]
            elif sh == "C_EXHAUST(>0.35)" and b and b["dual"] and b["bid"] <= 56: p = b["pnl_phiz"]
        elif mode == "ROUTER_V2_TREND_PHIZ_CHOP_FADE":
            if sh == "A_TREND(0.15-0.35)" and b and b["dual"]: p = b["pnl_phiz"]
            elif sh == "B_CHOP(<0.15)" and f: p = f["pnl_bell"]
            elif sh == "C_EXHAUST(>0.35)" and b and b["dual"] and b["bid"] <= 56: p = b["pnl_phiz"]
        elif mode == "ROUTER_V3_TREND_PHIZ_CHOP_TP69":
            if sh == "A_TREND(0.15-0.35)" and b and b["dual"]: p = b["pnl_phiz"]
            elif sh == "B_CHOP(<0.15)" and b: p = b["pnl_tp69"]
            elif sh == "C_EXHAUST(>0.35)" and b and b["dual"] and b["bid"] <= 56: p = b["pnl_phiz"]
        elif mode == "ROUTER_V4_ANYT_TREND_CHOP_SITOUT":
            if sh == "A_TREND(0.15-0.35)" and b and b["anyT"]: p = b["pnl_phiz"]
            elif sh == "C_EXHAUST(>0.35)" and b and b["dual"] and b["bid"] <= 56: p = b["pnl_phiz"]
        if p is not None:
            out.append(p); by_day.setdefault(r["day"], []).append(p)
    return out, by_day

for m in ["STATIC_TP69", "STATIC_ANYT_PHIZ", "STATIC_DUALT_PHIZ", "ROUTER_V1_TREND_PHIZ_CHOP_SITOUT", "ROUTER_V4_ANYT_TREND_CHOP_SITOUT", "ROUTER_V2_TREND_PHIZ_CHOP_FADE", "ROUTER_V3_TREND_PHIZ_CHOP_TP69"]:
    pnls, bd = router_pnls(m)
    summarize(m, pnls)
    green_days = sum(1 for d, vals in bd.items() if sum(vals) > 0)
    day_str = " | ".join(f"{d[5:]}:{sum(vals):+.0f}c({len(vals)})" for d, vals in sorted(bd.items()))
    print(f"     Days green={green_days}/{len(bd)} -> {day_str}")
