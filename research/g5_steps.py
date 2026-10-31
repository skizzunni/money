"""G5 (docs/NINJATRADER_V38.md): growth mode with faster contract steps, on the window, NQ and the index.

    [SCAN_MINUTES=30] python research/g5_steps.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
for step, top in ((1500.0, 15), (1000.0, 15), (750.0, 15), (1000.0, 20)):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "profit_step": step, "size_up_to": top})
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
        print({"bars": S.MIN[0], "step": step, "max qty": top, "set": name, "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1),
               "largest loss $": round(float(p.min())),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": tr[f"{name} tb0"]}, flush=True)
