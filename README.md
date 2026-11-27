# crosscoin-open-bench

A public build of short-horizon crypto prediction-market research on Kalshi and Polymarket 5-minute and 15-minute up/down markets. We publish the studies, the scripts, and the **red results too**, and invite other builders to bring their own fills and compare.

> **Not trading advice.** Everything here is research on historical or recorded data. Results are **paper** or **shadow** (simulated fills against recorded quotes or order books). None of it is live-money P&L, and past results do not predict future results. Do not copy a rule from here into a live account.

## 60-Second Quickstart (Test Your Own L2 Fill Decay)

Zero dependencies (Python 3.9+ standard library only). Test whether your intended limit orders still survive on the order book at `+0 / +150 / +300 / +900 ms`:

```bash
git clone https://github.com/jw83252014-creator/crosscoin-open-bench.git
cd crosscoin-open-bench
python3 scripts/l2_fill_decay_verifier.py --book examples/example_book.jsonl --orders examples/example_orders.csv
```

Expected output on the synthetic `examples/` fixture:
```text
latency_ms  n_scored  survived  gone  no_data  survival_rate
         0         3         3     0        1         100.0%
       150         3         2     1        1          66.7%
       300         3         1     2        1          33.3%
       900         4         0     4        0           0.0%
```
Feed `--book` your own recorded L2 top-of-book JSONL/CSV and open an issue with the **L2 Fill-Decay Checker Results** template (see `CONTRIBUTING.md` for exact 1-line JSONL schema).

## Labels used everywhere

- **Paper**: a rule scored on historical quotes, fills assumed at the quoted price.
- **Shadow**: a rule run against a live order-book feed with simulated fills (latency and fee modeled), no real order sent.
- **Real**: an actual exchange fill. There are none in this repo. Real fills are mentioned only where a study says so, and are not reproducible from here.
- Every result carries its **n**. Small samples are marked.

## Studies so far

### 1. CrossCoin Canary (`studies/crosscoin-canary/`), Kalshi 15m, paper
*Question: when Bitcoin's contract is at 90c, does buying a lagging SOL contract at 50-65c pay?*

| Headline | Value | Label |
|---|---|---|
| Rounds with BTC, ETH, SOL all trading (Sep 9 to Nov 16, 2026) | 6,419 | paper (official Kalshi results) |
| SOL settles the same way as BTC and ETH, when those two agree | 87.2% (n = 5,353) | observed |
| The trade (buy $20 of SOL at 50-65c once BTC first hits 90c, hold to settlement) | 207 trades, 47.8% won, avg ask 57.4c, **-11.3c per contract, -$833 total at $20/trade** | paper, minute-close quotes, taker fee 0.07 * p * (1 - p) |
| Break-even win rate at that price | about 59% | arithmetic |
| Best of 368 variants tried | 31 trades, 67.7% won, +$74.50 | paper, picked after the fact, **not proven** |
| Reverse corner (buy BTC at 80-90c in minutes 1-4 after ETH or SOL leads) | +1.96c per contract, n = 664 | paper, a lead for a forward test, not an edge |

Files: `REDO-FINDINGS.md` (independent cross-check by a second agent), `jeff_trade.py` and `jeff_output.txt` (the exact trade rule and its output).

### 2. Probability Bench (`studies/probability-bench/`), Kalshi 15m and Polymarket 5m, paper and shadow
*Question: can empirical probability tables replace hand-written if/then rules, once real asks, fees and latency are included?*

| Headline | Value | Label |
|---|---|---|
| SOL matches BTC when BTC and ETH agree | 87.2% | paper, official settlements |
| Cheap-laggard buy (SOL under 70c while BTC is 85-95c) | 38.3% won, n = 47, -8.6c per share | paper, **small sample** |
| Same setup gated on the laggard's spot already across its own strike (7 days) | 204 trades, 69.6% won, +$1,969.57 | **paper** |
| The same gate with a modeled fill at +150 ms / +300 ms | 91.4% / 90.7% fillable, +$43.28 / +$100.87 | **shadow**, simulated fills |
| Non-Big-3 control (XRP 5m) | 48.2% won, -$175.83 (n = 93) | shadow |
| Hold to the bell vs sell the excursion (801 five-minute windows) | bid hit 65c in 73.5% of 50-51c opens, 57.8% won at the bell | paper |
| Brier chain, 1,744 settled forecasts | Brier 0.0730 vs 0.0732 for the market | observed; the gap is tiny |
| Cross-venue dutch-book detector | 2,324 found, 1,514 survived a 135 ms check, +$555.98 | **shadow, simulated profit, not money** |

Sample counts differ between agents (6,574 rounds per coin vs 6,419 complete triplets, n = 5,473 vs 5,353 for the 87.2% figure). Both are counted on different windows and are reconciled in the study notes.

### 3. 15m Overextension Fade — Paper vs Live-L2 Passive Maker (`studies/passive-maker-fade-15m/`), paper and shadow
*Question: how much of a 96% paper 15m fade survives de-duplication, printed-tape depth checks, and strict live-L2 passive maker trade-throughs?*

| Headline | Value | Label |
|---|---|---|
| Consolidated 15m fade (`FADE15U`), de-duplicated unique signals | 268W–11L (96.0%), `n = 279`, +$8,397.31 at 5% compounding vs +$1,167 flat $25 | **paper**, fees netted |
| Single-probe replay against printed Kalshi trade tape | +$18.92 (`195.52` contracts printed <=21c) vs +$126.19 paper (`476.19` contracts) | **shadow**, `n = 1` depth illustration |
| Passive maker resting `15-27c` -> `+16c` maker exit (`+0.25c/sh` rebate), ETH+SOL 15m | 27W–10L (73.0%), `n = 37` settled, +$34.46 at flat $5 (+$146.67 on $400 compounding) | **shadow**, live WS L2, **small single-day sample** |
| Momentum sharp-copy control during same `CALM_RANGE` window | 3W–31L, `n = 34`, -$13.65 | **shadow** |

## How to reproduce

1. Python 3.9+ and nothing else (standard library only).
2. Fetch the public candles (see `data/README.md`; no account or key is needed):
   ```bash
   python3 scripts/fetch_kalshi_candles.py --out studies/crosscoin-canary --since 2026-09-09
   ```
3. Run the Canary trade rule:
   ```bash
   python3 studies/crosscoin-canary/jeff_trade.py
   ```
   Compare with `studies/crosscoin-canary/jeff_output.txt`. Your window may be longer, so counts can differ; the rule and fee model are the same.
4. The probability-bench study uses recorded order-book data that is **not published** here. Its numbers are documented but not yet reproducible from this repo.

## Fill-survival check (`scripts/l2_fill_decay_verifier.py`)

Feed it your own recorded top-of-book snapshots and the orders you meant to send. For each latency (0, 150, 300, 900 ms by default) it reports the share of orders whose limit price and size were still available at send time plus latency. It does not model queue position, partial fills or fees, and it contains no results of its own. The files in `examples/` are **synthetic** test data.

```bash
python3 scripts/l2_fill_decay_verifier.py --book examples/example_book.jsonl --orders examples/example_orders.csv
python3 -m unittest discover -s tests
```

`scripts/yozapata_drift_breaker.py` is an **illustration** of a paper-to-live drift rule @yozapata described on X (demote back to paper if R per trade drifts more than 0.3R from paper). It is not tuned or tested on our data.

## Before you commit anything

```bash
bash scripts/scrub_check.sh
```

It fails on keys, tokens, emails, account IDs, environment files and a few banned strings. Never commit raw venue data, account or order IDs, live order settings, or contact details.

## Data and licenses

- Code: MIT (`LICENSE`).
- Our own derived results and write-ups: CC BY 4.0 (`DATA-LICENSE`).
- Raw venue data is not included and stays under the venue's terms. See `data/README.md`.

## Contribute

Open an issue or PR with your own study or fills (timestamp, venue, market, side, limit price, fill price, size, and the price 10 and 60 seconds later). Label it paper, shadow or real, and include n. We won't publish anyone's fills without asking first.


### 4. Three-Brain Audit: `ER48` Regime Router & Brownian Physics `Phi(z_rem)` Peak-Lock (`studies/three-brain-er48-phi-zrem-2026-11-19/`), 15m BTC, paper + live-L2 shadow
*Question: Can a single-parameter regime prior (`ER48`) + zero-parameter Brownian close-to-strike exit beat live market odds and static `69¢` caps?*

| Headline | Value | Label |
|---|---|---|
| Pre-Round passive maker bids (adverse selection) | `38.8%` filled WR (`-10.20¢/sh`) vs `74.1%` runaway WR (`n = 166`) — **KILLED** | paper (Kalshi 15m replay) |
| Static unfiltered `TP69` (`69¢` maker cap) | `212W–85L` (`71.4%`), **`-6.06¢/sh`**, `2/7` days green (`n = 297`) | paper (Kalshi 15m replay) |
| Astra 1-Param `ER48` Market-Prior Residual Brier | **`+0.00111`** Brier beat OOS (`0.24310` vs `0.24422`, `n = 341` fills) | paper (Kalshi 15m replay) |
| 3-Shape Router (`ROUTER_V1`: `0.15 <= ER48 <= 0.35`, Dual-Trend + Big-3 -> Hold + `Phi(z_rem)`, sit out Chop `<0.15`) | `32W–10L` (`76.2%`), **`+19.00¢/sh`**, `MaxDD 108¢`, `6/6` active days green (`n = 42`) | paper (Kalshi 15m replay; small `n`, shadow-testing on Poly US) |
| Carbon Brownian Physics `Phi(z_rem)` Peak-Lock | **`+3.86¢/sh`** vs Hold-to-Bell (`n = 257` triggers in `n = 633` windows, 0 fitted weights) | paper (Kalshi 15m replay) |
| Live-L2 Polymarket US 10-arm shadow racer (`poly_3brain_shadow_racer.py`) | Unfiltered `TP69` `14W–3L (+14¢/1sh)`; trend-gated `x_t > 0` dodged all 3 chop losses (`4W–1L`, small `n`) | shadow (live Poly US L2) |

### 5. Slug-Rollover Bug Catch + Clean 7-Hour 5m Shadow Audit (`studies/tanto-5m-shadow-audit-2026-11-24/`), 5m Crypto, shadow
*Question: What happens after fixing a silent slug-rollover phantom-win bug and enforcing `+1¢` trade-through queue clearance on 5m passive maker scalping?*

| Headline | Value | Label |
|---|---|---|
| Big 3 (`BTC+ETH+SOL`, `n = 156` in `7h`) `+14¢` TP | **`114W–42L` (`73.1%`)**, `+339.0¢` (`+$104.99` on `$10` clips) | shadow (`+1¢` queue-cleared) |
| Big 3 (`BTC+ETH+SOL`, `n = 156` in `7h`) `+20¢` TP | **`102W–54L` (`65.4%`)**, `+433.0¢` (`+$135.02` on `$10` clips) | shadow (`+1¢` queue-cleared) |
| Non-Big-3 control (`XRP 5m`, `n = 45`) | `25W–20L` (`-225.0¢` TP14) / `22W–23L` (`-228.0¢` TP20) | shadow (**red result**) |
| 15m Multi-Coin Scalpers control (`MC15M`, same `7h`) | `31W–36L` (`46.3%`), **`-410.0¢`** (`SOL 15m` `-264¢`) | shadow (**red result**) |
| Session split (`BTC+ETH+SOL`, `1 AM ET` Asia vs `2 AM+ ET` London) | `1 AM ET`: `-267¢` / `-250¢`; `2 AM–7 AM ET`: `+485¢` / `+720¢` | shadow (single night, small `n`) |

Open reference tools added in `tools/sensor-bus-v3/`: `$0/mo` `HYG/IEF` credit-spread crash sensor (`credit_spread_guard.py`) and strict `slug_rollover_guard.py` (with unit tests in `tests/test_sensor_bus_v3.py`).

### 6. Two-Speed Quant Brain: `0.066 ms` LightGBM Abstain-Gate, `JEV v4` Episodic Memory & Stress Tests (`studies/two-speed-blackwell-audit-2026-11-26/`), 15m / 1H Crypto, paper + shadow
*Question: Can a strictly causal 145-tree LightGBM abstain-gate running locally in pure Python (`<0.1 ms`) lift out-of-sample Streak-4 Fade accuracy, and which new strategies survive brutal ask-cross and Leg-2 stress?*

| Headline | Value | Label |
|---|---|---|
| `v1` LightGBM Abstain-Gate (`23,546` causal ticks, `4,325` strict OOS rows, A100-80GB) | OOS Brier `0.16894` (4-model ensemble `0.16706`) vs Physics `0.19775` and Kalshi Mid `0.16544` (**honest: hasn't beaten Mid yet — v2 adds Volume Profile + diurnal features**) | paper (strict chronological OOS) |
| **Streak-4 Open Fade OOS Lift (`v1` gate `p >= 52%`)** | **`60.0%` (`n = 30`) -> `73.3%` (`n = 15`, `+13.3%` WR lift)** | paper (small OOS `n = 15`) |
| Pure-Python CPU Reflex Latency (`tools/two-speed-quant-brain/abstain_gate_inference.py`) | **`0.066 ms` p50** (`0.139 ms` p99), zero dependencies | reproducible locally |
| `PHOENIX_FLIP_DIP` (`<=20c -> >=80/85c -> <=60/55c`, `2,925` rounds) | CLASSIC (`n = 67`): **`+4.44c/sh`** | DEEPDIP (`n = 37`): **`+6.99c/sh`** even crossing full Ask + `1.5c` taker fee | paper (single-venue) |
| Cross-Venue Stress Test (`Polymarket/Kalshi x Gemini`, 10% Leg-2 miss + 50% `<=5 bps` pin flip) | `MIDDLE_1H_POLY_GEMINI_MAKER` survives green; **`KALSHI x GEMINI 15M TAKER` fails stress** | shadow (**red result included**) |
| `JEV v4` "Lucy's Book" Persistent Episodic Memory (`tools/two-speed-quant-brain/jev_v4_lucys_book.py`) | SQLite Top-K similarity recall + Brier grading + pluggable `Qwen/Qwen3-32B` / `Qwen/Qwen3.8-27B` LoRA backend | reproducible locally |

**Try the Two-Speed Quant Brain locally in 10 seconds (zero external dependencies):**
```bash
python3 tools/two-speed-quant-brain/abstain_gate_inference.py
python3 tools/two-speed-quant-brain/jev_v4_lucys_book.py --self-test
python3 tools/two-speed-quant-brain/strategy_blueprints.py
```
