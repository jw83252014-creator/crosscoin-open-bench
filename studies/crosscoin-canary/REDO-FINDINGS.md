# CrossCoin Canary: redo on the one-minute candle tape (Fable, Nov 16, 2026)

Research only. No trading change. Asked by Jeff.

**Bottom line:** the co-direction is real and stable (80-87%). Buying the laggard when Bitcoin leads loses in every price band and every month. The only corner that leans positive is the reverse trade: ETH or SOL runs first early in the round and you buy Bitcoin. That lean is small and not yet proven.

## Data
- Source: `full_candles.jsonl`, Kalshi one-minute candles (bid and ask at each minute close) for BTC, ETH and SOL 15-minute rounds.
- 6,419 rounds with all three coins, Sep 9 to Nov 16, 2026 (Sep 1,993 / Oct 2,936 / Nov 1,490).
- Settlement label: Kalshi's official result. Cross-check against the candles: when the minute-14 candle is decisive (bid 90c+ or ask 10c or less), it matches the official result 98.46% of 9,788 times. The other 1.5% are last-minute flips, which is why the candle alone is not used as the label.
- Entry: the ask at the signal minute's close, first signal per round, hold to settlement, fee 0.07*p*(1-p).
- Script `redo.py`, full output `redo_output.txt`.

## (a) Settlement co-direction
| Pair | Same side | n | Sep / Oct / Nov |
|---|---|---|---|
| BTC = ETH | 83.4% | 6,419 | 82.6 / 83.3 / 84.6 |
| BTC = SOL | 80.0% | 6,419 | 80.4 / 79.1 / 81.1 |
| ETH = SOL | 82.1% | 6,419 | 82.4 / 81.2 / 83.3 |
| All three | 72.7% | 6,419 | 72.8 / 71.8 / 74.5 |
| SOL joins when BTC and ETH agree | 87.2% | 5,353 | 88.0 / 86.2 / 88.0 |

## (b) After BTC's side first reaches a level at minute t
How often the follower settled the same way, with the follower's own price at that moment in brackets.

| BTC first at | Minute | ETH same way | SOL same way | n |
|---|---|---|---|---|
| 85c+ | 1-3 | 85.7% (86.7c) | 85.2% (84.9c) | 385 |
| 85c+ | 4-6 | 85.2% (86.3c) | 83.4% (84.5c) | 1,294 |
| 85c+ | 7-9 | 84.6% (85.1c) | 81.9% (82.8c) | 1,699 |
| 85c+ | 10-13 | 80.2% (80.0c) | 75.5% (77.1c) | 2,142 |
| 90c+ | 1-3 | 89.4% (90.3c) | 92.3% (89.0c) | 104 |
| 90c+ | 4-6 | 90.3% (90.6c) | 88.9% (88.9c) | 776 |
| 90c+ | 7-9 | 88.1% (89.1c) | 85.8% (86.7c) | 1,533 |
| 90c+ | 10-13 | 85.1% (84.7c) | 79.8% (81.5c) | 2,577 |
| 90c+ | any | 87.0% (87.1c) | 83.3% (84.4c) | 4,990 |
| 95c+ | 4-6 | 95.2% (94.9c) | 95.7% (93.8c) | 208 |
| 95c+ | 7-9 | 95.0% (94.3c) | 92.8% (92.6c) | 995 |
| 95c+ | 10-13 | 89.8% (90.0c) | 84.7% (86.2c) | 2,909 |
| 95c+ | any | 91.3% (91.3c) | 87.2% (88.2c) | 4,122 |

The follower's price and its win rate track each other within one or two cents in every row. SOL after minute 10 wins less than it costs.

## (c) Laggard result by price band, leader at 90c+, after the fee
Net cents per contract. "Won" against "need" is the win rate against break-even.

| Laggard band | BTC leads, buy SOL | ETH leads, buy SOL | BTC leads, buy ETH | SOL leads, buy ETH | SOL leads, buy BTC | ETH leads, buy BTC |
|---|---|---|---|---|---|---|
| 10-30c | -2.97 (n=241) | +1.91 (239) | -5.42 (161) | -3.78 (243) | +2.18 (308) | -3.22 (198) |
| 30-50c | -9.08 (377) | -5.88 (339) | -9.95 (219) | -1.75 (366) | +2.81 (439) | -0.94 (271) |
| 50-60c | -11.93 (297) | -7.09 (281) | -3.11 (202) | -2.87 (310) | -2.43 (429) | -6.83 (266) |
| 60-70c | -10.39 (370) | -10.24 (415) | -8.06 (290) | +0.85 (459) | -0.11 (552) | -3.29 (426) |
| 70-80c | -9.88 (656) | -8.23 (707) | -5.78 (557) | -0.71 (802) | -1.25 (1,005) | -6.20 (783) |
| 80-90c | -2.80 (1,323) | -2.19 (1,548) | -2.18 (1,357) | -0.26 (1,750) | -0.67 (1,997) | -1.79 (1,896) |

- **BTC leads, buy SOL** (the article's setup): negative in all six bands. At 60-70c SOL won 56.2% against 66.6% needed. Negative in Sep, Oct and Nov in five of the six bands.
- **BTC and ETH both at 90c+, buy SOL:** worse, not better (60-70c: 54.0% won, -12.55c, n=189).
- **SOL leads:** close to break-even everywhere. Nothing here is clearly positive (best t is 1.2).

## (d) Best scenarios and walk-forward
Grid: leader (BTC, ETH, SOL, or two together) x laggard x level (85/90/95c) x laggard band x minute bucket (1-4, 5-8, 9-13).

**Walk-forward: pick on Sep+Oct, test on Nov.**
- 205 cells had 80+ trades in Sep+Oct. 37 were positive there.
- Of those 37, 20 were still positive in November (54%). Of the 168 negative cells, 48 turned positive in November (29%).
- All 37 picked cells pooled in November: n=2,958, net -0.35c per contract. Picking winners on Sep+Oct did not make money in November.

**The corner that carried over: buy Bitcoin at 80-90c in minutes 1-4 when ETH or SOL got there first.**

| Scenario | Sep+Oct | Nov |
|---|---|---|
| SOL 90c+, buy BTC 80-90c, min 1-4 | +4.40 (n=166, t=1.9) | +3.27 (n=55) |
| ETH 85c+, buy BTC 80-90c, min 1-4 | +1.91 (n=509, t=1.3) | +2.10 (n=155) |
| ETH+SOL 85c+, buy BTC 80-90c, min 1-4 | +2.52 (n=305, t=1.4) | +1.79 (n=102) |
| ETH 90c+, buy BTC 80-90c, min 1-4 | +2.66 (n=166, t=1.1) | +5.86 (n=39) |
| SOL 85c+, buy BTC 80-90c, min 1-4 | +2.46 (n=466, t=1.6) | +0.42 (n=155) |

- Whole sample, ETH 85c+ / buy BTC 80-90c / minutes 1-4: 87.5% won at 84.6c against 85.5% needed, +1.96c (n=664), positive in Sep, Oct and Nov.
- These five rows overlap heavily; they are one idea, not five confirmations.
- The top Sep+Oct pick with SOL as the laggard (ETH 90c+, buy SOL 80-90c, min 1-4: +6.30, t=2.7) went to -4.88 in November.

**How much to trust it:** of 175 whole-sample cells, 31 are positive and one clears t=2; luck alone would produce about four. 64 cells are worse than t=-2. The reverse-canary corner is a lead worth a paper test, not a demonstrated edge.

## (e) Caveats
- **One-minute resolution.** A signal and its fill are both taken at a minute close. Anything that happens and reverses inside a minute is invisible, and a millisecond script would not be filled at these exact prices.
- **Quotes, not trades.** Prices are the closing bid and ask of each minute, not last-trade prices and not a fill. Depth is unknown, so size beyond a few contracts is unverified.
- **Entry at the ask assumes the quote was still there.** The median spread was 1c and the 90th percentile 2c, so the books were tight, but a fast move can pull the ask before an order lands.
- **Kalshi 15-minute only.** No Polymarket, no 5-minute markets.
- **Fee is the taker fee, unrounded.** Small orders pay slightly more after rounding. Maker entries were not tested.
- **Many cells were searched** (205 in the walk-forward, 175 on the whole sample). Treat any single cell as a candidate.
- **One entry per round per cell.** Coins move together, so trades in the same round are not independent; t-values are clustered by round.
- **Ten weeks, mostly a falling market.** A different regime could change the corner that leans positive.
