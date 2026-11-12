"""G461 (docs/NINJATRADER_V38.md): a measurement for the user. U58 on a 100K-style account ($3,000 end-of-day trailing
floor, $1,800 day budget, $1,500 until the floor stops; the rest of U58 unchanged, not tuned) against the 50K.

  funded: G396's 80 quarterly starts (index 2011-2023, NQ 2015-2022), 36 months: $ a session by year, the share of
          months at $750+, lost (intraday, each account's own floor).
  test:   G429's no-deadline Test, 116 starts (NQ 2015-2024, every 30 days): passed / failed, median days to pass.
          50K: +$3,000 over a $2,000 floor. 100K: +$6,000 over a $3,000 floor (the target is an assumption). Pass also
          needs 3 trading days and the best day under half the profit (E.test_run).

    PROCS=4 python research/g461_100k.py funded <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
    PROCS=4 python research/g461_100k.py test <data dir>
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
TEST = {"50K": (3000.0, 2000.0, {}), "100K": (6000.0, 3000.0, K100)}
if os.environ.get("G473"):  # G473's Test check: the 50K with the brake at 0.25 (U58 0.45)
    TEST = {"50K": (3000.0, 2000.0, {}), "50K, brake 0.25": (3000.0, 2000.0, {"giveback_brake": 0.25})}
B: dict = {}


def test_job(a):
    import v2_stops_eval as V
    import v3_eval as E
    from test_ninjatrader_v38 import GROW

    from mnqbot.noise import run
    tag, start = a
    target, dd, extra = TEST[tag]
    E.TARGET, E.DD = target, dd
    b = B["b"]
    s0 = pd.Timestamp(start, tz=V.NY)
    w = b[b.index >= s0 - pd.Timedelta(days=150)]
    cfg = dataclasses.replace(GROW, trail_from=start, slippage_ticks=2, skip_dates=V.BASE["skip_dates"],
                              fed_dates=V.FOMC, **extra)
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
        import g396_bigger_account as G396
        from g423_wide_when_wild import U58
        G396.VARIANTS.clear()
        G396.VARIANTS.update({"50K, U58": U58, "100K, U58": {**U58, **K100}})
        G396.main()
        return
    import v3_eval as E
    jobs = [(t, s.strftime("%Y-%m-%d")) for t in TEST for s in E.STARTS]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=test_init, initargs=(sys.argv[1],)) as ex:
        d = pd.DataFrame(list(ex.map(test_job, jobs, chunksize=4)))
    for tag, g in d.groupby("tag"):
        p = g[g.outcome == "pass"]
        print(f"{tag}: starts {len(g)}, passed {len(p) / len(g):.1%}, failed {(g.outcome == 'fail').mean():.1%}, "
              f"open {(g.outcome == 'open').sum()}, median trading days to pass {p.sessions.median():.0f}, "
              f"quartiles {p.sessions.quantile(0.25):.0f}-{p.sessions.quantile(0.75):.0f}, "
              f"passed within 60 days {(p.sessions <= 60).sum() / len(g):.1%}", flush=True)


if __name__ == "__main__":
    main()
