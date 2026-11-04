"""G200 (docs/NINJATRADER_V38.md): what simple setups earn on the days U41 takes no trade. A measurement.

On NQ and the index, for the sessions U41 doesn't trade, 1 MNQ, $1.24 commission and 1 tick each way:
  A. last-half-hour momentum (Gao et al.): 15:30 to 16:00 in the direction of the 09:30-15:30 move;
  B. the same in the direction of the 09:30-10:00 move;
  C. the opening-range breakout: the first 5-minute close beyond the 09:30-10:00 range, out at 16:00, a stop at the
     range's other side;
  D. the morning fade: 10:00 to 16:00 against the 09:30-10:00 move.
Per year: trades, net per contract.

    PACK_JSON='{...}' python research/g200_idle_days.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file>
"""
import json
import os
import sys

import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

S.init({}, *sys.argv[1:4])
PACK = json.loads(os.environ["PACK_JSON"])
NY = "America/New_York"
COST = 2 * 0.62 + 2 * 0.25 * 2.0  # commission and a tick each way, per MNQ
for name, (bars, first, skip) in S.D.items():
    if name in ("win",):
        continue
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "time_stop": 60,
                         "gap_go_skip_month_first": name != "proxy", **PACK})
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=5).trades_frame()
    traded = set(tf.entry_time.dt.tz_convert(NY).dt.date)
    b = bars.copy()
    b.index = b.index.tz_convert(NY)
    if first:
        b = b[b.index >= pd.Timestamp(first, tz=NY)]
    m = b.index.hour * 60 + b.index.minute
    rows = []
    for day, g in b[(m >= 570) & (m < 960)].groupby(b[(m >= 570) & (m < 960)].index.date):
        if day in traded:
            continue
        gm = g.index.hour * 60 + g.index.minute
        if not ((gm == 570).any() and (gm == 595).any() and (gm == 925).any() and (gm == 955).any()):
            continue
        o930 = g.open[gm == 570].iloc[0]
        c1000 = g.close[gm == 595].iloc[0]
        c1530 = g.close[gm == 925].iloc[0]
        c1600 = g.close[gm == 955].iloc[0]
        hi, lo = g.high[gm < 600].max(), g.low[gm < 600].min()
        a = (1 if c1530 > o930 else -1) * (c1600 - c1530)
        bb = (1 if c1000 > o930 else -1) * (c1600 - c1530)
        d = -(1 if c1000 > o930 else -1) * (c1600 - c1000)
        c = 0.0
        later = g[gm >= 600]
        for t, r in later.iterrows():
            if r.close > hi or r.close < lo:
                side = 1 if r.close > hi else -1
                stop = lo if side > 0 else hi
                rest = later[later.index > t]
                hit = (rest.low <= stop) if side > 0 else (rest.high >= stop)
                c = side * ((stop if hit.any() else c1600) - r.close)
                break
        else:
            c = None
        rows.append({"y": day.year, "A": a, "B": bb, "C": c, "D": d})
    df = pd.DataFrame(rows)
    print(f"\n{name}: {len(df)} sessions without a U41 trade; net $ per MNQ after costs (points x 2 - ${COST:.2f})")
    out = {}
    for k in "ABCD":
        s = df.dropna(subset=[k])
        pnl = s[k] * 2.0 - COST
        out[k] = pnl.groupby(s.y).sum().round(0)
        print(f"  {k}: trades {len(s)}, net ${pnl.sum():,.0f}, win {100 * (pnl > 0).mean():.1f}%, "
              f"years up {(out[k] > 0).sum()} of {len(out[k])}", flush=True)
    print(pd.DataFrame(out).to_string())
