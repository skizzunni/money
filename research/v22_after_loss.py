"""The v2.2 study (docs/RESULTS.md): v2.0 with the trade after a losing trade handled differently (the research-only
after_loss_* options of mnqbot/noise.py), on the user's TradingView window (trades from 8/24/2026) and NQ 2015-2025 /
index 2011-2026. Besides net and drawdown: the longest losing streak and the back-to-back rate (the share of losing
trades followed by another loser).

    python research/v22_after_loss.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <nq5m_scaled.pkl> <bars5_scaled.pkl> \
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
from v21_streak_scan import V2, streak  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

VARIANTS = ([{}, {"max_losers": 0}]
            + [{"after_loss_lock": k} for k in (0.25, 0.4, 0.5)]
            + [{"after_loss_qty_div": k} for k in (1.5, 2.0)]
            + [{"after_loss_hourly": True}]
            + [{"after_loss_lock": 0.4, "after_loss_qty_div": 2.0}, {"after_loss_lock": 0.5, "after_loss_hourly": True},
               {"after_loss_lock": 0.4, "max_losers": 0}, {"after_loss_qty_div": 2.0, "max_losers": 0}]
            + [{"after_loss_ml_mult": m} for m in (1.25, 1.5, 2.0)]
            + [{"after_loss_ml_mult": 1.5, "after_loss_qty_div": 1.25}, {"after_loss_ml_mult": 1.5, "max_losers": 0},
               {"after_loss_ml_mult": 1.25, "after_loss_qty_div": 1.25}]
            + [{"after_loss_ml_mult": m, "after_loss_qty_div": q} for m in (1.1, 1.25, 1.4) for q in (1.1, 1.25, 1.5)
               if (m, q) != (1.25, 1.25)])
T1 = {"after_loss_qty_div": 10 / 9, "after_loss_ml_mult": 1.4}  # v2.1
VARIANTS += ([T1, {**T1, "after_loss_same_side": True}]
             + [{**T1, "after_loss2_qty_div": q, "after_loss2_ml_mult": m}
                for q, m in ((10 / 7, 1.0), (2.0, 1.0), (10 / 9, 1.0), (1.0, 1.0), (10 / 9, 1.8), (10 / 8, 1.25))])
VARIANTS += [{**T1, "tp_keep": k, "runner_lock": rl, "tp2": t2} for k in (0.3, 0.5) for rl in (0.0, 0.5)
             for t2 in (0.0, 4.0)]


def back_to_back(pnl: np.ndarray) -> float:
    lost = pnl < 0
    return 100 * float((lost[1:] & lost[:-1]).sum()) / max(1, int(lost[:-1].sum()))


def job(kw: dict) -> dict:
    out = {"rule": ", ".join(f"{k}={v}" for k, v in kw.items()) or "v2.0"}
    for name, (bars, _) in V.DATA.items():
        cfg = NoiseConfig(**{"max_losers": 4, **V2, **kw})
        if name != "mnq":
            cfg.skip_dates, cfg.fed_dates = "", ""
        tf = run(bars, cfg, minutes=5).trades_frame()
        t = tf[tf.entry_time.dt.strftime("%Y-%m-%d") >= ("2026-08-24" if name == "mnq" else "0")]
        p = t.pnl.to_numpy()
        e = np.r_[0, np.cumsum(p)]
        out.update({f"{name} net": round(p.sum()), f"{name} dd": round((np.maximum.accumulate(e) - e).max()),
                    f"{name} losers": int((p < 0).sum()), f"{name} n": len(p), f"{name} streak": streak(p),
                    f"{name} b2b %": round(back_to_back(p), 1)})
        if name != "mnq":
            out[f"{name} 23+"] = round(t[t.entry_time.dt.year >= 2023].pnl.sum())
    return out


def main() -> None:
    paths, out = sys.argv[1:5], Path(sys.argv[5])
    variants = VARIANTS if len(sys.argv) <= 6 else [VARIANTS[int(k)] for k in sys.argv[6].split(",")]  # by number
    with ProcessPoolExecutor(4, initializer=V.init, initargs=(paths,)) as ex:
        rows = list(ex.map(job, variants))
    pd.DataFrame(rows).to_csv(out, index=False)
    pd.set_option("display.width", 300)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
