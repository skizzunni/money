"""Round forty-two: skip the signal when the half-hour close is a spike (the bar closed at its extreme).

    python research/spike.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running the tests below but after looking at 2011-2018. At 10 MNQ and $350 (v1.3, 1-minute
bars, 2011-2018), entries whose 5-minute check bar closed in the top fifth of its range toward the signal (a spike
into the half-hour close) won 44.8% of the time and lost $17 a contract on average, against 52-55% and +$91 to +$123
for entries that closed off the extreme; a last minute of 10+ points toward the signal won 42%. A spike into the close
tends to snap back, and a 17.5-point stop can't sit through it. Rule: no entry when the 5-minute bar ending at the
check closed at or beyond 0.9 (or 0.8) of its range toward the signal's side (1 = at its high for a buy, its low for
a sell); computable on the 5-minute chart. 2011-2018 was used to find it, so it only picks between 0.9 and 0.8 (the
one with the most $ per day among those meeting the bar); the tests are 2019-2022, then 2023 - Sep 2026 (run once),
then NQ futures 2015 - July 2025.
Pass bar against the bot as it trades now (v1.3), on 1-minute bars: win rate at least 1.5 points higher, $ per day no
lower, t-stat no more than 0.3 lower, $ per day per dollar of worst losing stretch no lower (on NQ: win rate 1.5
points higher, $ per day no lower). 1 contract with a 17.5-point max loss stands for 10 MNQ at $350.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
VARIANTS = {"bot": {}, "skip spikes 0.9": {"skip_spike": 0.9}, "skip spikes 0.8": {"skip_spike": 0.8}}
VARIANTS = {n: {**BASE, **kw} for n, kw in VARIANTS.items()}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] >= b["win %"] + 1.5 and a["$/day"] >= b["$/day"]
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
