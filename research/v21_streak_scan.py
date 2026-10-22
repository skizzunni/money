"""The v2.1 study (docs/RESULTS.md): v2.0 with the daily loser limit off, and the research-only losing-streak rules of
mnqbot/noise.py, on the user's TradingView window (trades from 8/24/2026) and NQ 2015-2025 / index 2011-2026.

    python research/v21_streak_scan.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <nq5m_scaled.pkl> <bars5_scaled.pkl> \
        <out.csv>
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v18_scan as V  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

V2 = {"qty": 10, "max_loss_per_trade": 500.0, "tighten_only": True, "lock_at": 0.75, "take_profit": 2.0}
VARIANTS = ([{"max_losers": 4}, {"max_losers": 0}]
            + [{"max_losers": 0, "streak_k": k, "streak_skip": s} for k in (2, 3) for s in (1, 2)]
            + [{"max_losers": 0, "side_cooldown": c} for c in (1, 2)]
            + [{"max_losers": 0, "side_margin": m} for m in (0.25, 0.5)]
            + [{"max_losers": 4, "streak_k": k, "streak_skip": 1} for k in (2, 3)])


def streak(pnl) -> int:
    longest = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        longest = max(longest, cur)
    return longest


def job(kw: dict) -> dict:
    out = {"rule": ", ".join(f"{k}={v}" for k, v in kw.items())}
    for name, (bars, _) in V.DATA.items():
        cfg = NoiseConfig(**V2, **kw)
        if name != "mnq":
            cfg.skip_dates, cfg.fed_dates = "", ""
        tf = run(bars, cfg, minutes=5).trades_frame()
        t = tf[tf.entry_time.dt.strftime("%Y-%m-%d") >= ("2026-08-24" if name == "mnq" else "0")]
        e = np.r_[0, t.pnl.cumsum().to_numpy()]
        out.update({f"{name} net": round(t.pnl.sum()), f"{name} dd": round((np.maximum.accumulate(e) - e).max()),
                    f"{name} losers": int((t.pnl < 0).sum()), f"{name} n": len(t),
                    f"{name} streak": streak(t.pnl.to_numpy())})
        if name != "mnq":
            out[f"{name} 23+"] = round(t[t.entry_time.dt.year >= 2023].pnl.sum())
            yearly = [streak(g.to_numpy()) for _, g in t.groupby(t.entry_time.dt.year).pnl]
            out[f"{name} p90 streak/yr"] = int(np.percentile(yearly, 90))
    return out


def main() -> None:
    paths, out = sys.argv[1:5], Path(sys.argv[5])
    with ProcessPoolExecutor(4, initializer=V.init, initargs=(paths,)) as ex:
        rows = list(ex.map(job, VARIANTS))
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
