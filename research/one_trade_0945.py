# ruff: noqa: E501
"""The "one trade a day at 09:45 ET" plan from a TikTok the user sent (2026-11-19: "91%, 10 of 11 days green", a Topstep
50K, +$160 funded days, one Combine lost on day 2). Tested on NQ 2015-2025 (MNQ, $2 a point) and ES 2020-2024 (MES).

Rules: every session, at the 09:45 bar's open, enter 1 micro in the direction of the 09:30-09:45 move ("with") or
against it ("fade"); a fixed target `tp` points and stop `sl` points from the fill; out at 15:59 otherwise. $0.62 a side,
a tick of slippage on the entry and on a stop fill; the stop first when a minute reaches both. The account test as
research/orb_every_day.py (fresh 50K starts every quarter, 12 months, the $2,000 floor).

    python research/one_trade_0945.py <nq1m_scaled.pkl> <es_continuous_1m.parquet> <out.csv>
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd
from orb_every_day import FEE, NY, SPEC, account_test, sessions


def trade(s, mode: str, tp: float, sl: float, tick: float):
    d, mm, o, h, lo, c = s
    i = np.flatnonzero(mm == 585)
    if len(i) == 0:
        return None
    e = int(i[0])
    move = o[e] - o[0]
    if move == 0:
        return None
    side = (1 if move > 0 else -1) * (1 if mode == "with" else -1)
    fill = o[e] + side * tick
    st, tg = fill - side * sl, fill + side * tp
    for k in range(e, len(o)):
        if (side > 0 and lo[k] <= st) or (side < 0 and h[k] >= st):
            px = (min(o[k], st) if side > 0 else max(o[k], st)) if k > e else st
            return d, (px - side * tick - fill) * side
        if (side > 0 and h[k] >= tg + tick) or (side < 0 and lo[k] <= tg - tick):
            return d, tp
        if mm[k] >= 959:
            break
    return d, (c[k] - side * tick - fill) * side


def study(name, ss, sym, grid):
    tick, pv = SPEC[sym]
    rows = []
    for mode, tp, mult in grid:
        sl = tp * mult
        tr = [x for x in (trade(s, mode, tp, sl, tick) for s in ss) if x is not None]
        t = pd.DataFrame(tr, columns=["d", "pts"])
        t["usd"] = t.pts * pv - 2 * FEE
        daily = t.groupby("d").usd.sum()
        eq = daily.cumsum()
        yr = t.groupby(pd.to_datetime(t.d).dt.year).usd.sum()
        rows.append({"set": name, "mode": mode, "tp": tp, "sl": sl, "win": round((t.usd > 0).mean(), 3),
                     "net": round(t.usd.sum()), "per_day": round(t.usd.mean(), 2),
                     "pf": round(t.usd[t.usd > 0].sum() / max(1e-9, -t.usd[t.usd < 0].sum()), 2),
                     "dd": round((eq.cummax().clip(lower=0) - eq).max()), "worst_day": round(daily.min()),
                     "yrs_up": f"{(yr > 0).sum()}/{len(yr)}", **account_test(daily)})
    return pd.DataFrame(rows)


def main() -> None:
    nq = pd.read_pickle(sys.argv[1])
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)][["open", "high", "low", "close"]]
    es = pd.read_parquet(sys.argv[2])[["open", "high", "low", "close"]]
    es.index = es.index.tz_convert(NY)
    gq = list(itertools.product(("with", "fade"), (10.0, 20.0, 40.0, 80.0), (1.0, 2.0, 4.0)))
    ge = list(itertools.product(("with", "fade"), (2.5, 5.0, 10.0, 20.0), (1.0, 2.0, 4.0)))
    out = pd.concat([study("NQ 2015-25 (MNQ)", sessions(nq), "MNQ", gq), study("ES 2020-24 (MES)", sessions(es), "MES", ge)])
    out.to_csv(sys.argv[3], index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    for s, g in out.groupby("set"):
        print(s)
        print(g.sort_values("net", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
