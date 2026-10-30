"""Fresh-account replays of v3.6 under the user's limits ($2,000 end-of-day trailing drawdown that stops at the starting
balance, $1,000 daily loss limit; docs/V37_MAX.md). A new account starts at 1 MNQ at each quarter start on the NQ
2015-2025 and Nasdaq-100 index 2011-2026 histories, and runs 21 months, the length of the user's Jan 2025 – Oct 2026
window. Descriptive only: nothing is chosen from it.

    SCAN_MINUTES=30 python research/v37_windows.py <data dir> <MNQ_09-26> <MNQ_12-26> <out.csv>
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import t1_eval as T  # noqa: E402
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
CFG = {**S.V23, **T.REFERENCE, "daily_loss_limit": 1000.0, "trail_dd": 2000.0}


def one(job: tuple) -> dict:
    name, start = job
    bars, _first, skip = S.D[name]
    s = pd.Timestamp(start, tz=NY)
    e = s + pd.DateOffset(months=21)
    b = bars[(bars.index >= s - pd.Timedelta(days=150)) & (bars.index < e)]
    cfg = NoiseConfig(**CFG)
    cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    tf = run(b, cfg, minutes=S.MIN[0]).trades_frame()
    tf = tf[tf.entry_time >= s]
    p = tf.pnl.to_numpy()
    eq = np.r_[0.0, np.cumsum(p)]
    tr = S.trail_stats(name, tf)
    return {"set": name, "start": start, "trades": len(p), "net": round(float(p.sum())),
            "closed dd": round(float((np.maximum.accumulate(eq) - eq).max())), "eod dd": tr[f"{name} eoddd"],
            "floor touches": tr[f"{name} tb0"], "win %": round(100 * float((p > 0).mean()), 1) if len(p) else 0.0,
            "pf": round(float(p[p > 0].sum() / max(1e-9, -p[p < 0].sum())), 3) if len(p) else 0.0,
            "worst day": round(float(tf.groupby(tf.exit_time.dt.date).pnl.sum().min())) if len(p) else 0,
            "max qty": int(tf.qty.max()) if len(p) else 0}


def main() -> None:
    os.environ.setdefault("TRAIL_DD", "2000")
    S.init({}, *sys.argv[1:4])
    jobs = []
    for name, last in (("nq", "2023-10-01"), ("index", "2024-12-01")):
        first = S.D[name][0].index[0].tz_convert(NY) + pd.Timedelta(days=200)
        for q in pd.date_range(first.strftime("%Y-%m-01"), last, freq="QS"):
            jobs.append((name, q.strftime("%Y-%m-%d")))
    with ProcessPoolExecutor(4, initializer=S.init, initargs=({}, *sys.argv[1:4])) as ex:
        rows = list(ex.map(one, jobs))
    d = pd.DataFrame(rows)
    d.to_csv(sys.argv[4], index=False)
    for name, g in d.groupby("set"):
        q = g.net.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round().astype(int).tolist()
        print(name, "windows", len(g), "net p10/p25/p50/p75/p90", q, "losing windows", int((g.net < 0).sum()),
              "floor touched", int((g["floor touches"] > 0).sum()), "median closed dd", int(g["closed dd"].median()),
              "max closed dd", int(g["closed dd"].max()), "median win %", g["win %"].median(),
              "median pf", g.pf.median(), flush=True)


if __name__ == "__main__":
    main()
