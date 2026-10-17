"""Round one hundred and ten: intraday momentum into the close (Gao, Han, Li and Zhou 2018), description and test.

    python research/last_half_hour.py nsx1m_scaled.pkl nq1m_scaled.pkl

Gao, Han, Li and Zhou ("Market intraday momentum", Journal of Financial Economics 2018) find the market's return from
the previous close to 10:00 predicts the return of the last half hour, more so on volatile days. The bot checks at
15:30 too, but only trades if price is outside its noise area; this trades the sign alone.
Trades at 1 MNQ, in the direction of the signal's sign, at the open of the 15:30 minute (or 15:00 for the last hour),
out at the 15:59 close; $2.24 costs a trade. Sessions after a month end's first session skipped (the rescaled data's
gap); signals of exactly zero: no trade.
Signals: S1 the previous 16:00 close to 10:00; S2 the 09:30 open to 15:30; S3 the previous close to 15:30.
Windows: 15:30-16:00 and 15:00-16:00 (for S2/S3 at 15:00 the signal runs to 15:00). Conditions: every day; the half
of days with the larger |S1| (above its median over the previous 250 sessions). 12 rules.
Bar, fixed before running: Benjamini-Hochberg at 10% on 2011-18 (one-sided), then t >= 2 on 2019-26 and NQ 2015-25.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402

PV, COST = 2.0, 1.24 + 2 * 0.25 * 2.0


def sessions(path):
    bars = A.rth(path)
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o, c = bars.open.to_numpy(float), bars.close.to_numpy(float)
    starts = np.flatnonzero(tmin == 570)
    rows, prev_close = [], np.nan
    for n, a in enumerate(starts):
        b = starts[n + 1] if n + 1 < len(starts) else len(bars)
        b = a + int(np.searchsorted(day[a:b], day[a], side="right"))
        t = tmin[a:b]
        at = {m: a + int(np.searchsorted(t, m)) for m in (600, 900, 930)}
        last = a + int(np.searchsorted(t, 960)) - 1
        ok = all(i < b and tmin[i] == m for m, i in at.items()) and tmin[last] == 959
        fresh = n > 0 and day[starts[n - 1]].month == day[a].month
        if ok and fresh and not np.isnan(prev_close):
            rows.append({"day": day[a].tz_localize(None), "s1": o[at[600]] - prev_close,
                         "s2_30": o[at[930]] - o[a], "s3_30": o[at[930]] - prev_close,
                         "s2_60": o[at[900]] - o[a], "s3_60": o[at[900]] - prev_close,
                         "r30": c[last] - o[at[930]], "r60": c[last] - o[at[900]]})
        prev_close = c[b - 1] if tmin[b - 1] < 960 else c[b - 2]
    df = pd.DataFrame(rows)
    df["big"] = df.s1.abs() > df.s1.abs().rolling(250, min_periods=60).median().shift(1)
    return df


def rules(df):
    out = []
    for win in (30, 60):
        for sig in ("s1", "s2", "s3"):
            col = "s1" if sig == "s1" else f"{sig}_{win}"
            for cond in ("all", "big |S1|"):
                x = df if cond == "all" else df[df.big]
                d = np.sign(x[col].to_numpy())
                pnl = (d * x[f"r{win}"].to_numpy() * PV - COST)[d != 0]
                out.append((f"{sig} {15 if win == 60 else '15:30'}-16:00 {cond}", pnl))
    return out


def table(df, first, last):
    df = df[(df.day >= pd.Timestamp(first)) & (df.day <= pd.Timestamp(last))]
    rows = []
    for name, pnl in rules(df):
        t, p = stats.ttest_1samp(pnl, 0.0, alternative="greater")
        rows.append({"rule": name, "trades": len(pnl), "$/trade": pnl.mean(), "win %": 100 * (pnl > 0).mean(),
                     "t": t, "p": p})
    return pd.DataFrame(rows)


def main() -> None:
    with ProcessPoolExecutor(max_workers=2) as pool:
        nsx, nq = pool.map(sessions, sys.argv[1:3])
    res = {"2011-2018": table(nsx, "2011-01-01", "2018-12-31"), "2019-2026": table(nsx, "2019-01-01", "2026-09-30"),
           "NQ 2015-2025": table(nq, "2015-01-01", "2025-07-31")}
    pd.set_option("display.width", 200)
    for k, v in res.items():
        print(f"\n{k}")
        print(v.round(3).to_string(index=False))
    disc = res["2011-2018"]
    m = len(disc)
    rank = disc.p.rank(method="first")
    passing = rank[disc.p <= 0.10 * rank / m]
    cut = passing.max() if len(passing) else 0
    found = False
    print()
    for i, r in disc.iterrows():
        if rank[i] > cut or r["$/trade"] <= 0:
            continue
        h = [res[p].iloc[i] for p in ("2019-2026", "NQ 2015-2025")]
        ok = all(x["$/trade"] > 0 and x.t >= 2 for x in h)
        found |= ok
        print(f"{r.rule}: holdouts t {h[0].t:.2f} / {h[1].t:.2f}: {'COUNTS' if ok else 'does not count'}")
    print("found" if found else "nothing counts")


if __name__ == "__main__":
    main()
