"""E50R, registered in docs/CANDIDATE_E50.md: v3.8 with each trade sized to its own stop at a fixed $260 risk (most
contracts 3, 5 or 10; take-profit 2.0 or none), replayed as 50K evaluations like research/e50_eval.py.

    SCAN_MINUTES=5 python research/e50r_eval.py <data dir> <MNQ_09-26> <MNQ_12-26> <out.csv>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import e50_eval as E  # noqa: E402
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"


def main() -> None:
    S.init({}, *sys.argv[1:4])
    rows = []
    variants = [(0, 2.0)] + [(mq, tp) for mq in (3, 5, 10) for tp in (2.0, 0.0)]  # (0, 2.0): v3.8 itself
    for mq, tp in variants:
        for name, (bars, first, skip) in S.D.items():
            kw = {**E.config(1, tp, 260.0, 0), "daily_loss_limit": 900.0}
            if mq:
                kw.update({"risk_per_trade": 260.0, "risk_max_qty": mq})
            cfg = NoiseConfig(**kw)
            if isinstance(skip, str):
                cfg.skip_dates, cfg.fed_dates = skip, ""
            tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
            if first:
                tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
            p = tf.pnl.to_numpy()
            e = np.r_[0.0, np.cumsum(p)]
            days = sorted(set(bars.index.tz_convert(NY).strftime("%Y-%m-%d")))
            if first:
                days = [x for x in days if x >= first]
            years = max(0.1, (tf.exit_time.max() - tf.entry_time.min()).days / 365.25)
            r = {"bars": S.MIN[0], "max qty": mq or "v3.8", "take_profit": tp, "set": name, "trades": len(p),
                 "avg qty": round(float(tf.qty.mean()), 2), "net $": round(float(p.sum())),
                 "net $/yr": round(float(p.sum()) / years), "win %": round(100 * float((p > 0).mean()), 1),
                 "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3), "largest loss $": round(float(p.min()), 2),
                 "closed dd $": round(float((np.maximum.accumulate(e) - e).max())),
                 "worst day $": round(float(tf.groupby(tf.exit_time.dt.date).pnl.sum().min())),
                 **E.streaks(p), **E.evals(tf, days)}
            rows.append(r)
            print(r, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[4], index=False)


if __name__ == "__main__":
    main()
