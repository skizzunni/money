"""Candidate comparison (docs/RUNNER.md): original B, B with the new sizing and account protections ("B-protected"),
and the runner exit with the same sizing and protections.

    python research/runner_compare.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>
    python research/runner_compare.py nq <nq1m_scaled.pkl> <sim.dll> <out folder> [first last]

mnq: the contracts actually traded (research/mnq_bars.py: 09-26 to the 9/10 roll session, then 12-26), 09:30-16:00 and
the 16:00 bar, warm-up 6/29 to 7/17, evaluations from 7/20. nq (a separate check, not the user's contract): NQ 1-minute
bars rescaled to today's level, 2015-03 to 2025-06 by default, B's skip dates plus sessions with missing minutes.
Costs: $0.95 a side; slippage 1 and 2 ticks on every market and stop fill. All runs are the stand-in simulator (it
reproduces NinjaTrader on the MNQ bars for B: research/mnq_reconcile.py; the candidate has not run in NinjaTrader).

Evaluations: one per session, identical start dates for all three. B is start-independent (one continuous run; the
replay applies its live evaluation-target close). The candidates' account protections depend on where the evaluation
starts, so each start is its own run (EvaluationStart = that session) on that start's slice of bars: 35 calendar days
of warm-up and the 30-day window. Every window is replayed with research/eval_sim.py (valid price paths, the trail after
every fill and commission, four paths). Fully observed starts (30 days within the data) are reported apart from later
ones. "Halted": an expired window whose last signal was refused for lack of room above the account reserve.

Trading statistics: back-to-back attempts (the next starts the session after an outcome), each attempt's trades up to
its outcome; a position open at a pass or a breach ends there at the replay's equity ("Evaluation target (replay)" /
"Liquidation (replay)").
"""
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import mnq_bars as M  # noqa: E402

CONFIGS = {"1 original B": None, "2 B-protected": False, "3 runner": True}
OUTCOMES = ("pass", "fail", "expired", "unresolved (data ends)")
WARMUP_DAYS = 35


def run(dll, csv, props):
    """One stand-in run: its trades (bars as in the file) and the signals the candidate did not take."""
    args = [f"{k}={v}" for k, v in props.items()]
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "1", *args], capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    rows = [{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]), "why": a[5],
             "pnl": float(a[6]), "name": b[0], "q": int(b[1])} for a, b in zip(t, n, strict=True)]
    skips = [x.split("signal ", 1)[1].split(" not taken: ") for x in lines if " not taken: " in x]
    cols = ["d", "eb", "en", "xb", "ex", "why", "pnl", "name", "q"]
    return pd.DataFrame(rows, columns=cols), [(pd.Timestamp(a), b) for a, b in skips]


class Market:
    """Bars and the session calendar, with the first session an evaluation may start."""

    def __init__(self, bars, first_ok, skip_dates=None, period="M"):
        self.bars, self.first_ok, self.skip_dates, self.period = bars, first_ok, skip_dates, period
        m = bars.index.tz_convert(K.NY)
        self.t = m.tz_localize(None)
        self.o, self.h, self.lo = (bars[c].to_numpy(float) for c in ("open", "high", "low"))
        self.bar_day = m.normalize().tz_localize(None)
        self.sessions = pd.DatetimeIndex(sorted(set(self.bar_day)))
        self.day_of = np.searchsorted(self.sessions, self.bar_day)
        self.last = self.sessions[-1]


def mnq_market(sep_path, dec_path):
    series, _ = M.traded_series(M.load(sep_path), M.load(dec_path))
    bars = K.rth(series)
    cov = M.coverage(series)
    skip = set(pd.to_datetime(K.DEFAULT_SKIP.split(",")))
    full = [pd.Timestamp(r.session) for r in cov.itertuples()
            if r.minutes == 390 and pd.Timestamp(r.session) not in skip]
    sessions = pd.DatetimeIndex(sorted(set(bars.index.tz_convert(K.NY).normalize().tz_localize(None))))
    return Market(bars, int(np.searchsorted(sessions, full[13])) + 1)


def nq_market(pkl, first, last):
    bars = K.rth(pd.read_pickle(pkl))
    m = bars.index.tz_convert(K.NY)
    lo = pd.Timestamp(first, tz=K.NY) - pd.Timedelta(days=WARMUP_DAYS)
    bars = bars[(m >= lo) & (m < pd.Timestamp(last, tz=K.NY) + pd.Timedelta(days=1))]
    skip = K.DEFAULT_SKIP + "," + ",".join(K.incomplete_sessions(bars))
    sessions = pd.DatetimeIndex(sorted(set(bars.index.tz_convert(K.NY).normalize().tz_localize(None))))
    return Market(bars, int(np.searchsorted(sessions, pd.Timestamp(first))), skip, "Y")


def compare(mk, dll, out, slips=(1, 2), workers=4):
    out.mkdir(parents=True, exist_ok=True)
    sessions, bar_day, last = mk.sessions, mk.bar_day, mk.last
    starts = list(range(mk.first_ok, len(sessions)))
    tmp = Path(tempfile.mkdtemp())
    whole = tmp / "bars.csv"
    K.write_bars(mk.bars, whole)
    extra = {"SkipDates": mk.skip_dates} if mk.skip_dates else {}

    def slice_run(cfg, slip, s):
        """The candidate for an evaluation starting at session s, on that start's slice; bars as in the whole file."""
        i0 = int(np.searchsorted(bar_day, sessions[s] - pd.Timedelta(days=WARMUP_DAYS)))
        i1 = int(np.searchsorted(bar_day, sessions[s] + pd.Timedelta(days=E.DAYS + 1)))
        csv = tmp / f"{cfg.split()[0]}_{slip}_{s}.csv"
        K.write_bars(mk.bars.iloc[i0:i1], csv)
        tr, skips = run(dll, csv, {"Strategy": "Runner", "SimSlippageTicks": slip, "SimCommissionPerSide": E.FEE,
                                   "RunnerExit": CONFIGS[cfg], "EvaluationStart": sessions[s].strftime("%Y-%m-%d"),
                                   **extra})
        csv.unlink()
        tr[["eb", "xb"]] += i0
        return tr, skips

    def windows(tr, skips, s, slip):
        trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
        w = E.run_windows(trs, sessions, s, mk.day_of, bar_day, limit=1).iloc[0].to_dict()
        d0 = sessions[s]
        sb, eb_ = int(np.searchsorted(bar_day, d0)), int(np.searchsorted(bar_day, d0 + pd.Timedelta(days=E.DAYS)))
        end_t = mk.t[eb_] if eb_ < len(mk.t) else mk.t[-1] + pd.Timedelta(minutes=1)
        taken = [mk.t[i - 1] for i in tr.eb if sb <= i < eb_]  # the signal bar is the bar before the entry
        refused = [(t, why) for t, why in skips if mk.t[sb] <= t < end_t]
        events = sorted([(t, "taken") for t in taken] + refused)
        w["room refusals"] = sum(why == "account reserve room" for _, why in refused)
        w["halted"] = w["outcome"] == "expired" and bool(events) and events[-1][1] == "account reserve room"
        w["trades"] = len(taken)
        return w

    def job(args):
        cfg, slip = args
        cache = {}
        b_trades = None
        if CONFIGS[cfg] is None:
            b_trades = (run(dll, whole, {"SimSlippageTicks": slip, "SimCommissionPerSide": E.FEE, "UseBreakout": False,
                                         **extra})[0], [])

        def get(s):
            if b_trades is not None:
                return b_trades
            if s not in cache:
                cache[s] = slice_run(cfg, slip, s)
            return cache[s]

        rows = [{"config": cfg, "slippage": slip, **windows(*get(s), s, slip)} for s in starts]
        chain, attempts, s = [], [], mk.first_ok
        while s < len(sessions):
            tr = get(s)[0]
            trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
            d0 = sessions[s]
            end_day = d0 + pd.Timedelta(days=E.DAYS)
            complete = end_day <= last + pd.Timedelta(days=1)
            sb = int(np.searchsorted(bar_day, d0))
            eb_ = int(np.searchsorted(bar_day, end_day)) if complete else 10**12
            outc, at, dd, eq, ti = E.evaluate_detail(trs, sb, eb_, mk.day_of, "worst mix")
            outc = "unresolved (data ends)" if outc == "open" else outc
            win = tr[(tr.eb >= sb) & (tr.eb < eb_)].copy()
            if at is not None:
                if ti is not None:  # the position open at the outcome ends there
                    before = win[win.index < ti]
                    why = "Evaluation target (replay)" if outc == "pass" else "Liquidation (replay)"
                    win = pd.concat([before, tr.loc[[ti]].assign(pnl=eq - before.pnl.sum(), xb=at, why=why)])
                else:
                    win = win[win.xb <= at]
            chain.append(win.assign(attempt=len(attempts)))
            attempts.append({"start": d0.date(), "outcome": outc, "result $": win.pnl.sum(), "intraday DD": dd,
                             "end": bar_day[at].date() if at is not None else None})
            if outc == "unresolved (data ends)":
                break
            if at is not None:
                s = int(np.searchsorted(sessions, bar_day[at])) + 1
            else:
                s = int(np.searchsorted(sessions, end_day))
        return cfg, slip, pd.DataFrame(rows), pd.concat(chain), pd.DataFrame(attempts)

    jobs = [(c, s) for c in CONFIGS for s in slips]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(job, jobs))
    table = []
    for cfg, slip, w, ch, att in results:
        tag = f"{cfg.split()[0]}_{slip}t"
        w.to_csv(out / f"windows_{tag}.csv", index=False)
        ch.to_csv(out / f"chain_trades_{tag}.csv", index=False)
        att.to_csv(out / f"chain_attempts_{tag}.csv", index=False)
        fo, late = w[w["fully observed"]], w[~w["fully observed"]]

        def c(df, x):
            return int((df.outcome == x).sum())

        pnl = ch.pnl
        wins, losses = pnl[pnl > 0], pnl[pnl < 0]
        streak = run_ = 0
        for p in pnl:
            run_ = run_ + 1 if p < 0 else 0
            streak = max(streak, run_)
        exit_day = bar_day[ch.xb.to_numpy()]
        day = pnl.groupby(exit_day).sum()
        per = pnl.groupby(exit_day.to_period(mk.period)).sum()
        fmt = "%b" if mk.period == "M" else "%Y"
        table.append({
            "config": cfg, "slippage": slip,
            "full starts": len(fo),
            "full: pass/fail/expired": f"{c(fo, 'pass')}/{c(fo, 'fail')}/{c(fo, 'expired')}",
            "full: path-dependent": int(fo.outcome.str.contains("/").sum()),
            "full: expired, halted at the reserve": int(fo.halted.sum()),
            "full: median days to pass": fo[fo.outcome == "pass"]["calendar days"].median(),
            "full: median intraday DD": fo["intraday DD"].median(),
            "full: worst intraday DD": fo["intraday DD"].max(),
            "late starts": len(late),
            "late: pass/fail/expired/unresolved": "/".join(str(c(late, x)) for x in OUTCOMES),
            "back to back: pass/fail/expired/unresolved": "/".join(str(c(att, x)) for x in OUTCOMES),
            "trades": len(ch), "net $": pnl.sum(),
            "profit factor": wins.sum() / -losses.sum() if len(losses) else np.inf,
            "avg win": wins.mean(), "avg loss": losses.mean(), "losing streak": streak, "worst day": day.min(),
            "max intraday DD (attempts)": att["intraday DD"].max(),
            "contracts/trade": ch.q.mean() if len(ch) else np.nan,
            "periods": " ".join(f"{k.strftime(fmt)} {v:+.0f}" for k, v in per.items()),
            "exits": ch.why.value_counts().to_dict(),
        })
    df = pd.DataFrame(table)
    df.to_csv(out / "comparison.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 400)
    print(f"sessions {sessions[0].date()}..{last.date()}; evaluations from {sessions[mk.first_ok].date()} "
          f"({len(starts)} starts)")
    print(df.round(1).T.to_string())
    return df


def main():
    if sys.argv[1] == "mnq":
        mk = mnq_market(sys.argv[2], sys.argv[3])
        dll, out = sys.argv[4], Path(sys.argv[5])
    else:
        first, last = (sys.argv[5], sys.argv[6]) if len(sys.argv) > 6 else ("2015-03-01", "2025-06-30")
        mk = nq_market(sys.argv[2], first, last)
        dll, out = sys.argv[3], Path(sys.argv[4])
    compare(mk, dll, out)


if __name__ == "__main__":
    main()
