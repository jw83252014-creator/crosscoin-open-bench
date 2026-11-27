# Study 6 — Two-Speed Quant Brain: `v1` LightGBM Abstain-Gate (`0.066 ms`), `PHOENIX_FLIP_DIP` Ask-Cross Proof & `Qwen3-32B` Red-Team Audit (Nov 26, 2026)

*Question: Can a strictly causal LightGBM abstain-gate cut losses on short-horizon crypto prediction-market setups in under 1 ms locally — and where do our newest shadow/paper ideas hold up or break under brutal execution stress?*

> **Honesty label:** Every figure below is strictly labeled **paper**, **shadow**, or **real** (where real fills are only summarized at the aggregate level and are not reproducible from this repo). We publish the **red results and model catches too**.

## 1. `v1` Abstain-Gate Out-of-Sample Benchmark (`NVIDIA A100-SXM4-80GB`)

- **Dataset:** `23,546` strictly causal multi-coin ticks across `2,925` completed `BTC/ETH/SOL` 15m rounds (`36` features, `0` NaNs).
- **Strict Chronological Split (Zero Leakage):** Train `15,598` | Val/Isotonic Cal `3,623` | Unseen OOS Test `4,325`.

| Metric / Model | Unseen OOS Result | Honest Note |
|---|---|---|
| Physics Gaussian Baseline (OOS Brier) | `0.19775` | Raw Brownian model |
| Fast Reflex `v1` LightGBM (`145` trees, OOS Brier) | `0.16894` | Big jump over physics |
| 4-Model GPU Ensemble (OOS Brier) | `0.16706` | Still trails Kalshi Mid (`0.16544`) — **v2 adds Volume Profile + diurnal features to beat `<0.1650`** |
| **Streak-4 Open Fade (Raw OOS)** | **`60.0%` (`n = 30`)** | Unfiltered OOS test window |
| **Streak-4 Open Fade (`v1` Gated `p >= 52%`)** | **`73.3%` (`n = 15`, `+13.3%` WR lift)** | Small OOS `n = 15`; promising filter, needs larger forward shadow `n` |
| Pure-Python Mac mini CPU Latency (`abstain_gate_inference.py`) | **`0.066 ms` p50** (`0.139 ms` p99) | Reproducible locally via `tools/two-speed-quant-brain/` |

**Top `v1` Feature Importances:** `prior_ret_bps (708)`, `hour_utc (621)`, `dow_utc (387)`, `sol_dist_bps (308)`, `bid (235)`, `btc_dist_bps (194)`, `eth_dist_bps (191)`, `spot_mom_30s_bps (173)`.

## 2. `PHOENIX_FLIP_DIP` — Crossing Full Ask + `1.5¢` Taker Fee (`2,925` Rounds, Paper)

*Rule:* A side starts at `<=20¢`, violently flips to `>=80¢/85¢`, then dips back to `<=60¢/55¢`.

| Variant | `n` | Win Rate | `0%` Maker EV / sh | **Full Ask + `1.5¢` Taker Fee EV / sh** | Label |
|---|---:|---:|---:|---:|---|
| `CLASSIC (<=20 -> >=80 -> <=60)` | `67` | `47.8%` | `+7.72¢/sh` | **`+4.44¢/sh`** | paper (single-venue, zero Leg-2 risk) |
| `DEEPDIP (<=20 -> >=85 -> <=55)` | `37` | `45.9%` | `+10.51¢/sh` | **`+6.99¢/sh`** | paper (small `n`, shadow-testing next) |

*(Notice the asymmetric payoff: `<50%` win rate is strongly `+EV` because entry is `<=55¢–60¢` and winners settle at `100¢`.)*

## 3. Cross-Venue Arb & Middle Stress Test (`Polymarket / Kalshi × Gemini`, Shadow)

Shadow arb books regularly display deceptive `100%` win rates (`ARB_15M_POLY_GEMINI_MAKER 415W–0L`, `MIDDLE_1H_POLY_GEMINI_MAKER 52W–0L`). When stressed against **10% Leg-2 misses (`-8¢` FOK unwind)**, **50% `<=5 bps` oracle-pin flips**, and **thin Gemini depth (`10–60` shares)**:
- **SURVIVES STRESS:** `MIDDLE_1H_POLY_GEMINI_MAKER` (`52W–0L`, 6 double-wins in shadow) and `ARB_15M_POLY_GEMINI_TAKER`.
- **FAILS STRESS (RED RESULT):** `KALSHI×GEMINI 15M TAKER` (`1.5%` Kalshi taker fee + thin depth erases the edge).

## 4. `Qwen/Qwen3-32B` `$0/token` A100 Audit — & Why LoRA (`Qwen/Qwen3.8-27B`) Is Next

Running `Qwen/Qwen3-32B` (`BF16`, `26.2s` load, `$0.00/token`) across our `18,906`-trade ledger + `v1` model card delivered two concrete upgrades AND one honest catch:
- **Verified Wins:** Flagged **diurnal (`hour_utc`) non-stationarity** in streak fades (`hour_utc` was our #2 LightGBM split!) and specified 5 concrete `v2` microstructure features (`tools/two-speed-quant-brain/strategy_blueprints.py`).
- **Honest Catch (Red Result on Base LLM):** Base `Qwen3-32B` conflated our cross-venue Leg-2 stress template onto single-venue `PHOENIX_FLIP_DIP` in Pass 3. That grounding catch directly motivates our next sprint: **fine-tuning a `Qwen/Qwen3.8-27B` LoRA adapter** on calibrated post-mortems + verified ledgers so Speed 2 stays strictly grounded in real desk telemetry.
