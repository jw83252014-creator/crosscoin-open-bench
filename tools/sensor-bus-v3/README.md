# Sensor Bus v3.3 Modules (Open Reference)

Zero-dependency Python 3.9+ reference utilities extracted from our live microstructure research stack:

1. **`credit_spread_guard.py`** — `$0/mo` `HYG` (high-yield corporate bonds) vs `IEF` (7-10Y US Treasuries) credit-spread crash detector via Yahoo Finance public JSON. Flags `CREDIT_STRESS` (`HYG <= -1.0%` while `IEF >= -0.1%`) and `CREDIT_CRASH` (`HYG <= -2.0%`) so mean-reversion bots stand down during macro risk-off cascades.
2. **`slug_rollover_guard.py`** — Strict `current_slug == position.slug` + `1.5s` pre-bell cutoff + `+1.0¢` trade-through queue-clearance guard that eliminates slug-rollover phantom wins in 5m/15m prediction-market shadow simulators.

## Quick Test

```bash
python3 -m unittest discover -s tests
python3 tools/sensor-bus-v3/credit_spread_guard.py
```
