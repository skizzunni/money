"""G253 (docs/NINJATRADER_V38.md): a search for passing the 50K Test within two weeks (10 sessions), G251's measure.

Stage 1 (development): 200 random combinations of the sprint size, the day stop and entry/exit settings, on the index's
Monday starts 2011-2018. Stage 2 (confirmation): the 10 best by passes (failures at most 15%) on NQ 2015-25 and the
index 2019-26, never seen in stage 1.

    SESS=10 python research/g253_test_search.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd

SPACE = {"sprint": [3, 4, 5, 6, 8], "day stop": [800.0, 1000.0, 1200.0, 1400.0],
         "lookback": [10, 12, 14, 16], "entry_k": [0.8, 0.9, 1.0, 1.1], "range_pos_min": [0.0, 0.5, 0.65, 0.7],
         "calm_k": [0.0, 0.6, 0.8], "take_profit": [1.0, 1.5, 2.0, 2.5], "lock_at": [0.25, 0.33, 0.5],
         "skip_checks": ["", "780,870"], "max_losers": [0, 2, 3], "time_stop": [30, 45, 60, 0],
         "trend_n": [0, 45], "big_day_k": [0.0, 1.5]}
rng = random.Random(253)
VARIANTS = []
while len(VARIANTS) < 200:
    v = {k: rng.choice(c) for k, c in SPACE.items()}
    if v not in VARIANTS:
        VARIANTS.append(v)


def job(args):
    k, name, start = args
    v = dict(VARIANTS[k])
    sq, ds = v.pop("sprint"), v.pop("day stop")
    r = G.one((name, start, sq, ds, v))
    return None if r is None else {"k": k, **r}


ROWS = "verification/noise_v2/g253_rows.jsonl"  # every result as it finishes (resumable after a restart)


def run_saved(ex, jobs, stage):
    done = {}
    if os.path.exists(ROWS):
        for line in open(ROWS):
            r = json.loads(line)
            done[(r["stage"], r["k"], r["set"], r["start"])] = r
    todo = [j for j in jobs if (stage, j[0], j[1], j[2]) not in done]
    with open(ROWS, "a") as f:
        for j, r in zip(todo, ex.map(job, todo, chunksize=16), strict=False):
            row = {"stage": stage, "k": j[0], "set": j[1], "start": j[2], **(r or {"skip": True})}
            done[(stage, j[0], j[1], j[2])] = row
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
    return [done[(stage, *j)] for j in jobs if not done[(stage, *j)].get("skip")]


def score(rows):
    d = pd.DataFrame([r for r in rows if r])
    return d.groupby("k").agg(weeks=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"))


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        s1 = score(run_saved(ex, [(k, n, s) for k in range(len(VARIANTS)) for n, s in dev], 1))
        s1.to_csv("verification/noise_v2/g253_stage1.csv")
        top = s1[s1.failed <= 0.15].sort_values("passed", ascending=False).head(10)
        print("stage 1 best (index 2011-18):\n" + top.round(3).to_string(), flush=True)
        s2 = score(run_saved(ex, [(k, n, s) for k in top.index for n, s in conf], 2))
    s2 = s2.join(pd.Series({k: json.dumps(VARIANTS[k]) for k in s2.index}, name="settings"))
    s2.to_csv("verification/noise_v2/g253_stage2.csv")
    print("stage 2 (NQ 2015-25 + index 2019-26):\n" + s2.sort_values("passed", ascending=False).round(3).to_string(),
          flush=True)


if __name__ == "__main__":
    main()
