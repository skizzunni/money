"""G326 (docs/NINJATRADER_V38.md): U56's Test sprint over longer horizons. A measurement (as G278, G295).

The share of Tests passed and failed within 10, 15, 20 and 30 sessions (2, 3, 4 and 6 weeks), U56's Test sprint (sprint
over the first 10 sessions; then the 50K's growth sizing), G250's Test rules, NQ 2015-25 and the index 2011-26 Monday
starts.

    python research/g326_horizon.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
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
NFP = ",".join(pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfp_dates.csv")).date)
U55 = {**K317, "sprint_target": 5000.0, "sprint_gap_qty": 2, "gap_go_be": 0.0, "sprint_days": 10, "day_cap_exit": True,
       "streak_k": 4, "streak_skip": 2, "big_day_k": 1.5, "day_guard": 1200.0, "day_guard_grid": True,
       "news_dates": NFP, "news_mult": 1.5}  # U56


def job(a):
    sess, name, start = a
    G.SESS = sess
    r = G.one((name, start, 4, 1500.0, U55))
    return None if r is None else {"sessions": sess, **r}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    starts = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-05-01", freq="W-MON")]
    starts += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2026-07-01", freq="W-MON")]
    jobs = [(s, n, d) for s in tuple(int(x) for x in os.environ.get("HORIZONS", "10,15,20,30").split(",")) for n, d in starts]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        d = pd.DataFrame([r for r in ex.map(job, jobs, chunksize=16) if r])
    d.to_csv(f"verification/noise_v2/g326_horizon{os.environ.get('TAG', '')}.csv", index=False)
    d["stuck"] = ~d.passed & ~d.failed & (d.room < 500)
    print(d.groupby("sessions").agg(starts=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"),
                                    stuck=("stuck", "mean"))
          .round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
