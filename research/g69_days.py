"""G69 (docs/NINJATRADER_V38.md): a trade on 70% of days, with 1-MNQ fill-in trades. Packages P0 (today's default),
P1 (small gaps), P2 (+ uptrend shorts), P3 (+ opening drive).

    [NT_EXEC=1] python research/g69_days.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> [P0,P1,...]
"""
import os
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run


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


S.init({}, *sys.argv[1:4])
NT = bool(os.environ.get("NT_EXEC"))
if NT:
    S.D = {k: (with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items()}
PACK = {"P0": {}, "P1": {"gap_go_small_k": 0.0}, "P2": {"gap_go_small_k": 0.0, "trend_small": True},
        "P3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5},
        # G70: the same fill-in trades only once the floor has stopped
        "P2L": {"gap_go_small_k": 0.0, "trend_small": True, "fill_after_lock": True},
        "P3L": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True},
        # G71: with a cushion, and today's gains don't widen today's budget
        "A": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
              "fill_min_room": 3000.0, "day_keep": 1.0},
        "B": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
              "fill_min_room": 4000.0, "day_keep": 1.0},
        # G72: G71 without day_keep
        "A2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0},
        "B2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 4000.0},
        # G73: the fill-ins don't raise the contract steps
        "A3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0, "fill_no_steps": True},
        "B3": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 4000.0, "fill_no_steps": True},
        # G74: A2 and a gap win doesn't widen the day's budget
        "A4": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
               "fill_min_room": 3000.0, "gap_no_budget": True},
        # G75: the room for a new trade at most $950, today's default and U21 on
        "P0c": {"trade_risk_cap": 950.0},
        "A2c": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                "fill_min_room": 3000.0, "trade_risk_cap": 950.0},
        # G76: sizing with 2 points more stop slippage
        "P0s": {"size_slip_pts": 2.0},
        "A2s": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                "fill_min_room": 3000.0, "size_slip_pts": 2.0},
        # G80: U22 with up to 5 gap contracts once the floor has stopped
        "U22q5": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 3000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 5},
        # G81: U23 with a $2,000 cushion
        "U23c2": {"gap_go_small_k": 0.0, "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True,
                  "fill_min_room": 2000.0, "size_slip_pts": 2.0, "gap_go_locked_qty": 5}}
for pk in (sys.argv[4].split(",") if len(sys.argv) > 4 else list(PACK)):
    for name, (bars, first, skip) in S.D.items():
        if name == "win":
            continue
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0,
                             "time_stop": 60, "gap_go": True, "gap_go_skip_month_first": name != "proxy",
                             "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 3, **PACK[pk]})
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
        t_ny = bars.index.tz_convert("America/New_York")
        sess = {d for d in t_ny[(t_ny.hour == 9) & (t_ny.minute == 30)].date if not first or str(d) >= first}
        traded = 100 * tf.entry_time.dt.tz_convert("America/New_York").dt.date.nunique() / max(1, len(sess))
        e = np.r_[0.0, np.cumsum(p)]
        dayp = tf.groupby(tf.exit_time.dt.date).pnl.sum()
        print({"nt": NT, "pack": pk, "set": name, "days traded %": round(traded, 1),
               "gap trades": int(tf.reason.str.startswith("Gap").sum()), "trades": len(p),
               "net $": round(float(p.sum())), "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3),
               "win %": round(100 * float((p > 0).mean()), 1),
               "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
               "worst day $": round(float(dayp.min())), "days <= -1000": int((dayp <= -1000).sum()),
               "floor touches": S.trail_stats(name, tf)[f"{name} tb0"]}, flush=True)
