"""G408 (docs/NINJATRADER_V38.md): a search around G400's pick on the 50K, judged on $ a session AND consistency.
150 random sets (seed 408; the first two are U48 and G400's pick) varying the pick's parts and nearby settings; each on
development (index starts 2011-2016) and unseen (index 2017-2023, NQ 2015-2022), 36 months: $ a session, lost, trades a
session, green days (of traded days), green weeks / months, longest losing-week run, worst month. Results appended in
chunks of 10 sets to verification/noise_v2/g408_local_search.csv (resumable).

    python research/g408_local_search.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
import g400_consistency as M

PICK = {"daily_loss_limit": 2000.0, "profit_step": 1000.0, "profit_step_fast_from": 6000.0, "vol_pro": False,
        "vol_lo": 0.5, "vol_hi": 1.5, "skip_checks": "", "last_entry_end": 930}
CHOICES = {
    "day budget": [{"daily_loss_limit": 900.0}, {"daily_loss_limit": 1200.0}, {"daily_loss_limit": 1500.0},
                   {"daily_loss_limit": 2000.0}],
    "step": [{"profit_step": 1500.0}, {"profit_step": 1250.0}, {"profit_step": 1000.0}],
    "fast": [{"profit_step_fast_from": 9000.0}, {"profit_step_fast_from": 6000.0}],
    "vol": [{}, {"vol_pro": False, "vol_lo": 0.5, "vol_hi": 1.5}, {"vol_pro": False, "vol_lo": 0.75, "vol_hi": 1.25}],
    "checks": [{}, {"skip_checks": "", "last_entry_end": 930}, {"skip_checks": "780"}],
    "day lock": [{}, {"day_lock_at": 1500.0, "day_lock_keep": 750.0}, {"day_lock_at": 2500.0, "day_lock_keep": 1250.0}],
    "floor guard": [{}, {"day_guard": 1e9, "guard_floor_buffer": 200.0}],
    "early budget": [{}, {"early_daily_loss": 600.0}, {"early_daily_loss": 900.0}],
    "trend": [{}, {"trend_n": 20}, {"trend_n": 100}],
}
rng = random.Random(408)
VARIANTS = {"U48": {}, "G400 pick": dict(PICK)}
while len(VARIANTS) < 150:
    pick = {k: rng.randrange(len(v)) for k, v in CHOICES.items()}
    tag = ", ".join(f"{k}={i}" for k, i in pick.items())
    if tag not in VARIANTS:
        VARIANTS[tag] = {k2: v2 for k, i in pick.items() for k2, v2 in CHOICES[k][i].items()}
M.VARIANTS = VARIANTS
OUT = "../verification/noise_v2/g408_local_search.csv"


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
