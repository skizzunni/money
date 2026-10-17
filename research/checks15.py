"""Round fifty-five: a check every 15 minutes instead of every 30.

    python research/checks15.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. More checks means more trades, which the user wants, and a breakout is caught up to
15 minutes sooner. Rounds four and fourteen found more frequent checks no better at $117 a contract without the lock;
at 10 MNQ and $350 with the lock and the 4-loser limit it is a different trade. Rule: checks at 10:00, 10:15, ...,
15:30, each with its own noise from the last 14 sessions; everything else v1.5, on 1-minute bars.
Pass bar against v1.5, fixed before running: $ per day no lower, win rate no more than 1 point lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch no lower; on 2011-2018, then 2019-2022, then 2023 - Sep
2026 (run once), then NQ futures 2015 - July 2025 ($ per day no lower, win rate no more than 1 point lower).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
VARIANTS = {"bot": {}, "checks every 15 min": {"step": 15}}
VARIANTS = {n: {**BASE, **kw} for n, kw in VARIANTS.items()}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] >= b["win %"] - 1 and a["$/day"] >= b["$/day"]
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = L.five_min_sessions(nsx)
    sessions = sessions[sessions >= "2011-01-01"]
    runs = W.runs_for(nsx, VARIANTS)
    table = W.table_for(runs, sessions, first, (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022)))
    W.show(table, VARIANTS, "2011-2018")
    print("$50K evaluation at 10 MNQ, 2011-2018 (pass %, fail %):", L.evals(runs, sessions, first, 2011, 2018))
    cands = [n for n in VARIANTS if n != "bot" and passes(table, n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    W.show(table, ["bot", best], "2019-2022")
    ok = passes(table, best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    table.update(W.table_for({n: runs[n] for n in ("bot", best)}, sessions, first, (("2023-2026", 2023, 2026),)))
    W.show(table, ["bot", best], "2023-2026")
    final = passes(table, best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    q_sessions, q_first = L.five_min_sessions(nq)
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q_runs = W.runs_for(nq, {n: VARIANTS[n] for n in ("bot", best)})
    q = W.table_for(q_runs, q_sessions, q_first, (("NQ 2015-2025", 2015, 2025),))
    W.show(q, ["bot", best], "NQ 2015-2025")
    print(f"Replication on NQ futures: {'PASS' if passes(q, best, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
