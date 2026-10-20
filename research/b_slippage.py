"""Frozen B on MNQ at 1, 2 and 3 ticks of slippage: 2 the base, 3 the stress (docs/FIXES_2026-10-20.md).

    python research/b_slippage.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>

The simulator (reconciled with native NinjaTrader, docs/B_NATIVE.md) on the traded-contract MNQ series; 4 MNQ / $200,
$0.95 a side. NinjaTrader's slippage setting slips market entries, market exits and stops alike, as the simulator
does. Per slippage: the continuous statistics over the 64 eligible sessions and the evaluation replay over the 44
fully observed starts (research/eval_sim.py).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_c as CC  # noqa: E402
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import runner_compare as RC  # noqa: E402


def main():
    mk, dll, out = RC.mnq_market(sys.argv[1], sys.argv[2]), sys.argv[3], Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(mk.bars, csv)
    skip = set(pd.to_datetime(K.DEFAULT_SKIP.split(",")))
    opens = pd.DatetimeIndex(sorted(set(mk.bar_day[(mk.t.hour == 9) & (mk.t.minute == 30)])))
    eligible = pd.DatetimeIndex([d for d in opens if d >= mk.sessions[mk.first_ok] and d not in skip])
    rows = []
    for slip in (1, 2, 3):
        tr = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=E.FEE)
        s, tr = CC.stats(tr, mk, eligible, slip)
        w = E.run_windows(E.marks(tr, mk.o, mk.h, mk.lo, slip), mk.sessions, mk.first_ok, mk.day_of, mk.bar_day)
        fo = E.summarize(w[w["fully observed"]], "")
        rows.append({"slippage ticks": slip, "role": {1: "reference", 2: "base", 3: "stress"}[slip],
                     "trades": s["trades"], "net $": round(s["net $"], 2),
                     "profit factor": round(s["profit factor"], 2),
                     "intraday DD $": round(s["intraday DD $"], 2),
                     "net / intraday DD": round(s["net $"] / s["intraday DD $"], 2),
                     "worst day $": round(s["worst day $"], 2), "months": s["periods"],
                     "44 starts: pass / breach / expired": f"{fo['pass']} / {fo['fail']} / {fo['expired']}",
                     "path-dependent": fo["outcome depends on path"]})
    df = pd.DataFrame(rows)
    df.to_csv(out / "b_slippage_mnq.csv", index=False)
    print(df.T.to_string())


if __name__ == "__main__":
    main()
