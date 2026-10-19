"""Control B in the 50K intraday-trail evaluation on MNQ bars - the stand-in simulator on the user's MNQ data.

    python research/mnq_eval.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll>

Bars: the contracts actually traded (research/mnq_bars.traded_series: 09-26 through the 9/10 roll session, then 12-26,
09-26 back-adjusted by the roll-day close difference). The stand-in reproduces NinjaTrader on these bars to the cent
(research/mnq_reconcile.py). Strategy: frozen B (breakout off), 4 MNQ / $200 and 2 MNQ / $100, $0.95 a side, slippage
1 and 2 ticks, the strategy's own skip dates only. Warm-up: the first 14 full sessions; evaluations start at every
session after it (overlapping) and back to back, with research/eval_sim.py's rules (unrealized peaks, $2,000 trail,
$3,000 target with the strategy's own close at $3,025, 30 calendar days, both orders of each bar's high and low).
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import mnq_bars as M  # noqa: E402

sep, dec, dll = M.load(sys.argv[1]), M.load(sys.argv[2]), sys.argv[3]
series, diff = M.traded_series(sep, dec)
bars = K.rth(series)
m = bars.index
csv = Path(tempfile.mkdtemp()) / "b.csv"
K.write_bars(bars, csv)
o, h, lo = (bars[c].to_numpy(float) for c in ("open", "high", "low"))
bar_day = m.normalize().tz_localize(None)
sessions = pd.DatetimeIndex(sorted(set(bar_day)))
day_of = np.searchsorted(sessions, bar_day)
cov = M.coverage(series)
skip = set(pd.to_datetime(K.DEFAULT_SKIP.split(",")))
full = [pd.Timestamp(r.session) for r in cov.itertuples() if r.minutes == 390 and pd.Timestamp(r.session) not in skip]
first_ok = int(np.searchsorted(sessions, full[13])) + 1
start_bar = int(np.searchsorted(bar_day, sessions[first_ok]))
print(f"traded series: 09-26 to the 9/10 session, 12-26 from 9/11 (09-26 shifted by {diff:+.2f} points); "
      f"{len(sessions)} sessions; warm-up {sessions[0].date()} to {full[13].date()}; first evaluation "
      f"{sessions[first_ok].date()}; last session {sessions[-1].date()}")
rows, per_start = [], {}
for size, props in E.SIZES.items():
    for slip in (1, 2):
        tr = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=E.FEE, **props)
        cont = tr[tr.eb >= start_bar].sort_values("xb")
        eq = cont.pnl.cumsum()
        trs = E.marks(tr, o, h, lo, slip)
        w = E.run_windows(trs, sessions, first_ok, day_of, bar_day)
        wb = E.run_windows(trs, sessions, first_ok, day_of, bar_day, chain=True)
        per_start[(size, slip)] = w.set_index("start")
        wins, losses = cont.pnl[cont.pnl > 0], cont.pnl[cont.pnl < 0]
        full_w, late = w[w["fully observed"]], w[~w["fully observed"]]
        sf = E.summarize(full_w, "")

        def count(df, o):
            return int((df.outcome == o).sum())
        rows.append({"size": size, "slippage": slip, "trades": len(cont), "net $": cont.pnl.sum(),
                     "profit factor": wins.sum() / -losses.sum(),
                     "closed DD": float((eq.cummax().clip(lower=0) - eq).max()),
                     "full starts": f"{full_w.start.min()}..{full_w.start.max()} ({len(full_w)})",
                     "full: pass": sf["pass"], "full: fail": sf["fail"], "full: expired": sf["expired"],
                     "full: outcome depends on path": sf["outcome depends on path"],
                     "full: only the day depends": sf["only the day depends on path"],
                     "late starts": f"{late.start.min()}..{late.start.max()} ({len(late)})",
                     "late: pass/fail/unresolved/seq": f"{count(late, 'pass')}/{count(late, 'fail')}/"
                                                       f"{count(late, 'unresolved (data ends)')}/"
                                                       f"{int(late['sequencing-dependent'].sum())}",
                     "back to back (pass/fail/expired/unresolved)": "/".join(
                         str(int((wb.outcome == x).sum())) for x in ("pass", "fail", "expired",
                                                                     "unresolved (data ends)")),
                     "median days to pass (full)": sf["median days to pass"]})
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 30)
print(pd.DataFrame(rows).round(1).T.to_string())
side = pd.concat({f"{s} {t}t": v["outcome"] for (s, t), v in per_start.items()}, axis=1)
side.insert(0, "fully observed", per_start[("4 MNQ / $200", 1)]["fully observed"])
side.to_csv("verification/mnq_native_eval_by_start.csv")
print("\nsame start dates in all four runs:", len({tuple(v.index) for v in per_start.values()}) == 1)
