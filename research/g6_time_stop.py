"""G6 (docs/NINJATRADER_V38.md): growth mode with a time stop, on the window, NQ and the index.

    [SCAN_MINUTES=30] [NT_EXEC=1] python research/g6_time_stop.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
    """Where a session's data stops at 16:00 with no 16:00 bar, one at the last price (as research/
    v38_ninjatrader_run.py): on an ETH chart MNQ trades to 17:00, so NinjaTrader's 16:00 exit fills there."""
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
for ts in (0, 30, 60):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "time_stop": ts})
        if NT:
            cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if first:
            cfg.trail_from = first
        tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        p = tf.pnl.to_numpy()
        e = np.r_[0.0, np.cumsum(p)]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        tr = S.trail_stats(name, tf)
        print({"bars": S.MIN[0], "time stop": ts, "set": name, "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1),
               "largest loss $": round(float(p.min())),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": tr[f"{name} tb0"]}, flush=True)
