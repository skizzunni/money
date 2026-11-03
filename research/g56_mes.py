"""G56 (docs/NINJATRADER_V38.md): Funded growth on MES (the S&P 500), as a second market beside the Nasdaq bot.

    python research/g56_mes.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import sys

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.data import resample
from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
S.init({}, *sys.argv[1:4])
sp = pd.read_pickle(f"{sys.argv[1]}/spx1m_scaled.pkl")
t = sp.index.tz_convert(NY)
tm = t.hour * 60 + t.minute
sp = resample(sp[(tm >= 570) & (tm < 960)].assign(volume=0.0), "5min")
t = sp.index.tz_convert(NY)
g = pd.DataFrame({"d": t.strftime("%Y-%m-%d"), "m": t.hour * 60 + t.minute}).groupby("d").m.agg(["count", "min", "max"])
holes = g[(g["max"] < 955) | (g["min"] > 570) | (g["count"] < 70)].index
skip = S.CLOSURES + "," + ",".join(holes)


def go(bars, cfg_kw, first, last, label):
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         **cfg_kw})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    cfg.skip_dates, cfg.fed_dates = skip if label == "mes" else cfg_kw.get("skip_dates", ""), ""
    cfg.trail_from = first
    b = bars[(bars.index >= pd.Timestamp(first, tz=NY) - pd.Timedelta(days=150))
             & (bars.index < pd.Timestamp(last, tz=NY))]
    tf = run(b, cfg, minutes=5).trades_frame()
    return tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]


ix_bars, _, ix_skip = S.D["index"]
for first, last in (("2011-01-03", "2019-01-01"), ("2019-01-02", "2026-10-01")):
    mes = go(sp, {"point_value": 5.0, "max_loss_per_trade": 120.0, "after_loss_ml_mult": 160 / 120}, first, last, "mes")
    nq = go(ix_bars, {"skip_dates": ix_skip}, first, last, "index")
    p = mes.pnl.to_numpy()
    e = np.r_[0.0, np.cumsum(p)]
    dm = mes.groupby(mes.exit_time.dt.tz_convert(NY).dt.date).pnl.sum()
    dn = nq.groupby(nq.exit_time.dt.tz_convert(NY).dt.date).pnl.sum()
    both = pd.concat([dm.rename("mes"), dn.rename("nq")], axis=1).fillna(0.0)
    peak = np.maximum.accumulate(np.r_[0.0, dm.cumsum().to_numpy()])
    lowest_room = float((np.r_[0.0, dm.cumsum().to_numpy()] - np.minimum(peak - 2000.0, 0.0)).min())
    print({"period": f"{first[:4]}-{last[:4]}", "mes trades": len(p), "mes net $": round(float(p.sum())),
           "mes win %": round(100 * float((p > 0).mean()), 1),
           "mes pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 2),
           "mes closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
           "mes worst day $": round(float(dm.min())), "mes lowest room above floor $": round(lowest_room),
           "mes days": len(dm), "nasdaq days": len(dn), "mes-only days": int(((both.mes != 0) & (both.nq == 0)).sum()),
           "daily correlation": round(float(both.corr().iloc[0, 1]), 2), "nasdaq net $": round(float(dn.sum()))},
          flush=True)
