"""Round fifty-one: three more settings re-chosen walk-forward at 10 MNQ and $350 (with the lock).

    python research/walkforward_more.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. Round forty-nine re-chose the take-profit walk-forward at the user's setting and
it stayed at 1.5. The same procedure, one setting at a time, everything else v1.3 on 1-minute bars; each year the
value with the best daily t-stat over all earlier years (from 2011 on the index, 2015 on NQ futures), traded that
year; the choice never sees the year it trades:
  sessions in the noise average: 10, 14 (v1.3), 20, 30;
  lock offset (points past the entry the lock moves the stop to): 1.25, 2.5 (v1.3), 5;
  losing trades a day before no new entries: 3, 4 (v1.3), 5, 6.
Pass bar, fixed before running, for each setting: the stitched walk-forward record beats v1.3 on $ per day and
t-stat with a worst losing stretch no larger and a win rate no lower, on the index 2013 - Sep 2026 and on NQ futures
2017 - July 2025.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import walkforward_tp35 as WF  # noqa: E402

BASE = {"target": 1.5, "target_on_fill_bar": False, "cap_on_fill_bar": True, "cap_pts": 17.5, "lock": (17.5, 2.5),
        "lock_touch": True, "minutes": 1, "day_losers": 4}
SETTINGS = {
    "lookback": ({10: {"lookback": 10}, 14: {}, 20: {"lookback": 20}, 30: {"lookback": 30}}, 14),
    "lock offset": ({1.25: {"lock": (17.5, 1.25)}, 2.5: {}, 5.0: {"lock": (17.5, 5.0)}}, 2.5),
    "losers a day": ({3: {"day_losers": 3}, 4: {}, 5: {"day_losers": 5}, 6: {"day_losers": 6}}, 4),
}


def _job(args):
    path, key, kw = args
    kw = dict(kw)
    P.LOOKBACK = kw.pop("lookback", 14)  # sessions in the noise average, read by simulate at run time (this worker)
    return key, P.simulate(pd.read_pickle(path), **{**BASE, **kw})


def walk(path, start, j0, j1, choices, current):
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = dict(ex.map(_job, [(path, k, kw) for k, kw in choices.items()]))
    sessions, first = L.five_min_sessions(path)
    sessions = sessions[sessions >= start]
    runs = {k: MT.clean(tf, first) for k, tf in runs.items()}
    days = {k: WF.daily(tf, sessions) for k, tf in runs.items()}
    picks, parts = {}, []
    for y in range(j0, j1 + 1):
        pick = max(choices, key=lambda k: WF.tstat(days[k][days[k].index.year < y]))
        picks[y] = pick
        parts.append(runs[pick][runs[pick].entry_time.dt.year == y])
    ss = sessions[(sessions.year >= j0) & (sessions.year <= j1)]
    cur = runs[current][(runs[current].entry_time.dt.year >= j0) & (runs[current].entry_time.dt.year <= j1)]
    return picks, MT.stats(pd.concat(parts), ss), MT.stats(cur, ss)


def main() -> None:
    for name, (choices, current) in SETTINGS.items():
        ok_all = True
        print(f"\n=== {name}")
        for label, path, start, j0, j1 in (("index", sys.argv[1], "2011-01-01", 2013, 2026),
                                           ("NQ futures", sys.argv[2], "2015-03-01", 2017, 2025)):
            picks, wf, cur = walk(path, start, j0, j1, choices, current)
            print(f" {label}: picks {picks}")
            for n, s in (("v1.3", cur), ("walk-forward", wf)):
                print(f"   {n:13s} win {s['win %']:.1f}%  $/day x10 {10 * s['$/day']:.0f}  t {s['t']:.2f}  "
                      f"worst x10 {10 * s['worst stretch']:,.0f}")
            ok = (wf["$/day"] > cur["$/day"] and wf["t"] > cur["t"] and wf["worst stretch"] <= cur["worst stretch"]
                  and wf["win %"] >= cur["win %"])
            ok_all = ok_all and ok
        print(f" {name}: {'PASS' if ok_all else 'no change'}")


if __name__ == "__main__":
    main()
