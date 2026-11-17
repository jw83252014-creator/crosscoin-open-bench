# Data

**This repo does not contain raw venue data.** We will not commit raw candles,
order books or trade tapes until each venue's terms have been checked for
republishing. Until then, we publish derived statistics and scripts that rebuild
the data on your machine.

## Where the candles come from

The Canary study uses one-minute candles from Kalshi's **public** market-data API
(no account or key needed for these read-only endpoints):

- Settled markets in a series:
  `GET https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXSOL15M&status=settled&limit=1000&cursor=...`
  Each market has `ticker`, `open_time`, `close_time`, `result` (`yes`/`no`), `floor_strike`, `expiration_value`.
- One-minute candles for one market:
  `GET https://api.elections.kalshi.com/trade-api/v2/series/{series}/markets/{ticker}/candlesticks?start_ts=...&end_ts=...&period_interval=1`
  Each candle has `end_period_ts`, `yes_bid.close_dollars` and `yes_ask.close_dollars` (the quote at the minute close).

Series used: `KXBTC15M`, `KXETH15M`, `KXSOL15M` (15-minute up/down rounds).

## Fetch it yourself

```bash
python3 scripts/fetch_kalshi_candles.py --out data/raw --since 2026-09-09
```

This writes `KXBTC15M.jsonl`, `KXETH15M.jsonl`, `KXSOL15M.jsonl` (market list with
official result) and `full_candles.jsonl` (`{"t": ticker, "c": [[end_ts, yes_bid, yes_ask], ...]}`).
These files are git-ignored on purpose. Be polite to the API (the script sleeps between calls).

## File formats the studies expect

| File | One line is | Fields |
|---|---|---|
| `KX{COIN}15M.jsonl` | a settled round | `ticker, open_time, close_time, result, floor_strike, expiration_value` |
| `full_candles.jsonl` | a round's candles | `t` (ticker), `c` = list of `[end_period_ts, yes_bid_close, yes_ask_close]` |

## Not here, on purpose

- Raw order-book snapshots, trade tapes and venue fills (used for the shadow studies in `studies/probability-bench/`).
- Anything tied to an exchange account (account IDs, order IDs, keys).
- Other builders' fills. If you share yours, we ask first before publishing.
