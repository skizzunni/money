"""G190 (docs/NINJATRADER_V38.md): do the bot's losing stretches show in the market beforehand? A measurement.

U40's per-contract P/L a session is summed over the next 20 sessions and set against four things known at the prior
session's close: the open-to-close efficiency (|close - open| / range, last 20 sessions' mean), the range against
its 100-session mean, the lag-1 autocorrelation of 5-minute returns (last 20 sessions) and the bot's own per-contract
P/L over the last 40 sessions. By quintile of each, on NQ and the index.

    PACK_JSON='{...}' python research/g190_regime.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
PACK = json.loads(os.environ["PACK_JSON"])
NY = "America/New_York"
for name, (bars, _first, skip) in S.D.items():
    if name in ("win", "proxy"):
        continue
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go": True, "gap_go_skip_month_first": True, "gap_go_exit": 595, "gap_go_max_qty": 1,
                         "gap_go_locked_qty": 3, **PACK})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
    tf["pc"] = tf.pnl / tf.qty
    day_pc = tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.date).pc.sum()
    b = bars.copy()
    b.index = b.index.tz_convert(NY)
    m = b.index.hour * 60 + b.index.minute
    rth = b[(m >= 570) & (m < 960)]
    g = rth.groupby(rth.index.date)
    d = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    r = rth.close.pct_change()
    r[rth.index.date != pd.Series(rth.index.date, index=rth.index).shift(1).to_numpy()] = np.nan
    rr = pd.DataFrame({"r": r, "r1": r.shift(1), "d": rth.index.date})
    ac = rr.groupby("d").apply(lambda x: x.r.corr(x.r1))
    d["eff"] = (d.c - d.o).abs() / (d.h - d.l)
    d["rng"] = (d.h - d.l) / d.c
    d["pc"] = day_pc.reindex(d.index).fillna(0.0)
    feat = pd.DataFrame({
        "eff20": d.eff.rolling(20).mean(),
        "rng_rel": d.rng.rolling(20).mean() / d.rng.rolling(100).mean(),
        "ac20": ac.reindex(d.index).rolling(20).mean(),
        "bot40": d.pc.rolling(40).sum()})
    fwd = d.pc[::-1].rolling(20).sum()[::-1].shift(-1)  # the next 20 sessions
    out = feat.assign(fwd=fwd).dropna()
    print(f"\n{name}: {len(out)} sessions, forward 20-session per-contract P/L ($), mean by quintile (1 = lowest)")
    for k in feat.columns:
        q = pd.qcut(out[k], 5, labels=False) + 1
        s = out.groupby(q).fwd.agg(["mean", lambda x: (x < -300).mean() * 100])
        print(f"  {k:8s} mean " + " ".join(f"{v:7.0f}" for v in s["mean"])
              + "   % below -$300 " + " ".join(f"{v:5.1f}" for v in s.iloc[:, 1]), flush=True)
