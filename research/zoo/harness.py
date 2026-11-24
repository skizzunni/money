# ruff: noqa: E501
"""A common test bench for intraday MNQ strategies (2026-11-23, the user: "every strategy known and unknown ... find
something that works", for the 50K Take Profit Trader account with the $2,000 end-of-day trailing floor).

Sets (5-minute regular-hours bars, 09:30-16:00 New York, the bar's start time):
  * dev:    NQ 2015-2019 (research/v4_search's 1-minute history, rescaled month by month; a day's prices are on one
            scale, and prior-day levels are carried over in today's scale by the ratio of the two scales);
  * unseen: NQ 2020 - mid 2025 and ES 2020-2024 (MES, $5 a point);
  * live:   the user's MNQ Sep 2026 - Nov 17 (NinjaTrader export) with the days it lacks (Oct 27 - Nov 12, Nov 18-20) from Yahoo's 5-minute bars.
A strategy is a function (days, i, **params) -> trades for day i, each (side, entry bar, entry px, exit px, why); the
bench applies slippage, $0.62 a side, the contract's point value, then the account test: a fresh 50K started on the first
session of every month, 12 months, the floor trailing the highest end-of-day balance by $2,000 and stopping at $50,000;
an account is lost when a trade or a day ends at or below the floor. Sizing: `qty_fn(profit) -> contracts`.

    python research/zoo/harness.py build <data dir>      # caches the sets as zoo_days.pkl in the data dir
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

NY = "America/New_York"
FEE = 0.62
SPEC = {"MNQ": (0.25, 2.0), "MES": (0.25, 5.0)}
DATA = os.environ.get("ZOO_DATA", "")


def rth5(df: pd.DataFrame, scale: pd.Series | None = None) -> list[dict]:
    t = df.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    df = df[(m >= 570) & (m < 960)]
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if "scale" in df.columns:
        agg["scale"] = "last"
    b = df.resample("5min", label="left", closed="left").agg(agg).dropna(subset=["open"])
    out = []
    tt = b.index.tz_convert(NY)
    for d, g in b.groupby(tt.date):
        if len(g) < 76:
            continue
        gt = g.index.tz_convert(NY)
        rec = {"d": d, "mm": (gt.hour * 60 + gt.minute).to_numpy()}
        for k in ("open", "high", "low", "close", "volume"):
            rec[k[0] if k != "low" else "l"] = g[k].to_numpy(float)
        rec["s"] = float(g["scale"].iloc[-1]) if "scale" in g.columns else 1.0
        out.append(rec)
    return out


def despike(days: list, frac: float = 0.01) -> list:
    """Yahoo's free bars carry the odd bad print (2026-10-30 15:00: an open 1,278 points off the market, back the same
    bar): a bar whose open is more than `frac` from the last close gets that close as its open, and its high / low are
    cut back to its open / close when they sit more than `frac` beyond both."""
    for d in days:
        for key in ("o", "h", "l", "c"):
            d[key] = d[key].copy()
        o, h, lo, c = d["o"], d["h"], d["l"], d["c"]
        for k in range(1, len(o)):
            if abs(o[k] / c[k - 1] - 1) > frac:
                o[k] = c[k - 1]
            top, bot = max(o[k], c[k]), min(o[k], c[k])
            if h[k] > top * (1 + frac):
                h[k] = top
            if lo[k] < bot * (1 - frac):
                lo[k] = bot
    return days


def build(ddir: str) -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import mnq_bars as M
    nq = pd.read_pickle(os.path.join(ddir, "nq1m_scaled.pkl"))
    nq = nq[nq.index < pd.Timestamp("2025-07-01", tz=NY)]
    nd = rth5(nq)
    es = pd.read_parquet(os.path.join(ddir, "es", "es_continuous_1m.parquet"))[["open", "high", "low", "close", "volume"]]
    es.index = es.index.tz_convert(NY)
    sep, dec = M.load(os.path.join(ddir, "MNQ_09-26.Last.txt")), M.load(os.path.join(ddir, "MNQ_12-26_nt_to_1117.Last.txt"))
    mnq, _ = M.traded_series(sep, dec)
    live = rth5(mnq)
    y = pd.read_pickle(os.path.join(ddir, "yahoo_mnq_5m.pkl"))
    have = {r["d"] for r in live}
    live = sorted(live + [r for r in despike(rth5(y)) if r["d"] not in have and r["d"] >= live[0]["d"]], key=lambda r: r["d"])
    sets = {"dev": ([r for r in nd if r["d"].year <= 2019], "MNQ"),
            "unseen_nq": ([r for r in nd if r["d"].year >= 2020], "MNQ"),
            "unseen_es": (rth5(es), "MES"),
            "live": (live, "MNQ")}
    for k, (v, _) in sets.items():
        print(k, len(v), v[0]["d"], v[-1]["d"])
    with open(os.path.join(ddir, "zoo_days.pkl"), "wb") as f:
        pickle.dump(sets, f)


def load_sets(ddir: str | None = None) -> dict:
    with open(os.path.join(ddir or DATA, "zoo_days.pkl"), "rb") as f:
        return pickle.load(f)


def prev(days: list, i: int, k: str, j: int = 1):
    """Day i-j's value of k (a scalar: 'c' last close, 'h' high, 'l' low, 'o' open) in day i's price scale."""
    p = days[i - j]
    v = {"c": p["c"][-1], "h": p["h"].max(), "l": p["l"].min(), "o": p["o"][0]}[k]
    return v * days[i]["s"] / p["s"] if p["s"] else v


def walk(day: dict, i: int, side: int, stop: float, target: float = np.nan, exit_m: int = 955, tick: float = 0.25,
         be_at: float = np.nan, trail: float = np.nan, slip: int = 1, entry: float | None = None, at_open: bool = False):
    """Enter at bar i's open (or `entry`, a limit fill), stop / target resting, out at the close of the first bar starting
    at or after exit_m. be_at: once a bar closes this many points in profit, the stop to entry + a tick; trail: the stop
    this many points behind the best close. The stop first in a bar reaching both; a target never on the fill bar.
    Returns (entry px, exit px, exit bar, why)."""
    o, h, lo, c, mm = day["o"], day["h"], day["l"], day["c"], day["mm"]
    px = o[i] + side * slip * tick if entry is None else entry
    st = stop
    for k in range(i, len(o)):
        if (side > 0 and lo[k] <= st) or (side < 0 and h[k] >= st):
            fill = (min(o[k], st) if side > 0 else max(o[k], st)) if k > i else st
            return px, fill - side * slip * tick, k, "stop"
        if k > i and not np.isnan(target) and ((side > 0 and h[k] >= target + tick) or (side < 0 and lo[k] <= target - tick)):
            return px, target, k, "target"
        if mm[k] >= exit_m:
            if at_open and k + 1 < len(o):  # a market exit sent at this bar's close fills at the next open
                return px, o[k + 1] - side * slip * tick, k, "time"
            return px, c[k] - side * slip * tick, k, "time"
        if not np.isnan(be_at) and side * (c[k] - px) >= be_at:
            st = max(st, px + tick) if side > 0 else min(st, px - tick)
        if not np.isnan(trail):
            st = max(st, c[k] - trail) if side > 0 else min(st, c[k] + trail)
    return px, c[-1] - side * slip * tick, len(o) - 1, "time"


def trades_of(strat, days: list, sym: str, **p) -> pd.DataFrame:
    tick, pv = SPEC[sym]
    rows = []
    for i in range(len(days)):
        for tr in strat(days, i, tick=tick, **p) or []:
            side, ib, epx, xpx, why = tr[:5]
            pts = (xpx - epx) * side
            rows.append((days[i]["d"], side, ib, pts, pts * pv - 2 * FEE, why))
    return pd.DataFrame(rows, columns=["d", "side", "bar", "pts", "usd", "why"])


def account(t: pd.DataFrame, all_days: list, qty_fn=lambda prof: 1, day_stop: float = 0.0, start_every: str = "M",
            early_max: int = 0, early_cushion: float = 0.0, eq_n: int = 0, eq_min: float = 0.0, steps: tuple = (),
            extra: pd.DataFrame | None = None, extra_from: float = 0.0, day_qty=None):
    """Fresh 50K starts (every month), 12 months each. day_stop: no more trades once the day is down this much ($, at
    the sizes taken). early_max: at most this many trades a day while the profit is under early_cushion. eq_n / eq_min:
    sit a day out when the strategy's own 1-contract P/L over the last eq_n sessions (taken or not) is below eq_min.
    steps: contracts by profit, e.g. ((0, 1), (1500, 2), (3500, 3)) (overrides qty_fn).
    Returns per-start (lost, profit, green days, traded days)."""
    days = [r["d"] for r in all_days]
    byday = {d: g.usd.to_numpy() for d, g in t.groupby("d")}
    exday = {d: g.usd.to_numpy() for d, g in extra.groupby("d")} if extra is not None else {}  # a second leg, first in the day
    hyp = np.array([byday[d].sum() if d in byday else 0.0 for d in days])
    idx = pd.Series(range(len(days)), index=pd.to_datetime(days))
    starts = sorted({x.to_period(start_every).start_time for x in idx.index})
    res = []
    for s0 in starts:
        end = s0 + pd.DateOffset(months=12)
        seg = idx[(idx.index >= s0) & (idx.index < end)].to_numpy()
        if len(seg) < 200 or (idx.index[-1] < end - pd.DateOffset(days=10)):
            continue
        bal, high, lost, green, traded = 50000.0, 50000.0, False, 0, 0
        for j in seg:
            d = days[j]
            floor = min(high - 2000.0, 50000.0)
            day_pl = 0.0
            g = byday.get(d)
            if g is not None and eq_n and j >= eq_n and hyp[j - eq_n:j].sum() < eq_min:
                g = None
            if extra is not None and d in exday and bal - 50000.0 >= extra_from:
                g = np.concatenate([exday[d], g]) if g is not None else exday[d]
            if g is not None:
                prof = bal - 50000.0
                q = qty_fn(prof)
                for lim, qq in steps:
                    if prof >= lim:
                        q = qq
                if day_qty is not None:  # research: a day's contracts from the day (e.g. news days)
                    q = day_qty(d, q)
                    if q <= 0:
                        g = None
                        q = 0
                if g is not None and early_max and prof < early_cushion:
                    g = g[:early_max]
                for usd in (g if g is not None else []):
                    if day_stop and day_pl <= -day_stop:
                        break
                    day_pl += usd * q
                    if bal + day_pl <= floor:
                        lost = True
                        break
            bal += day_pl
            if g is not None:
                traded += 1
                green += day_pl > 0
            if lost or bal <= floor:
                lost = True
                break
            high = max(high, bal)
        res.append((lost, bal - 50000.0, green, traded))
    return res


def summary(name: str, t: pd.DataFrame, all_days: list, **acc) -> dict:
    out = {"set": name, "trades": len(t)}
    if len(t) == 0:
        return out
    daily = t.groupby("d").usd.sum().reindex([r["d"] for r in all_days], fill_value=0.0)
    eq = daily.cumsum()
    gp, gl = t.usd[t.usd > 0].sum(), -t.usd[t.usd < 0].sum()
    traded = daily[daily != 0]
    out.update({"win": round(float((t.usd > 0).mean()), 3), "pf": round(float(gp / max(gl, 1e-9)), 2),
                "net": round(float(t.usd.sum())), "per_trade": round(float(t.usd.mean()), 1),
                "green_days": round(float((traded > 0).mean()), 3), "days_traded": round(len(traded) / len(daily), 2),
                "dd": round(float((eq.cummax().clip(lower=0) - eq).max())), "worst_day": round(float(daily.min()))})
    if name != "live":
        r = account(t, all_days, **acc)
        if r:
            lost = np.array([x[0] for x in r])
            prof = np.array([x[1] for x in r])
            out.update({"starts": len(r), "lost": round(float(lost.mean()), 3), "median_12m": round(float(np.median(prof))),
                        "reach_25k": round(float((prof >= 25000).mean()), 3)})
    return out


def evaluate(strat, sets: dict, label: str, **p) -> list[dict]:
    acc = p.pop("acc", {})
    rows = []
    for name, (days, sym) in sets.items():
        t = trades_of(strat, days, sym, **p)
        rows.append({"strategy": label, **summary(name, t, days, **acc)})
    return rows


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2])
