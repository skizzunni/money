"""An opening-range breakout that trades (almost) every session, on NQ (MNQ) and ES (MES), with the 50K account test.

The user (2026-11-18): "trade every day", most trades winners, never lose the account; MNQ, or ES or gold if MNQ can't.
Rules (one trade a day, 1 micro contract):
  * the opening range: the high and low of the first `orb` minutes from 09:30 New York;
  * entry: the first 1-minute close above the range high (long) or below the low (short) before 15:00, filled at the
    next minute's open (+1 tick of slippage);
  * stop: the other side of the range ("far") or its middle ("mid"), at most `cap` points from the fill; a stop fill
    costs a tick of slippage, and the stop is checked before the target in a minute that reaches both;
  * target: `r` times the stop distance (a limit, filled at its price once a minute trades a tick through it), or
    none (r = 0); out at the 15:59 close otherwise;
  * $0.62 a side.
The account test: fresh 50K accounts started on the first session of every quarter, 12 months each, 1 micro; the floor
trails the highest end-of-day balance by $2,000 and stops at $50,000; an account is lost when a day ends at or below it.

    python research/orb_every_day.py <nq1m_scaled.pkl> <es_continuous_1m.parquet>
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd

NY = "America/New_York"
SPEC = {"MNQ": (0.25, 2.0), "MES": (0.25, 5.0)}  # tick, $ a point
FEE = 0.62


def sessions(bars: pd.DataFrame) -> list[tuple]:
    t = bars.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    b = bars[(m >= 570) & (m < 960)]
    t = b.index.tz_convert(NY)
    out = []
    for d, g in b.groupby(t.date):
        if len(g) < 370:  # half days and holes
            continue
        mm = (g.index.tz_convert(NY).hour * 60 + g.index.tz_convert(NY).minute).to_numpy()
        out.append((d, mm, g.open.to_numpy(float), g.high.to_numpy(float), g.low.to_numpy(float),
                    g.close.to_numpy(float)))
    return out


def day_trade(s, orb: int, stop: str, cap: float, r: float, tick: float):
    d, mm, o, h, lo, c = s
    rng = mm < 570 + orb
    if rng.sum() < orb - 2:
        return None
    hi, lw = h[rng].max(), lo[rng].min()
    for i in np.flatnonzero(~rng):
        if mm[i] >= 900 or i + 1 >= len(o):
            return None
        side = 1 if c[i] > hi else -1 if c[i] < lw else 0
        if side == 0:
            continue
        j = i + 1
        fill = o[j] + side * tick
        ref = (lw if side > 0 else hi) if stop == "far" else (hi + lw) / 2
        dist = min(abs(fill - ref), cap)
        if dist < 4 * tick:
            dist = 4 * tick
        st = fill - side * dist
        tg = fill + side * r * dist if r > 0 else np.nan
        for k in range(j, len(o)):
            if (side > 0 and lo[k] <= st) or (side < 0 and h[k] >= st):
                px = (min(o[k], st) if side > 0 else max(o[k], st)) if k > j else st
                return d, side, (px - side * tick - fill) * side
            if r > 0 and ((side > 0 and h[k] >= tg + tick) or (side < 0 and lo[k] <= tg - tick)):
                return d, side, (tg - fill) * side
            if mm[k] >= 959:
                return d, side, (c[k] - side * tick - fill) * side
        return d, side, (c[-1] - side * tick - fill) * side
    return None


def account_test(daily: pd.Series) -> dict:
    days = daily.index
    starts = sorted({pd.Timestamp(x).to_period("Q").start_time.date() for x in days})
    res = []
    for s0 in starts:
        seg = daily[(days >= s0) & (days < (pd.Timestamp(s0) + pd.DateOffset(months=12)).date())]
        if len(seg) < 200:
            continue
        bal, high, lost = 50000.0, 50000.0, False
        for p in seg:
            bal += p
            if bal <= min(high - 2000.0, 50000.0):  # the floor trails by $2,000 and stops at the start
                lost = True
                break
            high = max(high, bal)
        res.append((lost, bal - 50000.0))
    if not res:
        return {"starts": 0}
    lost = np.array([x[0] for x in res])
    pnl = np.array([x[1] for x in res])
    return {"starts": len(res), "lost": round(lost.mean(), 3), "median_12m": round(float(np.median(pnl))),
            "reach_25k": round(float((pnl >= 25000).mean()), 3)}


def study(name: str, ss: list, sym: str) -> pd.DataFrame:
    tick, pv = SPEC[sym]
    rows = []
    n = len(ss)
    for orb, stop, cap, r in itertools.product((5, 15, 30), ("far", "mid"), (40.0, 80.0, 1e9) if sym == "MNQ"
                                                else (10.0, 20.0, 1e9), (0.5, 1.0, 1.5, 2.0, 0.0)):
        tr = [x for x in (day_trade(s, orb, stop, cap, r, tick) for s in ss) if x is not None]
        if not tr:
            continue
        t = pd.DataFrame(tr, columns=["d", "side", "pts"])
        t["usd"] = t.pts * pv - 2 * FEE
        daily = t.groupby("d").usd.sum()
        eq = daily.cumsum()
        yr = t.groupby(pd.to_datetime(t.d).dt.year).usd.sum()
        acc = account_test(daily)
        rows.append({"set": name, "orb": orb, "stop": stop, "cap": cap if cap < 1e8 else 0, "r": r,
                     "days_traded": round(len(t) / n, 3), "win": round((t.usd > 0).mean(), 3),
                     "net": round(t.usd.sum()), "per_day": round(t.usd.sum() / n, 2),
                     "pf": round(t.usd[t.usd > 0].sum() / -t.usd[t.usd < 0].sum(), 2),
                     "dd": round((eq.cummax().clip(lower=0) - eq).max()), "worst_day": round(daily.min()),
                     "yrs_up": f"{(yr > 0).sum()}/{len(yr)}", **acc})
    return pd.DataFrame(rows)


def main() -> None:
    nq = pd.read_pickle(sys.argv[1])
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)][["open", "high", "low", "close"]]
    es = pd.read_parquet(sys.argv[2])[["open", "high", "low", "close"]]
    es.index = es.index.tz_convert(NY)
    out = pd.concat([study("NQ 2015-25 (MNQ)", sessions(nq), "MNQ"), study("ES 2020-24 (MES)", sessions(es), "MES")])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    out.to_csv(sys.argv[3] if len(sys.argv) > 3 else "orb_every_day.csv", index=False)
    for s, g in out.groupby("set"):
        print(s, "- every rule with at least 90% of days traded, by win rate:")
        print(g[g.days_traded >= 0.9].sort_values(["win", "net"], ascending=False).head(25).to_string(index=False))


if __name__ == "__main__":
    main()
