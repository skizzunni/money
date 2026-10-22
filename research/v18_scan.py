"""The Pine noise strategy (v1.8: 10 MNQ, $350, lock 0.85, stop only tightens) over a grid of its own settings, on the
user's TradingView window and on the long histories, so a setting is kept only if it holds up beyond the window.

    python research/v18_scan.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <nq5m_scaled.pkl> <bars5_scaled.pkl> <out.csv>

Data: the user's MNQ bars (research/mnq_bars.py's traded contracts, 5-minute), trades opened 2026-07-27 to 10-16 (the
user's chart window, to the end of the data); NQ futures 5-minute 2015-2025 and the Nasdaq-100 index 5-minute
2011-2026, both scaled to today's price level. mnqbot/noise.py (the Pine script's reference, held to it by
tests/test_noise.py) at the script's costs ($0.62 a side, 1 tick) and at $0.95 / 2 ticks.

Grid: take-profit (noise units), the daily loser limit, the lock trigger and the lock offset.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
BASE = {"take_profit": 1.5, "max_losers": 4, "lock_at": 0.85, "lock_plus": 2.5}
GRID = {"take_profit": [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 0.0], "max_losers": [2, 3, 4, 0],
        "lock_at": [0.75, 0.85, 1.0], "lock_plus": [2.5, 5.0]}
DATA: dict = {}


def stats(trades: pd.DataFrame, first: str | None = None) -> dict:
    t = trades if first is None else trades[trades.entry_time.dt.strftime("%Y-%m-%d") >= first]
    if t.empty:
        return {"net": 0.0, "dd": 0.0, "losses": 0.0, "n": 0, "win": np.nan}
    eq = t.pnl.cumsum()
    return {"net": t.pnl.sum(), "dd": float((np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max()),
            "losses": t.pnl[t.pnl < 0].sum(), "n": len(t), "win": 100 * (t.pnl > 0).mean()}


def job(args):
    params, fee, slip = args
    cfg_kw = dict(qty=10, max_loss_per_trade=350.0, tighten_only=True, commission_per_side=fee, slippage_ticks=slip,
                  **params)
    out = {**params, "costs": f"{fee}/{slip}"}
    for name, (bars, first) in DATA.items():
        cfg = NoiseConfig(**cfg_kw)
        if name != "mnq":
            cfg.skip_dates, cfg.fed_dates = "", ""
        tf = run(bars, cfg, minutes=5).trades_frame()
        s = stats(tf, first)
        for k, v in s.items():
            out[f"{name} {k}"] = v
    return out


def init(paths):
    sep, dec, nq, idx = paths
    series, _ = M.traded_series(M.load(sep), M.load(dec))
    one = K.rth(series)
    DATA["mnq"] = (resample(one.assign(volume=one.get("volume", 0)), "5min"), "2026-07-27")
    for name, p, lo, hi in (("nq", nq, "2015-01-01", "2025-07-01"), ("index", idx, "2011-01-01", "2026-10-01")):
        b = pd.read_pickle(p)
        b = b[(b.index >= pd.Timestamp(lo, tz=NY)) & (b.index < pd.Timestamp(hi, tz=NY))]
        t = b.index.tz_convert(NY)
        tm = t.hour * 60 + t.minute
        b = b[(tm >= 570) & (tm < 960)]
        if "volume" not in b:
            b = b.assign(volume=0.0)
        DATA[name] = (b[["open", "high", "low", "close", "volume"]], None)


def main() -> None:
    paths, out = sys.argv[1:5], Path(sys.argv[5])
    grid = [dict(zip(GRID, v, strict=True)) for v in itertools.product(*GRID.values())]
    jobs = [(g, 0.62, 1) for g in grid] + [(BASE, 0.95, 2)]
    with ProcessPoolExecutor(max_workers=4, initializer=init, initargs=(paths,)) as ex:
        rows = list(ex.map(job, jobs, chunksize=4))
    pd.DataFrame(rows).to_csv(out, index=False)
    print(len(rows), "rows ->", out)


if __name__ == "__main__":
    main()
