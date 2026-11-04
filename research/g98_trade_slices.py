"""Measured 2026-11-04 (docs/NINJATRADER_V38.md): the bot's trades at 1 contract by kind, check time, weekday and
after a loser, on NQ 2015-25 and the index 2011-26.

    python research/g98_trade_slices.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
NY = "America/New_York"
for name in ("nq", "index"):
    bars, first, skip = S.D[name]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 0.0, "time_stop": 60,
                         "gap_go": True, "gap_go_skip_month_first": True, "gap_go_exit": 595, "gap_go_max_qty": 1,
                         "profit_step": 0.0, "qty": 1, "size_up_to": 1, "size_slip_pts": 3.0})
    cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    et = tf.entry_time.dt.tz_convert(NY)
    tf["hm"] = et.dt.strftime("%H:%M")
    tf["kind"] = np.where(tf.reason.str.startswith("Gap"), "gap", np.where(tf.direction > 0, "bot long", "bot short"))
    tf["dow"] = et.dt.day_name()
    tf["prev_loss"] = (tf.pnl.shift(1) < 0) & (et.dt.date == et.dt.date.shift(1))
    tf["yr"] = et.dt.year

    def summ(g: pd.DataFrame) -> pd.Series:
        return pd.Series({"n": len(g), "avg $": round(g.pnl.mean(), 2), "sum $": round(g.pnl.sum()),
                          "t": round(g.pnl.mean() / (g.pnl.std() / np.sqrt(len(g))) if len(g) > 2 else 0, 2)})
    print("==", name, len(tf))
    for col in ("kind", "hm", "dow", "prev_loss"):
        print(tf.groupby(col).apply(summ).to_string())
        print()
