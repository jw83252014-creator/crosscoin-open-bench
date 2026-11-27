# Two-Speed Quant Brain (`abstain-gate` + `jev-v4` + Strategy Blueprints)

Zero-dependency, reproducible open-source reference package for a two-speed prediction-market research architecture:

- **Speed 1 (`<0.1 ms` CPU Reflex Layer):** `abstain_gate_inference.py` — pure-Python evaluator for our 145-tree LightGBM + Isotonic Calibration model trained on `23,546` strictly causal multi-coin ticks (`models/abstain_gate_v1/`). No `lightgbm`, `numpy`, or `scipy` required at inference time.
- **Speed 2 (Deep Thinker + Persistent Episodic Memory):** `jev_v4_lucys_book.py` — "50 First Dates" architecture (`LUCYS_BOOK.md` + SQLite episodic recall + objective Brier settlement grading + pluggable OpenAI-compatible backend for `Qwen/Qwen3-32B` or `Qwen/Qwen3.8-27B` + LoRA adapters).
- **Strategy & Microstructure Blueprints:** `strategy_blueprints.py` — clean paper/shadow reference implementations of `PennyBell1HMaker`, `PhoenixFlipDipDetector`, `CrossVenueMiddleStressCheck`, and the 6 `v2` Abstain-Gate features (`POC distance`, `volume absorption`, `volume void`, `intra-round swing`, `cross-coin canary divergence`, `liquidity hour`).

> **Not trading advice.** Zero live execution code, zero private credentials, zero exchange order calls.

## 30-Second Quickstart (Zero External Dependencies)

```bash
# 1. Benchmark the 145-tree LightGBM Abstain-Gate in pure Python (~0.07 ms p50):
python3 tools/two-speed-quant-brain/abstain_gate_inference.py

# 2. Run the JEV v4 "Lucy's Book" persistent episodic memory self-test:
python3 tools/two-speed-quant-brain/jev_v4_lucys_book.py --self-test

# 3. Inspect the paper/shadow strategy blueprints & v2 microstructure features:
python3 tools/two-speed-quant-brain/strategy_blueprints.py
```

## LoRA Fine-Tuning Architecture (`Qwen/Qwen3.8-27B` on Colab A100 / Blackwell)

To specialize Speed 2 on domain-specific post-mortems and eliminate base-model cross-document hallucination, we fine-tune a lightweight `~150 MB` rank-16 PEFT LoRA adapter (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`) over calibrated JSONL episodes (`setup -> calibrated p_yes + ABSTAIN/MAKER verdict + falsifiable rule`) in BF16 on an 80–96 GB GPU, then serve the merged or LoRA-attached model via an OpenAI-compatible endpoint consumed by `jev_v4_lucys_book.py --endpoint ... --model Qwen/Qwen3.8-27B`.
