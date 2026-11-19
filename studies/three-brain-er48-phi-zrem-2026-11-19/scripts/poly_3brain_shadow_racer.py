#!/usr/bin/env python3
"""
[LIVE-L2 SHADOW] Frozen 4-Arm Polymarket US Venue-Matched Shadow Racer
Reads LIVE Polymarket US L2 BBO from http://127.0.0.1:8799/poly5m/latest.json
+ causal BTC spot/strike/sigma/ER48 from seven_coin_sync_snapshots.jsonl.
Zero real orders. Races 4 frozen arms simultaneously on exact live Poly US quotes:
  1. TP69:        Big3 BTC-only -> Passive Maker Entry -> Resting 69c Maker Sell
  2. ER48_BELL:   Big3 + Dual-Trend (T2h & T4h) + Concave ER48 (x_t>=0.45) -> Hold-to-Bell
  3. ER48_CLOSE85: Same entry -> Bell + Static Close85 (bid>=85c & |bps|<15)
  4. ER48_PHIZ:   Same entry -> Bell + Carbon Brownian Phi(z_rem) Lock (bid>=85c, 15<=t_left<=180, (bid-fee)-Phi(z_rem)>=14c)
"""
import json, math, os, time, urllib.request
from datetime import datetime, timezone

DATA_DIR = os.environ.get("OPEN_BENCH_DATA_DIR", "./data")
SNAP_PATH = os.path.join(DATA_DIR, "seven_coin_sync_snapshots.jsonl")
OUT_STATE = os.path.join(DATA_DIR, "bank_poly_3brain_shadow_racer.json")
OUT_LEDGER = os.path.join(DATA_DIR, "ledger_poly_3brain_shadow_racer.jsonl")
WS_URL = os.environ.get("POLY_L2_FEED_URL", "http://127.0.0.1:8799/poly5m/latest.json")

def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def poly_fee_c(pc):
    p = max(0.01, min(0.99, pc / 100.0))
    return 9.5 * p * (1.0 - p)

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-min(x, 40.0))) if x >= 0 else math.exp(max(x, -40.0)) / (1.0 + math.exp(max(x, -40.0)))

def logit(p):
    p = max(0.01, min(0.99, p))
    return math.log(p / (1.0 - p))

def read_tail_json(path, max_bytes=350000):
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        sz = f.tell()
        f.seek(max(0, sz - max_bytes))
        chunk = f.read().decode("utf-8", errors="ignore").splitlines()
    out = []
    for ln in chunk[1:] if sz > max_bytes else chunk:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def compute_causal_context():
    """Extract latest BTC spot, strike, 7-coin breadth, 2h/4h trend, causal sigma_15m, and Kaufman ER48."""
    rows = read_tail_json(SNAP_PATH, max_bytes=2400000)
    by_ws = {}
    latest = None
    for d in rows:
        ts = float(d.get("ts") or 0)
        c = d.get("c") or {}
        btc = c.get("BTC") or {}
        sp, st = btc.get("sp"), btc.get("st")
        if ts <= 0 or sp is None or st is None or st <= 0:
            continue
        ws = int(ts // 900) * 900
        by_ws[ws] = (float(st), float(sp))
        latest = d
    keys = sorted(by_ws.keys())
    if len(keys) < 2 or latest is None:
        return None
    cur_ws = keys[-1]
    completed = keys[:-1]
    strikes = [by_ws[k][0] for k in completed]
    cur_st = by_ws[cur_ws][0]
    cur_sp = by_ws[cur_ws][1]

    tr2 = (cur_st - strikes[-8]) / strikes[-8] * 10000.0 if len(strikes) >= 8 else 0.0
    tr4 = (cur_st - strikes[-16]) / strikes[-16] * 10000.0 if len(strikes) >= 16 else 0.0
    log_rets = [math.log(strikes[i] / strikes[i - 1]) for i in range(1, len(strikes))]
    u48 = log_rets[-48:]
    denom = sum(abs(x) for x in u48)
    er48 = (abs(sum(u48)) / denom) if denom > 1e-12 else 0.0
    r_tilde = 0.5 * (1.0 + min(er48, 0.25))  # Carbon-Quant concave cap

    rets_bps = [(by_ws[k][1] - by_ws[k][0]) / by_ws[k][0] * 10000.0 for k in completed[-16:]]
    sigma_bps = max(10.0, math.sqrt(sum(r * r for r in rets_bps) / len(rets_bps))) if len(rets_bps) >= 4 else 25.0

    # 7-coin breadth from latest snapshot
    c = latest.get("c") or {}
    ay = an = n_c = 0
    for cn, ci in c.items():
        yb, ya = (ci or {}).get("yb"), (ci or {}).get("ya")
        if yb is None or ya is None:
            continue
        n_c += 1
        mid = 0.5 * (yb + ya)
        if mid >= 52:
            ay += 1
        elif mid <= 48:
            an += 1
    return {
        "ts": float(latest.get("ts") or 0),
        "sp": cur_sp,
        "st": cur_st,
        "tr2": tr2,
        "tr4": tr4,
        "er48": er48,
        "r_tilde": r_tilde,
        "sigma_bps": sigma_bps,
        "breadth_yes": ay / max(1.0, float(n_c)),
        "breadth_no": an / max(1.0, float(n_c)),
    }

def fetch_poly_ws():
    try:
        with urllib.request.urlopen(WS_URL, timeout=1.5) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def load_state():
    arm_names = (
        "TP69", "ER48_BELL", "ER48_CLOSE85", "ER48_PHIZ",
        "TREND_ANY_PHIZ", "TREND_ANY_BELL",
        "ROUTER_V1_PHIZ", "ROUTER_V1_BELL", "STATIC_DUALT_PHIZ", "SHAPEC_FADE_BELL"
    )
    arms = {k: {"n": 0, "wins": 0, "losses": 0, "pnlCents1sh": 0.0, "earlyExits": 0} for k in arm_names}
    default = {
        "schema": "poly_3brain_shadow_racer_v1",
        "mode": "LIVE_L2_SHADOW_ONLY",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "arms": arms,
        "active": None,
        "activeFade": None,
        "seenWins": [],
        "seenFadeWins": [],
    }
    if os.path.exists(OUT_STATE):
        try:
            saved = json.load(open(OUT_STATE))
            if saved.get("schema") == default["schema"]:
                saved_arms = saved.setdefault("arms", {})
                for k in arm_names:
                    saved_arms.setdefault(k, {"n": 0, "wins": 0, "losses": 0, "pnlCents1sh": 0.0, "earlyExits": 0})
                saved.setdefault("activeFade", None)
                saved.setdefault("seenFadeWins", [])
                return saved
        except Exception:
            pass
    return default

def save_state(st):
    st["updatedAt"] = datetime.now(timezone.utc).isoformat()
    if len(st["seenWins"]) > 100:
        st["seenWins"] = st["seenWins"][-100:]
    tmp = OUT_STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, OUT_STATE)

def append_ledger(row):
    with open(OUT_LEDGER, "a") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **row}) + "\n")

def main():
    st = load_state()
    save_state(st)
    print(f"[3BRAIN-SHADOW] Started LIVE_L2_SHADOW_ONLY on {WS_URL}", flush=True)
    ctx_cache = None
    ctx_at = 0.0

    while True:
        try:
            now = time.time()
            ws = fetch_poly_ws()
            if not ws or not ws.get("ok") or not ws.get("quotes15m"):
                time.sleep(1.0)
                continue
            if now - ctx_at > 5.0 or ctx_cache is None:
                ctx_cache = compute_causal_context()
                ctx_at = now
            q15 = ws["quotes15m"]
            btc = q15.get("BTC") or {}
            win_start = int(ws.get("win15mStart") or 0)
            close_epoch = win_start + 900
            elapsed = now - win_start
            t_left = close_epoch - now

            # 1. Monitor active shadow position across all 4 arms
            act = st.get("active")
            if act:
                if now >= act["closeEpoch"] + 3:
                    # Settle using latest BTC spot vs strike (exact Poly US open-vs-close!)
                    ctx = compute_causal_context() or ctx_cache
                    yes_won = 1 if (ctx and ctx["sp"] >= act["strike"]) else 0
                    won_bell = 1 if ((act["side"] == "YES" and yes_won == 1) or (act["side"] == "NO" and yes_won == 0)) else 0
                    ep = float(act["entryBid"])
                    results = {}
                    if act["filled"]:
                        for arm in act["eligibleArms"]:
                            ex = act["armExits"].get(arm)
                            if ex is not None:
                                net = ex["exitCents"] - ep - ex["feeCents"]
                                st["arms"][arm]["earlyExits"] += 1
                            else:
                                net = (100.0 if won_bell else 0.0) - ep
                            st["arms"][arm]["n"] += 1
                            if net > 0:
                                st["arms"][arm]["wins"] += 1
                            else:
                                st["arms"][arm]["losses"] += 1
                            st["arms"][arm]["pnlCents1sh"] = round(st["arms"][arm]["pnlCents1sh"] + net, 2)
                            results[arm] = round(net, 2)
                    append_ledger({"event": "SETTLED", **act, "wonBell": won_bell, "results": results})
                    print(f"[3BRAIN-SHADOW] SETTLED {act['slug']} {act['side']} filled={act['filled']} wonBell={won_bell} res={results}", flush=True)
                    st["active"] = None
                    save_state(st)
                elif btc.get("slug") == act["slug"] and btc.get("yesBid") is not None and btc.get("yesAsk") is not None:
                    sb = int(btc["yesBid"] if act["side"] == "YES" else btc["noBid"])
                    sa = int(btc["yesAsk"] if act["side"] == "YES" else btc["noAsk"])
                    if not act["filled"]:
                        # Conservative passive maker fill on live Poly US L2: ask <= bid OR bid < bid within 60s
                        if now <= act["postedAt"] + 60.0 and (sa <= act["entryBid"] or sb < act["entryBid"]):
                            act["filled"] = True
                            act["filledAt"] = now
                            print(f"[3BRAIN-SHADOW] PASSIVE FILLED {act['slug']} {act['side']} @ {act['entryBid']}c (x_t={act['x_t']:.3f})", flush=True)
                            save_state(st)
                    else:
                        # Check Arm 1: TP69 (passive maker sell filled when live Poly US bid >= 70c)
                        if "TP69" in act["eligibleArms"] and "TP69" not in act["armExits"] and sb >= 70:
                            act["armExits"]["TP69"] = {"exitCents": 69.0, "feeCents": 0.0, "reason": "MAKER_TP69"}
                            save_state(st)
                        # Check Arm 3 & Arm 4: Close85 & Carbon Brownian Phi(z_rem)
                        if ctx_cache and act["strike"] > 0:
                            sign = 1.0 if act["side"] == "YES" else -1.0
                            signed_bps = sign * (ctx_cache["sp"] - act["strike"]) / act["strike"] * 10000.0
                            abs_bps = abs(signed_bps)
                            if "ER48_CLOSE85" in act["eligibleArms"] and "ER48_CLOSE85" not in act["armExits"]:
                                if sb >= 85 and abs_bps < 15.0 and t_left >= 15.0:
                                    act["armExits"]["ER48_CLOSE85"] = {"exitCents": float(sb), "feeCents": round(poly_fee_c(sb), 2), "reason": f"CLOSE85_bps={abs_bps:.1f}"}
                                    save_state(st)
                            for phiz_arm in ("ER48_PHIZ", "TREND_ANY_PHIZ", "ROUTER_V1_PHIZ", "STATIC_DUALT_PHIZ"):
                                if phiz_arm in act["eligibleArms"] and phiz_arm not in act["armExits"]:
                                    if sb >= 85 and 15.0 <= t_left <= 180.0:
                                        denom = max(1.0, ctx_cache["sigma_bps"] * math.sqrt(t_left / 900.0))
                                        z_rem = signed_bps / denom
                                        phi_c = norm_cdf(z_rem) * 100.0
                                        fee_c = poly_fee_c(sb)
                                        gap = (sb - fee_c) - phi_c
                                        if gap >= 14.0:
                                            act["armExits"][phiz_arm] = {"exitCents": float(sb), "feeCents": round(fee_c, 2), "reason": f"PHIZ_gap={gap:.1f}c_z={z_rem:.2f}"}
                                            print(f"[3BRAIN-SHADOW] PHI(Z_REM) LOCK ({phiz_arm}) {act['slug']} @ {sb}c (phi={phi_c:.1f}c gap=+{gap:.1f}c t_left={t_left:.0f}s)", flush=True)
                                            save_state(st)

            # 2. Look for new BTC-only Big-3 entry on live Poly US quotes (elapsed 15..75s, bid 48..58c)
            if not st.get("active") and win_start > 0 and win_start not in st["seenWins"] and 15.0 <= elapsed <= 75.0 and ctx_cache:
                coins = ("BTC", "ETH", "SOL")
                if all(q15.get(cn) and q15[cn].get("open") and (q15[cn].get("ageMs") or 9999) <= 1800 and q15[cn].get("yesBid") is not None for cn in coins):
                    b3_yes = all(int(q15[cn]["yesBid"]) >= 54 for cn in coins)
                    b3_no = all(int(q15[cn]["noBid"]) >= 54 for cn in coins)
                    side = "YES" if b3_yes else ("NO" if b3_no else None)
                    if side:
                        sb = int(btc["yesBid"] if side == "YES" else btc["noBid"])
                        sa = int(btc["yesAsk"] if side == "YES" else btc["noAsk"])
                        if 48 <= sb <= 58 and sa <= 60 and 1 <= (sa - sb) <= 4:
                            sign = 1.0 if side == "YES" else -1.0
                            H = ctx_cache["breadth_yes"] if side == "YES" else ctx_cache["breadth_no"]
                            T2 = 1.0 if (sign * ctx_cache["tr2"] > 10.0) else 0.0
                            T4 = 1.0 if (sign * ctx_cache["tr4"] > 15.0) else 0.0
                            S_t = 0.5 * (1.0 + H) * 0.5 * (T2 + T4)
                            x_t = ctx_cache["r_tilde"] * S_t
                            p_hat = sigmoid(logit(0.5 * (sb + sa) / 100.0) + 0.35 * x_t)
                            elig = ["TP69"]
                            er48 = ctx_cache["er48"]
                            if x_t > 0.0:
                                elig.extend(["TREND_ANY_PHIZ", "TREND_ANY_BELL"])
                            if T2 > 0 and T4 > 0:
                                elig.append("STATIC_DUALT_PHIZ")
                                if er48 >= 0.15 and x_t >= 0.45:
                                    elig.extend(["ER48_BELL", "ER48_CLOSE85", "ER48_PHIZ"])
                                if (0.15 <= er48 <= 0.35) or (er48 > 0.35 and sb <= 56):
                                    elig.extend(["ROUTER_V1_PHIZ", "ROUTER_V1_BELL"])
                            st["seenWins"].append(win_start)
                            st["active"] = {
                                "slug": btc["slug"],
                                "winStart": win_start,
                                "closeEpoch": close_epoch,
                                "side": side,
                                "entryBid": sb,
                                "entryAsk": sa,
                                "postedAt": now,
                                "strike": ctx_cache["st"],
                                "sigmaBps": round(ctx_cache["sigma_bps"], 2),
                                "er48": round(er48, 3),
                                "x_t": round(x_t, 3),
                                "pHat": round(p_hat, 3),
                                "eligibleArms": elig,
                                "filled": False,
                                "armExits": {},
                            }
                            save_state(st)
                            print(f"[3BRAIN-SHADOW] POSTED {btc['slug']} {side} @ {sb}c (er48={er48:.3f} x_t={x_t:.3f} arms={elig})", flush=True)

            # 3. Separate non-blocking slot for Shape C Exhaustion Passive Fade (ER48 > 0.35, 60..480s, 20..28c -> Bell)
            af = st.get("activeFade")
            if af:
                if now >= af["closeEpoch"] + 3:
                    ctx = compute_causal_context() or ctx_cache
                    yes_won = 1 if (ctx and ctx["sp"] >= af["strike"]) else 0
                    won_bell = 1 if ((af["side"] == "YES" and yes_won == 1) or (af["side"] == "NO" and yes_won == 0)) else 0
                    if af["filled"]:
                        net = (100.0 if won_bell else 0.0) - float(af["entryBid"])
                        arm = st["arms"]["SHAPEC_FADE_BELL"]
                        arm["n"] += 1
                        if net > 0: arm["wins"] += 1
                        else: arm["losses"] += 1
                        arm["pnlCents1sh"] = round(arm["pnlCents1sh"] + net, 2)
                        append_ledger({"event": "SETTLED_SHAPEC_FADE", **af, "wonBell": won_bell, "net": round(net, 2)})
                        print(f"[3BRAIN-SHADOW] SETTLED SHAPEC_FADE {af['slug']} {af['side']} @ {af['entryBid']}c wonBell={won_bell} net={net:+.1f}c", flush=True)
                    st["activeFade"] = None
                    save_state(st)
                elif btc.get("slug") == af["slug"] and not af["filled"] and btc.get("yesBid") is not None and btc.get("yesAsk") is not None:
                    sb = int(btc["yesBid"] if af["side"] == "YES" else btc["noBid"])
                    sa = int(btc["yesAsk"] if af["side"] == "YES" else btc["noAsk"])
                    if now <= af["postedAt"] + 90.0 and (sa <= af["entryBid"] or sb < af["entryBid"]):
                        af["filled"] = True
                        af["filledAt"] = now
                        print(f"[3BRAIN-SHADOW] FILLED SHAPEC_FADE {af['slug']} {af['side']} @ {af['entryBid']}c (er48={af['er48']:.3f})", flush=True)
                        save_state(st)
            elif win_start > 0 and win_start not in st["seenFadeWins"] and 60.0 <= elapsed <= 480.0 and ctx_cache and ctx_cache["er48"] > 0.35:
                if btc.get("open") and (btc.get("ageMs") or 9999) <= 1800 and btc.get("yesBid") is not None and btc.get("yesAsk") is not None:
                    yb, ya = int(btc["yesBid"]), int(btc["yesAsk"])
                    nb, na = int(btc["noBid"]), int(btc["noAsk"])
                    if 1 <= (ya - yb) <= 4:
                        f_side = "NO" if (yb >= 72 and 20 <= nb <= 28) else ("YES" if (nb >= 72 and 20 <= yb <= 28) else None)
                        if f_side:
                            fsb = yb if f_side == "YES" else nb
                            st["seenFadeWins"].append(win_start)
                            if len(st["seenFadeWins"]) > 100: st["seenFadeWins"] = st["seenFadeWins"][-100:]
                            st["activeFade"] = {
                                "slug": btc["slug"], "winStart": win_start, "closeEpoch": close_epoch,
                                "side": f_side, "entryBid": fsb, "postedAt": now,
                                "strike": ctx_cache["st"], "er48": round(ctx_cache["er48"], 3), "filled": False
                            }
                            save_state(st)
                            print(f"[3BRAIN-SHADOW] POSTED SHAPEC_FADE {btc['slug']} {f_side} @ {fsb}c (er48={ctx_cache['er48']:.3f})", flush=True)
        except Exception as e:
            print(f"[3BRAIN-SHADOW ERR] {e}", flush=True)
        time.sleep(1.0)

if __name__ == "__main__":
    main()
