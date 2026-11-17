# Example data (SYNTHETIC)

Everything in this folder is **made-up example data** for testing the scripts.
It is not recorded market data and its numbers mean nothing about any market.

- `example_book.jsonl`: a few fake top-of-book snapshots (prices in cents).
- `example_orders.csv`: four fake intended orders.

Run:

```bash
python3 scripts/l2_fill_decay_verifier.py --book examples/example_book.jsonl --orders examples/example_orders.csv
```
