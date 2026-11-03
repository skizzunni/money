"""G60 stage 2 (docs/NINJATRADER_V38.md): the bot with gap and go inside it (shared budget and floor).

    [SCAN_MINUTES=30] [NT_EXEC=1] python research/g60_integrated.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
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
for opex in (False, True):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":  # the real MNQ weeks, too short to judge (as G6)
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "time_stop": 60, "gap_go": opex, "gap_go_skip_month_first": opex and name != "proxy",
                             "gap_go_after_lock": opex, "gap_go_cap": opex})
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
        t_ny = bars.index.tz_convert("America/New_York")
        sess = {d for d in t_ny[(t_ny.hour == 9) & (t_ny.minute == 30)].date if not first or str(d) >= first}
        traded = 100 * tf.entry_time.dt.tz_convert("America/New_York").dt.date.nunique() / max(1, len(sess))
        gaps = int(tf.reason.str.startswith("Gap").sum())
        e = np.r_[0.0, np.cumsum(p)]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        tr = S.trail_stats(name, tf)
        print({"bars": S.MIN[0], "nt": NT, "gap go": opex, "set": name, "days traded %": round(traded, 1),
               "gap trades": gaps,
               "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1), "time stops": int((tf.reason == "Time stop").sum()),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": tr[f"{name} tb0"]}, flush=True)
