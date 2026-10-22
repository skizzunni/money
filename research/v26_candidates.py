"""The v2.6 candidates (docs/RESULTS.md, v2.6) on 30- and 5-minute bars: the stand-in from 2025 and its last part (the
user's MNQ bars, 7/2026 on), and the cleaned histories with their two halves and losing years.

    python research/v26_candidates.py <data dir> <dir with the user's MNQ_09-26 / MNQ_12-26 files (upload names)>
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as W  # noqa: E402
from v24_scan import V23, V25  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

S, U = sys.argv[1], sys.argv[2]
C = {"calm_k": 0.7, "calm_short": 10, "calm_long": 40}
CANDS = {"v2.3": V23, "v2.3+calm": {**V23, **C},
         "A 750/1500/1.0": {**V23, **C, "max_loss_per_trade": 750.0, "after_loss_ml_mult": 2.0, "lock_at": 1.0},
         "B 1000/1500/1.0": {**V23, **C, "max_loss_per_trade": 1000.0, "after_loss_ml_mult": 1.5, "lock_at": 1.0},
         "v2.5": V25}
NY = "America/New_York"


def dd(p):
    e = np.r_[0, np.cumsum(p)]
    return (np.maximum.accumulate(e) - e).max()



for m in (30, 5):
    os.environ["SCAN_MINUTES"] = str(m)
    W.D.clear()
    W.init({}, S, f"{U}/3731e345-MNQ_09-26.Last.txt", f"{U}/a6aa0530-MNQ_12-26.Last.txt")
    for lab, kw in CANDS.items():
        row = []
        for name, (bars, _first, skip) in W.D.items():
            cfg = NoiseConfig(**kw)
            if isinstance(skip, str):
                cfg.skip_dates, cfg.fed_dates = skip, ""
            tf = run(bars, cfg, minutes=m).trades_frame()
            if name == "proxy":
                a = tf[tf.entry_time >= pd.Timestamp("2025-01-02", tz=NY)]
                mq = tf[tf.entry_time >= pd.Timestamp("2026-07-01", tz=NY)]
                row.append(f"proxy {a.pnl.sum() / 1e3:.1f}k/{dd(a.pnl.to_numpy()) / 1e3:.1f}k  "
                           f"mnqJul-Oct {mq.pnl.sum() / 1e3:.1f}k/{dd(mq.pnl.to_numpy()) / 1e3:.1f}k")
            elif name in ("nq", "index"):
                y = tf.groupby(tf.entry_time.dt.year).pnl.sum()
                h = len(y) // 2
                row.append(f"{name} {tf.pnl.sum() / 1e3:.0f}k/{dd(tf.pnl.to_numpy()) / 1e3:.1f}k halves "
                           f"{y.iloc[:h].sum() / 1e3:.0f}k|{y.iloc[h:].sum() / 1e3:.0f}k neg yrs {(y < 0).sum()}")
        print(m, f"{lab:16s}", " | ".join(row), flush=True)
