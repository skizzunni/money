"""G400 (docs/NINJATRADER_V38.md): a big random search on the user's 50K for the most $ a session over 36 months with
the account kept, the bot's own $900 day budget free to rise (the user: "fk this limit... protected losses so i dont lose
the account"). 300 random sets (seed 400; the first is U48) over: the day budget, the early budget, a floor guard (the
trade closed inside the bar before the floor; `day_guard` very large, `guard_floor_buffer` $100 / $300), the start size,
the steps, the cap, take-profit, time stop, losers a day, inverse-volatility size, the drive tilt, the checks. Each set
on G397's development (index starts 2011-2016) and unseen (index 2017-2023, NQ 2015-2022) starts, 36 months each:
$ a session, the share of starts lost (intraday floor check), the share of days below -$1,000, the worst day.
Results are appended to verification/noise_v2/g400_big_search.csv in chunks of 20 sets (resumable).

    python research/g400_big_search.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
import g397_150k_sizing as M

CHOICES = {
    "day budget": [None, {"daily_loss_limit": 1500.0}, {"daily_loss_limit": 2000.0}, {"daily_loss_limit": 3000.0}],
    "early budget": [None, {"early_daily_loss": 1000.0}, {"early_daily_loss": 1500.0}],
    "floor guard": [None, {"day_guard": 1e9, "guard_floor_buffer": 100.0}, {"day_guard": 1e9, "guard_floor_buffer": 300.0}],
    "start": [None, {"qty": 2, "max_loss_per_trade": 375.0}],
    "step": [None, {"profit_step": 1000.0}],
    "fast": [None, {"profit_step_fast_from": 6000.0}],
    "cap": [None, {"size_up_to": 100}],
    "tp": [None, {"take_profit": 2.5}],
    "time stop": [None, {"time_stop": 90}],
    "losers": [None, {"max_losers": 4}],
    "vol": [None, {"vol_pro": False, "vol_lo": 0.5, "vol_hi": 1.5}],
    "drive": [None, {"drive_size_k": 0.5, "drive_mult": 1.5, "drive_against_mult": 0.5, "drive_none_mult": 0.75}],
    "checks": [None, {"skip_checks": "", "last_entry_end": 930}],
}
rng = random.Random(400)
VARIANTS = {"U48": {}}
while len(VARIANTS) < 300:
    pick = {k: rng.randrange(len(v)) for k, v in CHOICES.items()}
    tag = ", ".join(f"{k}={i}" for k, i in pick.items() if i) or "U48"
    if tag not in VARIANTS:
        VARIANTS[tag] = {k2: v2 for k, i in pick.items() if i for k2, v2 in CHOICES[k][i].items()}
M.VARIANTS = VARIANTS
OUT = "../verification/noise_v2/g400_big_search.csv"


def summarize(rows, label):
    d = pd.DataFrame(rows)
    m = d.groupby(["tag", "start", "set", "month"]).agg(pnl=("pnl", "mean"), lost=("lost", "max")).reset_index()
    out = m.groupby("tag").agg(per_session=("pnl", "mean"))
    out["lost"] = m[m.month == 36].groupby("tag").lost.mean()
    out["year3"] = m[m.month >= 25].groupby("tag").pnl.mean()
    out["days_below_1000"] = d.groupby("tag").pnl.apply(lambda x: (x <= -1000).mean())
    out["worst_day"] = d.groupby("tag").pnl.min()
    out["half"] = label
    return out.reset_index()


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    dev = [("index", mon(d)) for d in pd.date_range("2011-04-01", "2016-10-01", freq="QS")]
    unseen = [("index", mon(d)) for d in pd.date_range("2017-01-01", "2023-07-01", freq="QS")]
    unseen += [("nq", mon(d)) for d in pd.date_range("2015-04-01", "2022-07-01", freq="QS")]
    done = set(pd.read_csv(OUT).tag + "|" + pd.read_csv(OUT).half) if os.path.exists(OUT) else set()
    tags = list(VARIANTS)
    for label, starts in (("development", dev), ("unseen", unseen)):
        todo = [t for t in tags if f"{t}|{label}" not in done]
        for i in range(0, len(todo), 20):
            chunk = todo[i:i + 20]
            with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
                rows = [x for r in ex.map(M.job, [(t, n, s) for t in chunk for n, s in starts]) if r for x in r]
            s = summarize(rows, label)
            s.to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
            print(label, i + len(chunk), "of", len(todo), flush=True)


if __name__ == "__main__":
    main()
