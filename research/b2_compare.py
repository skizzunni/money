"""Control B against candidate B2 (second lock step), as pre-registered in docs/DEVELOPMENT.md.

    python research/b2_compare.py <sim.dll> <nq1m_scaled.pkl> <nsx1m_scaled.pkl> <out.csv>

Needs the rejected candidate code (verification/candidate_b2_rejected.patch) applied for the SecondLock settings.
Complete reruns on the stand-in, same data, dates, warm-up, settings and costs ($0.95 a side; 1 and 2 ticks), the only
difference SecondLockAt 0 (control) / 2 (candidate, stop to entry + 25 points). Per run: the strategy's continuous
results, and the 50K intraday-trail evaluation from every session (and back to back), research/eval_sim.py's rules.
"""
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402

PERIODS = [("development: NQ 2015-03..2020-12", 1, "2015-03-01", "2020-12-31"),
           ("validation: NQ 2021-01..2025-06", 1, "2021-01-01", "2025-06-30"),
           ("validation: index 2025-07..2026-09", 2, "2025-07-01", "2026-09-30")]
ARMS = {"control B": {"SecondLockAt": 0}, "candidate B2": {"SecondLockAt": 2, "SecondLockPlus": 25}}


def prepare(pkl, first, last):
    bars = K.rth(pd.read_pickle(pkl))
    m = bars.index.tz_convert(K.NY)
    # 14 sessions of warm-up before the period: start loading a month early, evaluate and count from `first`
    lo = pd.Timestamp(first, tz=K.NY) - pd.Timedelta(days=35)
    bars = bars[(m >= lo) & (m < pd.Timestamp(last, tz=K.NY) + pd.Timedelta(days=1))]
    return bars


def run_period(dll, label, pkl, first, last):
    bars = prepare(pkl, first, last)
    m = bars.index.tz_convert(K.NY)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(bars, csv)
    bad = K.incomplete_sessions(bars)
    skip = K.DEFAULT_SKIP + "," + ",".join(bad)
    o, h, lo_ = (bars[c].to_numpy(float) for c in ("open", "high", "low"))
    bar_day = m.normalize().tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(bar_day)))
    day_of = np.searchsorted(sessions, bar_day)
    first_ok = int(np.searchsorted(sessions, pd.Timestamp(first)))
    start_bar = int(np.searchsorted(bar_day, sessions[first_ok]))

    def job(args):
        arm, props, slip = args
        tr = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=E.FEE, SkipDates=skip,
                   **props)
        tr = tr[tr.eb >= start_bar].sort_values("xb").reset_index(drop=True)  # warm-up trades not counted
        eq = tr.pnl.cumsum()
        wins, losses = tr.pnl[tr.pnl > 0], tr.pnl[tr.pnl < 0]
        run = best = 0
        for p in tr.pnl:
            run = run + 1 if p < 0 else 0
            best = max(best, run)
        day = tr.groupby(bar_day[tr.xb.to_numpy()]).pnl.sum()
        r = {"period": label, "arm": arm, "slippage": slip, "trades": len(tr), "net $": tr.pnl.sum(),
             "profit factor": wins.sum() / -losses.sum(), "avg win": wins.mean(), "avg loss": losses.mean(),
             "closed DD": float((eq.cummax().clip(lower=0) - eq).max()), "losing streak": best,
             "worst day": day.min()}
        trs = E.marks(tr, o, h, lo_, slip)
        w = E.run_windows(trs, sessions, first_ok, day_of, bar_day)
        s = E.summarize(w, "")
        wb = E.run_windows(trs, sessions, first_ok, day_of, bar_day, chain=True)
        sb = E.summarize(wb, "")
        r.update({"eval starts": s["evaluations"], "pass": s["pass"], "fail": s["fail"], "expired": s["expired"],
                  "path-dependent": s["outcome depends on path"], "unresolved": s["unresolved (data ends)"],
                  "pass %": s["pass %"], "fail %": s["fail %"],
                  "median days to pass": s["median days to pass"],
                  "back-to-back pass/fail/expired": f"{sb['pass']}/{sb['fail']}/{sb['expired']}"})
        return r

    jobs = [(a, p, slip) for a, p in ARMS.items() for slip in (1, 2)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(job, jobs))
    print(f"done {label}: first counted session {sessions[first_ok].date()}, {len(bad)} sessions with missing "
          f"minutes", flush=True)
    return rows


def main():
    dll, nq, nsx, out = sys.argv[1:5]
    rows = []
    for label, which, first, last in PERIODS:
        rows += run_period(dll, label, nq if which == 1 else nsx, first, last)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))


if __name__ == "__main__":
    main()
