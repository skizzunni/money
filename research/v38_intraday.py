"""Two more strategy families on raw 5-minute bars (docs/RESULTS.md, after v3.6), NQ futures 2015-2025 (roll weeks
skipped), the Nasdaq-100 index 2011-2026 and the 2025-2026 stand-in, 1 MNQ, $0.62 a side, a tick of slippage on
market and stop fills:

- "rsi2": a pullback in an intraday trend. With the close above its n-bar EMA, a 2-bar RSI under lo buys at the next
  bar's open (shorts mirrored below the EMA above 100 - lo, when "both"); out when the RSI passes the exit level, at a
  stop k x the 14-bar average range, or at 15:55. Entries 09:45-15:00, one position at a time.
- "lasthalf": the last half hour follows the first (Gao, Han, Li and Zhou, 2018). The return from the previous close to
  10:00 picks the side; in at the 15:30 open, out at 15:55's close.

    python research/v38_intraday.py <data dir> <out.csv>
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v38_gap as G  # noqa: E402

TICK, PV, FEE = 0.25, 2.0, 0.62


def rsi2(c: np.ndarray) -> np.ndarray:
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=0.5, adjust=False).mean().to_numpy()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=0.5, adjust=False).mean().to_numpy()
    return 100 - 100 / (1 + up / np.maximum(dn, 1e-12))


def run_rsi2(sess: list[tuple], ema_n: int, lo: float, ex: float, k: float, side: str) -> pd.DataFrame:
    mi = np.concatenate([s[2] for s in sess])
    o, h, low, c = (np.concatenate([s[i] for s in sess]) for i in (3, 4, 5, 6))
    day = np.concatenate([[s[0]] * len(s[2]) for s in sess])
    ema = pd.Series(c).ewm(span=ema_n, adjust=False).mean().to_numpy()
    r = rsi2(c)
    tr = np.maximum(h - low, np.abs(h - np.r_[c[0], c[:-1]]))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    rows, pos, i = [], 0, 200
    n = len(c)
    while i < n - 1:
        if pos == 0:
            sig = 0
            if 585 <= mi[i] + 5 <= 900 and np.isfinite(atr[i]) and day[i + 1] == day[i]:
                if c[i] > ema[i] and r[i] < lo:
                    sig = 1
                elif side == "both" and c[i] < ema[i] and r[i] > 100 - lo:
                    sig = -1
            if sig:
                pos, entry, d0 = sig, o[i + 1] + sig * TICK, day[i]
                stop = entry - sig * k * atr[i]
                i += 1
                continue
        else:
            out = None
            if (pos > 0 and low[i] <= stop) or (pos < 0 and h[i] >= stop):
                out = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif day[i] != d0 or mi[i] >= 955:
                out = c[i] - pos * TICK
            elif (pos > 0 and r[i] > ex) or (pos < 0 and r[i] < 100 - ex):
                out = o[i + 1] - pos * TICK if day[i + 1] == day[i] else c[i] - pos * TICK
            if out is not None:
                pnl = (out - entry) * pos * PV - 2 * FEE
                rows.append({"day": d0, "pnl": pnl, "r": pnl / (abs(entry - stop) * PV + 2 * FEE)})
                pos = 0
        i += 1
    return pd.DataFrame(rows)


def run_lasthalf(sess: list[tuple], min_move: float) -> pd.DataFrame:
    rows = []
    for day, pc, mi, o, _h, _low, c in sess:
        k10 = np.flatnonzero(mi == 595)  # the 09:55 bar closes at 10:00
        k1530 = np.flatnonzero(mi == 930)
        if not len(k10) or not len(k1530):
            continue
        ret = c[k10[0]] / pc - 1
        if abs(ret) < min_move:
            continue
        d = 1 if ret > 0 else -1
        entry = o[k1530[0]] + d * TICK
        out = c[-1] - d * TICK
        pnl = (out - entry) * d * PV - 2 * FEE
        rows.append({"day": day, "pnl": pnl, "r": pnl / (abs(entry) * 0.002 * PV)})
    return pd.DataFrame(rows)


def main() -> None:
    data, out = Path(sys.argv[1]), sys.argv[2]
    import glob

    from nsx_study import load_histdata
    nq = pd.read_pickle(data / "nq1m_all.pkl")
    files = sorted(glob.glob(str(data / "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv")))
    ix = pd.concat([load_histdata(f) for f in files]).sort_index()
    ix = ix[~ix.index.duplicated()]
    sets = {"nq": G.sessions(G.rth5(nq), True), "index": G.sessions(G.rth5(ix), False),
            "proxy": [s for s in G.sessions(pd.read_pickle(data / "proxy_5m.pkl"), False) if s[0] >= "2025-01-02"]}
    splits = {"nq": ("2020", "nq15-19", "nq20-25"), "index": ("2018", "ix11-17", "ix18-26")}
    rows = []

    def add(r: dict, name: str, f: pd.DataFrame) -> None:
        if name in splits:
            cut, a, b = splits[name]
            for tag, part in ((a, f[f.day < cut] if len(f) else f), (b, f[f.day >= cut] if len(f) else f)):
                r.update({f"{tag} {k}": v for k, v in G.stats(part).items()})
        else:
            r.update({f"proxy {k}": v for k, v in G.stats(f).items()})

    grid = itertools.product((100, 300), (5, 10, 20), (50, 70), (1.5, 3.0, 6.0), ("buy", "both"))
    for ema_n, lo, ex, k, side in grid:
        r = {"family": "rsi2", "ema": ema_n, "lo": lo, "exit": ex, "k": k, "side": side}
        for name, s in sets.items():
            add(r, name, run_rsi2(s, ema_n, lo, ex, k, side))
        rows.append(r)
        print(r["family"], ema_n, lo, ex, k, side, r.get("nq15-19 pf"), r.get("ix11-17 pf"), r.get("proxy pf"),
              flush=True)
    for mm in (0.0, 0.002, 0.005):
        r = {"family": "lasthalf", "min_move": mm}
        for name, s in sets.items():
            add(r, name, run_lasthalf(s, mm))
        rows.append(r)
        print(r, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
