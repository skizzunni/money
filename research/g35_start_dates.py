"""G35 (docs/NINJATRADER_V38.md): a fresh account started every quarter and run for 21 months, growth mode with the
time stop, NinjaTrader's execution, 5-minute bars, on NQ and the index.

    python research/g35_start_dates.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> [variant: base|gentle|cap10]
"""
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
VARIANT = sys.argv[4] if len(sys.argv) > 4 else "base"
EXTRA = {"base": {}, "gentle": {"steps_after_lock": True}, "cap10": {"size_up_to": 10}}[VARIANT]


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
    s1 = s0 + pd.DateOffset(months=21)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s1)]  # history for the noise and the trend
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         **EXTRA})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    tf = run(b, cfg, minutes=5).trades_frame()
    tf = tf[tf.entry_time >= s0]
    eq = np.r_[0.0, np.cumsum(tf.pnl.to_numpy())]
    tr = S.trail_stats(name, tf)
    return {"set": name, "start": start, "trades": len(tf), "net $": round(float(eq[-1])),
            "lowest $": round(float(eq.min())), "reached +2000": bool(eq.max() >= 2000),
            "floor touched": tr[f"{name} tb0"] > 0}


def main() -> None:
    S.init({}, *sys.argv[1:4])
    S.D = {k: (with_1600(b, 5), first, skip) for k, (b, first, skip) in S.D.items() if k != "win"}
    jobs = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-01", "2023-10-01", freq="QS")]
    jobs += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-01", "2024-07-01", freq="QS")]
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(one, jobs))
    d = pd.DataFrame(rows)
    d.to_csv(f"verification/noise_v2/g35_start_dates_{VARIANT}.csv", index=False)
    for name, g in d.groupby("set"):
        print(name, VARIANT, "starts", len(g), "floor touched", int(g["floor touched"].sum()),
              "below start", int((g["net $"] < 0).sum()), "median net", int(g["net $"].median()),
              "worst net", int(g["net $"].min()), "lowest point", int(g["lowest $"].min()),
              "reached +2000", int(g["reached +2000"].sum()), flush=True)


if __name__ == "__main__":
    main()
