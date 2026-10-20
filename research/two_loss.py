"""R2 (2 losing trades a day) against R4 (Pine v1.5's 4), everything else the reference's (docs/PINE_REFERENCE.md).

    python research/two_loss.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>
    python research/two_loss.py nq <nq1m_scaled.pkl> <sim.dll> <out folder>

Full strategy runs of the NinjaTrader strategy MnqNoiseMomentum (frozen B's code) at the Pine reference's settings (2
MNQ, $70 max loss = 17.5 points, lock 17.5 -> +2.5, take-profit 1.5, line stop 0.24, stop free to follow the line) on
5-minute bars, in the stand-in; $0.95 a side; slippage 1 and 2 ticks. Continuous research over every eligible session,
and the Apex $50K evaluation replay (research/eval_sim.py) from every start. Stand-in simulator results.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_c as CC  # noqa: E402
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import runner_compare as RC  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mnqbot.data import resample  # noqa: E402

SETTINGS = {"R4": 4, "R2": 2}


def five(one):
    return resample(one.assign(volume=one["volume"] if "volume" in one else 0), "5min")


def market(kind, args):
    if kind == "mnq":
        mk1 = RC.mnq_market(args[0], args[1])
        bars = five(mk1.bars)
        first = mk1.sessions[mk1.first_ok]
        skip = None
    else:
        mk1 = RC.nq_market(args[0], "2015-03-01", "2025-06-30")
        bars = five(mk1.bars)
        first = mk1.sessions[mk1.first_ok]
        skip = mk1.skip_dates
    sessions = pd.DatetimeIndex(sorted(set(bars.index.tz_convert(K.NY).normalize().tz_localize(None))))
    return RC.Market(bars, int(np.searchsorted(sessions, first)), skip, "M" if kind == "mnq" else "Y")


def run(dll, csv, losers, slip, extra):
    props = {"UseBreakout": False, "Funded": False, "AutoAccountType": False, "EvalQty": 2, "EvalMaxLoss": 70,
             "EvalMaxLosers": losers, "EvalLockAt": 1.0, "EvalLockPlus": 2.5, "TakeProfit": 1.5, "StopBuffer": 0.24,
             "TightenOnly": False, "SimSlippageTicks": slip, "SimCommissionPerSide": E.FEE, **extra}
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "5", *[f"{k}={v}" for k, v in props.items()]],
                       capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    return pd.DataFrame([{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]),
                          "why": a[5], "pnl": float(a[6]), "q": int(b[1])} for a, b in zip(t, n, strict=True)])


def side_stats(tr):
    w, lo = tr.pnl[tr.pnl > 0], tr.pnl[tr.pnl < 0]
    return f"{len(tr)} trades, ${tr.pnl.sum():,.0f}, PF {w.sum() / -lo.sum() if len(lo) else np.inf:.2f}"


def main():
    kind = sys.argv[1]
    if kind == "mnq":
        mk, dll, out = market(kind, sys.argv[2:4]), sys.argv[4], Path(sys.argv[5])
    else:
        mk, dll, out = market(kind, sys.argv[2:3]), sys.argv[3], Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(mk.bars, csv)
    extra = {"SkipDates": mk.skip_dates} if mk.skip_dates else {}
    skip = set(pd.to_datetime((mk.skip_dates or K.DEFAULT_SKIP).split(",")))
    opens = pd.DatetimeIndex(sorted(set(mk.bar_day[(mk.t.hour == 9) & (mk.t.minute == 30)])))
    eligible = pd.DatetimeIndex([d for d in opens if d >= mk.sessions[mk.first_ok] and d not in skip])
    rows, windows, trades = [], [], {}
    for slip in (1, 2):
        for name, losers in SETTINGS.items():
            tr = run(dll, csv, losers, slip, extra)
            s, tr = CC.stats(tr, mk, eligible, slip)
            trades[(name, slip)] = tr
            tr.to_csv(out / f"trades_{name}_{slip}t.csv", index=False)
            eq = tr.pnl.cumsum()
            closed_dd = float((eq.cummax().clip(lower=0) - eq).max()) if len(tr) else 0.0
            day = mk.bar_day[tr.eb.to_numpy(dtype=int)]
            row = {"settings": name, "slippage": slip, **s,
                   "expectancy / trade $": tr.pnl.mean(), "closed DD $": closed_dd,
                   "net / intraday DD": s["net $"] / s["intraday DD $"] if s["intraday DD $"] else np.nan,
                   "long": side_stats(tr[tr.d > 0]), "short": side_stats(tr[tr.d < 0])}
            if kind == "nq":
                sub = tr[(day >= pd.Timestamp("2023-01-01"))]
                row["2023-2025.06"] = side_stats(sub)
                row["2025 (to 06-30)"] = side_stats(tr[day >= pd.Timestamp("2025-01-01")])
            # the evaluation replay from every start (the strategy is start-independent)
            trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
            w = E.run_windows(trs, mk.sessions, mk.first_ok, mk.day_of, mk.bar_day)
            fo = w[w["fully observed"]]
            starts_ = pd.to_datetime(fo.start).reset_index(drop=True)
            picks, nxt = [], starts_.iloc[0]
            for i, st in enumerate(starts_):
                if st >= nxt:
                    picks.append(i)
                    nxt = st + pd.Timedelta(days=E.DAYS)
            ind = fo.reset_index(drop=True).loc[picks]

            def c(df, x):
                return int((df.outcome == x).sum())

            row.update({"eval starts (full)": len(fo),
                        "eval: pass / breach / expired": f"{c(fo, 'pass')} / {c(fo, 'fail')} / {c(fo, 'expired')}",
                        "eval: pass %": 100 * c(fo, "pass") / len(fo),
                        "eval: path-dependent": int(fo.outcome.str.contains("/").sum()),
                        "eval: non-overlapping pass / breach / expired":
                            f"{c(ind, 'pass')} / {c(ind, 'fail')} / {c(ind, 'expired')} of {len(ind)}",
                        "eval: median days to pass": fo[fo.outcome == "pass"]["calendar days"].median(),
                        "eval: worst intraday DD": fo["intraday DD"].max()})
            rows.append(row)
            windows.append(w.assign(settings=name, slippage=slip))
        # the trades the limit removes: R4's that R2 does not take
        a, b = trades[("R4", slip)], trades[("R2", slip)]
        kb = set(zip(b.eb, b.d, strict=True))
        removed = a[[(e, d) not in kb for e, d in zip(a.eb, a.d, strict=True)]]
        ka = set(zip(a.eb, a.d, strict=True))
        added = b[[(e, d) not in ka for e, d in zip(b.eb, b.d, strict=True)]]
        rows.append({"settings": "removed by the limit (R4 not R2)", "slippage": slip, "trades": len(removed),
                     "net $": removed.pnl.sum(), "long": side_stats(removed[removed.d > 0]),
                     "short": side_stats(removed[removed.d < 0])})
        rows.append({"settings": "added (R2 not R4)", "slippage": slip, "trades": len(added), "net $": added.pnl.sum()})
        if kind == "nq":
            yr4 = a.pnl.groupby(mk.bar_day[a.xb.to_numpy(dtype=int)].year).sum()
            yr2 = b.pnl.groupby(mk.bar_day[b.xb.to_numpy(dtype=int)].year).sum()
            diff = (yr2 - yr4).fillna(0)
            rows.append({"settings": "R2 - R4 by year", "slippage": slip,
                         "periods": " ".join(f"{y} {v:+.0f}" for y, v in diff.items()),
                         "trades": int((diff > 0).sum()), "net $": diff.sum()})
    df = pd.DataFrame(rows)
    df.to_csv(out / "comparison.csv", index=False)
    pd.concat(windows).to_csv(out / "replay_windows.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 160)
    print(f"eligible sessions {len(eligible)}: {eligible[0].date()}..{eligible[-1].date()}")
    print(df.round(2).T.to_string())


if __name__ == "__main__":
    main()
