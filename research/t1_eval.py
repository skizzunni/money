"""The evaluation pre-registered in docs/CANDIDATE_T1.md: the unchanged reference (v3.6's settings) against candidate T1
(the same with the broker-style lock at 0.15 max losses) on identical bars: the user's MNQ window, the 2025-2026
stand-in, NQ futures 2015-2025 and the Nasdaq-100 index 2011-2026. Participation, executions and costs, net expectancy,
net win rate, profit factor, closed, marked-equity and end-of-day drawdowns, and the four acceptance checks on the
stand-in.

    SCAN_MINUTES=5 python research/t1_eval.py <data dir> <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out.csv>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
FEE, TICK, PV = 0.62, 0.25, 2.0
REFERENCE = {"calm_k": 0.7, "calm_short": 10, "calm_long": 40, "qty": 1, "max_loss_per_trade": 187.5,
             "lock_at": 0.35, "after_loss_qty_div": 1.0, "after_loss_ml_mult": 250.0 / 187.5,
             "daily_loss_limit": 2000.0, "max_losers": 0,
             "tv_path": True, "range_pos_min": 0.65, "trail_dd": 3000.0, "trail_cap": 0.0, "profit_step": 1500.0,
             "size_up_to": 15, "budget_actual": True, "trend_n": 50, "trend_side": -1, "squeeze_min": 20.0,
             "take_profit": 2.0, "stop_buffer": 0.24, "lock_plus": 2.5, "last_entry_end": 900, "big_day_k": 1.5,
             "big_day_n": 10, "tighten_only": True}
CANDIDATE_T1 = {**REFERENCE, "lock_intrabar": True, "lock_at": 0.15}
CRITERIA = {"net": 75000.0, "win": 80.0, "pf": 2.0, "marked_dd": 4000.0}


def drawdowns(bars: pd.DataFrame, tf: pd.DataFrame, start: int) -> tuple[float, float]:
    """The closed-trade drawdown, and the marked-equity drawdown: at every bar from `start`, the closed equity plus the
    open position marked at the bar's worst price (low for a long, high for a short), against the highest close-marked
    equity before it."""
    p = tf.pnl.to_numpy()
    e = np.r_[0.0, np.cumsum(p)]
    closed_dd = float((np.maximum.accumulate(e) - e).max())
    n = len(bars)
    lo, hi, cl = (bars[x].to_numpy(float) for x in ("low", "high", "close"))
    realized = np.zeros(n)
    np.add.at(realized, tf.exit_bar.to_numpy(int), p)
    closed = np.cumsum(realized)  # closed equity after each bar's exits
    mark_close, mark_worst = closed.copy(), closed.copy()
    for t in tf.itertuples():
        for j in range(t.entry_bar, t.exit_bar):  # the exit bar itself counts at its realized result
            worst = lo[j] if t.direction > 0 else hi[j]
            mark_worst[j] = closed[j] + t.direction * (worst - t.entry) * t.qty * PV - FEE * t.qty
            mark_close[j] = closed[j] + t.direction * (cl[j] - t.entry) * t.qty * PV - FEE * t.qty
    mc, mw = mark_close[start:], mark_worst[start:]
    peak = np.maximum.accumulate(np.r_[0.0, mc])[:-1]  # the highest close-marked equity before each bar
    peak = np.maximum(peak, np.maximum.accumulate(mc))
    return closed_dd, float(max(0.0, (peak - mw).max()))


def measure(name: str, bars: pd.DataFrame, first, skip, cfg_kw: dict, minutes: int) -> dict:
    cfg = NoiseConfig(**cfg_kw)
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    if first:
        cfg.trail_from = first
    tf = run(bars, cfg, minutes=minutes).trades_frame()
    t = bars.index.tz_convert(NY)
    start = int(np.searchsorted(bars.index, pd.Timestamp(first, tz=NY))) if first else 0
    if first:
        tf = tf[tf.entry_time >= pd.Timestamp(first, tz=NY)]
    days = pd.Index(t[start:].strftime("%Y-%m-%d")).unique()
    active = tf.entry_time.dt.tz_convert(NY).dt.strftime("%Y-%m-%d").nunique() if len(tf) else 0
    in_pos = int((tf.exit_bar - tf.entry_bar + 1).sum()) if len(tf) else 0
    p = tf.pnl.to_numpy()
    q = tf.qty.to_numpy()
    commission = float((2 * FEE * q).sum())
    slip_exits = (tf.reason != "Target").to_numpy()
    slippage = float((TICK * PV * q).sum() + (TICK * PV * q * slip_exits).sum())
    closed_dd, marked_dd = drawdowns(bars, tf, start)
    trail = S.trail_stats(name, tf)
    return {"sessions": len(days), "active days": active, "active %": round(100 * active / max(1, len(days)), 1),
            "trades": len(tf), "trades/active day": round(len(tf) / max(1, active), 2),
            "in position %": round(100 * in_pos / max(1, len(bars) - start), 1), "fills": 2 * len(tf),
            "contracts traded": int(q.sum()), "commission $": round(commission), "slippage $": round(slippage),
            "net $": round(float(p.sum())), "expectancy $/trade": round(float(p.mean()), 2) if len(p) else 0.0,
            "expectancy $/contract": round(float(p.sum() / max(1, q.sum())), 2),
            "net win %": round(100 * float((p > 0).mean()), 1) if len(p) else 0.0,
            "profit factor": round(float(p[p > 0].sum() / max(1e-9, -p[p < 0].sum())), 3),
            "closed dd $": round(closed_dd), "marked dd $": round(marked_dd), "eod dd $": trail[f"{name} eoddd"],
            "floor touches": trail[f"{name} tb0"],
            "worst day $": round(float(tf.groupby(tf.exit_time.dt.date).pnl.sum().min())) if len(tf) else 0}


def main() -> None:
    m = int(os.environ.get("SCAN_MINUTES", "5"))
    S.init({}, *sys.argv[1:4])
    rows = []
    for name, (bars, first, skip) in S.D.items():
        for system, kw in (("reference v3.6", REFERENCE), ("candidate T1", CANDIDATE_T1)):
            r = {"bars": f"{m}-min", "data": name, "system": system, **measure(name, bars, first, skip,
                                                                             {**S.V23, **kw}, m)}
            if name == "proxy":
                r.update({"pass net": r["net $"] >= CRITERIA["net"], "pass win": r["net win %"] >= CRITERIA["win"],
                          "pass pf": r["profit factor"] >= CRITERIA["pf"],
                          "pass marked dd": r["marked dd $"] < CRITERIA["marked_dd"]})
                r["accepted"] = all(r[k] for k in ("pass net", "pass win", "pass pf", "pass marked dd"))
            rows.append(r)
            print(r, flush=True)
    pd.DataFrame(rows).to_csv(sys.argv[4], index=False)


if __name__ == "__main__":
    main()
