"""Round forty-eight: lock the breakouts the S&P doesn't confirm earlier; leave the confirmed ones alone.

    python research/confirm_lock.py spx_1m.pkl nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running the tests below, after a look at 2011-2018. At 10 MNQ and $350, trades whose signal
the S&P 500 confirmed (it also closed beyond its own noise line, computed the same way) made about twice as much per
trade as unconfirmed ones ($79 against $41 on 2011-2018) at about the same win rate: the unconfirmed breakouts carry
less trend, so they have less to give up by banking a small win sooner. On 2011-2018, locking the unconfirmed trades
at 13.1 points instead of 17.5 raised their win rate from 48.6% to 53.9% and their $ a trade from $41 to $49.
Rule, fixed before running: every trade is taken as now; a trade whose signal the S&P did not confirm locks at 13.125
points (0.75 of the max loss) instead of 17.5; confirmed trades, and signals with no S&P bar, keep 17.5. In Pine the
S&P comes from request.security on the S&P futures. 2011-2018 found it; the tests are 2019-2022, then 2023 - Sep 2026
(run once), then NQ futures 2015 - July 2025 (with the same S&P data).
Pass bar against v1.3 on 1-minute bars, fixed before running: win rate higher, $ per day no lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch no lower (on NQ: win rate higher, $ per day no lower).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

BASE = {"target": 1.5, "target_on_fill_bar": False, "cap_on_fill_bar": True, "cap_pts": 17.5,
        "lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}


def confirmation_sets(spx_path: str) -> tuple[set, set, set]:
    spx = pd.read_pickle(spx_path)
    bands = run(spx, NoiseConfig(skip_dates="", fed_no_shorts=False), minutes=1).bands
    c = spx.close.to_numpy()
    up = {spx.index[i] for i, u, lo in bands if c[i] > u}
    down = {spx.index[i] for i, u, lo in bands if c[i] < lo}
    return up, down, {spx.index[i] for i, _, _ in bands}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] > b["win %"] and a["$/day"] >= b["$/day"]
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def main() -> None:
    spx, nsx, nq = sys.argv[1:4]
    conf = confirmation_sets(spx)
    variants = {"bot": BASE, "unconfirmed lock at 13.1": {**BASE, "lock_unconfirmed": 13.125, "confirmed": conf}}
    sessions, first = L.five_min_sessions(nsx)
    sessions = sessions[sessions >= "2011-01-01"]
    runs = W.runs_for(nsx, variants)
    periods = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))
    table = W.table_for(runs, sessions, first, periods)
    name = "unconfirmed lock at 13.1"
    for label, _, _ in periods:
        W.show(table, variants, label)
        ok = passes(table, name, label)
        print(f"{label}{' (where it was found)' if label == '2011-2018' else ''}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return
    q_sessions, q_first = L.five_min_sessions(nq)
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q = W.table_for(W.runs_for(nq, variants), q_sessions, q_first, (("NQ 2015-2025", 2015, 2025),))
    W.show(q, variants, "NQ 2015-2025")
    print(f"Replication on NQ futures: {'PASS' if passes(q, name, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
