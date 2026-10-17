"""Round forty-nine: the take-profit re-chosen walk-forward at the user's setting (10 MNQ, $350, with the lock).

    python research/walkforward_tp35.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. The 1.5-noise-unit take-profit was chosen walk-forward in round twenty-six at $117 a
contract, before the lock and the daily loser limit existed. At $35 a contract with the lock, most trades end at the
stop or the lock and the take-profit decides how much a trend day pays; the best level may have moved. Procedure, as
in round twenty-six: each year, pick the take-profit with the highest daily t-stat over all earlier years (from
2011 on the index, 2015 on NQ futures) among none, 1.0, 1.25, 1.5, 2.0, 2.5 and 3.0 noise units, and trade that year
with it; the choice never sees the year it trades. Everything else is v1.3, on 1-minute bars.
Pass bar, fixed before running: the stitched walk-forward record beats fixed 1.5 on $ per day and t-stat with a worst
losing stretch no larger and a win rate no lower, on the index 2013 - Sep 2026 and on NQ futures 2017 - July 2025.
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

BASE = {"target_on_fill_bar": False, "cap_on_fill_bar": True, "cap_pts": 17.5, "lock": (17.5, 2.5),
        "lock_touch": True, "minutes": 1, "day_losers": 4}
CHOICES = (None, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)


def _job(args):
    path, tp = args
    return tp, P.simulate(pd.read_pickle(path), target=tp, **BASE)


def daily(tf, sessions):
    day = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum()
    return day.reindex(sessions).fillna(0.0)


def tstat(x: pd.Series) -> float:
    return float(x.mean() / x.std() * len(x) ** 0.5) if len(x) > 1 and x.std() > 0 else 0.0


def walk_forward(path, start, judge_from, judge_to):
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = dict(ex.map(_job, [(path, tp) for tp in CHOICES]))
    sessions, first = L.five_min_sessions(path)
    sessions = sessions[sessions >= start]
    runs = {tp: MT.clean(tf, first) for tp, tf in runs.items()}
    days = {tp: daily(tf, sessions) for tp, tf in runs.items()}
    picks, parts = {}, []
    for y in range(judge_from, judge_to + 1):
        past = {tp: d[d.index.year < y] for tp, d in days.items()}
        pick = max(CHOICES, key=lambda tp: tstat(past[tp]))
        picks[y] = pick
        parts.append(runs[pick][runs[pick].entry_time.dt.year == y])
    stitched = pd.concat(parts)
    ss = sessions[(sessions.year >= judge_from) & (sessions.year <= judge_to)]
    fixed = runs[1.5][(runs[1.5].entry_time.dt.year >= judge_from) & (runs[1.5].entry_time.dt.year <= judge_to)]
    return picks, MT.stats(stitched, ss), MT.stats(fixed, ss)


def main() -> None:
    ok_all = True
    for label, path, start, j0, j1 in (("index", sys.argv[1], "2011-01-01", 2013, 2026),
                                       ("NQ futures", sys.argv[2], "2015-03-01", 2017, 2025)):
        picks, wf, fixed = walk_forward(path, start, j0, j1)
        print(f"\n{label}: picks by year {picks}")
        for name, s in (("fixed 1.5 (v1.3)", fixed), ("walk-forward", wf)):
            print(f"  {name:18s} win {s['win %']:.1f}%  $/day x10 {10 * s['$/day']:.0f}  t {s['t']:.2f}  "
                  f"worst stretch x10 {10 * s['worst stretch']:,.0f}")
        ok = (wf["$/day"] > fixed["$/day"] and wf["t"] > fixed["t"] and wf["worst stretch"] <= fixed["worst stretch"]
              and wf["win %"] >= fixed["win %"])
        print(f"  {label}: {'PASS' if ok else 'FAIL'}")
        ok_all = ok_all and ok
    print(f"\nOverall: {'PASS' if ok_all else 'FAIL'}")


if __name__ == "__main__":
    main()
