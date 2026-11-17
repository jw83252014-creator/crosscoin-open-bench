# Study 3: 15m Overextension Fade — Paper vs Live-L2 Passive Maker Shadow

> **Accounting labels:** Every number below is explicitly tagged **[PAPER]** or **[SHADOW]**. None of these figures are real-money P&L.

## 1. The Question
On 15-minute BTC/ETH/SOL up/down contracts, early 2–3 sigma price spikes in minutes 1–4 frequently overshoot spot reality. Does fading those spikes survive once we replace optimistic midpoint assumptions with:
1. De-duplicated signal counting (one entry per unique market signal),
2. Actual printed trade-tape volume (`shadow_real` check), and
3. Strict passive maker trade-throughs on a live WebSocket L2 feed?

## 2. Observed Results Across Three Realism Tiers

| Tier | Setup & Fill Rule | Sample (`n`) | Win–Loss | Headline Result | Label |
|---|---|---|---|---|---|
| **Tier A — Paper (de-duplicated)** | Consolidated 15m fade (`FADE15U`), Kalshi 15m quotes, taker fee `0.07 * p * (1 - p)` netted, 5%-of-bank sizing ($10 floor, $250 cap, 15% window cap) | `n = 279` unique signals (Nov 11–17, 2026) | `268W – 11L` (96.0%) | `+$8,397.31` (vs `+$1,167` at flat $25/trade; stake shape alone drove the gap) | **[PAPER]** |
| **Tier B — Printed-Tape Replay Probe** | Re-walk paper entry against actual Kalshi printed trades within 60s at/below limit price; require real `+12c` print for early TP else hold to settlement | `n = 1` method-proof probe (XRP 15m, Nov 17 09:00 PT) | `1W – 0L` | Paper booked `+$126.19` (`476.19` contracts); real tape printed `195.52` contracts at/below `21c` (VWAP `18.75c`) -> **`+$18.92`** (~85% size haircut from book depth) | **[SHADOW]** (tape replay, `n = 1` illustration) |
| **Tier C — Live-L2 Passive Maker Shadow** | Post resting maker bids at `15–27c` on live Polymarket US 15m WebSocket L2; count entry **only** on strict trade-through; rest `+16c` maker exit (`+0.25c/sh` maker rebate) | `n = 37` settled ETH+SOL (`39` filled) + `n = 17` settled BTC (`18` filled), Nov 17, 2026 | ETH+SOL: `27W – 10L` (73.0%, 27 early maker exits)<br>BTC: `11W – 6L` (64.7%) | ETH+SOL: **`+$34.46`** at flat `$5`/trade (`+$146.67` on `$400` 5%-compounding shadow bank)<br>BTC: **`+$4.77`** at flat `$5`/trade | **[SHADOW]** (live WS L2, **small single-day sample**) |

## 3. What Broke & What Survived
- **Single-book depth caps compounding quickly:** Paper compounding assumes `$250` clips fill cleanly at `18–25c`. On a single venue's 15m book, real printed volume at that price is often a fraction of intended size.
- **Regime dependence:** The Nov 17 live-L2 shadow window ran during a `CALM_RANGE` mean-reverting session (where momentum copy-trading went `3W – 31L`, `-$13.65` shadow). In a sustained macro trend/breakout session, unhedged fades face correlated tail losses across coins (`15%` per-window exposure cap and rolling-40 `<92%` half-stake demotion are mandatory).
- **Multi-venue consensus vs blind fan-out (open architecture problem):** Splitting clips across multiple regulated/on-chain venues reduces single-book impact, **but** blindly firing all venues on a true breakout multiplies losses. Using cross-venue quote dispersion as a *consensus filter* (fading a single-venue `82c` outlier when peer venues sit at `74–76c`) is an open research track we invite contributors to test.
