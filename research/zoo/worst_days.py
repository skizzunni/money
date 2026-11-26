"""Research (2026-11-26, docs section 189): the shipped strategy's worst days (1 contract, FOMC days skipped, the $600
day stop at 1 contract not binding), per period: the 20 worst days and what they share against all traded days
(mild-news days left out as the news rule skips them; weekday, a big-news day, the gap trade taken, the number of
trades, the trend's side, the day's range against its 14-day average, the overnight gap against its average, the share
of the day's band trades that hit the full hard stop). Descriptive: it names candidates for later rounds, it ships
nothing by itself. Run from research/: python zoo/worst_days.py
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "zoo")
warnings.filterwarnings("ignore")
import bench as B  # noqa: E402
import fomc_days as F  # noqa: E402


def features(d, t):
    idx = {x["d"]: i for i, x in enumerate(d)}
    rows = []
    for day, g in t.groupby("d"):
        i = idx[day]
        x = d[i]
        rng = (x["h"].max() - x["l"].min())
        avg = np.mean([(y["h"].max() - y["l"].min()) * x["s"] / y["s"] for y in d[max(0, i - 14):i]])
        gap = x["o"][0] - d[i - 1]["c"][-1] * x["s"] / d[i - 1]["s"] if i else np.nan
        gavg = np.mean([abs(d[j]["o"][0] - d[j - 1]["c"][-1] * d[j]["s"] / d[j - 1]["s"]) * x["s"] / d[j]["s"]
                        for j in range(max(1, i - 14), i)])
        sp = x["news"][0]
        band = g[g.bar > 1]
        rows.append(dict(d=day, usd=g.usd.sum(), n=len(g), wd=pd.Timestamp(day).day_name()[:3],
                         news="2-3x" if sp == sp and 2 <= sp < 3 else "6x+" if sp == sp and sp >= 6 else "none/other",
                         gap_trade=bool((g.bar <= 1).any()), rng=rng / avg, gapx=abs(gap) / gavg if gavg else np.nan,
                         full_stops=float((band.usd <= -195).mean()) if len(band) else np.nan,
                         sides=("mixed" if g.side.nunique() > 1 else "long" if g.side.iloc[0] > 0 else "short")))
    return pd.DataFrame(rows)


def main():
    sets = pickle.load(open(B.PK, "rb"))
    for n, lab in (("dev", "2015-19"), ("unseen_nq", "2020-25")):
        d, s = sets[n]
        t, _st = F.tables(d, s, skip=True)
        f = features(d, t)
        f = f[f.news != "2-3x"]  # the news rule: no trades on a mild-news day (as the account trades)
        w = f.nsmallest(20, "usd")
        print(f"{lab}: {len(f)} traded days; the 20 worst: ${w.usd.sum():,.0f} "
              f"({w.usd.min():,.0f} to {w.usd.max():,.0f})")
        for col in ("wd", "news", "gap_trade", "sides"):
            a, b = w[col].value_counts(normalize=True), f[col].value_counts(normalize=True)
            print(f"  {col}: " + ", ".join(f"{k} {a.get(k, 0):.0%} (all {b.get(k, 0):.0%})" for k in b.index))
        for col in ("n", "rng", "gapx", "full_stops"):
            print(f"  {col}: worst median {w[col].median():.2f}, all {f[col].median():.2f}")
        print("  the 20: " + ", ".join(f"{r.d} ${r.usd:,.0f}" for r in w.itertuples()), flush=True)


if __name__ == "__main__":
    main()
