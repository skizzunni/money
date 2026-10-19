"""Candidate C against B (docs/CANDIDATE_C.md): continuous research and the evaluation replay, as pre-registered.

    python research/candidate_c.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>
    python research/candidate_c.py nq <nq1m_scaled.pkl> <sim.dll> <out folder> [first last]

Configurations: B (frozen, breakout off); C0 (SignalsFromModel on, the earlier pass rule: B-protected, the runner's
code path); C1a (signals kept apart from the model, the earlier pass rule); C1 (C1a, and the pass only on realized
profit).

Continuous research: one run each over the whole history, per-trade sizing, daily limits and the 15:55 flat on, the
evaluation-account limits off (EvalTarget 0, no trail, no reserve). Eligible sessions: from the first evaluation start,
each session with a 09:30 bar that is not a skip date. Evaluation replay: as research/runner_compare.py (identical
starts; each candidate start its own run with EvaluationStart; research/eval_sim.py rules). RUNNER_CACHE caches
per-start runs.
All results are the stand-in simulator's.
"""
import os
import pickle
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
import runner_compare as RC  # noqa: E402

C_CONFIGS = {"C0": {"SignalsFromModel": True, "PassOnRealizedOnly": False},
             "C1a": {"SignalsFromModel": False, "PassOnRealizedOnly": False},
             "C1": {"SignalsFromModel": False, "PassOnRealizedOnly": True}}
CONTINUOUS = {"EvalTarget": 0, "EvalTrail": 100000, "AccountReserve": 0}
OUTCOMES = RC.OUTCOMES


def run(dll, csv, props):
    """One stand-in run: trades (bars as in the file) and the checks: (time, 'taken' or the refusal)."""
    args = [f"{k}={v}" for k, v in props.items()]
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "1", *args], capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    rows = [{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]), "why": a[5],
             "pnl": float(a[6]), "q": int(b[1])} for a, b in zip(t, n, strict=True)]
    checks = []
    for x in lines:
        if x.startswith("P,C check "):
            head, what = x[len("P,C check "):].split(": ", 1)
            checks.append((pd.Timestamp(head[:16]), "taken" if what.startswith("entry sent") else
                           what.split("not taken: ", 1)[-1].split(" [")[0]))
    audit = [x[2:] for x in lines if x.startswith("P,C audit")]
    return pd.DataFrame(rows, columns=["d", "eb", "en", "xb", "ex", "why", "pnl", "q"]), checks, audit


def props_for(cfg, slip, extra):
    base = {"SimSlippageTicks": slip, "SimCommissionPerSide": E.FEE, **extra}
    if cfg == "B":
        return {**base, "UseBreakout": False}
    return {"Strategy": "C", **base, **C_CONFIGS[cfg]}


def intraday_dd(trs, start_bar, day_of):
    """Peak-to-trough of equity with open P/L at bar extremes (the replay's worst path), no account limits."""
    tgt, trail = E.TARGET, E.TRAIL
    try:
        E.TARGET, E.TRAIL = 1e12, 1e12
        return E.evaluate_detail(trs, start_bar, 10**12, day_of, "worst mix")[2]
    finally:
        E.TARGET, E.TRAIL = tgt, trail


def stats(tr, mk, eligible, slip):
    """Continuous-research statistics over the eligible sessions."""
    day = mk.bar_day[tr.eb.to_numpy(dtype=int)] if len(tr) else pd.DatetimeIndex([])
    tr = tr[np.isin(day, eligible)].reset_index(drop=True)
    day = mk.bar_day[tr.eb.to_numpy(dtype=int)]
    per_day = pd.Series(1, index=day).groupby(level=0).sum().reindex(eligible, fill_value=0)
    pnl = tr.pnl
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    top5 = wins.nlargest(5).sum()
    streak = run_ = 0
    for p in pnl:
        run_ = run_ + 1 if p < 0 else 0
        streak = max(streak, run_)
    exit_day = mk.bar_day[tr.xb.to_numpy(dtype=int)]
    trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
    return {
        "eligible sessions": len(eligible), "trades": len(tr),
        "trades / session": len(tr) / len(eligible),
        "days 0 / 1 / 2 / 3+ trades %": " / ".join(f"{100 * x:.0f}" for x in (
            (per_day == 0).mean(), (per_day == 1).mean(), (per_day == 2).mean(), (per_day >= 3).mean())),
        "net $": pnl.sum(), "net / session $": pnl.sum() / len(eligible),
        "profit factor": wins.sum() / -losses.sum() if len(losses) else np.inf,
        "win %": 100 * len(wins) / max(len(tr), 1), "avg win": wins.mean(), "avg loss": losses.mean(),
        "5 largest winners, share of net %": 100 * top5 / pnl.sum() if pnl.sum() > 0 else np.nan,
        "net without the 5 largest winners $": pnl.sum() - top5,
        "intraday DD $": intraday_dd(trs, 0, mk.day_of),
        "losing streak": streak, "worst day $": pnl.groupby(exit_day).sum().min(),
        "contracts / trade": tr.q.mean(),
        "periods": " ".join(f"{k.strftime('%b' if mk.period == 'M' else '%Y')} {v:+.0f}"
                            for k, v in pnl.groupby(exit_day.to_period(mk.period)).sum().items()),
        "exits": tr.why.value_counts().to_dict(),
    }, tr


def continuous(mk, dll, whole, extra, eligible, slips):
    out, trades = [], {}
    for slip in slips:
        for cfg in ("B", "C0", "C1"):
            p = props_for(cfg, slip, extra)
            if cfg != "B":
                p.update(CONTINUOUS)
            tr, checks, audit = run(dll, whole, p)
            s, tr = stats(tr, mk, eligible, slip)
            refused = pd.Series([w for _, w in checks if w != "taken"], dtype=object).value_counts().to_dict()
            out.append({"config": cfg, "slippage": slip, **s, "checks refused": refused})
            trades[(cfg, slip)] = tr
        # the trades C1 has and C0 has not ("recovered"), and the reverse
        for a, b, label in (("C1", "C0", "recovered (C1 not C0)"), ("C0", "C1", "displaced (C0 not C1)")):
            ta, tb = trades[(a, slip)], trades[(b, slip)]
            keys = set(zip(tb.eb, tb.d, strict=True))
            extra_tr = ta[[(e, d) not in keys for e, d in zip(ta.eb, ta.d, strict=True)]]
            w, lo = extra_tr.pnl[extra_tr.pnl > 0], extra_tr.pnl[extra_tr.pnl < 0]
            out.append({"config": label, "slippage": slip, "trades": len(extra_tr), "net $": extra_tr.pnl.sum(),
                        "profit factor": w.sum() / -lo.sum() if len(lo) else np.nan,
                        "avg win": w.mean(), "avg loss": lo.mean()})
    return pd.DataFrame(out), trades


def replay(mk, dll, whole, extra, configs, slips, workers=4):
    sessions, bar_day = mk.sessions, mk.bar_day
    starts = list(range(mk.first_ok, len(sessions)))
    tmp = Path(tempfile.mkdtemp())
    cache_dir = Path(os.environ["RUNNER_CACHE"]) if os.environ.get("RUNNER_CACHE") else None

    def slice_run(cfg, slip, s):
        key = cache_dir / f"C_{cfg}_{slip}_{sessions[s]:%Y%m%d}.pkl" if cache_dir else None
        if key is not None and key.exists():
            return pickle.loads(key.read_bytes())
        i0 = int(np.searchsorted(bar_day, sessions[s] - pd.Timedelta(days=RC.WARMUP_DAYS)))
        i1 = int(np.searchsorted(bar_day, sessions[s] + pd.Timedelta(days=E.DAYS + 1)))
        csv = tmp / f"{cfg}_{slip}_{s}.csv"
        K.write_bars(mk.bars.iloc[i0:i1], csv)
        tr, checks, _ = run(dll, csv, {**props_for(cfg, slip, extra), "EvaluationStart": f"{sessions[s]:%Y-%m-%d}"})
        csv.unlink()
        tr[["eb", "xb"]] += i0
        if key is not None:
            key.parent.mkdir(parents=True, exist_ok=True)
            key.write_bytes(pickle.dumps((tr, checks)))
        return tr, checks

    def job(args):
        cfg, slip = args
        b_run = (run(dll, whole, props_for("B", slip, extra))[0], []) if cfg == "B" else None
        rows = []
        for s in starts:
            tr, checks = b_run if b_run is not None else slice_run(cfg, slip, s)
            trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
            w = E.run_windows(trs, sessions, s, mk.day_of, bar_day, limit=1).iloc[0].to_dict()
            d0 = sessions[s]
            sb, eb_ = int(np.searchsorted(bar_day, d0)), int(np.searchsorted(bar_day, d0 + pd.Timedelta(days=E.DAYS)))
            end_t = mk.t[eb_] if eb_ < len(mk.t) else mk.t[-1] + pd.Timedelta(minutes=1)
            inside = [(t, why) for t, why in checks if mk.t[sb] <= t < end_t]
            w["halted"] = w["outcome"] == "expired" and bool(inside) and inside[-1][1] == "account reserve room"
            w["trades"] = int(((tr.eb >= sb) & (tr.eb < eb_)).sum())
            rows.append({"config": cfg, "slippage": slip, **w})
        return pd.DataFrame(rows)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        frames = list(pool.map(job, [(c, s) for c in configs for s in slips]))
    table = []
    for w in frames:
        fo, late = w[w["fully observed"]], w[~w["fully observed"]]

        def c(df, x):
            return int((df.outcome == x).sum())

        starts_ = pd.to_datetime(fo.start).reset_index(drop=True)
        picks, nxt = [], starts_[0]
        for i, st in enumerate(starts_):
            if st >= nxt:
                picks.append(i)
                nxt = st + pd.Timedelta(days=E.DAYS)
        ind = fo.reset_index(drop=True).loc[picks]
        table.append({
            "config": w.config.iloc[0], "slippage": w.slippage.iloc[0], "full starts": len(fo),
            "full: pass / fail / expired": f"{c(fo, 'pass')} / {c(fo, 'fail')} / {c(fo, 'expired')}",
            "full: pass %": 100 * c(fo, "pass") / len(fo),
            "full: path-dependent": int(fo.outcome.str.contains("/").sum()),
            "full: expired, halted at the reserve": int(fo.halted.sum()),
            "full: median days to pass": fo[fo.outcome == "pass"]["calendar days"].median(),
            "full: median / worst intraday DD": f"{fo['intraday DD'].median():.0f} / {fo['intraday DD'].max():.0f}",
            "worst intraday DD": fo["intraday DD"].max(),
            "non-overlapping starts": len(ind),
            "non-overlapping: pass / fail / expired": f"{c(ind, 'pass')} / {c(ind, 'fail')} / {c(ind, 'expired')}",
            "late starts: pass / fail / expired / unresolved": " / ".join(str(c(late, x)) for x in OUTCOMES),
        })
    return pd.DataFrame(table), pd.concat(frames)


def main():
    if sys.argv[1] == "mnq":
        mk = RC.mnq_market(sys.argv[2], sys.argv[3])
        dll, out = sys.argv[4], Path(sys.argv[5])
        configs = ["B", "C0", "C1a", "C1"]
    else:
        first, last = (sys.argv[5], sys.argv[6]) if len(sys.argv) > 6 else ("2015-03-01", "2025-06-30")
        mk = RC.nq_market(sys.argv[2], first, last)
        dll, out = sys.argv[3], Path(sys.argv[4])
        configs = os.environ.get("C_CONFIGS", "B,C0,C1a,C1").split(",")
    out.mkdir(parents=True, exist_ok=True)
    extra = {"SkipDates": mk.skip_dates} if mk.skip_dates else {}
    whole = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(mk.bars, whole)
    skip = set(pd.to_datetime((mk.skip_dates or K.DEFAULT_SKIP).split(",")))
    opens = pd.DatetimeIndex(sorted(set(mk.bar_day[(mk.t.hour == 9) & (mk.t.minute == 30)])))
    eligible = pd.DatetimeIndex([d for d in opens if d >= mk.sessions[mk.first_ok] and d not in skip])
    slips = (1, 2)
    cont, trades = continuous(mk, dll, whole, extra, eligible, slips)
    cont.to_csv(out / "continuous.csv", index=False)
    for (cfg, slip), tr in trades.items():
        tr.to_csv(out / f"continuous_trades_{cfg}_{slip}t.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 300)
    print(f"eligible sessions {len(eligible)}: {eligible[0].date()}..{eligible[-1].date()}")
    print(cont.round(2).T.to_string())
    rep, windows = replay(mk, dll, whole, extra, configs, slips)
    rep.to_csv(out / "replay.csv", index=False)
    windows.to_csv(out / "replay_windows.csv", index=False)
    print(rep.round(1).T.to_string())


if __name__ == "__main__":
    main()
