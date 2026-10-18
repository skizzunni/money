"""Control B in the 50K intraday-trail evaluation on the user's native MNQ bars (docs/MNQ_NATIVE.md, test 2).

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
rows = []
for size, props in E.SIZES.items():
    for slip in (1, 2):
        tr = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=E.FEE, **props)
        cont = tr[tr.eb >= start_bar].sort_values("xb")
        eq = cont.pnl.cumsum()
        trs = E.marks(tr, o, h, lo)
        w = E.run_windows(trs, sessions, first_ok, day_of, bar_day)
        wb = E.run_windows(trs, sessions, first_ok, day_of, bar_day, chain=True)
        s, sb = E.summarize(w, ""), E.summarize(wb, "")
        wins, losses = cont.pnl[cont.pnl > 0], cont.pnl[cont.pnl < 0]
        rows.append({"size": size, "slippage": slip, "trades": len(cont), "net $": cont.pnl.sum(),
                     "profit factor": wins.sum() / -losses.sum(),
                     "closed DD": float((eq.cummax().clip(lower=0) - eq).max()),
                     "eval starts": s["evaluations"], "resolved": s["evaluations"] - s["unresolved (data ends)"],
                     "pass": s["pass"], "fail": s["fail"], "expired": s["expired"],
                     "seq-dependent": s["sequencing-dependent"], "median days to pass": s["median days to pass"],
                     "back to back pass/fail/expired/unresolved": f"{sb['pass']}/{sb['fail']}/{sb['expired']}/"
                                                                  f"{sb['unresolved (data ends)']}",
                     "intraday DD of passes median/max": s["intraday DD, passes: median / max"]})
        if size.startswith("4") and slip == 1:
            w.to_csv("verification/mnq_native_eval_windows_4mnq_1tick.csv", index=False)
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 30)
print(pd.DataFrame(rows).round(1).to_string(index=False))
