# Contributing to crosscoin-open-bench

We welcome empirical order-book snapshots, fill-decay tables, and shadow/real fill logs (including **red/negative results**) from quants, market makers, and autonomous agent builders.

## Run this first (60 seconds)
Clone the repo and run the standard-library L2 fill-decay verifier on the synthetic test fixtures:

```bash
python3 scripts/l2_fill_decay_verifier.py --book examples/example_book.jsonl --orders examples/example_orders.csv
python3 -m unittest discover -s tests
```

Order-book recordings for our Probability Bench and Passive Maker Fade studies are intentionally unpublished under venue data terms — **external fill-decay tables and scrubbed community fills are the primary way to extend this benchmark across venues and latencies.**

## Input Schema for `l2_fill_decay_verifier.py`
No third-party packages are needed (Python 3.9+ standard library). Pass `.jsonl` or `.csv` files:

1. **Top-of-book snapshots (`--book`, prices in cents):**
   ```json
   {"timestamp_ms": 1700000000000, "best_bid": 49, "best_ask": 51, "ask_size": 120, "bid_size": 95}
   ```
2. **Intended orders (`--orders`, `side` is `"buy"` or `"sell"`):**
   ```csv
   timestamp_ms,side,limit_price_cents,size
   1700000000050,buy,51,25
   ```

## How to Submit Fills or Verifier Output
1. Open a **GitHub Issue** using the **L2 Fill-Decay Checker Results** or **Fill Data Submission** template, OR fork and add scrubbed summaries under `data/community_fills/<handle>/`.
2. Label every table **`paper`**, **`shadow`**, or **`real`**, and always include sample size **`n`** and time window.
3. **Mandatory scrub check before every commit:**
   ```bash
   bash scripts/scrub_check.sh
   ```
   Never include API keys, emails, wallet addresses, hostnames, or raw exchange order/account IDs.
