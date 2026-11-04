import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
bars, first, skip = S.D["proxy"]
NY = "America/New_York"
t = bars.index.tz_convert(NY)
print("proxy data", t[0], "to", t[-1])
U28 = {"gap_go": True, "gap_go_exit": 595, "gap_go_max_qty": 1, "gap_go_locked_qty": 10, "gap_go_small_k": 0.0,
       "trend_small": True, "gap_go_drive_k": 0.5, "fill_after_lock": True, "fill_min_room": 3000.0,
       "size_slip_pts": 3.0, "fill_qty2_room": 6000.0, "giveback_brake": 0.5}
def with_1600(bars, m=5):
    t = bars.index.tz_convert(NY)
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()
NTB = with_1600(bars)
def go(data_from, start, end="2026-11-03", nt=True):
    src = NTB if nt else bars
    b = src[(src.index >= pd.Timestamp(data_from, tz=NY)) & (src.index < pd.Timestamp(end, tz=NY))]
    extra = {"tv_path": False, "nt_execution": True, "round_prices": True, "target_on_fill_bar": True} if nt else {}
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60, **U28,
                         **extra})
    cfg.trail_from = start
    tf = run(b, cfg, minutes=5).trades_frame()
    tf = tf[tf.entry_time >= pd.Timestamp(start, tz=NY)]
    days = tf.entry_time.dt.tz_convert(NY).dt.date.nunique()
    tt = b.index.tz_convert(NY)
    sess = len({d for d in tt[(tt.hour == 9) & (tt.minute == 30)].date if str(d) >= start})
    tf2 = tf.copy()
    tf2["cum"] = tf2.pnl.cumsum()
    fill_start = tf2[tf2.cum >= 3000].entry_time.min()
    print(f"data from {data_from}, account from {start}: {len(tf)} trades on {days} days, net ${tf.pnl.sum():,.0f}, "
          f"max qty {tf.qty.max() if len(tf) else 0}, {sess} sessions ({100*days/max(1,sess):.0f}% with a trade), "
          f"+$3,000 first reached {fill_start}")
go("2024-09-01", "2025-01-02")   # the window as reported (22 months)
go("2024-09-01", "2025-01-02", nt=False)
go("2025-08-01", "2026-01-02")   # a fresh account from Jan 2026, with 2025 history for the filters
go("2026-05-03", "2026-05-04")   # the user's data: DEC26 history from 2026-05-03, no history before
go("2026-05-03", "2026-07-15")   # the same, the account counted once the filters have 50 sessions
