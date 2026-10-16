"""Round thirty-eight: on top of the lock, at 10 MNQ and $350 ($35 a contract), on 1-minute bars.

    python research/lock_more.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. The bot now locks a trade at entry + 2.5 points once it has been 17.5 points up
(v1.2, round thirty-seven), so about half the trades win, many of them small. Three ideas, fixed before running:
  a second lock step: once 35 points up, the stop to entry + 17.5; or once 52.5 up, to entry + 35 (locked trades
    that keep going keep more);
  done after a take-profit: no new entries today once a take-profit has filled (a target at 10 MNQ is about $3,000;
    the re-entries after it may give some back, and the 50% consistency rule judges the best day);
  a daily loss limit: no new entries after 3, or after 4, losing trades today (1 or 2 cost a third or more of the
    money before the lock, round thirty-six).
Baseline: the bot as it trades now (lock armed on the touch, moved from the next minute, as a broker's auto-breakeven
would). Pass bar against it, fixed before running: on the index data 2011-2018 $ per day no lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch no lower, win rate no more than 2 points lower. The
passing variant with the most $ per day must do the same on 2019-2022, then 2023 - Sep 2026 (run once), then on the
NQ futures data 2015 - July 2025 ($ per day no lower, win rate no more than 2 points lower). The $50K evaluation odds
at 10 MNQ are shown for each, as a description. 1 contract with a 17.5-point max loss stands for 10 MNQ at $350.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval50k as E  # noqa: E402
import more_trades as MT  # noqa: E402
import win_rate35 as W  # noqa: E402

LOCK = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1}
VARIANTS = {"bot": {}, "second step 35 -> +17.5": {"lock2": (35.0, 17.5)},
            "second step 52.5 -> +35": {"lock2": (52.5, 35.0)}, "done after a take-profit": {"done_after_target": True},
            "stop after 3 losers": {"day_losers": 3}, "stop after 4 losers": {"day_losers": 4}}
VARIANTS = {n: {**LOCK, **kw} for n, kw in VARIANTS.items()}


def five_min_sessions(path):
    bars = pd.read_pickle(path).resample("5min", label="left", closed="left").agg(
        {"open": "first", "close": "last"}).dropna()
    import stress as S

    return S.sessions_of(bars)


def evals(runs, sessions, first, y0, y1):
    ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
    out = {}
    for n, tf in runs.items():
        tf = MT.clean(tf, first)
        tf = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
        p, f, _, _ = E.odds(E.daily(tf, ss), 10, 125)
        out[n] = (round(100 * p), round(100 * f))
    return out


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["$/day"] >= b["$/day"] and a["win %"] >= b["win %"] - 2
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = five_min_sessions(nsx)
    sessions = sessions[sessions >= "2011-01-01"]
    runs = W.runs_for(nsx, VARIANTS)
    table = W.table_for(runs, sessions, first, (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022)))
    W.show(table, VARIANTS, "2011-2018")
    print("$50K evaluation at 10 MNQ, 2011-2018 (pass %, fail %):", evals(runs, sessions, first, 2011, 2018))
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
    print("$50K evaluation at 10 MNQ, 2023-2026:", evals({n: runs[n] for n in ("bot", best)}, sessions, first,
                                                          2023, 2026))
    final = passes(table, best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    q_sessions, q_first = five_min_sessions(nq)
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q_runs = W.runs_for(nq, {n: VARIANTS[n] for n in ("bot", best)})
    q = W.table_for(q_runs, q_sessions, q_first, (("NQ 2015-2025", 2015, 2025),))
    W.show(q, ["bot", best], "NQ 2015-2025")
    print("$50K evaluation at 10 MNQ, NQ 2015-2025:", evals(q_runs, q_sessions, q_first, 2015, 2025))
    print(f"Replication on NQ futures: {'PASS' if passes(q, best, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
