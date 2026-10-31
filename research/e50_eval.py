"""E50, pre-registered in docs/CANDIDATE_E50.md: v3.6's entries with at most $300 lost per trade (the whole position),
no take-profit and no limit on trades a day, replayed as 50K evaluations ($2,000 end-of-day trailing drawdown that
stops at the start, $1,000 daily limit, $3,000 target).

    SCAN_MINUTES=5 python research/e50_eval.py <data dir> <MNQ_09-26> <MNQ_12-26> <out.csv> [b]

"b" runs E50b: 1 MNQ at $260, take-profit off or 2.0, with or without a stop for the day after a loss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import t1_eval as T  # noqa: E402
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
TARGET, TRAIL = 3000.0, 2000.0


def config(qty: int, tp: float, ml: float = 300.0, losers: int = 0) -> dict:
    return {**S.V23, **T.REFERENCE, "qty": qty, "max_loss_per_trade": ml, "after_loss_ml_mult": 1.0,
            "after_loss_qty_div": 1.0, "take_profit": tp, "max_losers": losers, "daily_loss_limit": 1000.0,
            "trail_dd": 0.0, "profit_step": 0.0, "size_up_to": 0, "budget_actual": False}


def evals(tf: pd.DataFrame, days: list[str]) -> dict:
    """Fresh evaluations from every 5th session: pass at +$3,000 closed; fail when the closed equity after a trade is
    below the floor (the highest end-of-day equity so far, at least the start, less $2,000; it stops at the start)."""
    if tf.empty:
        return {"evals": 0}
    t = tf.sort_values("exit_time")
    tday = t.exit_time.dt.tz_convert(NY).dt.strftime("%Y-%m-%d").to_numpy()
    p = t.pnl.to_numpy()
    res = []
    for s in days[::5]:
        k0 = int(np.searchsorted(tday, s))
        if k0 >= len(p):
            break
        eq, peak_eod, cur_day, out = 0.0, 0.0, tday[k0], None
        for k in range(k0, len(p)):
            if tday[k] != cur_day:
                peak_eod = max(peak_eod, eq)
                cur_day = tday[k]
            eq += p[k]
            floor = min(peak_eod - TRAIL, 0.0)
            if eq < floor:
                out = ("fail", tday[k])
                break
            if eq >= TARGET:
                out = ("pass", tday[k])
                break
        if out is None:
            res.append(("open", None, s))
        else:
            res.append((out[0], out[1], s))
    d = pd.DataFrame(res, columns=["result", "end", "start"])
    n = len(d)
    passed = d[d.result == "pass"]
    dur = [np.busday_count(a, b) for a, b in zip(passed.start, passed.end, strict=True)]
    return {"evals": n, "pass %": round(100 * len(passed) / n, 1),
            "fail %": round(100 * (d.result == "fail").mean(), 1),
            "open %": round(100 * (d.result == "open").mean(), 1),
            "median days to pass": int(np.median(dur)) if dur else None}


def streaks(p: np.ndarray) -> dict:
    loss = p <= 0
    run = best = 0
    for x in loss:
        run = run + 1 if x else 0
        best = max(best, run)
    after = int((loss[1:] & loss[:-1]).sum())
    return {"longest losing run": best, "loss after a loss % of losses": round(100 * after / max(1, int(loss.sum())), 1)}


def main() -> None:
    S.init({}, *sys.argv[1:4])
    rows = []
    variants = [(q, tp, 300.0, 0) for q in (1, 2, 3) for tp in (0.0, 2.0)]
    if len(sys.argv) > 5 and sys.argv[5] == "b":  # E50b: 1 MNQ at $260, stop for the day after a loss or not
        variants = [(1, tp, 260.0, lo) for tp in (0.0, 2.0) for lo in (0, 1)]
    for qty, tp, ml, losers in variants:
        if True:
            for name, (bars, first, skip) in S.D.items():
                cfg = NoiseConfig(**config(qty, tp, ml, losers))
                if isinstance(skip, str):
                    cfg.skip_dates, cfg.fed_dates = skip, ""
                tf = run(bars, cfg, minutes=S.MIN[0]).trades_frame()
                if first:
                    tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
                p = tf.pnl.to_numpy()
                e = np.r_[0.0, np.cumsum(p)]
                t = bars.index.tz_convert(NY)
                days = sorted(set(t.strftime("%Y-%m-%d")))
                if first:
                    days = [x for x in days if x >= first]
                tr = S.trail_stats(name, tf)
                r = {"bars": f"{S.MIN[0]}-min", "qty": qty, "take_profit": tp, "max loss": ml, "max losers": losers,
                     "set": name, "trades": len(p), **streaks(p),
                     "trades/day": round(len(p) / max(1, tf.entry_time.dt.date.nunique()), 2),
                     "net $": round(float(p.sum())), "win %": round(100 * float((p > 0).mean()), 1),
                     "pf": round(float(p[p > 0].sum() / max(1e-9, -p[p <= 0].sum())), 3),
                     "largest loss $": round(float(p.min())), "largest win $": round(float(p.max())),
                     "closed dd $": round(float((np.maximum.accumulate(e) - e).max())), "eod dd $": tr[f"{name} eoddd"],
                     "worst day $": round(float(tf.groupby(tf.exit_time.dt.date).pnl.sum().min())),
                     **evals(tf, days)}
                rows.append(r)
                print(r, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[4], index=False)


if __name__ == "__main__":
    main()
