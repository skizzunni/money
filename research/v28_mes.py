"""v2.7 on the S&P 500 (MES) beside MNQ (docs/RESULTS.md, v2.8 study): the same rules, the stop the same share of price
(37.5 MNQ points at ~30,000 is 0.125%: ~9.6 points on the scaled S&P), $5 a point; alone with the $1,000 daily budget,
and split $500 + $500 with 7 MNQ and 10 MES.

    python research/v28_mes.py <data dir with spx1m_scaled.pkl> <dir with the user's MNQ files (upload names)>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as W  # noqa: E402
from v24_scan import V27  # noqa: E402

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

S, U = sys.argv[1:3]
NY = "America/New_York"
W.D.clear()
W.init({}, S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")
sp = pd.read_pickle(f"{S}/spx1m_scaled.pkl")
t = sp.index.tz_convert(NY)
tm = t.hour * 60 + t.minute
sp = resample(sp[(tm >= 570) & (tm < 960)].assign(volume=0.0), "5min")


def dd(x):
    e = np.r_[0, np.cumsum(x)]
    return (np.maximum.accumulate(e) - e).max()


def daily(bars, kw, skip=None, first=None, last=None):
    cfg = NoiseConfig(**kw)
    if skip is not None:
        cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=5).trades_frame()
    if first:
        tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
    if last:
        tf = tf[tf.entry_time < pd.Timestamp(last, tz=NY)]
    return tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.normalize()).pnl.sum()


def mes(budget, q):
    return {**V27, "qty": q, "point_value": 5.0, "max_loss_per_trade": q * 5.0 * 9.6, "daily_loss_limit": budget}


def mnq(budget, q):
    return {**V27, "qty": q, "max_loss_per_trade": q * 2.0 * 37.5, "daily_loss_limit": budget}



for name, nqbars, key, first, last in (("index 11-26", W.D["index"][0], "index", None, "2026-10-01"),
                                       ("NQ 15-25", W.D["nq"][0], "nq", "2015-01-01", "2025-07-01"),
                                       ("stand-in 25-26", W.D["proxy"][0], None, "2025-01-02", "2026-10-01")):
    skip = W.D[key][2] if key else None
    a = daily(nqbars, mnq(1000, 10), skip, first, last)
    b = daily(sp, mes(1000, 15), W.D["index"][2] if key else None, first or "2011-01-01", last)
    both = pd.concat([a.rename("nq"), b.rename("es")], axis=1).fillna(0)
    corr = both.corr().iloc[0, 1]
    half_nq = daily(nqbars, mnq(500, 7), skip, first, last)
    half_es = daily(sp, mes(500, 10), W.D["index"][2] if key else None, first or "2011-01-01", last)
    h = pd.concat([half_nq.rename("nq"), half_es.rename("es")], axis=1).fillna(0).sum(axis=1)
    print(f"{name:15s} MNQ v2.7 {a.sum() / 1e3:6.1f}k dd {dd(a.values) / 1e3:4.1f}k | MES alone {b.sum() / 1e3:6.1f}k "
          f"dd {dd(b.values) / 1e3:4.1f}k | daily corr {corr:.2f} | split $500+$500 (7 MNQ + 10 MES) "
          f"{h.sum() / 1e3:6.1f}k dd {dd(h.values) / 1e3:4.1f}k worst {h.min():6.0f}")
