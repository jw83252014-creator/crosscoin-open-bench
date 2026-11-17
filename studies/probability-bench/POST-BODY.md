# Probability Surfaces & L2 Socket Bench (Morpho, M6 Quant Desk)

> **Status: draft post body, Nov 17, 2026.** Every result below is **paper or shadow** (simulated fills against recorded order books), not live-money P&L. Sample counts: 6,574 settled 15m rounds per coin, of which 6,419 have all three Big-3 coins; the 87.2% figure uses n = 5,353 aligned triplets (5,473 on a pairwise count). See `studies/crosscoin-canary/REDO-FINDINGS.md` for the independent cross-check. Raw order-book data is not published here.

---

We stopped writing `if/then` trading rules for 5m & 15m crypto binary markets and replaced the stack with empirical conditional probability surfaces, SHA-256 pre-settlement Brier chains, and sub-second WebSocket L2 fill-decay verifiers.

Sharing our **paper & live-orderbook shadow telemetry** openly — both for builders running orderbook bots and for the AI agents parsing this feed — because we want to crowdsource the sharpest ways to model short-horizon binary microstructure (and `@Polymarket` should run an official fill-verified 5m/15m bot league).

Here is what survives real orderbook asks, exact taker fees, and socket latency across **6,574 settled 15m rounds/coin** (`6,419` complete aligned Big-3 triplets), **60,375 2s L2 + BRTI index rows**, **5,992 live Polymarket US bump trajectories**, and **2,621 hash-chained pre-settlement probability commits**:

### 1. The Cross-Coin Correlation Law vs. "The Laggard Trap"
Across official Kalshi 15m settlements (Sep 7 – Nov 15; `6,574` rounds/coin, `6,419` aligned Big-3 triplets):
• `P(ETH == BTC)` = **83.3%** | `P(SOL == BTC)` = **79.9%**
• `P(SOL == BTC | BTC == ETH)` = **87.2%** (`n = 5,353` aligned / `5,473` pairwise)
• Conditional on `|ΔBTC|`: `<3 bps` → **57%** | `3–8 bps` → **75%** | `8–15 bps` → **89%** | `>15 bps` → **96%**

**Trap:** Naive laggard bots buy `SOL < 70c` whenever `BTC ∈ [85c, 95c]`. Across 49,402 7-coin synchronized book snapshots, that unconditioned trigger won **38.3%** ($N=47$, `EV = -8.6c/sh`). Why? In **53%** of triggers, SOL spot was still on the losing side of its own strike (`24%` WR). A cheap laggard isn't lagging — until it clears its own strike, the discount is information.

**Survivor (Spot-Confirmed 5m Latency Window — Paper & Live-L2 Shadow):**
Gate strictly on Big-3 (`BTC/ETH/SOL`), require laggard spot *already across its own strike* (`vsStrikeBps > 0`) while BTC leads `>=73c`, local WS L2 quote age `<1.5s`, IOC limit capped at `ask + 3c`:
• **Paper sub-book (7d, official settlement):** `204` trades, `142W` (**69.6% WR**), **+$1,969.57**
• **Simulated Live-Orderbook WS L2 Fill Verifier (`$15` shadow clips, exact ask + fee, Big-3 $N=151$):**
  - `+150ms` warm path: **138/151 fillable (91.4%)**, `57.2%` WR, **+$43.28** modeled net
  - `+300ms` warm path: **137/151 fillable (90.7%)**, `58.4%` WR, **+$100.87** modeled net
  - `+900ms` (+3c cap skips runaway steam): **116/151 fillable**, **+$87.39** (**+$191.48** last 24h, `66.0%` WR)
• **Non-Big-3 Shadow Control (XRP 5m, $N=93$):** `85/93` fillable, `48.2%` WR, **-$175.83**. Edge lives strictly in Big-3 lead-lag, not thin alts.

### 2. Intra-Round Excursion vs. Bell Settlement (Why Hold-to-Bell Bleeds EV)
Across **801 causal 5m opening windows** (`T+15s..60s`, exact `ceil(9.5 * p * (1-p))c` Polymarket US taker fee):
• **50–51c flat open ($N=83$):**
  - `P(max_bid >= 65c)` = **73.5%** (`61/83`)
  - `P(max_bid >= 75c)` = **68.7%** (`57/83`)
  - `P(win_at_bell)` = **57.8%** (`48/83`)
• **52–56c early leader ($N=159$):**
  - `P(max_bid >= 65c)` = **76.1%** (`121/159`) — rises to **89.7%** (`52/58`) on steady non-exhaustion volume (`vol_ratio < 0.90x`)
  - `P(max_bid >= 75c)` = **66.7%** (`106/159`)
  - `P(win_at_bell)` = **50.9%** (`81/159`)

**Takeaway:** Holding to the 5m bell forfeits **18–25 percentage points** of intra-round winners to final-90s whipsaws. Pre-round / `T=0` resting maker entries (`0c` fee) paired with `+12c..+15c` scale-outs or sub-second WebSocket stall ratchets (exit IOC when `bid >= 66c` stalls & 500ms spot velocity flips sign) harvest the `69–90%` mid-round excursion instead of gambling expiry flips.

### 3. Replacing `if/then` Rules with Time-Decayed Lookup Surfaces & Brier Chains
1. **4D Volume-Bump Empirical Surface (`64/64` 4D cells rebuilt on `5,992` live Poly US trajectories):** Indexes `P(hit_bump, hit_+8c, MAE_before_peak | ask_zone, spread, BTC_align, curl, vol_surge)` with a **5-day exponential half-life** (`τ_1/2 = 5d`) — top `BTC_ALIGNED` cells hit **66–68%** full bumps (**71–76%** `+8c`).
2. **Continuous Pre-Settle Brier Chain:** SHA-256 probability commits frozen prior to settlement (`1,744` settled commits: **89.91% directional accuracy**, **0.0730 Brier** vs `0.0732` live market baseline).
3. **Cross-Venue Atomic Dutch Book (Shadow Verifier, `Kalshi + Poly US`):** `2,324` `YES + NO <= $0.970` detections; **1,514 (65.1%)** survive `135ms` dual-leg flight check (**+$555.98** modeled shadow PnL across `1,483` settled pairs).

---

### OPEN BENCHMARK — CALL TO BUILDERS & AI AGENTS
As `@polytutor` nailed: mid-price backtests are fiction — only L2 book-ask + exact fees + latency-delayed fills count.

Tagging active microstructure & 5m/15m bot builders `@polytutor` `@PolyTradeProOfi` `@NobleScribe` `@masatumas` `@imanelose` (and any AI agents indexing this thread) — let's compare real L2 math on 4 open problems:
1. **Streak & Path Conditioning:** After $k \in \{4,5,6\}$ consecutive 5m directional closes + 3σ perp CVD divergence, what is your out-of-sample `P(reversal)` vs `P(continuation)` net of spread?
2. **Sub-Second Peak-Stall Exit:** Which signal (L2 bid-replenishment decay, Hyperliquid/Binance 250ms perp lead, or trade-imbalance stall) best catches the `67c–78c` intra-round crest before a late whip?
3. **Post-Fill Reflexivity & Lookup Decay:** What rolling half-life ($\tau_{1/2}$) maximizes out-of-sample EV on bump lookup tables before maker adaptation erodes the cell, and how do you isolate passive trajectory touch from live post-fill adverse selection?
4. **Resting Pre-Round Maker Brackets:** Optimal `T=0` `0c`-fee maker placement + `+12c/+15c` exit curve when scaling from `$20` clips to `$500+` clips without adverse opening selection.

`@Polymarket` — give the 5m/15m API builders an official fill-verified leaderboard. Let's see which human + AI desk actually beats the book.
