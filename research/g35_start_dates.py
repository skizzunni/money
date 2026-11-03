"""G35 (docs/NINJATRADER_V38.md): a fresh account started every quarter and run for 21 months, growth mode with the
time stop, NinjaTrader's execution, 5-minute bars, on NQ and the index.

    python research/g35_start_dates.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> [variant: base|gentle|cap10]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
VARIANT = sys.argv[4] if len(sys.argv) > 4 else "base"
MONTHS = int(os.environ.get("HORIZON_MONTHS", "21"))  # G43: 60, and the months to +$50,000
EXTRA = {"base": {}, "gentle": {"steps_after_lock": True}, "cap10": {"size_up_to": 10},
         "reserve500": {"trail_buffer": 500.0}, "half": {"trail_frac": 0.5},
         "early125": {"early_ml": 125.0}, "early100": {"early_ml": 100.0},
         "acct100": {"qty": 2, "daily_loss_limit": 1800.0, "trail_dd": 3000.0, "size_up_to": 30},
         "acct150": {"qty": 3, "daily_loss_limit": 2700.0, "trail_dd": 4500.0, "size_up_to": 45},
         "cush100": {"daily_loss_limit": 1800.0, "trail_dd": 3000.0},
         "cush150": {"daily_loss_limit": 2700.0, "trail_dd": 4500.0},
         "cush100s1000": {"daily_loss_limit": 1800.0, "trail_dd": 3000.0, "profit_step": 1000.0},
         "cush150s1000": {"daily_loss_limit": 2700.0, "trail_dd": 4500.0, "profit_step": 1000.0},
         "apex100": {"daily_loss_limit": 1350.0, "trail_dd": 3000.0},
         "apex150": {"daily_loss_limit": 1800.0, "trail_dd": 4000.0}}[VARIANT]


def with_1600(bars: pd.DataFrame, m: int) -> pd.DataFrame:
    """A 16:00 bar at the last price where a session's data stops at 16:00 (as research/g6_time_stop.py)."""
    t = bars.index.tz_convert(NY)
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()


def one(job):
    name, start = job
    bars, _, skip = S.D[name]
    s0 = pd.Timestamp(start, tz=NY)
    s1 = s0 + pd.DateOffset(months=MONTHS)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s1)]  # history for the noise and the trend
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         **EXTRA})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    tf = run(b, cfg, minutes=5).trades_frame()
    tf = tf[tf.entry_time >= s0]
    S.TRAIL = cfg.trail_dd  # the account's own trailing drawdown, for the floor checks
    eq = np.r_[0.0, np.cumsum(tf.pnl.to_numpy())]
    tr = S.trail_stats(name, tf)
    # the floor at the end: the highest end-of-day equity less $2,000, stopping at the start; an account within $100 of
    # it can't size a trade any more (and at most firms, at it, has failed)
    eod = tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.date).pnl.sum().cumsum()
    floor = min(max(0.0, float(eod.max()) if len(eod) else 0.0) - cfg.trail_dd, 0.0)
    room = float(eq[-1]) - floor
    return {"set": name, "start": start, "trades": len(tf), "net $": round(float(eq[-1])),
            "lowest $": round(float(eq.min())), "reached +2000": bool(eq.max() >= cfg.trail_dd),
            "floor touched": tr[f"{name} tb0"] > 0, "room at end $": round(room), "lost": room < 100.0,
            # frozen: no trade in the last 90 days of the 21 months (stopped above the floor, but no longer trading)
            "frozen": bool(len(tf) == 0 or (s1 - tf.exit_time.max()).days > 90),
            # G43: the months from the start to the first close at +$50,000 (none: not within the horizon)
            "months to 50k": (round((tf.exit_time.iloc[int(np.argmax(eq[1:] >= 50000))] - s0).days / 30.44, 1)
                              if (eq[1:] >= 50000).any() else None)}


def main() -> None:
    S.init({}, *sys.argv[1:4])
    S.D = {k: (with_1600(b, 5), first, skip) for k, (b, first, skip) in S.D.items() if k != "win"}
    if MONTHS == 21:
        jobs = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-01", "2023-10-01", freq="QS")]
        jobs += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-01", "2024-07-01", freq="QS")]
    else:  # G43: every six months, with the whole horizon in the data
        last_nq = pd.Timestamp("2025-07-01") - pd.DateOffset(months=MONTHS)
        last_ix = pd.Timestamp("2026-09-01") - pd.DateOffset(months=MONTHS)
        jobs = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-01", last_nq, freq="6MS")]
        jobs += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-01", last_ix, freq="6MS")]
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(one, jobs))
    d = pd.DataFrame(rows)
    tag = "" if MONTHS == 21 else f"_{MONTHS}m"
    d.to_csv(f"verification/noise_v2/g35_start_dates_{VARIANT}{tag}.csv", index=False)
    for name, g in d.groupby("set"):
        print(name, VARIANT, "starts", len(g), "lost (at the floor)", int(g["lost"].sum()),
              "dead (lost or frozen)", int((g["lost"] | g["frozen"]).sum()),
              "below start", int((g["net $"] < 0).sum()), "median net", int(g["net $"].median()),
              "worst net", int(g["net $"].min()), "lowest point", int(g["lowest $"].min()),
              "reached +2000", int(g["reached +2000"].sum()), flush=True)


if __name__ == "__main__":
    main()
