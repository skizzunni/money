"""Round fifty-seven: lock the half-hour entries earlier, keep the hourly ones at 17.5.

    python research/lock_half.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running the tests below, after a look at 2011-2018. At 10 MNQ and $350 (v1.3, 1-minute
bars), entries from the hourly checks (10:00, 11:00, ..., 15:00) made about $95 a trade and those from the half-hour
checks (10:30, ..., 15:30) about $28; checks moved off the half hour (:05/:35, :10/:40) made far less (round
fifty-six), so the clock matters. A half-hour breakout carries less trend, so it has less to give up by banking a small
win sooner. Rule: every trade taken as now; entries from the :30 checks lock at 13.125 points, entries from the hourly
checks keep 17.5. 2011-2018 found it; the tests are 2019-2022, then 2023 - Sep 2026 (run once), then NQ futures 2015 -
July 2025.
Pass bar against v1.5 on 1-minute bars, fixed before running: win rate higher, $ per day no lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch no lower (on NQ: win rate higher, $ per day no lower).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
VARIANTS = {"bot": {}, "half-hour entries lock at 13.1": {"lock_half": 13.125}}
VARIANTS = {n: {**BASE, **kw} for n, kw in VARIANTS.items()}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] > b["win %"] and a["$/day"] >= b["$/day"]
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
