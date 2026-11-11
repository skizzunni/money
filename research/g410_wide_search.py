"""G410 (docs/NINJATRADER_V38.md): a wide search on the 50K, money and consistency: 200 random sets (seed 410; U48
first) over sizing, the day budget, exits, filters and tilts; G408's measure (36 months, development and unseen,
consistency columns). Results appended in chunks of 10 to verification/noise_v2/g410_wide_search.csv (resumable).

    python research/g410_wide_search.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import g400_consistency as M
import pandas as pd

PICK = {"daily_loss_limit": 2000.0, "profit_step": 1000.0, "profit_step_fast_from": 6000.0, "vol_pro": False,
        "vol_lo": 0.5, "vol_hi": 1.5, "skip_checks": "", "last_entry_end": 930}
CHOICES = {
    "day budget": [{}, {"daily_loss_limit": 1200.0}, {"daily_loss_limit": 1500.0}],
    "step": [{}, {"profit_step": 1250.0}],
    "tp": [{}, {"take_profit": 1.75}, {"take_profit": 2.5}],
    "time stop": [{}, {"time_stop": 30}, {"time_stop": 60}],
    "lock": [{}, {"lock_at": 0.3}, {"lock_at": 0.45}],
    "losers": [{}, {"max_losers": 2}, {"max_losers": 4}],
    "vol": [{}, {"vol_pro": False, "vol_lo": 0.75, "vol_hi": 1.25}],
    "drive": [{}, {"drive_size_k": 0.5, "drive_mult": 1.25, "drive_against_mult": 0.75}],
    "weekday": [{}, {"weekday_mult": "2:0.75"}],
    "checks": [{}, {"skip_checks": "780"}, {"skip_checks": "", "last_entry_end": 930}],
    "day lock": [{}, {"day_lock_at": 1500.0, "day_lock_keep": 750.0}],
    "big day": [{}, {"big_day_k": 2.0}],
    "trend": [{}, {"trend_n": 20}, {"trend_n": 100}],
    "entry": [{}, {"entry_k": 0.9}],
}
rng = random.Random(410)
VARIANTS = {"U48": {}}
while len(VARIANTS) < 200:
    pick = {k: rng.randrange(len(v)) for k, v in CHOICES.items()}
    tag = ", ".join(f"{k}={i}" for k, i in pick.items() if i) or "U48"
    if tag not in VARIANTS:
        VARIANTS[tag] = {k2: v2 for k, i in pick.items() for k2, v2 in CHOICES[k][i].items()}
M.VARIANTS = VARIANTS
OUT = "../verification/noise_v2/g410_wide_search.csv"


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    dev = [("index", mon(d)) for d in pd.date_range("2011-04-01", "2016-10-01", freq="QS")]
    unseen = [("index", mon(d)) for d in pd.date_range("2017-01-01", "2023-07-01", freq="QS")]
    unseen += [("nq", mon(d)) for d in pd.date_range("2015-04-01", "2022-07-01", freq="QS")]
    done = set()
    if os.path.exists(OUT):
        o = pd.read_csv(OUT)
        done = set(o.tag + "|" + o.half)
    for label, starts in (("development", dev), ("unseen", unseen)):
        todo = [t for t in VARIANTS if f"{t}|{label}" not in done]
        for i in range(0, len(todo), 10):
            chunk = todo[i:i + 10]
            with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
                rows = [x for r in ex.map(M.job, [(t, n, s) for t in chunk for n, s in starts]) if r for x in r]
            s = M.table(pd.DataFrame(rows))
            s.index.name = "tag"
            s = s.reset_index().assign(half=label)
            s.to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
            print(label, i + len(chunk), "of", len(todo), flush=True)


if __name__ == "__main__":
    main()
