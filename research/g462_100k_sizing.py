"""G462 / G463 (docs/NINJATRADER_V38.md): U58's sizing on a 100K-style account ($3,000 floor, $1,800 day budget,
$1,500 until the floor stops): as it is (1 MNQ, +1 per $1,500), starting at 2 or 3 MNQ, +1 per $1,000, or 2 MNQ
and +1 per $1,000. G463 (G463=1): the early day budget at $1,000 or $2,000. G464 (G464=1): gap cap 15 / 20.
G465 (G465=1): +1 per $2,000, or at most half the room a trade. G467 (G467=1): 2 gap contracts early.
G468 (G468=1): steps $1,750 / $2,500.

  funded: G397's measure (months 1-36; development = index starts 2011-2016, unseen = index 2017-2023 + NQ 2015-2022).
  test:   G461's no-deadline Test (+$6,000 over $3,000, an assumed target), 116 starts.

    PROCS=4 python research/g462_100k_sizing.py funded <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
    PROCS=4 python research/g462_100k_sizing.py test <data dir>
"""
from __future__ import annotations

import dataclasses
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

K100 = {"trail_dd": 3000.0, "daily_loss_limit": 1800.0, "early_daily_loss": 1500.0}
SIZING = {"100K U58": {}, "start 2 MNQ": {"qty": 2, "max_loss_per_trade": 375.0},
          "start 3 MNQ": {"qty": 3, "max_loss_per_trade": 562.5}, "+1 per $1,000": {"profit_step": 1000.0},
          "start 2 MNQ, +1 per $1,000": {"qty": 2, "max_loss_per_trade": 375.0, "profit_step": 1000.0}}
if os.environ.get("G468"):  # G468: the 100K funded mode's step around G466's $2,000
    SIZING = {"100K funded ($2,000 steps)": {"profit_step": 2000.0}, "+1 per $1,750": {"profit_step": 1750.0},
              "+1 per $2,500": {"profit_step": 2500.0}}
if os.environ.get("G467"):  # G467: 2 gap contracts before the floor stops (U58 1), Test pair and funded pair
    SIZING = {"100K U58": {}, "100K U58, gap 2 early": {"gap_go_max_qty": 2},
              "100K funded ($2,000 steps)": {"profit_step": 2000.0},
              "100K funded, gap 2 early": {"profit_step": 2000.0, "gap_go_max_qty": 2}}
if os.environ.get("G465"):  # G465: fewer lost 100K starts (slower steps, or a cap on a trade's share of the room)
    SIZING = {"100K U58": {}, "+1 per $2,000": {"profit_step": 2000.0},
              "risk at most half the room": {"trail_frac": 0.5}}
if os.environ.get("G464"):  # G464: the gap trade's cap once the floor has stopped (U58 10)
    SIZING = {"100K U58": {}, "gap cap 15": {"gap_go_locked_qty": 15}, "gap cap 20": {"gap_go_locked_qty": 20}}
if os.environ.get("G463"):  # G463: the day budget until the floor stops ($1,500 as assumed in G461)
    SIZING = {"100K U58": {}, "early budget $1,000": {"early_daily_loss": 1000.0},
              "early budget $2,000": {"early_daily_loss": 2000.0, "daily_loss_limit": 2000.0}}
B: dict = {}


def test_job(a):
    import v2_stops_eval as V
    import v3_eval as E
    from test_ninjatrader_v38 import GROW

    from mnqbot.noise import run
    tag, start = a
    E.TARGET, E.DD = 6000.0, 3000.0
    b = B["b"]
    s0 = pd.Timestamp(start, tz=V.NY)
    w = b[b.index >= s0 - pd.Timedelta(days=150)]
    cfg = dataclasses.replace(GROW, trail_from=start, slippage_ticks=2, skip_dates=V.BASE["skip_dates"],
                              fed_dates=V.FOMC, **{**K100, **SIZING[tag]})
    tr = [t for t in run(w, cfg, 5).trades if t.entry_time >= s0]
    closed, worst, _ = V.marks(w, tr)
    day = np.asarray(w.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    out, sessions, mdd = E.test_run(day, closed, worst, int(np.searchsorted(w.index, s0)), len(w))
    return {"tag": tag, "start": start, "outcome": out, "sessions": sessions, "dd": mdd}


def test_init(d):
    import v2_stops_eval as V
    B["b"] = V.load(d)


def main() -> None:
    part = sys.argv.pop(1)
    if part == "funded":
        import g397_150k_sizing as G397
        from g423_wide_when_wild import U58
        G397.VARIANTS.clear()
        G397.VARIANTS.update({k: {**U58, **K100, **v} for k, v in SIZING.items()})
        if os.environ.get("G464"):  # G464 also reports the worst day (each row is one session's P/L)
            base_table = G397.table
            G397.table = lambda d: base_table(d).assign(worst_day=d.groupby("tag").pnl.min())
        G397.main()
        return
    import v3_eval as E
    jobs = [(t, s.strftime("%Y-%m-%d")) for t in SIZING for s in E.STARTS]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=test_init, initargs=(sys.argv[1],)) as ex:
        d = pd.DataFrame(list(ex.map(test_job, jobs, chunksize=4)))
    for tag, g in d.groupby("tag", sort=False):
        p = g[g.outcome == "pass"]
        print(f"{tag}: starts {len(g)}, passed {len(p) / len(g):.1%}, failed {(g.outcome == 'fail').mean():.1%}, "
              f"open {(g.outcome == 'open').sum()}, median trading days to pass {p.sessions.median():.0f}, "
              f"quartiles {p.sessions.quantile(0.25):.0f}-{p.sessions.quantile(0.75):.0f}", flush=True)


if __name__ == "__main__":
    main()
