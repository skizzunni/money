"""The trend pullback (research/patterns.py `trendpb`, mornings, 3R) added to v2.7: daily P/L summed, at $500 and
$250 risk a trade (docs/RESULTS.md, "The ONYX models").

    python research/onyx_combo.py <data dir> <dir with the user's MNQ_09-26 / MNQ_12-26 files (upload names)>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patterns as P  # noqa: E402
import v24_scan as W  # noqa: E402
from v24_scan import V27  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

S, U = sys.argv[1:3]
NY = "America/New_York"
P.init(S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")
W.D.clear()
W.init({}, S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")


def dd(x):
    e = np.r_[0, np.cumsum(x)]
    return (np.maximum.accumulate(e) - e).max()



skip = {"nq": W.D["nq"][2], "index": W.D["index"][2]}
for name, key in (("NQ 15-19 (dev)", "nq"), ("NQ 20-25", "nq"), ("index 11-26", "index"), ("stand-in 25-26", None)):
    bars, first = P.D[name]
    cfg = NoiseConfig(**V27)
    if key:
        cfg.skip_dates, cfg.fed_dates = skip[key], ""
    tb = run(bars, cfg, minutes=5).trades_frame()
    if first:
        tb = tb[tb.entry_time >= pd.Timestamp(first, tz=NY)]
    bot = tb.groupby(tb.exit_time.dt.tz_convert(NY).dt.normalize()).pnl.sum()
    days = P.prepare(bars, "trendpb")
    for risk in (500.0, 250.0):
        P.RISK = risk
        f = P.execute(days, False, False, True, 3.0, False)
        if first:
            f = f[f.time >= pd.Timestamp(first, tz=NY)]
        sl = f.groupby("day").pnl.sum()
        yrs = f.groupby(f.time.dt.year).pnl.sum()
        both = pd.concat([bot.rename("bot"), sl.rename("sl")], axis=1).fillna(0).sort_index()
        tot = both.bot + both.sl
        corr = both[(both.bot != 0) & (both.sl != 0)].corr().iloc[0, 1]
        print(f"{name:15s} risk {risk:.0f}: bot {both.bot.sum() / 1e3:6.1f}k dd {dd(both.bot.values) / 1e3:4.1f}k | "
              f"pullback {both.sl.sum() / 1e3:5.1f}k dd {dd(both.sl.values) / 1e3:4.1f}k "
              f"yrs+ {int((yrs > 0).sum())}/{len(yrs)} | together {tot.sum() / 1e3:6.1f}k "
              f"dd {dd(tot.values) / 1e3:4.1f}k worst {tot.min():6.0f} days<-1000 {(tot < -1000).sum():3d} | "
              f"corr {corr:.2f}")
    P.RISK = 500.0
