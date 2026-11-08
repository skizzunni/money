"""G349 (docs/NINJATRADER_V38.md): 150 random combinations (seed 349; k 0 is U57) of the prior-day size rule with U57's
own levels.

Stage 1 (development): the index's Monday starts 2011-2018. Stage 2 (confirmation): the 10 best by passes with failures
at most U57's 3.7% and failed or near-frozen at most its 16.8%, on NQ 2015-25 and the index 2019-26.

    SESS=10 python research/g349_u57_prior_mix.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G

import random

NFP = ",".join(pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfp_dates.csv")).date)
K317 = {"lookback": 18, "entry_k": 0.7, "range_pos_min": 0.7, "calm_k": 0.7, "take_profit": 0.75, "lock_at": 0.2,
        "skip_checks": "", "max_losers": 3, "time_stop": 30, "trend_n": 0, "big_day_k": 0.0, "stop_buffer": 0.24,
        "lock_plus": 2.5, "squeeze_min": 0.0, "last_entry_end": 930, "gap_go_k": 0.5}
FIXED = {**K317, "sprint_target": 5000.0, "sprint_gap_qty": 2, "gap_go_be": 0.0, "day_cap_exit": True}  # U55's
FOMC = ",".join(pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fomc_dates.csv")).date)
U56R = {"streak_k": 4, "streak_skip": 2, "big_day_k": 1.5, "day_guard": 1200.0, "day_guard_grid": True,
        "news_dates": NFP, "news_mult": 1.5, "day_lock_at": 800.0, "day_lock_keep": 300.0}  # U57
CHOICES = {"past": [None, {"pdhl_mult": 0.75}, {"pdhl_mult": 1.25}],
           "inside": [None, {"pdhl_in_mult": 0.75}, {"pdhl_in_mult": 1.25}, {"pdhl_in_mult": 1.5}],
           "gap trigger": [None, {"gap_go_k": 0.65}],
           "guard": [None, {"day_guard": 1000.0}, {"day_guard": 1400.0}],
           "lock": [None, {"day_lock_at": 1000.0}, {"day_lock_at": 600.0, "day_lock_keep": 200.0}],
           "gap qty": [None, {"sprint_gap_qty": 1}],
           "jobs": [None, {"news_mult": 1.25}, {"news_mult": 2.0}],
           "big day": [None, {"big_day_k": 2.0}],
           "time lock": [None, {"time_lock": 30}],
           "eq": [None, {"eq_n": 40}]}
rng = random.Random(349)
VARIANTS = [{"sprint": 4, "day stop": 1500.0, "rules": {}}]  # k 0: U56
while len(VARIANTS) < 150:
    pick = {r: rng.randrange(len(c)) for r, c in CHOICES.items()}
    v = {"sprint": rng.choice([3, 4, 4, 4, 5]), "day stop": 1500.0, "rules": {r: i for r, i in pick.items() if i}}
    if v not in VARIANTS:
        VARIANTS.append(v)


def job(args):
    k, name, start = args
    v = VARIANTS[k]
    extra = {**FIXED, **U56R}
    for rule, i in v["rules"].items():
        extra.update(CHOICES[rule][i])
    r = G.one((name, start, v["sprint"], v["day stop"], extra))
    return None if r is None else {"k": k, **r}


ROWS = "verification/noise_v2/g349_rows.jsonl"  # every result as it finishes (resumable after a restart)


def run_saved(ex, jobs, stage):
    done = {}
    if os.path.exists(ROWS):
        for line in open(ROWS):
            r = json.loads(line)
            done[(r["stage"], r["k"], r["set"], r["start"])] = r
    todo = [j for j in jobs if (stage, j[0], j[1], j[2]) not in done]
    with open(ROWS, "a") as f:
        for j, r in zip(todo, ex.map(job, todo, chunksize=16)):
            row = {"stage": stage, "k": j[0], "set": j[1], "start": j[2], **(r or {"skip": True})}
            done[(stage, j[0], j[1], j[2])] = row
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
    return [done[(stage, *j)] for j in jobs if not done[(stage, *j)].get("skip")]


def score(rows):
    d = pd.DataFrame([r for r in rows if r])
    d["stuck"] = ~d.passed & ~d.failed & (d.room < 500)
    d["failed_or_stuck"] = d.failed | d.stuck
    return d.groupby("k").agg(weeks=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"),
                              failed_or_stuck=("failed_or_stuck", "mean"))


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        s1 = score(run_saved(ex, [(k, n, s) for k in range(len(VARIANTS)) for n, s in dev], 1))
        s1 = s1.join(pd.Series({k: json.dumps({"sprint": VARIANTS[k]["sprint"], "rules": VARIANTS[k]["rules"]}) for k in s1.index}, name="settings"))
        s1.to_csv("verification/noise_v2/g349_stage1.csv")
        top = s1[(s1.failed <= 0.0371) & (s1.failed_or_stuck <= 0.1681)].sort_values("passed", ascending=False).head(10)
        print("stage 1 best (index 2011-18):\n" + top.round(3).to_string(), flush=True)
        s2 = score(run_saved(ex, [(k, n, s) for k in top.index for n, s in conf], 2))
    s2 = s2.join(pd.Series({k: json.dumps({"sprint": VARIANTS[k]["sprint"], "rules": VARIANTS[k]["rules"]}) for k in s2.index}, name="settings"))
    s2.to_csv("verification/noise_v2/g349_stage2.csv")
    print("stage 2 (NQ 2015-25 + index 2019-26):\n" + s2.sort_values("passed", ascending=False).round(3).to_string(),
          flush=True)


if __name__ == "__main__":
    main()
