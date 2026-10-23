"""The candlestick chart the user sent, against the noise strategy (docs/RESULTS.md, "Candlestick patterns").
"filter": for each v2.7 trade, whether its signal bar completes a pattern with or against it, and what those trades
made. "ensemble": the four setups that held on every set (research/patterns.py: trendpb, three white soldiers, morning
star, the previous-day sweep; their settings chosen on NQ 2015-2019), $250 risk each, added to v2.7 (daily P/L
summed).

    python research/candles_vs_bot.py <data dir> <dir with the user's MNQ_09-26 / MNQ_12-26 files (upload names)>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patterns as P  # noqa: E402
import v24_scan as W  # noqa: E402
from v24_scan import V27  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
SETS = (("NQ 15-19 (dev)", "nq"), ("NQ 20-25", "nq"), ("index 11-26", "index"), ("stand-in 25-26", None))
SLEEVES = [("trendpb", (False, False, True, 3.0, False)),
           ("candle:three_white:img:any", (False, False, True, 2.0, False)),
           ("candle:morning_star:img:any", (True, False, True, 3.0, False)),
           ("sweep", (True, False, False, 1.0, False))]


def dd(x) -> float:
    e = np.r_[0, np.cumsum(x)]
    return float((np.maximum.accumulate(e) - e).max())


def bot_trades(name: str, key: str | None) -> pd.DataFrame:
    bars, first = P.D[name]
    cfg = NoiseConfig(**V27)
    if key:
        cfg.skip_dates, cfg.fed_dates = W.D[key][2], ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    return tf[tf.entry_time >= pd.Timestamp(first, tz=NY)] if first else tf


def filter_study() -> None:
    rows = []
    for name, key in SETS:
        bars, _ = P.D[name]
        tf = bot_trades(name, key).groupby("exit_bar").agg(d=("direction", "first"), eb=("entry_bar", "first"),
                                                          pnl=("pnl", "sum")).reset_index()
        did = bars.index.tz_convert(NY).normalize()
        starts = np.flatnonzero(np.r_[True, did[1:] != did[:-1]])
        ends = np.r_[starts[1:], len(bars)]
        keep = np.array([a for a, b in zip(starts, ends, strict=True) if b - a >= 30])
        day_of = dict(zip(keep, [d[0] for d in P.prepare(bars, "orb")], strict=True))
        for r in tf.itertuples():
            g = r.eb - 1  # the check's bar
            k = keep[np.searchsorted(keep, g, side="right") - 1]
            fl = {nm: P.candle_at(day_of[k], g - k, nm) for nm in P.CANDLES}
            bull = fl["three_white"] or fl["morning_star"] or fl["engulfing"] or fl["hammer"] or fl["dragonfly"]
            bear = fl["three_black"] or fl["hanging_man"] or fl["gravestone"]
            rows.append({"set": name, "pnl": r.pnl, "with": (bull and r.d > 0) or (bear and r.d < 0),
                         "against": (bear and r.d > 0) or (bull and r.d < 0)})
    f = pd.DataFrame(rows)
    for col in ("with", "against"):
        print(col)
        print(f.groupby(["set", col]).pnl.agg(["count", "mean", "sum"]).round(0).unstack(col).to_string())


def ensemble() -> None:
    P.RISK = 250.0
    for name, key in SETS:
        bars, first = P.D[name]
        tb = bot_trades(name, key)
        bot = tb.groupby(tb.exit_time.dt.tz_convert(NY).dt.normalize()).pnl.sum()
        parts = []
        for st, var in SLEEVES:
            f = P.execute(P.prepare(bars, st), *var)
            if first:
                f = f[f.time >= pd.Timestamp(first, tz=NY)]
            parts.append(f.groupby("day").pnl.sum())
        e = pd.concat(parts, axis=1).fillna(0).sum(axis=1)
        both = pd.concat([bot.rename("bot"), e.rename("ens")], axis=1).fillna(0).sort_index()
        tot = both.bot + both.ens
        print(f"{name:15s} v2.7 {both.bot.sum() / 1e3:6.1f}k dd {dd(both.bot.values) / 1e3:4.1f}k | four setups "
              f"{both.ens.sum() / 1e3:5.1f}k dd {dd(both.ens.values) / 1e3:4.1f}k | together {tot.sum() / 1e3:6.1f}k "
              f"dd {dd(tot.values) / 1e3:4.1f}k worst day {tot.min():6.0f}")


if __name__ == "__main__":
    S, U = sys.argv[1:3]
    P.init(S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")
    W.D.clear()
    W.init({}, S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")
    filter_study()
    ensemble()
