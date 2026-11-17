# crosscoin-open-bench

A public build of short-horizon crypto prediction-market research on Kalshi and Polymarket 5-minute and 15-minute up/down markets. We publish the studies, the scripts, and the **red results too**, and invite other builders to bring their own fills and compare.

> **Not trading advice.** Everything here is research on historical or recorded data. Results are **paper** or **shadow** (simulated fills against recorded quotes or order books). None of it is live-money P&L, and past results do not predict future results. Do not copy a rule from here into a live account.

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

Files: `article-v2.md` (the write-up, a draft), `REDO-FINDINGS.md` (independent cross-check by a second agent), `jeff_trade.py` and `jeff_output.txt` (the exact trade rule and its output).

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
