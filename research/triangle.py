"""The ascending-triangle breakout from the user's video (TikTok @traders_notes_team, ETHUSDT 5-minute), as rules,
long only, unchanged: a flat resistance through two or more equal swing highs, two or more rising swing lows under it;
buy the first close above the resistance (filled at the next bar's open); target = the triangle's height (the resistance
minus its first low) above the resistance; stop a tick under the last swing low. Optional: volume falling while it
forms.

Day trading on MNQ: regular hours only (09:30-16:00 New York), patterns within one session, no entry after 15:30, any
open trade closed at 16:00. Costs as the noise strategy's: $0.62 a contract a side and a tick of slippage on market and
stop fills. Size: the contracts that risk about $500 to the stop (1-10 MNQ), or a fixed 10 MNQ. A bar that reaches both
the stop and the target counts as the stop.

The choices the video leaves open are swept (pivot strength k: a swing high/low is the extreme of k bars each side;
"equal" highs: within tol of each other; the pattern's longest span in bars), so the verdict doesn't rest on one pick.

    python research/triangle.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out.csv>
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
TICK, PV, FEE = 0.25, 2.0, 0.62
D: dict = {}


def init(data: str, sep: str, dec: str) -> None:
    V.init([sep, dec, f"{data}/nq5m_scaled.pkl", f"{data}/bars5_scaled.pkl"])
    D["mnq 8/24-10/16"] = (V.DATA["mnq"][0], "2026-08-24")
    D["stand-in 2025-26"] = (pd.read_pickle(f"{data}/proxy_5m.pkl"), "2025-01-02")
    D["NQ 2015-25"] = (V.DATA["nq"][0], None)
    D["index 2011-26"] = (V.DATA["index"][0], None)


def trades(bars: pd.DataFrame, k: int, tol: float, span: int, vol_rule: bool, sizing: str) -> list[dict]:
    t = bars.index.tz_convert(NY)
    mins = (t.hour * 60 + t.minute).to_numpy()
    day = t.normalize()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    v = bars["volume"].to_numpy(float) if "volume" in bars else np.zeros(len(bars))
    out = []
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(bars)]
    for a, b in zip(starts, ends, strict=True):
        n = b - a
        if n < 2 * k + 10:
            continue
        hh, ll = h[a:b], l[a:b]
        ph = [i for i in range(k, n - k) if hh[i] == hh[i - k:i + k + 1].max() and hh[i] > hh[i + 1:i + k + 1].max()]
        pl = [i for i in range(k, n - k) if ll[i] == ll[i - k:i + k + 1].min() and ll[i] < ll[i + 1:i + k + 1].min()]
        pos = None  # (entry index, entry price, stop, target, qty)
        i = 2 * k
        while i < n:
            g = a + i
            if pos is not None:  # manage the open trade on bar i
                e_i, px, stop, tgt, q = pos
                exit_px = why = None
                if l[g] <= stop:
                    exit_px, why = min(o[g], stop) - TICK, "stop"
                elif h[g] >= tgt:
                    exit_px, why = tgt, "target"
                elif mins[g] + 5 >= 960:
                    exit_px, why = c[g] - TICK, "16:00"
                if why:
                    pnl = (exit_px - px) * q * PV - 2 * FEE * q
                    out.append({"time": t[a + e_i], "qty": q, "entry": px, "exit": exit_px, "why": why, "pnl": pnl,
                                "risk": (px - stop) * q * PV, "day": day[g]})
                    pos = None
                i += 1
                continue
            if mins[g] + 5 > 930 or i >= n - 1:  # no entries from 15:30
                i += 1
                continue
            # the pattern known at bar i's close: confirmed pivots (k bars old) inside the span
            hs = [p for p in ph if i - span <= p <= i - k]
            if len(hs) >= 2 and c[g] > 0:
                p2 = hs[-1]
                for p1 in reversed(hs[:-1]):
                    lvl = max(hh[p1], hh[p2])
                    if abs(hh[p1] - hh[p2]) > tol * lvl:
                        continue
                    if hh[p1:i].max() > lvl * (1 + tol) or c[a + p1:g].max() > lvl:  # broken before: no triangle
                        continue
                    before = [p for p in pl if p < p1 and p >= i - span]
                    first = before[-1] if before else None
                    lows = ([first] if first is not None else []) + [p for p in pl if p1 < p <= i - k]
                    if len(lows) < 2 or any(ll[x] >= ll[y] for x, y in zip(lows, lows[1:], strict=False)):
                        continue  # two or more rising lows
                    if not (c[g] > lvl and c[g - 1] <= lvl):  # the breakout: first close above
                        break
                    if vol_rule and v[a + lows[0]:g].sum() > 0:
                        mid = (lows[0] + i) // 2
                        if v[a + mid:g].mean() >= v[a + lows[0]:a + mid].mean():
                            break
                    height = lvl - ll[lows[0]]
                    px = o[g + 1] + TICK
                    stop = ll[lows[-1]] - TICK
                    tgt = lvl + height
                    per_c = (px - stop) * PV + 2 * FEE
                    if px <= stop or px >= tgt:
                        break
                    q = 10 if sizing == "10" else max(0, min(10, math.floor(500 / per_c)))
                    if q >= 1:
                        pos = (i + 1, px, stop, tgt, q)
                        i += 1  # the entry fills at the next bar's open; manage from there
                        g = a + i
                        # the fill bar itself: stop first, then target
                        e_i, px, stop, tgt, q = pos
                        if l[g] <= stop or h[g] >= tgt:
                            hit_stop = l[g] <= stop
                            exit_px = (min(o[g], stop) - TICK) if hit_stop else tgt
                            pnl = (exit_px - px) * q * PV - 2 * FEE * q
                            out.append({"time": t[g], "qty": q, "entry": px, "exit": exit_px,
                                        "why": "stop" if hit_stop else "target", "pnl": pnl,
                                        "risk": (px - stop) * q * PV, "day": day[g]})
                            pos = None
                    break
            i += 1
        if pos is not None:  # data ended inside the session
            e_i, px, stop, tgt, q = pos
            g = b - 1
            out.append({"time": t[a + e_i], "qty": q, "entry": px, "exit": c[g], "why": "end",
                        "pnl": (c[g] - px) * q * PV - 2 * FEE * q, "risk": (px - stop) * q * PV, "day": day[g]})
    return out


def stats(tr: list[dict], first: str | None) -> dict:
    f = pd.DataFrame(tr)
    if first and len(f):
        f = f[f.time >= pd.Timestamp(first, tz=NY)]
    if f.empty:
        return {"n": 0}
    p = f.pnl.to_numpy()
    e = np.r_[0, np.cumsum(p)]
    r = p / f.risk.to_numpy()
    days = f.groupby("day").pnl.sum()
    years = max(1e-9, (f.time.max() - f.time.min()).days / 365.25)
    return {"n": len(f), "per yr": round(len(f) / years), "win%": round(100 * (p > 0).mean(), 1),
            "pf": round(p[p > 0].sum() / max(1e-9, -p[p < 0].sum()), 2), "avg R": round(float(r.mean()), 3),
            "net": round(p.sum()), "net/yr": round(p.sum() / years), "dd": round((np.maximum.accumulate(e) - e).max()),
            "worst day": round(days.min()), "target%": round(100 * (f.why == "target").mean(), 1),
            "stop%": round(100 * (f.why == "stop").mean(), 1)}


def job(args):
    k, tol, span, vol_rule, sizing = args
    row = {"k": k, "tol%": tol * 100, "span": span, "volume rule": vol_rule, "size": sizing}
    for name, (bars, first) in D.items():
        for key, val in stats(trades(bars, k, tol, span, vol_rule, sizing), first).items():
            row[f"{name} {key}"] = val
    return row


def main() -> None:
    data, sep, dec, out = sys.argv[1:5]
    grid = list(itertools.product((2, 3), (0.0003, 0.0006, 0.001), (36, 72), (False, True), ("$500",)))
    grid += [(3, 0.0006, 72, False, "10")]
    with ProcessPoolExecutor(4, initializer=init, initargs=(data, sep, dec)) as ex:
        rows = list(ex.map(job, grid))
    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    pd.set_option("display.width", 400)
    cols = ["k", "tol%", "span", "volume rule", "size"]
    for name in ("mnq 8/24-10/16", "stand-in 2025-26", "NQ 2015-25", "index 2011-26"):
        print(f"\n{name}")
        sub = d[cols + [c for c in d.columns if c.startswith(name + " ")]]
        print(sub.rename(columns={c: c[len(name) + 1:] for c in sub.columns if c.startswith(name + " ")})
              .to_string(index=False))


if __name__ == "__main__":
    main()
