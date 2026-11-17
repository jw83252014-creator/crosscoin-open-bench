# Contributing to crosscoin-open-bench

We welcome real empirical orderbook data, fill logs, and latency measurements from quants, market makers, and retail builders.

## How to Submit Fills
1. Fork this repo.
2. Add your scrubbed JSON fill log under `data/community_fills/<your-handle>/`.
3. Ensure all private API keys, account numbers, and secrets are 100% scrubbed before PR (`./scripts/scrub_check.sh`).
4. Include:
   - Venue (Polymarket / Kalshi / Hyperliquid)
   - Timeframe (5m / 15m)
   - Observed top-of-book bid/ask vs filled execution price
   - Latency to execution (ms)
5. Label it paper, shadow or real, and include n.
6. If you want to check fill survival, the format `scripts/l2_fill_decay_verifier.py` reads is documented at the top of that script (see `examples/` for synthetic samples).
7. Open a Pull Request!
