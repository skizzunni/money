"""Round thirty-seven: the lock, with room, and skipping the signals a $35 stop can't survive.

    python research/win_rate35b.py nsx_5m_scaled.pkl nq_5m_scaled.pkl

Reasoning, written before running. Round thirty-six: at 10 MNQ and $350 ($35 a contract) locking a small win once a
trade is 17.5 points up raised the win rate from about 15% to 37% at the same money on 2011-2018, then cost about a
sixth of the money on 2019-2022. The lock at entry + 2.5 points is hit by the ordinary pullback after a first push, so
some trades that went on to the target were cut. Two families, fixed before running:
  lock with room: (arm, lock) in points = (17.5, 5), (17.5, 8.75), (26.25, 8.75), (26.25, 13.125), (35, 17.5);
  skip hopeless signals: no entry when the 17.5-point max loss is under f noise units (sigma x price) from the signal
    close, f = 0.1, 0.15, 0.2, 0.3: there the stop sits inside the noise the bot itself measures;
  and each lock with each skip, in pairs (20).
Disclosure: 2019-2022 was seen once in round thirty-six, for the (17.5, 2.5) lock only. 2023 - Sep 2026 and the NQ
futures data are unseen for every variant here.
Pass bar against the bot at $35 a contract, fixed before running: on the index data 2011-2018 the win rate at least
10 points higher, $ per day no lower, t-stat no more than 0.3 lower, $ per day per dollar of worst losing stretch no
lower. The passing variant with the most $ per day must do the same on 2019-2022, then on 2023 - Sep 2026 (run once),
then on the NQ futures data 2015 - July 2025 (win rate 10 points higher, $ per day no lower).
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import stress as S  # noqa: E402
import win_rate35 as W  # noqa: E402

LOCKS = {f"lock {a}/{b}": {"lock": (a, b)} for a, b in ((17.5, 5), (17.5, 8.75), (26.25, 8.75), (26.25, 13.125),
                                                        (35, 17.5))}
SKIPS = {f"skip under {f}": {"min_cap_units": f} for f in (0.1, 0.15, 0.2, 0.3)}
PAIRS = {f"{a} + {b}": {**LOCKS[a], **SKIPS[b]} for a, b in itertools.product(LOCKS, SKIPS)}
VARIANTS = {"bot": {}, **LOCKS, **SKIPS, **PAIRS}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = S.sessions_of(pd.read_pickle(nsx))
    sessions = sessions[sessions >= "2011-01-01"]
    runs = W.runs_for(nsx, VARIANTS)
    table = W.table_for(runs, sessions, first, (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022)))
    W.show(table, VARIANTS, "2011-2018")
    cands = [n for n in VARIANTS if n != "bot" and W.passes(table, n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    W.show(table, ["bot", best], "2019-2022")
    ok = W.passes(table, best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    table.update(W.table_for({n: runs[n] for n in ("bot", best)}, sessions, first, (("2023-2026", 2023, 2026),)))
    W.show(table, ["bot", best], "2023-2026")
    final = W.passes(table, best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    q_sessions, q_first = S.sessions_of(pd.read_pickle(nq))
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q = W.table_for(W.runs_for(nq, {"bot": {}, best: VARIANTS[best]}), q_sessions, q_first,
                    (("NQ 2015-2025", 2015, 2025),))
    W.show(q, ["bot", best], "NQ 2015-2025")
    print(f"Replication on NQ futures: {'PASS' if W.passes(q, best, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
