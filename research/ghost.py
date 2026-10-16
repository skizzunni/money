"""Round thirty-nine: skip the trades the first minutes would have stopped (the ghost trade), and a lower lock.

    python research/ghost.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. At 10 MNQ and $350 with the lock and the 4-loser limit (v1.3), on 2011-2018 1-minute
data half the losing trades are stopped within 2 minutes of the fill and three quarters within 5, mostly by the
bounce just after the breakout; only a tenth of the winners close within 2 minutes. On 16 October 2026 the 10:00,
10:30, 11:30 and 13:30 shorts all went that way. Ideas, fixed before running:
  the ghost trade: at a signal, wait N minutes (N = 1, 2, 3, 5); if a trade filled at the first minute's open would
    have hit its stop (the closer of the line stop and the max loss) during them, skip the signal: no trade, no loss;
    otherwise enter at market at the next minute's open, with the max loss and lock measured from that fill;
  a lower lock: trigger 12.5 or 8.75 points instead of 17.5, still to entry + 2.5.
Unconditional delay costs 15-25% of the money a minute (round thirty-five); the question is whether skipping the
fast losers pays for it. Baseline: the bot as it trades now (v1.3), on 1-minute bars. Pass bar against it, fixed before
running: on the index data 2011-2018 the win rate at least 5 points higher, $ per day no lower, t-stat no more than
0.3 lower, $ per day per dollar of worst losing stretch no lower. The passing variant with the most $ per day must do
the same on 2019-2022, then 2023 - Sep 2026 (run once), then on NQ futures 2015 - July 2025 (win rate 5 points higher,
$ per day no lower). 1 contract with a 17.5-point max loss stands for 10 MNQ at $350.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
VARIANTS = {"bot": {}, **{f"ghost {n} min": {"entry_delay": n, "ghost": True} for n in (1, 2, 3, 5)},
            "lock at 12.5": {"lock": (12.5, 2.5)}, "lock at 8.75": {"lock": (8.75, 2.5)}}
VARIANTS = {n: {**BASE, **kw} for n, kw in VARIANTS.items()}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] >= b["win %"] + 5 and a["$/day"] >= b["$/day"]
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
