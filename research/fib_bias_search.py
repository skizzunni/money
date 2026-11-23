# ruff: noqa: E501
"""The user's idea (2026-11-23): a bias, the trend, a Fibonacci entry. research/fib_pullback.py (fixed: a setup dies once
price trades through its stop) with the bias as a filter: none, the 20-day trend (yesterday's close against the 20-day
average), the day's direction (the last close against the day's 09:30 open), or both; the leg's size, the entry, the stop,
the target and the last entry time varied. Chosen on NQ 2015-2019 only; then NQ 2020-2025, ES 2020-2024 and the user's MNQ
2026 are reported for the chosen rules.

    python research/fib_bias_search.py <nq1m_scaled.pkl> <es_continuous_1m.parquet> <MNQ 1-minute series csv.gz> <out.csv>
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from orb_every_day import FEE, NY, SPEC, sessions

SETS: dict = {}


def trade(s, bias20: int, mode: str, leg: float, ent: float, sl: float, tp: float, last: int, tick: float):
    d, mm, o, h, lo, c = s
    n = len(o)
    hi_v, hi_t, lo_v, lo_t = h[0], 0, lo[0], 0
    for k in range(1, n):
        if mm[k] >= last:
            return None
        if mm[k] >= 600:
            sides = (1, -1)
            if mode in ("sma20", "both"):
                sides = tuple(x for x in sides if x == bias20)
            if mode in ("open", "both"):
                day_dir = 1 if c[k - 1] > o[0] else -1 if c[k - 1] < o[0] else 0
                sides = tuple(x for x in sides if x == day_dir)
            for side in sides:
                if (side > 0 and hi_t == 0) or (side < 0 and lo_t == 0):
                    continue
                top, bot = (hi_v, lo[:hi_t + 1].min()) if side > 0 else (h[:lo_t + 1].max(), lo_v)
                size = top - bot
                if size < leg * c[k - 1]:
                    continue
                level = top - ent * size if side > 0 else bot + ent * size
                stop = top - sl * size - tick if side > 0 else bot + sl * size + tick
                if (side > 0 and lo[hi_t:k].min() <= stop) or (side < 0 and h[lo_t:k].max() >= stop):
                    continue
                target = bot + tp * size if side > 0 else top - tp * size
                if not (lo[k] <= level - tick if side > 0 else h[k] >= level + tick):
                    continue
                fill = min(o[k], level) if side > 0 else max(o[k], level)
                for j in range(k, n):
                    if (side > 0 and lo[j] <= stop) or (side < 0 and h[j] >= stop):
                        px = (min(o[j], stop) if side > 0 else max(o[j], stop)) if j > k else stop
                        return d, side, (px - side * tick - fill) * side
                    if j > k and ((side > 0 and h[j] >= target + tick) or (side < 0 and lo[j] <= target - tick)):
                        return d, side, (target - fill) * side
                    if mm[j] >= 959:
                        return d, side, (c[j] - side * tick - fill) * side
                return d, side, (c[-1] - side * tick - fill) * side
        if h[k] > hi_v:
            hi_v, hi_t = h[k], k
        if lo[k] < lo_v:
            lo_v, lo_t = lo[k], k
    return None


def score(args):
    name, rule = args
    ss, bias, sym = SETS[name]
    tick, pv = SPEC[sym]
    mode, leg, ent, sl, tp, last = rule
    tr = []
    for i, s in enumerate(ss):
        if mode in ("sma20", "both") and bias[i] == 0:
            continue
        x = trade(s, int(bias[i]), mode, leg, ent, sl, tp, last, tick)
        if x is not None:
            tr.append(x)
    if not tr:
        return {"set": name, "rule": rule, "trades": 0}
    t = pd.DataFrame(tr, columns=["d", "side", "pts"])
    t["usd"] = t.pts * pv - 2 * FEE
    yr = t.groupby(pd.to_datetime(t.d).dt.year).usd.sum()
    daily = t.groupby("d").usd.sum()
    eq = daily.cumsum()
    return {"set": name, "rule": rule, "trades": len(t), "days_traded": round(len(t) / len(ss), 3),
            "win": round(float((t.usd > 0).mean()), 3), "net": round(float(t.usd.sum())),
            "pf": round(float(t.usd[t.usd > 0].sum() / max(1e-9, -t.usd[t.usd < 0].sum())), 2),
            "dd": round(float((eq.cummax().clip(lower=0) - eq).max())), "yrs_up": f"{(yr > 0).sum()}/{len(yr)}"}


def bias_of(ss):
    closes = pd.Series([s[5][-1] for s in ss])
    sma, prev = closes.rolling(20).mean().shift(1), closes.shift(1)
    return np.where(prev > sma, 1, np.where(prev < sma, -1, 0))


def load(nq_path, es_path, mnq_path):
    nq = pd.read_pickle(nq_path)[["open", "high", "low", "close"]]
    es = pd.read_parquet(es_path)[["open", "high", "low", "close"]]
    es.index = es.index.tz_convert(NY)
    m = pd.read_csv(mnq_path, header=None, names=["t", "open", "high", "low", "close"])
    m.index = pd.to_datetime(m.pop("t")).dt.tz_localize(NY)
    for name, df, lo, hi, sym in (("NQ 2015-19", nq, "2014-11-01", "2020-01-01", "MNQ"),
                                  ("NQ 2020-25", nq, "2019-11-01", "2025-07-01", "MNQ"),
                                  ("ES 2020-24", es, "2020-01-01", "2025-01-01", "MES"),
                                  ("MNQ 2026", m, "2026-01-01", "2027-01-01", "MNQ")):
        ss = sessions(df[(df.index >= pd.Timestamp(lo, tz=NY)) & (df.index < pd.Timestamp(hi, tz=NY))])
        b = bias_of(ss)
        if name.startswith("NQ"):  # the 2 warm-up months only feed the 20-day bias
            first = pd.Timestamp(name[3:7] + "-01-01").date()
            keep = [i for i, s in enumerate(ss) if s[0] >= first]
            ss, b = [ss[i] for i in keep], b[keep]
        SETS[name] = (ss, b, sym)


GRID = list(itertools.product(("none", "sma20", "open", "both"), (0.003, 0.005, 0.008), (0.5, 0.618, 0.705),
                              (0.786, 1.0), (0.9, 1.0, 1.272), (720, 870)))


def init(*a):
    load(*a)


def main() -> None:
    a = sys.argv[1:4]
    with ProcessPoolExecutor(4, initializer=init, initargs=a) as ex:
        dev = pd.DataFrame(list(ex.map(score, [("NQ 2015-19", r) for r in GRID if r[3] > r[2]], chunksize=4)))
        dev = dev[dev.trades >= 200].sort_values("pf", ascending=False)
        top = list(dev.rule.head(10))
        rest = pd.DataFrame(list(ex.map(score, [(s, r) for r in top for s in ("NQ 2020-25", "ES 2020-24", "MNQ 2026")])))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print("NQ 2015-19 (choosing), best by profit factor:")
    print(dev.head(10).to_string(index=False))
    print("the same rules elsewhere:")
    print(rest.to_string(index=False))
    pd.concat([dev, rest]).to_csv(sys.argv[4], index=False)


if __name__ == "__main__":
    main()
