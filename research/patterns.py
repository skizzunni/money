"""Popular chart-pattern and price-action day trades on MNQ, each as usually taught, then with improvements chosen on
NQ 2015-2019 only and confirmed on NQ 2020-2025, the Nasdaq-100 index 2011-2026 and the 2025-2026 stand-in
(docs/RESULTS.md, "Pattern strategies").

All share one execution: 5-minute regular-hours bars, a signal at a bar's close fills at the next bar's open (a tick of
slippage), a resting stop and target (a bar reaching both counts as the stop), flat at 16:00, one trade at a time, no
entry after 15:30, $0.62 a contract a side. Size: the contracts that risk about $500 to the stop (1-10 MNQ).

Setups (as taught):
  triangle   ascending / descending triangle: flat line through 2+ equal swing highs (lows), 2+ rising (falling)
             swing lows (highs); trade the first close through the flat line; target its height; stop past the last
             swing point
  flag       bull / bear flag: a pole (a move of 2+ ATR in 6 bars or less), then 3-8 bars holding in its top (bottom)
             half; trade the close through the flag; stop past the flag; target the pole's length
  orb        opening-range breakout: the 09:30-10:00 range; first close outside it; stop at the other side; target 2R
  vwap       VWAP reclaim: after 6+ bars on one side of the day's VWAP, a bar dips through it and closes back; stop past
             the dip; target 2R
  double     double bottom / top: two swing lows (highs) within 0.1% of each other; close through the neckline (the
             high between); stop past the lows; target the pattern's height
  sweep      previous day's high / low sweep: price trades through yesterday's low (high) and closes back inside;
             stop past the sweep; target 2R
  ema        9/21 EMA cross in the direction of the 200 EMA (5-minute); stop past the last swing; target 2R
  inside     inside-bar breakout: a bar inside the one before; close through the mother bar; stop at its other side;
             target 2R

Improvements tried on each (dev period only to choose): only with the day's direction (long above the day's VWAP and
open, short below), a stop to breakeven at 1R, mornings only (entries to 12:00), and the target at 1/1.5/2/3R.

    python research/patterns.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out.csv>
"""
from __future__ import annotations

import itertools
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v18_scan as V  # noqa: E402

NY = "America/New_York"
TICK, PV, FEE, RISK = 0.25, 2.0, 0.62, 500.0
SETUPS = ("triangle", "flag", "orb", "vwap", "double", "sweep", "ema", "inside", "fvg", "trendpb")
D: dict = {}
ETH = [False]  # PATTERNS_ETH=1: around the clock (sessions 18:00-17:00 New York) on raw NQ futures and the user's MNQ


def init(data: str, sep: str, dec: str) -> None:
    import os
    if os.environ.get("PATTERNS_ETH") == "1":
        from mnqbot.data import resample
        ETH[0] = True
        nq = pd.concat([pd.read_parquet(f) for f in sorted(Path(data).glob("nq1m/NQ_1min_*.parquet"))])
        nq = nq.set_index(pd.to_datetime(nq.timestamp).dt.tz_localize("UTC").dt.tz_convert(NY))
        nq = resample(nq.drop(columns="timestamp").astype(float), "5min")
        cut = pd.Timestamp("2020-01-01", tz=NY)
        D["NQ 15-19 ETH (dev)"] = (nq[nq.index < cut], None)
        D["NQ 20-25 ETH"] = (nq[nq.index >= cut], None)
        mq = pd.read_pickle(f"{data}/mnq_eth.pkl")
        D["MNQ 7-10/2026 ETH"] = (resample(mq.assign(volume=mq.get("volume", 0.0)), "5min"), "2026-07-01")
        return
    V.init([sep, dec, f"{data}/nq5m_scaled.pkl", f"{data}/bars5_scaled.pkl"])
    nq = V.DATA["nq"][0]
    cut = pd.Timestamp("2020-01-01", tz=NY)
    D["NQ 15-19 (dev)"] = (nq[nq.index < cut], None)
    D["NQ 20-25"] = (nq[nq.index >= cut], None)
    D["index 11-26"] = (V.DATA["index"][0], None)
    D["stand-in 25-26"] = (pd.read_pickle(f"{data}/proxy_5m.pkl"), "2025-01-02")


def pivots(x: np.ndarray, k: int, high: bool) -> list[int]:
    n = len(x)
    if high:
        return [i for i in range(k, n - k) if x[i] == x[i - k:i + k + 1].max() and x[i] > x[i + 1:i + k + 1].max()]
    return [i for i in range(k, n - k) if x[i] == x[i - k:i + k + 1].min() and x[i] < x[i + 1:i + k + 1].min()]


def ema(x: np.ndarray, n: int) -> np.ndarray:
    a, out, m = 2 / (n + 1), np.empty(len(x)), x[0]
    for i, v in enumerate(x):
        m = v if i == 0 else a * v + (1 - a) * m
        out[i] = m
    return out


class Day:
    """One session's arrays plus what the setups need from before it."""

    def __init__(self, o, h, l, c, v, mins, pdh, pdl, e9, e21, e200, atr):
        self.o, self.h, self.l, self.c, self.mins = o, h, l, c, mins
        self.n = len(c)
        w = np.where(v > 0, v, 1.0)
        tp = (h + l + c) / 3
        self.vwap = np.cumsum(w * tp) / np.cumsum(w)
        self.pdh, self.pdl, self.e9, self.e21, self.e200, self.atr = pdh, pdl, e9, e21, e200, atr
        self.k = 3
        self.ph, self.pl = pivots(h, self.k, True), pivots(l, self.k, False)


def signals(day: Day, setup: str):
    """(bar index of the signal close, direction, stop, target or None for an R target, kind of target)."""
    h, l, c, n, k = day.h, day.l, day.c, day.n, day.k
    out = []
    if setup == "triangle":
        for d in (1, -1):
            top, bot = (day.ph, day.pl) if d > 0 else (day.pl, day.ph)
            ext, opp = (h, l) if d > 0 else (l, h)
            done = -1
            for i in range(2 * k, n - 1):
                hs = [p for p in top if i - 72 <= p <= i - k and p > done]
                if len(hs) < 2:
                    continue
                p2 = hs[-1]
                for p1 in reversed(hs[:-1]):
                    lvl = max(ext[p1], ext[p2]) if d > 0 else min(ext[p1], ext[p2])
                    if abs(ext[p1] - ext[p2]) > 0.0006 * lvl:
                        continue
                    seg = ext[p1:i]
                    if (d > 0 and (seg.max() > lvl * 1.0006 or c[p1:i].max() > lvl)) or \
                       (d < 0 and (seg.min() < lvl * 0.9994 or c[p1:i].min() < lvl)):
                        continue
                    before = [p for p in bot if i - 72 <= p < p1]
                    lows = before[-1:] + [p for p in bot if p1 < p <= i - k]
                    if len(lows) < 2 or any(d * (opp[x] - opp[y]) >= 0 for x, y in zip(lows, lows[1:], strict=False)):
                        continue
                    if d * (c[i] - lvl) > 0 >= d * (c[i - 1] - lvl):
                        height = d * (lvl - opp[lows[0]])
                        out.append((i, d, opp[lows[-1]] - d * TICK, lvl + d * height, "pattern"))
                        done = i
                    break
    elif setup == "flag":
        for i in range(10, n - 1):
            a = day.atr[i]
            if not a > 0:
                continue
            for d in (1, -1):
                for fl in range(3, 9):  # flag length
                    f0 = i - fl  # first flag bar; the pole ends at f0 - 1
                    if f0 < 7:
                        break
                    pe = f0 - 1
                    seg = slice(pe - 6, pe + 1)
                    pole = (h[pe] - l[seg].min()) if d > 0 else (h[seg].max() - l[pe])
                    if pole < 2 * a:
                        continue
                    if d > 0:
                        fh, flo = h[f0:i].max(), l[f0:i].min()
                        ok = fh <= h[pe] and flo >= h[pe] - pole / 2 and c[i] > fh and c[i - 1] <= fh
                        if ok:
                            out.append((i, 1, flo - TICK, c[i] + pole, "pattern"))
                    else:
                        fl_, fhi = l[f0:i].min(), h[f0:i].max()
                        ok = fl_ >= l[pe] and fhi <= l[pe] + pole / 2 and c[i] < fl_ and c[i - 1] >= fl_
                        if ok:
                            out.append((i, -1, fhi + TICK, c[i] - pole, "pattern"))
                    break
    elif setup == "orb":
        hi, lo = h[:6].max(), l[:6].min()
        for i in range(6, n - 1):
            if c[i] > hi:
                out.append((i, 1, lo - TICK, None, "R"))
                break
            if c[i] < lo:
                out.append((i, -1, hi + TICK, None, "R"))
                break
    elif setup == "vwap":
        vw = day.vwap
        side = np.sign(c - vw)
        for i in range(7, n - 1):
            for d in (1, -1):
                if (side[i - 7:i - 1] == d).all() and d * (l[i] if d > 0 else h[i]) < d * vw[i] and side[i] == d:
                    out.append((i, d, (l[i] if d > 0 else h[i]) - d * TICK, None, "R"))
    elif setup == "double":
        for d in (1, -1):
            pts, ext = (day.pl, l) if d > 0 else (day.ph, h)
            used = set()
            for j, p2 in enumerate(pts):
                for p1 in pts[:j]:
                    if p2 - p1 < 4 or abs(ext[p1] - ext[p2]) > 0.001 * ext[p1] or p1 in used:
                        continue
                    neck = h[p1:p2 + 1].max() if d > 0 else l[p1:p2 + 1].min()
                    edge = min(ext[p1], ext[p2]) if d > 0 else max(ext[p1], ext[p2])
                    for i in range(p2 + k, min(n - 1, p2 + 36)):
                        if d * (c[i] - neck) > 0:
                            if d * (c[i - 1] - neck) <= 0:
                                out.append((i, d, edge - d * TICK, neck + d * abs(neck - edge), "pattern"))
                                used.add(p1)
                            break
                        if d * (ext[i] - edge) < 0:
                            break
    elif setup == "sweep":
        if not math.isnan(day.pdl):
            for i in range(1, n - 1):
                if l[i] < day.pdl < c[i]:
                    out.append((i, 1, l[:i + 1].min() - TICK, None, "R"))
                    break
            for i in range(1, n - 1):
                if h[i] > day.pdh > c[i]:
                    out.append((i, -1, h[:i + 1].max() + TICK, None, "R"))
                    break
    elif setup == "ema":
        e9, e21, e200 = day.e9, day.e21, day.e200
        for i in range(1, n - 1):
            for d in (1, -1):
                if d * (e9[i] - e21[i]) > 0 >= d * (e9[i - 1] - e21[i - 1]) and d * (c[i] - e200[i]) > 0:
                    sw = [p for p in (day.pl if d > 0 else day.ph) if p <= i - k]
                    if sw:
                        out.append((i, d, (l[sw[-1]] if d > 0 else h[sw[-1]]) - d * TICK, None, "R"))
    elif setup == "inside":
        for i in range(2, n - 1):
            m = i - 2
            if h[i - 1] < h[m] and l[i - 1] > l[m]:
                if c[i] > h[m]:
                    out.append((i, 1, l[m] - TICK, None, "R"))
                elif c[i] < l[m]:
                    out.append((i, -1, h[m] + TICK, None, "R"))
    elif setup == "fvg":  # displacement fill: a strong bar leaves a gap; enter when a later bar retests it and holds
        for g in range(2, n - 2):
            a = day.atr[g]
            if not a > 0:
                continue
            for d in (1, -1):
                body = d * (c[g - 1] - day.o[g - 1])
                if body < 1.5 * a:
                    continue
                top, bot = (l[g], h[g - 2]) if d > 0 else (h[g], l[g - 2])  # the gap: (near edge, far edge)
                if d * (top - bot) <= 0:
                    continue
                stop = (l[g - 2] if d > 0 else h[g - 2]) - d * TICK
                for j in range(g + 1, min(n - 1, g + 13)):
                    if d * (c[j] - bot) < 0:  # closed through the gap: no setup
                        break
                    touched = (l[j] <= top) if d > 0 else (h[j] >= top)
                    if touched and d * (c[j] - top) > 0:  # the retest bar closes back out of the gap
                        out.append((j, d, stop, None, "R"))
                        break
    elif setup == "trendpb":  # trend follow: a regression slope, a pullback, and the bar that resumes it
        x = np.arange(24) - 11.5
        for i in range(25, n - 1):
            a = day.atr[i]
            if not a > 0:
                continue
            slope = float(np.dot(x, c[i - 24:i] - c[i - 24:i].mean()) / np.dot(x, x))  # points a bar
            for d in (1, -1):
                if d * slope * 24 < 3 * a:  # the last two hours moved 3+ ATR on the fitted line
                    continue
                pulled = (l[i - 1] < l[i - 2]) if d > 0 else (h[i - 1] > h[i - 2])
                if pulled and d * (c[i] - (h[i - 1] if d > 0 else l[i - 1])) > 0:
                    lo = l[i - 6:i + 1].min() if d > 0 else h[i - 6:i + 1].max()
                    out.append((i, d, lo - d * TICK, None, "R"))
    return sorted(out, key=lambda s: s[0])


def prepare(bars: pd.DataFrame, setup: str) -> list:
    """The sessions and each one's signals (the same for every execution variant)."""
    t = bars.index.tz_convert(NY)
    mins = (t.hour * 60 + t.minute).to_numpy()
    day_id = t.normalize()
    if ETH[0]:  # a session runs 18:00-17:00; shift the clock so the 15:30 / 16:00 rules fall at 16:25 / 16:55
        day_id = (t + pd.Timedelta(hours=6)).normalize()
        mins = (mins - 1080) % 1440 - 420
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = bars["volume"].to_numpy(float) if "volume" in bars else np.zeros(len(bars))
    e9, e21, e200 = ema(c, 9), ema(c, 21), ema(c, 200)
    tr = np.maximum(h - l, np.abs(h - np.r_[c[0], c[:-1]]))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    starts = np.flatnonzero(np.r_[True, day_id[1:] != day_id[:-1]])
    ends = np.r_[starts[1:], len(bars)]
    days, pdh, pdl = [], math.nan, math.nan
    for a, b in zip(starts, ends, strict=True):
        if b - a >= 30:
            dy = Day(o[a:b], h[a:b], l[a:b], c[a:b], v[a:b], mins[a:b], pdh, pdl, e9[a:b], e21[a:b], e200[a:b],
                     atr[a:b])
            days.append((dy, t[a:b], day_id[a], signals(dy, setup)))
        pdh, pdl = h[a:b].max(), l[a:b].min()
    return days


def execute(days: list, trend: bool, be: bool, morning: bool, r_target: float, use_pattern_target: bool):
    rows = []
    for dy, tt, did, sigs in days:
        busy_until = -1
        for i, d, stop, tgt, kind in sigs:
            if i <= busy_until or i >= dy.n - 1 or dy.mins[i] + 5 > (720 if morning else 930):
                continue
            if trend and not (d * (dy.c[i] - dy.vwap[i]) > 0 and d * (dy.c[i] - dy.o[0]) > 0):
                continue
            e = i + 1
            px = dy.o[e] + d * TICK
            risk_pts = d * (px - stop)
            if risk_pts <= 0:
                continue
            if kind == "R" or not use_pattern_target:
                tgt = px + d * r_target * risk_pts
            if d * (tgt - px) <= 0:
                continue
            q = min(10, math.floor(RISK / (risk_pts * PV + 2 * FEE)))
            if q < 1:
                continue
            st, why, j = stop, "16:00", e
            while j < dy.n:
                if d * (dy.l[j] if d > 0 else dy.h[j]) <= d * st:
                    x = (min(dy.o[j], st) if d > 0 else max(dy.o[j], st)) - d * TICK
                    why = "stop"
                    break
                if d * ((dy.h[j] if d > 0 else dy.l[j]) - tgt) >= 0:
                    x, why = tgt, "target"
                    break
                if be and d * ((dy.h[j] if d > 0 else dy.l[j]) - (px + d * risk_pts)) >= 0:
                    st = px + d * TICK if d * (px + d * TICK - st) > 0 else st
                if dy.mins[j] + 5 >= 960:
                    x = dy.c[j] - d * TICK
                    break
                j += 1
            else:
                j, x = dy.n - 1, dy.c[-1] - d * TICK
            pnl = d * (x - px) * q * PV - 2 * FEE * q
            rows.append((tt[e], d, q, pnl, risk_pts * q * PV, why, did))
            busy_until = j
    return pd.DataFrame(rows, columns=["time", "dir", "qty", "pnl", "risk", "why", "day"])


def stats(f: pd.DataFrame, first: str | None) -> dict:
    if first and len(f):
        f = f[f.time >= pd.Timestamp(first, tz=NY)]
    if f.empty:
        return {"n/yr": 0}
    p = f.pnl.to_numpy()
    e = np.r_[0, np.cumsum(p)]
    years = max(0.25, (f.time.max() - f.time.min()).days / 365.25)
    return {"n/yr": round(len(f) / years), "win%": round(100 * (p > 0).mean(), 1),
            "pf": round(p[p > 0].sum() / max(1e-9, -p[p < 0].sum()), 2), "R": round(float((p / f.risk).mean()), 3),
            "net/yr": round(p.sum() / years), "dd": round((np.maximum.accumulate(e) - e).max()),
            "worst day": round(f.groupby("day").pnl.sum().min())}


def job(setup: str) -> list[dict]:
    prepared = {name: (prepare(bars, setup), first) for name, (bars, first) in D.items()}
    pat_opts = (True, False) if setup in ("triangle", "flag", "double") else (False,)
    rows = []
    for trend, be, morning, r, pat in itertools.product((False, True), (False, True), (False, True),
                                                        (1.0, 1.5, 2.0, 3.0), pat_opts):
        if pat and r != 2.0:
            continue
        row = {"setup": setup, "trend": trend, "be": be, "morning": morning, "R target": r, "pattern target": pat}
        for name, (days, first) in prepared.items():
            for key, val in stats(execute(days, trend, be, morning, r, pat), first).items():
                row[f"{name} {key}"] = val
        rows.append(row)
    return rows


def main() -> None:
    data, sep, dec, out = sys.argv[1:5]
    with ProcessPoolExecutor(4, initializer=init, initargs=(data, sep, dec)) as ex:
        rows = [r for rs in ex.map(job, SETUPS) for r in rs]
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"{len(rows)} variants -> {out}")


if __name__ == "__main__":
    main()
