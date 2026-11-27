#!/usr/bin/env python3
"""
JEV v4 — "Lucy's Book" Persistent Episodic Memory Harness (Two-Speed Quant Brain — Speed 2)
===========================================================================================
Gives a deep-reasoning LLM a durable, objective memory instead of stateless prompts:
  1. Core Playbook (`LUCYS_BOOK.md`): Distilled structural laws read on EVERY wake-up.
  2. Episodic SQLite DB (`data/jev_v4_memory.db`): Stores every setup + forecast and
     grades it objectively after settlement (hit, Brier score, simulated PnL cents, lesson).
  3. Top-K Similarity Recall: Retrieves the 5 closest historical graded setups before
     every new forecast ("Last 5 times this exact setup appeared...").
  4. Pluggable OpenAI-Compatible Backend: Points to local vLLM (`Qwen/Qwen3-32B` or
     `Qwen/Qwen3.8-27B` + LoRA), OpenRouter, or `--dry-run` for zero-cost offline testing.
  5. Nightly Compression ("Henry Updates Lucy's Book"): Summarizes graded statistics
     into a dated addendum appended to `LUCYS_BOOK.md`.

Strictly research / paper / shadow advisory harness (ZERO live order placement).
"""
import argparse
import json
import os
import shutil
import sqlite3
import tempfile
import urllib.request
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB = os.path.join(DEFAULT_DATA_DIR, "jev_v4_memory.db")
DEFAULT_BOOK = os.path.join(BASE_DIR, "LUCYS_BOOK.md")


def ensure_book(book_path=DEFAULT_BOOK):
    parent = os.path.dirname(book_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if not os.path.exists(book_path):
        with open(book_path, "w", encoding="utf-8") as fh:
            fh.write("# JEV v4 — LUCY'S BOOK\n\n## Chapter 3 — Nightly Memory Updates\n")
    return book_path


def init_db(db_path=DEFAULT_DB):
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            coin TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            setup_tag TEXT NOT NULL,
            prior_streak INTEGER DEFAULT 0,
            dist_bps REAL DEFAULT 0.0,
            spread_cents REAL DEFAULT 0.0,
            regime TEXT DEFAULT 'UNKNOWN',
            sweep_usd REAL DEFAULT 0.0,
            market_mid REAL DEFAULT 0.5,
            summary TEXT DEFAULT '',
            predicted_action TEXT NOT NULL,
            predicted_p_yes REAL NOT NULL,
            reasoning TEXT DEFAULT '',
            model_used TEXT DEFAULT 'dry-run',
            recalled_ids TEXT DEFAULT '[]',
            settled INTEGER DEFAULT 0,
            actual_y_yes INTEGER,
            hit INTEGER,
            brier_score REAL,
            pnl_cents REAL,
            lesson TEXT DEFAULT '',
            settled_at TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_ep_settled ON episodes(settled, coin, setup_tag)")
    con.commit()
    return con


def similarity_score(ep, query):
    """Deterministic feature similarity between a stored episode and a new setup."""
    score = 0.0
    if ep["coin"].upper() == str(query.get("coin", "")).upper():
        score += 3.0
    if ep["timeframe"].lower() == str(query.get("timeframe", "")).lower():
        score += 2.0
    if ep["setup_tag"].upper() == str(query.get("setup_tag", "")).upper():
        score += 4.0
    if ep["regime"].upper() == str(query.get("regime", "")).upper():
        score += 1.5
    s_diff = abs((ep["prior_streak"] or 0) - int(query.get("prior_streak", 0)))
    score += max(0.0, 2.5 - 0.6 * s_diff)
    d_diff = abs((ep["dist_bps"] or 0.0) - float(query.get("dist_bps", 0.0)))
    score += max(0.0, 2.0 - d_diff / 30.0)
    if (float(query.get("sweep_usd", 0.0)) > 0) == ((ep["sweep_usd"] or 0.0) > 0):
        score += 1.0
    return round(score, 3)


def recall_similar(con, query, k=5):
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM episodes WHERE settled = 1 ORDER BY id DESC LIMIT 1000").fetchall()
    scored = [(similarity_score(dict(r), query), dict(r)) for r in rows]
    scored.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
    return [{"sim": sc, **d} for sc, d in scored[:k]]


def build_prompt(book_path, recalled, setup):
    ensure_book(book_path)
    with open(book_path, "r", encoding="utf-8") as fh:
        book_text = fh.read()
    if len(book_text) > 6000:
        book_text = book_text[:3000] + "\n...\n" + book_text[-2800:]

    if recalled:
        wins = sum(1 for r in recalled if r.get("hit") == 1)
        avg_pnl = sum((r.get("pnl_cents") or 0.0) for r in recalled) / len(recalled)
        mem_lines = [
            f"TOP {len(recalled)} MOST SIMILAR PAST EPISODES "
            f"(Recalled Hit Rate: {wins}/{len(recalled)}, Avg PnL: {avg_pnl:+.1f}c):"
        ]
        for r in recalled:
            outcome = "WIN" if r.get("hit") == 1 else "LOSS"
            mem_lines.append(
                f"  - [#{r['id']} sim={r['sim']}] {r['coin']} {r['timeframe']} {r['setup_tag']} | "
                f"streak={r['prior_streak']} dist={r['dist_bps']:+.1f}bps regime={r['regime']} | "
                f"Call={r['predicted_action']} (p_yes={r['predicted_p_yes']:.2f}) -> {outcome} "
                f"({r.get('pnl_cents', 0):+.1f}c) | Lesson: {r.get('lesson') or 'none'}"
            )
        mem_block = "\n".join(mem_lines)
    else:
        mem_block = "No similar graded episodes in episodic memory yet — rely on Lucy's Book core laws."

    system_msg = (
        "You are JEV v4, a calibrated prediction-market research analyst with persistent memory ('Lucy's Book').\n"
        "Respond ONLY with valid JSON: "
        '{"predicted_action": "BUY_YES_MAKER"|"BUY_NO_MAKER"|"ABSTAIN", '
        '"predicted_p_yes": float (0.05..0.95), "confidence": "LOW"|"MED"|"HIGH", '
        '"reasoning": "2 crisp sentences citing Lucy\'s Book or recalled memory"}'
    )
    user_msg = (
        f"=== LUCY'S BOOK ===\n{book_text}\n\n"
        f"=== EPISODIC MEMORY RECALL ===\n{mem_block}\n\n"
        f"=== CURRENT SETUP TO ANALYZE ===\n{json.dumps(setup, indent=2)}\n"
    )
    return system_msg, user_msg


def call_llm_openai_compat(endpoint, auth_header_val, model, system_msg, user_msg, timeout=45):
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.15,
        "max_tokens": 350,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if auth_header_val:
        headers["Authorization"] = f"Bearer {auth_header_val}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    if "</think>" in content:
        content = content.split("</think>")[-1].strip()
    if "```" in content:
        for p in content.split("```"):
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                content = p
                break
    return json.loads(content)


def ask_jev(con, book_path, setup, endpoint=None, model="Qwen/Qwen3.8-27B", auth_header_val=None, dry_run=False):
    recalled = recall_similar(con, setup, k=5)
    sys_msg, usr_msg = build_prompt(book_path, recalled, setup)
    recalled_ids = [r["id"] for r in recalled]

    if dry_run or not endpoint:
        mid = float(setup.get("market_mid", 0.5))
        streak = int(setup.get("prior_streak", 0))
        if abs(streak) >= 4 and abs(float(setup.get("dist_bps", 0.0))) < 80.0:
            p_yes = 0.41 if streak >= 4 else 0.59
            action = "BUY_NO_MAKER" if streak >= 4 else "BUY_YES_MAKER"
            reason = f"Dry-run Lucy's Book rule: Streak={streak} mean-reversion edge; recalled {len(recalled)} episodes."
        else:
            p_yes = max(0.05, min(0.95, mid))
            action = "ABSTAIN"
            reason = f"Dry-run abstain: mid={mid:.2f}, no dominant edge after checking {len(recalled)} recalled episodes."
        parsed = {
            "predicted_action": action,
            "predicted_p_yes": round(p_yes, 4),
            "confidence": "MED" if action != "ABSTAIN" else "LOW",
            "reasoning": reason,
        }
        used_model = "dry-run-lucys-book"
    else:
        parsed = call_llm_openai_compat(endpoint, auth_header_val, model, sys_msg, usr_msg)
        used_model = model

    now_iso = datetime.now(timezone.utc).isoformat()
    cur = con.execute(
        """INSERT INTO episodes (
            created_at, coin, timeframe, setup_tag, prior_streak, dist_bps, spread_cents,
            regime, sweep_usd, market_mid, summary, predicted_action, predicted_p_yes,
            reasoning, model_used, recalled_ids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            now_iso,
            str(setup.get("coin", "BTC")).upper(),
            str(setup.get("timeframe", "15m")),
            str(setup.get("setup_tag", "GENERAL")),
            int(setup.get("prior_streak", 0)),
            float(setup.get("dist_bps", 0.0)),
            float(setup.get("spread_cents", 0.0)),
            str(setup.get("regime", "UNKNOWN")),
            float(setup.get("sweep_usd", 0.0)),
            float(setup.get("market_mid", 0.5)),
            str(setup.get("summary", "")),
            str(parsed.get("predicted_action", "ABSTAIN")),
            float(parsed.get("predicted_p_yes", 0.5)),
            str(parsed.get("reasoning", "")),
            used_model,
            json.dumps(recalled_ids),
        ),
    )
    con.commit()
    return {
        "episode_id": cur.lastrowid,
        "recalled_count": len(recalled),
        "recalled_ids": recalled_ids,
        "model_used": used_model,
        **parsed,
    }


def grade_episode(con, episode_id, actual_y_yes, pnl_cents, lesson=""):
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
    if not row:
        raise ValueError(f"Episode {episode_id} not found")
    y = 1 if int(actual_y_yes) == 1 else 0
    p = float(row["predicted_p_yes"])
    brier = round((p - y) ** 2, 5)
    act = row["predicted_action"]
    if act == "BUY_YES_MAKER":
        hit = 1 if y == 1 else 0
    elif act == "BUY_NO_MAKER":
        hit = 1 if y == 0 else 0
    else:
        hit = 1 if pnl_cents >= 0 else 0
    now_iso = datetime.now(timezone.utc).isoformat()
    con.execute(
        """UPDATE episodes
           SET settled=1, actual_y_yes=?, hit=?, brier_score=?, pnl_cents=?, lesson=?, settled_at=?
           WHERE id=?""",
        (y, hit, brier, float(pnl_cents), lesson, now_iso, episode_id),
    )
    con.commit()
    return {"episode_id": episode_id, "hit": hit, "brier_score": brier, "pnl_cents": pnl_cents}


def henry_update_book(con, book_path=DEFAULT_BOOK):
    """Compresses recent graded episodes into a dated addendum in LUCYS_BOOK.md."""
    ensure_book(book_path)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM episodes WHERE settled = 1 ORDER BY id DESC LIMIT 200").fetchall()
    if not rows:
        return {"updated": False, "reason": "no_settled_episodes"}
    total = len(rows)
    wins = sum(r["hit"] for r in rows)
    avg_brier = sum(r["brier_score"] for r in rows) / total
    tot_pnl = sum((r["pnl_cents"] or 0.0) for r in rows)
    by_tag = {}
    for r in rows:
        st = by_tag.setdefault(r["setup_tag"], {"w": 0, "n": 0, "pnl": 0.0})
        st["n"] += 1
        st["w"] += r["hit"]
        st["pnl"] += r["pnl_cents"] or 0.0

    day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"\n### Henry's Memory Update — {day_str}",
        f"- **Rolling Graded Record:** `{wins}W-{total-wins}L` (`{wins/total*100:.1f}%`) | **Avg Brier:** `{avg_brier:.4f}` | **Net Shadow PnL:** `{tot_pnl:+.1f}c`",
    ]
    for tag, st in sorted(by_tag.items(), key=lambda x: x[1]["pnl"], reverse=True):
        lines.append(f"- **{tag}:** `{st['w']}W-{st['n']-st['w']}L` (`{st['w']/st['n']*100:.1f}%`), `{st['pnl']:+.1f}c`")
    recent_lessons = [r["lesson"] for r in rows[:5] if r["lesson"]]
    if recent_lessons:
        lines.append("- **Latest Lessons:** " + " | ".join(recent_lessons[:3]))
    with open(book_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"updated": True, "episodes": total, "wr_pct": round(wins / total * 100, 1), "avg_brier": round(avg_brier, 4)}


def run_self_test():
    with tempfile.TemporaryDirectory() as tmp:
        tdb = os.path.join(tmp, "test_jev.db")
        tbook = os.path.join(tmp, "LUCYS_BOOK.md")
        if os.path.exists(DEFAULT_BOOK):
            shutil.copy2(DEFAULT_BOOK, tbook)
        else:
            ensure_book(tbook)
        con = init_db(tdb)

        r1 = ask_jev(con, tbook, {
            "coin": "BTC", "timeframe": "15m", "setup_tag": "STREAK4_FADE",
            "prior_streak": 4, "dist_bps": 18.0, "spread_cents": 2.0,
            "regime": "TRANSITION_CHOP", "sweep_usd": 140000, "market_mid": 0.62,
        }, dry_run=True)
        grade_episode(con, r1["episode_id"], actual_y_yes=0, pnl_cents=38.0,
                      lesson="4-up streak faded cleanly at 38c NO maker.")

        r2 = ask_jev(con, tbook, {
            "coin": "BTC", "timeframe": "15m", "setup_tag": "STREAK4_FADE",
            "prior_streak": 4, "dist_bps": 24.0, "spread_cents": 2.0,
            "regime": "TRANSITION_CHOP", "sweep_usd": 0, "market_mid": 0.64,
        }, dry_run=True)
        grade_episode(con, r2["episode_id"], actual_y_yes=0, pnl_cents=36.0,
                      lesson="Confirmed Streak=4 fade win; tight 2c spread.")

        r3 = ask_jev(con, tbook, {
            "coin": "BTC", "timeframe": "15m", "setup_tag": "STREAK4_FADE",
            "prior_streak": 4, "dist_bps": 20.0, "spread_cents": 2.0,
            "regime": "TRANSITION_CHOP", "sweep_usd": 120000, "market_mid": 0.63,
        }, dry_run=True)
        assert r3["recalled_count"] == 2
        assert r3["predicted_action"] == "BUY_NO_MAKER"

        upd = henry_update_book(con, book_path=tbook)
        assert upd["updated"] is True and upd["episodes"] == 2
        con.close()
    return {"ok": True, "self_test": "PASSED", "recalled_verified": 2}


def main():
    ap = argparse.ArgumentParser(description="JEV v4 — Lucy's Book Persistent Memory Harness")
    ap.add_argument("--self-test", action="store_true", help="Run isolated zero-cost self-test")
    ap.add_argument("--henry-update", action="store_true", help="Compress settled episodes into LUCYS_BOOK.md")
    ap.add_argument("--endpoint", type=str, default=None, help="OpenAI-compatible vLLM endpoint")
    ap.add_argument("--model", type=str, default="Qwen/Qwen3.8-27B")
    ap.add_argument("--setup-json", type=str, default=None, help="JSON string of setup to score")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))
        return

    con = init_db(DEFAULT_DB)
    if args.henry_update:
        print(json.dumps(henry_update_book(con, DEFAULT_BOOK), indent=2))
    elif args.setup_json:
        endpoint_hdr = os.environ.get("LLM_ENDPOINT_TOKEN")
        print(json.dumps(ask_jev(con, DEFAULT_BOOK, json.loads(args.setup_json),
                                 endpoint=args.endpoint, model=args.model, auth_header_val=endpoint_hdr,
                                 dry_run=args.dry_run), indent=2))
    else:
        ap.print_help()
    con.close()


if __name__ == "__main__":
    main()
