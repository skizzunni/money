"""Walk-forward check of v2.5's choices (docs/RESULTS.md, v2.5): each year, the settings with the best net per drawdown
over all earlier years (from a small grid: max loss $500 / $1,000 / $1,500, lock 0.5 / 0.75 max losses, calm-stretch
rule off / on) trade that year. NQ futures 2015-2025 and the Nasdaq-100 index 2011-2026, 5-minute bars, 10 MNQ.

    python research/v25_walk_forward.py <nq5m_scaled.pkl> <bars5_scaled.pkl> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v18_scan as V  # noqa: E402
from v24_scan import V23  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

GRID = [{"max_loss_per_trade": ml, "lock_at": lk, "max_losers": 3 if ml > 500 else 4,
         **({"calm_k": 0.7, "calm_short": 10, "calm_long": 40} if calm else {})}
        for ml, lk, calm in itertools.product((500.0, 1000.0, 1500.0), (0.5, 0.75), (False, True))]


def job(args):
    name, k = args
    cfg = NoiseConfig(**{**V23, **GRID[k]})
    cfg.skip_dates, cfg.fed_dates = "", ""
    tf = run(V.DATA[name][0], cfg, minutes=5).trades_frame()
    return name, k, tf[["entry_time", "pnl"]]


def dd(p: np.ndarray) -> float:
    e = np.r_[0, np.cumsum(p)]
    return float((np.maximum.accumulate(e) - e).max())


def main() -> None:
    nq, idx, sep, dec = sys.argv[1:5]
    with ProcessPoolExecutor(4, initializer=V.init, initargs=([sep, dec, nq, idx],)) as ex:
        res = list(ex.map(job, [(n, k) for n in ("nq", "index") for k in range(len(GRID))]))
    for name in ("nq", "index"):
        runs = {k: tf for n, k, tf in res if n == name}
        years = sorted(runs[0].entry_time.dt.year.unique())
        oos, picks = [], []
        for y in years[3:]:  # three years of history before the first pick
            def score(k, y=y, runs=runs):
                t = runs[k][runs[k].entry_time.dt.year < y].pnl.to_numpy()
                return t.sum() / max(dd(t), 1.0)
            best = max(range(len(GRID)), key=score)
            picks.append((y, best))
            oos.append(runs[best][runs[best].entry_time.dt.year == y])
        o = pd.concat(oos).pnl.to_numpy()
        v25 = len(GRID) - 1 - 2  # $1,500, lock 0.5, calm on
        fixed = runs[v25][runs[v25].entry_time.dt.year >= years[3]].pnl.to_numpy()
        base = runs[2][runs[2].entry_time.dt.year >= years[3]].pnl.to_numpy()  # $500, lock 0.75: v2.3's
        print(f"{name}: walk-forward from {years[3]}: net {o.sum():,.0f}, drawdown {dd(o):,.0f}; "
              f"v2.5 fixed: net {fixed.sum():,.0f}, drawdown {dd(fixed):,.0f}; v2.3's risk: net {base.sum():,.0f}, "
              f"drawdown {dd(base):,.0f}")
        print("   picks:", ", ".join(f"{y}: {GRID[k]['max_loss_per_trade']:.0f}/{GRID[k]['lock_at']}/"
                                     f"{'calm' if 'calm_k' in GRID[k] else '-'}" for y, k in picks))


if __name__ == "__main__":
    main()
