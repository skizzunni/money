"""Round one hundred and twenty: a breakout of the overnight range, on its own.

    python research/overnight_range.py nsx1m_scaled.pkl nq1m_scaled.pkl

The overnight session's high and low (18:00 to 09:29 New York) are levels futures traders watch, and they are not the
breakout's (today's open +/- half of yesterday's 09:30-16:00 range). Rule, fixed before running, everything but the
levels as the strategy's breakout (research/combo_live.williams_legs): when the 09:30 open is inside the overnight
range, the first 1-minute bar from 09:30 to 15:00 that trades through its high (low) buys (sells) at the next bar's
open plus a tick; stop a quarter of yesterday's regular-hours range from the fill; $200 of risk, 1-10 MNQ; out at the
15:59 close; one trade a day; a bar through both: none. Sessions after a month end skipped (the rescaled data's gap).
Bar, fixed before running: one test, so mean $ a trade > 0 with t >= 2 on 2011-18, then t >= 2 on 2019-26 AND NQ
2015-25, and positive in the 13 months from July 2025. Also its daily P/L's correlation with the breakout's.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_live as C  # noqa: E402


def trades(path):
    bars = pd.read_pickle(path)
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o, h, lo, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(tmin == 570)
    out, prev_rng = [], None
    for n, a in enumerate(starts):
        b = a + int(np.searchsorted(day[a:a + 600], day[a], side="right"))  # this calendar day's bars from 09:30
        rth_end = a + int(np.searchsorted(tmin[a:b], 960))
        rng = prev_rng
        prev_rng = h[a:rth_end].max() - lo[a:rth_end].min() if rth_end > a else None
        if rng is None or rng <= 0 or n == 0 or day[starts[n - 1]].month != day[a].month:
            continue
        # the overnight session: from the previous calendar day's 18:00 to 09:29
        night0 = int(np.searchsorted(idx, (day[a] - pd.Timedelta(hours=6))))
        if night0 >= a:
            continue
        onh, onl = h[night0:a].max(), lo[night0:a].min()
        if not (onl < o[a] < onh):
            continue
        dist = C.S * rng
        q = math.floor(C.RISK / (dist * C.PV))
        if q < 1:
            if dist * C.PV > 1.5 * C.RISK:
                continue
            q = 1
        q = min(q, 10)
        last = rth_end - 1
        for j in range(a, last):
            if tmin[j] > C.LAST_ENTRY:
                break
            hu, hd = h[j] >= onh, lo[j] <= onl
            if hu and hd:
                break
            if not (hu or hd):
                continue
            d = 1 if hu else -1
            e = j + 1
            entry = o[e] + d * C.TICK
            stop = entry - d * dist
            px = c[last] - d * C.TICK
            for m in range(e, last + 1):
                if (d > 0 and lo[m] <= stop) or (d < 0 and h[m] >= stop):
                    px = (min(o[m], stop) if d > 0 else max(o[m], stop)) - d * C.TICK
                    break
            out.append((day[a].tz_localize(None), d, q * (d * (px - entry) * C.PV - C.FEE)))
            break
    return pd.DataFrame(out, columns=["day", "dir", "pnl"])


def williams_daily(path):
    bars = A.rth(path)
    w = C.williams_legs(bars)
    idx = bars.index.tz_convert(A.NY)
    return pd.Series({idx[a].normalize().tz_localize(None): pnl for a, _, _, _, _, pnl, _ in w})


def main() -> None:
    with ProcessPoolExecutor(max_workers=4) as pool:
        nsx, nq = pool.map(trades, sys.argv[1:3])
        w_nsx, w_nq = pool.map(williams_daily, sys.argv[1:3])
    rows = []
    for label, df, w, first, last in (("2011-2018", nsx, w_nsx, "2011-01-01", "2018-12-31"),
                                      ("2019-2026", nsx, w_nsx, "2019-01-01", "2026-09-30"),
                                      ("Jul 2025-Sep 2026", nsx, w_nsx, "2025-07-01", "2026-09-30"),
                                      ("NQ 2015-2025", nq, w_nq, "2015-01-01", "2025-07-31")):
        x = df[(df.day >= pd.Timestamp(first)) & (df.day <= pd.Timestamp(last))]
        t = stats.ttest_1samp(x.pnl, 0.0).statistic
        both = pd.concat([x.set_index("day").pnl, w], axis=1, join="inner").fillna(0)
        years = (pd.Timestamp(last) - pd.Timestamp(first)).days / 365.25
        rows.append({"period": label, "trades": len(x), "trades/year": len(x) / years,
                     "$/trade": x.pnl.mean(), "win %": 100 * (x.pnl > 0).mean(), "t": t,
                     "corr with breakout (days both trade)": both.corr().iloc[0, 1] if len(both) > 10 else np.nan})
    res = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(res.round(3).to_string(index=False))
    r = res.set_index("period")
    ok = (r.loc["2011-2018", "$/trade"] > 0 and r.loc["2011-2018", "t"] >= 2 and r.loc["2019-2026", "t"] >= 2 and
          r.loc["NQ 2015-2025", "t"] >= 2 and r.loc["Jul 2025-Sep 2026", "$/trade"] > 0)
    print("COUNTS" if ok else "does not count")


if __name__ == "__main__":
    main()
