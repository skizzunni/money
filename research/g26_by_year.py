"""G26's decision (docs/NINJATRADER_V38.md): growth mode against G26 (G16 + G25), net by calendar year, NinjaTrader's
execution, on NQ and the index (and the window, for reference).

    [SCAN_MINUTES=5] python research/g26_by_year.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])


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


rows = []
for name, (bars, first, skip) in S.D.items():
    if name == "win":
        continue
    bars = with_1600(bars, S.MIN[0])
    for label, extra in (("now", {}), ("G26", {"after_loss_ml_mult": 1.0, "trend_n": 30})):
        cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                             **extra})
        cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        if first:
            cfg.trail_from = first
        tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
        if first:
            tf = tf[tf.entry_time >= pd.Timestamp(first, tz="America/New_York")]
        for y, p in tf.groupby(tf.exit_time.dt.year).pnl.sum().items():
            rows.append({"set": name, "config": label, "year": y, "net $": round(float(p))})
        print(name, label, round(float(tf.pnl.sum())), flush=True)
out = pd.DataFrame(rows).pivot_table(index=["set", "year"], columns="config", values="net $").reset_index()
out["G26 better"] = out["G26"] > out["now"]
print(out.to_string(index=False))
out.to_csv("verification/noise_v2/g26_by_year.csv", index=False)
