# Study 5: Catching a Slug-Rollover Phantom-Win Bug + Clean 7-Hour 5m Shadow Audit (Nov 24, 2026)

> **Label:** `shadow` (live Polymarket US WebSocket L2 top-of-book feed, simulated maker entries with strict `cur_slug == pos["slug"]` checking, `1.5s` pre-bell cutoff, and `+1¢` queue-clearance requirement — **no real exchange fills are represented in this dataset**).

## 1. The Bug We Caught (Why Every Shadow Bench Needs a Slug-Rollover Guard)

While auditing our live-L2 5-minute and 15-minute shadow scalpers, we caught a silent accounting bug that inflated apparent win rates and inverted our take-profit parameter comparison:

- **What went wrong:** Our shadow take-profit check evaluated `best_bid >= tp_target` *before* confirming that the live WebSocket feed's current market `slug` still matched the open position's `slug`.
- **The failure mode:** Roughly `0.7s` after a 5m/15m window closed (before the `+1.0s` settlement handler ran), the order-book sidecar rolled to the *next* window's `50¢` opening quote. A losing trade entered at `<= 36¢` suddenly saw a `50¢` bid from the *next* round and booked a fake `+14¢` or `+20¢` win.
- **Why it was extra dangerous:** It disproportionately rewarded wider targets (`+20¢`), tricking the naive shadow table into ranking `+20¢` far ahead of `+14¢` before the fix.
- **The fix (`tools/sensor-bus-v3/slug_rollover_guard.py`):**
  1. Require `current_slug == position.slug` strictly before evaluating any mid-round exit.
  2. Enforce a pre-bell cutoff (`now < close_ts - 1.5s`) so stale final-second ticks never book phantom exits.
  3. Require **`+1¢` trade-through queue clearance** (`best_bid >= tp_target + 1.0`) so resting maker exits only score when the book actually clears through our price level.
  4. Archive pre-fix shadow ledgers and reset all patched benches cleanly to `0W–0L`.

## 2. Clean Post-Fix 7-Hour Live-L2 Shadow Audit (`n = 201` per TP bench)

Window: **2026-11-24 `04:55 UTC` – `12:05 UTC`** (`11:55 PM ET` – `7:05 AM ET`, `7.1 hours`, zero-phantom, `+1¢` queue-cleared). All entries are simulated passive maker fills (`<= 44¢` cap, `0%` maker fee) on 5-minute crypto up/down contracts.

### A. 5-Minute Coin-by-Coin Breakdown (`TANTO 5M`, `n = 201` per TP arm)

| Coin | Avg Entry | `+14¢` TP (`W–L`, WR) | `+14¢` PnL (`1sh` / `$10` clip) | `+20¢` TP (`W–L`, WR) | `+20¢` PnL (`1sh` / `$10` clip) | Label |
|---|---:|---|---:|---|---:|---|
| **BTC 5m** | `31.3¢` | `34W–15L` (`69.4%`) | `+34.0¢` (`+$10.87`) | `31W–18L` (`63.3%`) | `+90.0¢` (`+$28.79`) | shadow |
| **ETH 5m** | `32.5¢` | `42W–12L` (`77.8%`) | `+233.0¢` (`+$71.73`) | `35W–19L` (`64.8%`) | `+144.0¢` (`+$44.33`) | shadow |
| **SOL 5m** | `32.2¢` | `38W–15L` (`71.7%`) | `+72.0¢` (`+$22.39`) | `36W–17L` (`67.9%`) | `+199.0¢` (`+$61.90`) | shadow |
| **XRP 5m (Control / Bleed)** | `31.3¢` | `25W–20L` (`55.6%`) | **`-225.0¢` (`-$71.96`)** | `22W–23L` (`48.9%`) | **`-228.0¢` (`-$72.92`)** | shadow |
| **All 4 Coins (`n = 201`)** | `31.8¢` | `139W–62L` (`69.2%`) | `+114.0¢` (`+$35.82`) | `124W–77L` (`61.7%`) | `+205.0¢` (`+$64.41`) | shadow |
| **Big 3 Only (`BTC+ETH+SOL`, `n = 156`)** | `32.0¢` | **`114W–42L` (`73.1%`)** | **`+339.0¢` (`+$104.99`)** | **`102W–54L` (`65.4%`)** | **`+433.0¢` (`+$135.02`)** | shadow |

### B. Session Regime Split (Eastern Time, `BTC + ETH + SOL` Only)

| Hour (`ET`) | Session | `+14¢` TP (`1sh`) | `+20¢` TP (`1sh`) | Observation |
|---|---|---:|---:|---|
| `12:00 AM` | Late US / Early Asia | `+121¢` | `-37¢` | Tighter target catches choppy mean-reversion |
| `01:00 AM` | Thin Asia Dead-Zone | **`-267¢`** | **`-250¢`** | **Lone deep-red hour across both targets** |
| `02:00 AM` | London Pre-Open | `+233¢` | `+331¢` | Liquidity arrives; sharp snapbacks resume |
| `03:00 AM` | London Open | `-8¢` | `+59¢` | Flat on TP14, green on TP20 |
| `04:00 AM` | Mid-London | `+103¢` | `+162¢` | Clean two-way order flow |
| `05:00 AM` | Late London | `+129¢` | `+179¢` | Sustained maker spread capture |
| `06:00 AM` | Early US Pre-Market (`n = 3`) | `+28¢` | `-11¢` | Partial hour at snapshot time |

**Key takeaway:** From `2:00 AM ET` London open onward, `BTC+ETH+SOL` generated `+485¢` on `+14¢` TP and `+720¢` on `+20¢` TP, while `1:00–2:00 AM ET` thin Asia chop accounted for the entire early drawdown.

### C. Honest Red Results (Published Alongside the Winners)

We publish red controls from the exact same post-fix 7-hour window:

| Control Bench (Post-Fix `7h`) | Record (`W–L`, WR) | PnL (`1sh`) | Label |
|---|---|---:|---|
| `XRP 5m` (`TP14` / `TP20`) | `25W–20L` (`55.6%`) / `22W–23L` (`48.9%`) | **`-225.0¢` / `-228.0¢`** | shadow |
| `15m Multi-Coin Scalpers` (`MC15M`, all arms) | `31W–36L` (`46.3%`) | **`-410.0¢`** (`SOL 15m` `-264¢`) | shadow |
| `BINANCE_LEAD_SCALP` (`15m`) | `10W–6L` (`62.5%`) | **`-105.0¢`** | shadow |
| `OI_FLUSH_SNAPBACK` (`15m`) | `2W–5L` (`28.6%`) | **`-112.0¢`** | shadow |

## 3. Take-Profit Break-Even Arithmetic (Why Wider Targets Survive Lower Hit Rates)

At an average `32¢` passive maker entry (`0%` fee, `$0` value at expiry if wrong):

- **`+10¢` TP:** Break-even WR = `32 / (32 + 10) = 76.2%`
- **`+14¢` TP:** Break-even WR = `32 / (32 + 14) = 69.6%`
- **`+20¢` TP:** Break-even WR = `32 / (32 + 20) = 61.5%`

Notice how `ETH 5m` cleared `77.8%` on `+14¢` TP (`+8.2%` above break-even), while `SOL 5m` (`67.9%` on `+20¢`, `+6.4%` above break-even) and `BTC 5m` (`63.3%` on `+20¢`, `+2.3%` above break-even) outperformed at `+20¢`.

## 4. Caveats

- **Small single-night sample (`7 hours`, `n = 156` Big-3 trades):** One overnight session is a forward-test signal, not a proven multi-week edge.
- **Queue priority:** Even with `+1¢` trade-through clearance (`best_bid >= tp + 1.0`), real live maker fill rates can still experience adverse selection when spot jumps across strike before an entry quote cancels.
