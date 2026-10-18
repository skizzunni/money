"""Frozen B on the user's native MNQ fills, against the 50K evaluation on CLOSED-trade equity (release/REPORT.md).

    python research/native_eval_closed.py verification/native_long

Input: B_L1 / B_L2 trades rebuilt from the NinjaTrader runs' own fills (6/29 to 10/16/2026, $1.90 a contract).
2 MNQ is the same trades at half the dollars (exact on the stand-in; not run natively). Evaluation: $3,000 target,
$2,000 trail below the highest CLOSED equity, 30 calendar days, one start per session whose 30 days end by 10/16.
Unrealized peaks and intraday troughs are NOT in the fills, so this understates the trailing risk: a real intraday
evaluation fails at least as often as the trail measured on closed equity says, unless the strategy's own target
close would have passed it first. It is a floor on the trail's bite, not the evaluation's result.
"""
import sys
from pathlib import Path

import pandas as pd

folder = Path(sys.argv[1])
for run in ("B_L1", "B_L2"):
    t = pd.read_csv(folder / f"{run}_trades_from_output.csv", parse_dates=["entry_time", "exit_time"])
    t = t.sort_values("exit_time")
    sessions = pd.DatetimeIndex(sorted(t.entry_time.dt.normalize().unique()))
    all_days = pd.bdate_range("2026-06-29", "2026-10-16")
    all_days = all_days[~all_days.isin(pd.to_datetime(["2026-07-03", "2026-09-07", "2026-08-31"]))]
    for size, f in (("4 MNQ / $200", 1.0), ("2 MNQ / $100", 0.5)):
        res = []
        for d0 in all_days:
            end = d0 + pd.Timedelta(days=30)
            if end > pd.Timestamp("2026-10-17"):
                break
            w = t[(t.entry_time >= d0) & (t.entry_time < end)]
            eq = peak = 0.0
            out, when = "expired", None
            for r in w.itertuples():
                eq += r.net * f
                peak = max(peak, eq)
                if eq >= 3000:
                    out, when = "pass", r.exit_time
                    break
                if eq <= peak - 2000:
                    out, when = "fail", r.exit_time
                    break
            res.append((d0.date(), out, (when - d0).days + 1 if when is not None else None))
        df = pd.DataFrame(res, columns=["start", "outcome", "days"])
        c = df.outcome.value_counts()
        print(f"{run} {size}: {len(df)} start dates {df.start.min()}..{df.start.max()} (overlapping): "
              f"pass {c.get('pass', 0)}, fail {c.get('fail', 0)}, expired {c.get('expired', 0)}; "
              f"median days to pass {df[df.outcome == 'pass'].days.median()}, "
              f"to fail {df[df.outcome == 'fail'].days.median()}")
