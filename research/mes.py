"""Round forty-seven: the same bot on MES (Micro S&P 500) at the same size, 10 contracts and $350.

    python research/mes.py nsx_1m_scaled.pkl spx_1m_scaled.pkl

Reasoning, written before running. At 10 MNQ and $350 the stop is $35 a contract, 17.5 Nasdaq points: about 0.06%
of the index, inside the noise of the first minutes, which is why half the trades lose however the entry is timed.
MES is $5 a point, so the same $35 a contract is 7 S&P points, about 0.09% of the index, and the S&P moves less than
the Nasdaq: measured against the noise, the stop is about twice as wide, at the same contracts and the same max loss.
The noise-area momentum paper (Zarattini, Aziz & Barbon 2024) was tested on the S&P 500 (SPY).
Rules: v1.3 exactly (half-hour checks, line stop 0.24 noise units past the line, max loss $35 a contract from the fill,
take-profit 1.5 noise units, lock at 1R to entry + $5 a contract, no new entries after 4 losers a day), on 1-minute
bars, prices rescaled month by month to today's level. MNQ: $2 a point, 17.5-point stop, lock to +2.5. MES: $5 a
point, 7-point stop, lock to +1. Both: $1.24 fees and a 0.25-point tick of slippage per side (a tick is $0.50 on MNQ,
$1.25 on MES). Data: HistData NSXUSD and SPXUSD 1-minute, Nov 2010 - Sep 2026 (index CFDs; NQ futures replication
is not possible without ES futures data).
Pass bar, fixed before running, MES against MNQ at 10 contracts and $350, account $: win rate higher, $ per day no
lower, worst losing stretch no larger, on 2011-2018, then 2019-2022, then 2023 - Sep 2026 (run once). The $50K
evaluation odds at 10 contracts are shown for each.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval50k as E  # noqa: E402
import lock_more as L  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402

QTY = 10
INSTRUMENTS = {"MNQ": {"pv": 2.0, "cap": 17.5, "lock_plus": 2.5}, "MES": {"pv": 5.0, "cap": 7.0, "lock_plus": 1.0}}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def _job(args):
    name, path = args
    spec = INSTRUMENTS[name]
    P.PV = spec["pv"]  # dollars a point, read by simulate at run time (this worker only)
    tf = P.simulate(pd.read_pickle(path), minutes=1, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True,
                    cap_pts=spec["cap"], lock=(spec["cap"], spec["lock_plus"]), lock_touch=True, day_losers=4)
    return name, tf


def main() -> None:
    paths = {"MNQ": sys.argv[1], "MES": sys.argv[2]}
    with ProcessPoolExecutor(max_workers=2) as ex:
        runs = dict(ex.map(_job, paths.items()))
    table = {}
    for name, path in paths.items():
        sessions, first = L.five_min_sessions(path)
        sessions = sessions[sessions >= "2011-01-01"]
        tf = MT.clean(runs[name], first)
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            p, f, _, _ = E.odds(E.daily(t, ss), QTY, 125)
            table[(name, label)] = {"trades/day": s["trades/day"], "win %": s["win %"], "$/day": QTY * s["$/day"],
                                    "t": s["t"], "worst stretch": QTY * s["worst stretch"], "pass %": 100 * p,
                                    "fail %": 100 * f}
    for label, _, _ in PERIODS:
        print(f"\n{label}, 10 contracts, $350 max loss (account $)")
        print(pd.DataFrame({n: table[(n, label)] for n in INSTRUMENTS}).T.round(2).to_string())

    def passes(label):
        a, b = table[("MES", label)], table[("MNQ", label)]
        return a["win %"] > b["win %"] and a["$/day"] >= b["$/day"] and a["worst stretch"] <= b["worst stretch"]

    for label, _, _ in PERIODS:
        ok = passes(label)
        print(f"{label}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return


if __name__ == "__main__":
    main()
