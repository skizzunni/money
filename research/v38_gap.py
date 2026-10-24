"""The opening-gap fade (docs/RESULTS.md, after v3.6): when the 09:30 open is away from the previous 16:00 close by a
gap between g_min and g_max (a share of the price), trade toward the close at the open (a tick of slippage), target
the previous close (a limit, filled once price trades a tick through it), stop k x the gap past the entry, flat at
the time exit. Raw prices only (the scaled histories have no real gaps): NQ futures 2015-2025 (1-minute, roll weeks
skipped), the Nasdaq-100 index 2011-2026 (HistData, 1-minute) and the 2025-2026 stand-in (5-minute). 1 MNQ, $0.62 a
side; a bar that reaches both the stop and the target counts as the stop.

    python research/v38_gap.py <data dir> <out.csv>
"""
from __future__ import annotations

import glob
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nsx_study import load_histdata  # noqa: E402

NY = "America/New_York"
TICK, PV, FEE = 0.25, 2.0, 0.62


def rth5(df: pd.DataFrame) -> pd.DataFrame:
    t = df.index.tz_convert(NY)
    m = t.hour * 60 + t.minute
    df = df[(m >= 570) & (m < 960)]
    return df.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def sessions(bars: pd.DataFrame, skip_rolls: bool) -> list[tuple]:
    """(day, previous close, the day's bars as arrays (minute, open, high, low, close))."""
    t = bars.index.tz_convert(NY)
    day = np.asarray(t.strftime("%Y-%m-%d"))
    mins = np.asarray(t.hour * 60 + t.minute)
    o, h, lo, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(bars)]
    out = []
    prev_close = None
    for a, b in zip(starts, ends, strict=True):
        full = mins[a] == 570 and mins[b - 1] == 955
        d = pd.Timestamp(day[a])
        roll = d.month in (3, 6, 9, 12) and 7 <= d.day <= 21
        if full and prev_close is not None and not (skip_rolls and roll):
            out.append((day[a], prev_close, mins[a:b], o[a:b], h[a:b], lo[a:b], c[a:b]))
        prev_close = c[b - 1] if mins[b - 1] == 955 else None
    return out


def trades(sess: list[tuple], g_min: float, g_max: float, k: float, t_exit: int, side: str) -> pd.DataFrame:
    rows = []
    for day, pc, mi, o, h, lo, c in sess:
        gap = o[0] / pc - 1
        if not (g_min <= abs(gap) <= g_max):
            continue
        d = -1 if gap > 0 else 1
        if side == "buy" and d < 0:
            continue
        entry = o[0] + d * TICK
        tgt = pc
        stop = entry - d * k * abs(gap) * o[0]
        risk = abs(entry - stop) * PV + 2 * FEE
        exit_px = None
        for j in range(len(mi)):
            hit_stop = lo[j] <= stop if d > 0 else h[j] >= stop
            hit_tgt = h[j] >= tgt + TICK if d > 0 else lo[j] <= tgt - TICK
            if hit_stop:
                exit_px = (min(o[j], stop) if d > 0 else max(o[j], stop)) - d * TICK
                break
            if hit_tgt:
                exit_px = tgt
                break
            if mi[j] + 5 >= t_exit:
                exit_px = c[j] - d * TICK
                break
        if exit_px is None:
            exit_px = c[-1] - d * TICK
        pnl = (exit_px - entry) * d * PV - 2 * FEE
        rows.append({"day": day, "d": d, "gap": gap, "pnl": pnl, "r": pnl / risk})
    return pd.DataFrame(rows)


def stats(f: pd.DataFrame) -> dict:
    if f.empty:
        return {"n": 0, "win": 0.0, "pf": 0.0, "avgR": 0.0, "net": 0}
    p = f.pnl.to_numpy()
    return {"n": len(p), "win": round(100 * (p > 0).mean(), 1),
            "pf": round(p[p > 0].sum() / max(1e-9, -p[p < 0].sum()), 2), "avgR": round(f.r.mean(), 3),
            "net": round(p.sum())}


def main() -> None:
    data, out = Path(sys.argv[1]), sys.argv[2]
    nq = pd.read_pickle(data / "nq1m_all.pkl")
    files = sorted(glob.glob(str(data / "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv")))
    ix = pd.concat([load_histdata(f) for f in files]).sort_index()
    ix = ix[~ix.index.duplicated()]
    proxy = pd.read_pickle(data / "proxy_5m.pkl")
    sets = {"nq": sessions(rth5(nq), True), "index": sessions(rth5(ix), False),
            "proxy": [s for s in sessions(proxy, False) if s[0] >= "2025-01-02"]}
    for name, s in sets.items():
        print(name, len(s), s[0][0], s[-1][0], flush=True)
    rows = []
    grid = itertools.product((0.001, 0.002, 0.003), (0.005, 0.008, 0.012), (0.5, 1.0, 1.5, 2.0), (630, 720, 960),
                             ("both", "buy"))
    for g_min, g_max, k, t_exit, side in grid:
        r = {"g_min": g_min, "g_max": g_max, "k": k, "t_exit": t_exit, "side": side}
        for name, s in sets.items():
            f = trades(s, g_min, g_max, k, t_exit, side)
            if name == "nq":
                early, late = f[f.day < "2020"], f[f.day >= "2020"]
                for tag, part in (("nq15-19", early), ("nq20-25", late)):
                    r.update({f"{tag} {k2}": v for k2, v in stats(part).items()})
            elif name == "index":
                early, late = f[f.day < "2018"], f[f.day >= "2018"]
                for tag, part in (("ix11-17", early), ("ix18-26", late)):
                    r.update({f"{tag} {k2}": v for k2, v in stats(part).items()})
            else:
                r.update({f"proxy {k2}": v for k2, v in stats(f).items()})
        rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    pd.set_option("display.width", 400)
    good = d[(d["nq15-19 pf"] > 1.2) & (d["ix11-17 pf"] > 1.2)]
    print(len(good), "configs with PF > 1.2 on both early periods")
    cols = ["g_min", "g_max", "k", "t_exit", "side"] + [f"{p} {s}" for p in ("nq15-19", "nq20-25", "ix11-17",
                                                                            "ix18-26", "proxy")
                                                         for s in ("n", "win", "pf")]
    print(good.sort_values("nq15-19 pf", ascending=False)[cols].head(25).to_string(index=False))


if __name__ == "__main__":
    main()
