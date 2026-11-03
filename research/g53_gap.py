"""G53 (docs/NINJATRADER_V38.md): no entries against an opening gap of more than 1%.

    [SCAN_MINUTES=30] [NT_EXEC=1] python research/g53_gap.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import os
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
NT = bool(os.environ.get("NT_EXEC"))  # NinjaTrader's execution, as MnqNoiseV38.cs trades it


def with_1600(bars: pd.DataFrame, m: int) -> pd.DataFrame:
    """A 16:00 bar at the last price where a session's data stops at 16:00 (as research/g6_time_stop.py)."""
    t = bars.index.tz_convert("America/New_York")
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()


if NT:
    S.D = {k: (with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items()}
OPEX = ",".join(d.strftime("%Y-%m-%d") for d in pd.date_range("2011-01-01", "2027-01-01", freq="WOM-3FRI"))
for opex in (0.0, 0.01):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":  # the real MNQ weeks, too short to judge (as G6)
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "time_stop": 60, "gap_block": opex})
        if NT:
            cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if False:
            cfg.skip_dates = cfg.skip_dates + "," + OPEX
        if first:
            cfg.trail_from = first
        tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        p = tf.pnl.to_numpy()
        e = np.r_[0.0, np.cumsum(p)]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        tr = S.trail_stats(name, tf)
        print({"bars": S.MIN[0], "nt": NT, "gap block": opex, "set": name, "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1), "time stops": int((tf.reason == "Time stop").sum()),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": tr[f"{name} tb0"]}, flush=True)
