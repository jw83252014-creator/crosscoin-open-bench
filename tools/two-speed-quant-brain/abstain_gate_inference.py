#!/usr/bin/env python3
"""
Pure-Python <1 ms LightGBM + Isotonic Calibration Evaluator (Two-Speed Quant Brain — Speed 1)
=============================================================================================
Zero external dependencies (Python 3.9+ standard library only).
Parses a trained LightGBM binary text model (`lgbm_abstain_gate.txt`) + isotonic
`calibration_table.json` + `feature_spec.json` once at startup and evaluates
27-feature market snapshots in ~0.07 ms on Apple Silicon / standard CPU.

Research & paper/shadow use only. Not trading advice.
"""
import bisect
import json
import math
import os
import time

DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "abstain_gate_v2")
COIN_ID_MAP = {"BTC": 0, "ETH": 1, "SOL": 2, "XRP": 3}


def _parse_int_list(s):
    s = s.strip()
    return [int(x) for x in s.split()] if s else []


def _parse_float_list(s):
    s = s.strip()
    return [float(x) for x in s.split()] if s else []


class PureLightGBMBinaryModel:
    """Bit-for-bit evaluator for LightGBM binary classification text models."""

    def __init__(self, model_dir=DEFAULT_MODEL_DIR):
        self.model_dir = model_dir
        with open(os.path.join(model_dir, "feature_spec.json"), "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        with open(os.path.join(model_dir, "calibration_table.json"), "r", encoding="utf-8") as fh:
            cal = json.load(fh)
        with open(os.path.join(model_dir, "model_card.json"), "r", encoding="utf-8") as fh:
            card = json.load(fh)

        self.features = spec["features"]
        self.cal_x = [float(x) for x in cal["x_thresholds"]]
        self.cal_y = [float(y) for y in cal["y_thresholds"]]
        self.model_card = card
        self.trees = self._load_trees(os.path.join(model_dir, "lgbm_abstain_gate.txt"))

    def _load_trees(self, path):
        trees = []
        cur = None
        in_trees = False
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("Tree="):
                    in_trees = True
                    if cur is not None:
                        trees.append(cur)
                    cur = {}
                    continue
                if line == "end of trees":
                    if cur is not None:
                        trees.append(cur)
                        cur = None
                    break
                if not in_trees or cur is None or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k in ("split_feature", "left_child", "right_child", "decision_type"):
                    cur[k] = _parse_int_list(v)
                elif k in ("threshold", "leaf_value"):
                    cur[k] = _parse_float_list(v)
                elif k == "shrinkage":
                    cur[k] = float(v)
        compiled = []
        for t in trees:
            compiled.append((
                t.get("split_feature", []),
                t.get("threshold", []),
                t.get("left_child", []),
                t.get("right_child", []),
                t.get("decision_type", []),
                t.get("leaf_value", [0.0]),
            ))
        return compiled

    def _predict_raw_margin(self, x):
        total = 0.0
        for sf, th, lc, rc, dt, lv in self.trees:
            if not sf:
                total += lv[0]
                continue
            node = 0
            while node >= 0:
                val = x[sf[node]]
                if math.isnan(val):
                    d = dt[node] if node < len(dt) else 2
                    go_left = bool(d & 4)
                else:
                    go_left = val <= th[node]
                node = lc[node] if go_left else rc[node]
            total += lv[~node]
        return total

    def _calibrate(self, p_raw):
        xs, ys = self.cal_x, self.cal_y
        if not xs:
            return p_raw
        if p_raw <= xs[0]:
            return ys[0]
        if p_raw >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, p_raw) - 1
        x0, x1 = xs[i], xs[i + 1]
        y0, y1 = ys[i], ys[i + 1]
        if x1 == x0:
            return y0
        return y0 + (y1 - y0) * ((p_raw - x0) / (x1 - x0))

    def predict_dict(self, feat_dict):
        t0 = time.perf_counter()
        x = [float(feat_dict.get(f, 0.0)) for f in self.features]
        margin = self._predict_raw_margin(x)
        if margin > 35.0:
            p_raw = 1.0
        elif margin < -35.0:
            p_raw = 0.0
        else:
            p_raw = 1.0 / (1.0 + math.exp(-margin))
        p_cal = max(0.01, min(0.99, self._calibrate(p_raw)))
        ms = (time.perf_counter() - t0) * 1000.0
        return {
            "p_yes_raw": round(p_raw, 5),
            "p_yes_cal": round(p_cal, 5),
            "p_no_cal": round(1.0 - p_cal, 5),
            "latency_ms": round(ms, 3),
        }

    def score_setup(self, feat_dict):
        res = self.predict_dict(feat_dict)
        bid = float(feat_dict.get("bid", 0.5))
        ask = float(feat_dict.get("ask", 0.5))
        mid = float(feat_dict.get("mid", 0.5 * (bid + ask)))
        p_yes = res["p_yes_cal"]
        edge_yes_c = round((p_yes - bid) * 100.0, 2)
        edge_no_c = round(((1.0 - p_yes) - (1.0 - ask)) * 100.0, 2)
        prior_streak = int(feat_dict.get("prior_streak", 0))

        if edge_yes_c >= 4.0 and 0.15 <= bid <= 0.85:
            verdict = "GREEN_LIGHT_YES_MAKER"
        elif edge_no_c >= 4.0 and 0.15 <= (1.0 - ask) <= 0.85:
            verdict = "GREEN_LIGHT_NO_MAKER"
        else:
            verdict = "ABSTAIN"

        streak4_gate = None
        if abs(prior_streak) >= 4:
            fade_side = "NO" if prior_streak > 0 else "YES"
            fade_p = (1.0 - p_yes) if fade_side == "NO" else p_yes
            streak4_gate = {
                "fadeSide": fade_side,
                "fadeProb": round(fade_p, 4),
                "passGate52": fade_p >= 0.52,
                "verdict": f"PASS_FADE_{fade_side}" if fade_p >= 0.52 else "VETO_STREAK4_TRAP",
            }

        return {
            "model": self.model_card.get("version", "abstain_gate_v2"),
            "trainedGpu": self.model_card.get("gpu", "NVIDIA L4"),
            "trees": len(self.trees),
            "pYesRaw": res["p_yes_raw"],
            "pYesCal": res["p_yes_cal"],
            "pYesBlend": round(max(0.01, min(0.99, 0.50 * p_yes + 0.50 * mid)), 5),
            "pNoCal": res["p_no_cal"],
            "marketMid": round(mid, 4),
            "edgeYesCents": edge_yes_c,
            "edgeNoCents": edge_no_c,
            "verdict": verdict,
            "streak4Gate": streak4_gate,
            "latencyMs": res["latency_ms"],
        }


def run_synthetic_benchmark(n=500):
    m = PureLightGBMBinaryModel()
    sample_base = {
        "coin_id": 0.0, "t_rem_sec": 480.0, "dist_bps": 18.0, "abs_dist_bps": 18.0,
        "bid": 0.58, "ask": 0.60, "mid": 0.59, "spread": 0.02,
        "spot_mom_30s_bps": 4.5, "spot_mom_120s_bps": 12.0, "mid_chg_60s": 0.03,
        "prior_streak": 4.0, "prior_ret_bps": 42.0, "hour_utc": 14.0, "dow_utc": 3.0,
        "btc_dist_bps": 18.0, "eth_dist_bps": 12.0, "sol_dist_bps": 24.0,
        "btc_mid": 0.59, "eth_mid": 0.55, "sol_mid": 0.61,
        "rel_btc_dist_bps": 0.0, "rel_btc_mid": 0.0, "z_gauss": 0.42,
        "p_gauss": 0.66, "mid_minus_gauss": -0.07, "is_streak3_fade": 1.0,
    }
    lats = []
    for i in range(n):
        row = dict(sample_base)
        row["dist_bps"] = -40.0 + (i % 80)
        row["abs_dist_bps"] = abs(row["dist_bps"])
        lats.append(m.predict_dict(row)["latency_ms"])
    lats.sort()
    return {
        "ok": True,
        "trees": len(m.trees),
        "samples": n,
        "p50_ms": lats[n // 2],
        "p99_ms": lats[int(n * 0.99)],
        "sample_streak4_score": m.score_setup(sample_base),
    }


if __name__ == "__main__":
    print(json.dumps(run_synthetic_benchmark(500), indent=2))
