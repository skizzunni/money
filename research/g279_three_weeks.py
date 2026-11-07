"""G279 (docs/NINJATRADER_V38.md): the Test sprint tuned for three weeks (15 sessions), G250's Test rules.

U53's settings with the sprint over 10 or 15 sessions, 4 or 5 MNQ, a day stop of $900 or $1,100; development weeks (the
index 2011-18) and unseen weeks (NQ 2015-25, the index 2019-26), as G253.

    python research/g279_three_weeks.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G

K317 = {"lookback": 18, "entry_k": 0.7, "range_pos_min": 0.7, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2,
        "skip_checks": "", "max_losers": 3, "time_stop": 30, "trend_n": 0, "big_day_k": 0.0, "stop_buffer": 0.24,
        "lock_plus": 2.5, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go_k": 0.5}
U53 = {**K317, "sprint_target": 5000.0, "sprint_gap_qty": 2, "gap_go_be": 0.0}
VARIANTS = {"U53 (sprint 10 sessions)": (4, 1100.0, 10), "sprint 15 sessions": (4, 1100.0, 15),
            "sprint 15, day stop $900": (4, 900.0, 15), "sprint 15, 5 MNQ": (5, 1100.0, 15),
            "sprint 15, 5 MNQ, day stop $900": (5, 900.0, 15)}


def job(a):
    tag, name, start = a
    G.SESS = 15
    q, ds, sd = VARIANTS[tag]
    r = G.one((name, start, q, ds, {**U53, "sprint_days": sd}))
    return None if r is None else {"tag": tag, **r}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-16", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-17", freq="W-MON")]
    for label, starts in (("development (index 2011-18)", dev), ("unseen (NQ 2015-25 + index 2019-26)", conf)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts], chunksize=16) if r])
        print(label + ":\n" + d.groupby("tag").agg(weeks=("passed", "size"), passed=("passed", "mean"),
                                                  failed=("failed", "mean")).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
