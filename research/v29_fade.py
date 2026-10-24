"""Fading the noise lines on calm days (docs/RESULTS.md, v2.9 study): on the days the strategy doesn't trade after a
calm stretch (the last 10 sessions' average range under 0.7 x the last 40's), a half-hour check that closes past a noise
line is faded: short above the upper line, long below the lower, at the next bar's open. The stop is stop_k noise
units past the entry, the target tgt_k noise units back toward the day's open; flat at 16:00. One trade at a time,
entries 10:00-15:00. Size: the contracts that risk about $500 (1-10 MNQ). A bar that reaches both counts as the stop.

    python research/v29_fade.py <out.csv> <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
SCAN_MINUTES=30 (environment): 30-minute bars.
"""
from __future__ import annotations

import itertools
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
TICK, PV, FEE = 0.25, 2.0, 0.62


def trades(bars: pd.DataFrame, bands: list, m: int, stop_k: float, tgt_k: float, calm_only: bool, calm_k: float,
           risk: float = 500.0) -> list[dict]:
    t = bars.index.tz_convert(NY)
    day = np.asarray(t.strftime("%Y-%m-%d"))
    mins = np.asarray(t.hour * 60 + t.minute)
    o, h, lo_, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(bars)] - 1
    rng = np.array([(h[a:b + 1].max() - lo_[a:b + 1].min()) / o[a] for a, b in zip(starts, ends, strict=True)])
    s10 = pd.Series(rng).rolling(10).mean().shift(1).to_numpy()
    s40 = pd.Series(rng).rolling(40).mean().shift(1).to_numpy()
    calm = {day[a]: (s10[k] < calm_k * s40[k]) if np.isfinite(s40[k]) else False for k, a in enumerate(starts)}
    end_of = {day[a]: b for a, b in zip(starts, ends, strict=True)}
    out = []
    busy_until = -1
    for i, up, lw in bands:
        if i <= busy_until or i + 1 >= len(bars) or day[i + 1] != day[i]:
            continue
        end = mins[i] + m
        if end > 900 or (calm_only and not calm[day[i]]):
            continue
        if c[i] > up:
            d = -1
        elif c[i] < lw:
            d = 1
        else:
            continue
        a = starts[np.searchsorted(starts, i, side="right") - 1]
        base = max(o[a], c[a - 1]) if d < 0 and a > 0 else (min(o[a], c[a - 1]) if a > 0 else o[a])
        sig = abs((up if d < 0 else lw) / base - 1)
        px = o[i + 1] + d * TICK
        stop = px * (1 - d * stop_k * sig)
        tgt = px * (1 + d * tgt_k * sig)
        per_c = abs(px - stop) * PV + 2 * FEE + 2 * TICK * PV
        q = max(0, min(10, math.floor(risk / per_c)))
        if q < 1:
            continue
        last = end_of[day[i]]
        exit_px = why = None
        for j in range(i + 1, last + 1):
            if (d > 0 and lo_[j] <= stop) or (d < 0 and h[j] >= stop):
                exit_px, why = (min(o[j], stop) if d > 0 else max(o[j], stop)) - d * TICK, "stop"
            elif (d > 0 and h[j] >= tgt) or (d < 0 and lo_[j] <= tgt):
                exit_px, why = tgt, "target"
            elif j == last:
                exit_px, why = c[j] - d * TICK, "16:00"
            if why:
                break
        pnl = (exit_px - px) * d * q * PV - 2 * FEE * q
        out.append({"time": t[i + 1], "day": day[i], "pnl": pnl, "why": why, "q": q})
        busy_until = j
    return out


def stats(tr: list[dict], first) -> dict:
    f = pd.DataFrame(tr)
    if first and len(f):
        f = f[f.time >= pd.Timestamp(first, tz=NY)]
    if f.empty:
        return {"n": 0}
    p = f.pnl.to_numpy()
    e = np.r_[0, np.cumsum(p)]
    return {"n": len(f), "win%": round(100 * (p > 0).mean(), 1),
            "pf": round(p[p > 0].sum() / max(1e-9, -p[p < 0].sum()), 2), "net": round(p.sum()),
            "dd": round((np.maximum.accumulate(e) - e).max()), "wday": round(f.groupby("day").pnl.sum().min())}


def main() -> None:
    out = sys.argv[1]
    m = int(os.environ.get("SCAN_MINUTES", "5"))
    S.init({}, *sys.argv[2:5])
    bands = {}
    for name, (bars, _, skip) in S.D.items():
        cfg = NoiseConfig(**{**S.V23, "calm_k": 0.0})
        if isinstance(skip, str):
            cfg.skip_dates, cfg.fed_dates = skip, ""
        bands[name] = run(bars, cfg, minutes=m).bands
    rows = []
    for stop_k, tgt_k, calm_only, calm_k in itertools.product((0.5, 1.0, 1.5), (0.5, 1.0, 1.5), (True, False), (0.7,)):
        r = {"stop_k": stop_k, "tgt_k": tgt_k, "calm only": calm_only}
        for name, (bars, first, _) in S.D.items():
            for k, v in stats(trades(bars, bands[name], m, stop_k, tgt_k, calm_only, calm_k), first).items():
                r[f"{name} {k}"] = v
        rows.append(r)
        print({k: v for k, v in r.items() if not k.startswith("win ")}, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
