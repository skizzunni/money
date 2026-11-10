"""docs/V2_STOPS.md, Phase 4: the v1.5 rules at a fixed 2 MNQ, v1.5 stops against the v2 stops, on NQ 2015-2025 (5-minute,
back-adjusted, rescaled), as consecutive 30-day $50K evaluations under Take Profit Trader's Test rules, end-of-day and
intraday trailing. Also the tight-stop grid and the lock / cap separation (reported, not selected on).

    PROCS=4 python research/v2_stops_eval.py <data dir> <out.csv> [part]

part: "gates" (v1.5 + the 12 v2 variants), "grid" (cap x buffer), "sep" (the separation), "qty" (QTY_OF=<variant
name> at 1, 2, 3, 5, 8 MNQ), or "all" (the first three). The engine is mnqbot.noise.run with its defaults (the model
MnqNoiseEngine.cs matches trade for trade); costs $0.62 a side, 2 ticks on market and stop fills.
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

NY = "America/New_York"
TARGET, DD, MIN_DAYS, PV = 3000.0, 2000.0, 5, 2.0
FOMC = ",".join(pd.read_csv(Path(__file__).parent / "fomc_dates.csv").date)
BASE = {"qty": 2, "slippage_ticks": 2, "fed_dates": FOMC}  # skip_dates: the closures and data holes (load)
V2 = {"lock_noise": 0.75, "tighten_only": True}

GATES = {"v1.5 stops": {}}
for dll in (300.0, 400.0, 500.0):
    for buf in (0.24, 0.35):
        for gap in (True, False):
            GATES[f"v2, limit -{dll:.0f}, buffer {buf}, gap guard {'on' if gap else 'off'}"] = {
                **V2, "dll_v2": dll, "stop_buffer": buf, "gap_guard": gap}
GRID = {f"cap ${cap:.0f}, buffer {buf}": {"max_loss_per_trade": cap, "stop_buffer": buf}
        for cap in (100.0, 200.0, 350.0) for buf in (0.10, 0.24, 0.35)}
SEP = {}
for cap in (100.0, 200.0, 350.0):
    SEP[f"cap ${cap:.0f}, lock 0.75 noise"] = {"max_loss_per_trade": cap, "lock_noise": 0.75}
for cap in (100.0, 200.0, 350.0):  # v1.5's lock at 1 max loss of a $cap cap, with the cap at $350
    SEP[f"cap $350, lock at {cap / 2:.1f} points"] = {"max_loss_per_trade": 350.0, "lock_at": cap / 350.0}
B: dict = {}


def load(data: str) -> pd.DataFrame:
    """NQ as every NQ result here: bad bars dropped; US closures, half days and sessions with missing data skipped (a
    trade there would be held to the next session, across the monthly rescaling); a 16:00 bar added where missing."""
    b = S.drop_bad(pd.read_pickle(Path(data) / "nq5m_scaled.pkl")[["open", "high", "low", "close", "volume"]])
    t = b.index.tz_convert(NY)
    g = pd.DataFrame({"d": t.strftime("%Y-%m-%d"), "m": t.hour * 60 + t.minute}).groupby("d").m.agg(["count", "min", "max"])
    holes = g[(g["max"] < 955) | (g["min"] > 570) | (g["count"] < 70)].index
    BASE["skip_dates"] = S.CLOSURES + "," + ",".join(holes)
    m = t.hour * 60 + t.minute
    last = (m + 5 == 960) & ~pd.Series(m == 960).shift(-1, fill_value=False).to_numpy()  # a 16:00 bar where missing
    add = b[last].copy()
    add.index = add.index + pd.Timedelta(minutes=5)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([b, add]).sort_index()


def marks(b: pd.DataFrame, trades) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per bar: the closed P/L booked at it, and the open trade's P/L at the bar's worst and best prices (round-trip
    fees taken), bounded by the exit price on the exit bar of a stop (worst) or a target (best)."""
    o, h, lo = (b[x].to_numpy() for x in ("open", "high", "low"))
    n = len(b)
    closed, worst, best = np.zeros(n), np.zeros(n), np.zeros(n)
    for t in trades:
        q, d, e = t.qty, t.direction, t.entry
        fee = t.pnl - d * (t.exit - e) * q * PV
        for k in range(t.entry_bar, t.exit_bar + 1):
            wp, bp = (lo[k], h[k]) if d > 0 else (h[k], lo[k])
            if k == t.exit_bar:
                if t.reason not in ("Target", "16:00 close", "Session ended"):
                    wp = max(wp, t.exit) if d > 0 else min(wp, t.exit)
                if t.reason == "Target":
                    bp = min(bp, t.exit) if d > 0 else max(bp, t.exit)
            if k == t.entry_bar:
                wp = min(wp, o[k]) if d > 0 else max(wp, o[k])
            worst[k] += d * (wp - e) * q * PV + fee
            best[k] += d * (bp - e) * q * PV + fee
        closed[t.exit_bar] += t.pnl
    return closed, worst, best


def evaluate(day_of_bar, closed, worst, best, i0, i1, intraday: bool) -> tuple[str, float]:
    """One evaluation over bars i0..i1-1: ('pass' | 'fail' | 'expiry', its end-of-day drawdown until the outcome)."""
    eq, peak_eod, peak_mark, dd, days, best_day = 0.0, 0.0, 0.0, 0.0, set(), 0.0
    day_pnl, cur = 0.0, day_of_bar[i0]
    for k in range(i0, i1):
        if day_of_bar[k] != cur:  # the day's end
            if day_pnl != 0.0 or cur in days:
                best_day = max(best_day, day_pnl)
            peak_eod = max(peak_eod, eq)
            dd = max(dd, peak_eod - eq)
            if eq >= TARGET and len(days) >= MIN_DAYS and best_day < 0.5 * eq:
                return "pass", dd
            cur, day_pnl = day_of_bar[k], 0.0
        if intraday:
            peak_mark = max(peak_mark, eq + best[k])  # the worst order: the bar's best mark first
            floor = min(peak_mark - DD, 0.0)
        else:
            floor = min(peak_eod - DD, 0.0)
        if eq + worst[k] <= floor or eq + closed[k] <= floor:
            return "fail", max(dd, peak_eod - (eq + closed[k]))
        if closed[k] != 0.0:
            days.add(cur)
        eq += closed[k]
        day_pnl += closed[k]
    best_day = max(best_day, day_pnl)
    peak_eod = max(peak_eod, eq)
    dd = max(dd, peak_eod - eq)
    if eq >= TARGET and len(days) >= MIN_DAYS and best_day < 0.5 * eq:
        return "pass", dd
    return "expiry", dd


def job(a):
    name, extra = a
    b = B["bars"]
    cfg = NoiseConfig(**{**BASE, **extra})
    res = run(b, cfg, minutes=5)
    tr = res.trades
    closed, worst, best = marks(b, tr)
    t = b.index.tz_convert(NY)
    day = np.asarray(t.strftime("%Y-%m-%d"))
    m = t.hour * 60 + t.minute
    rth = (m >= 570) & (m <= 960)
    sessions = sorted(set(day[rth]))
    out = {"variant": name, "qty": cfg.qty}
    starts = pd.date_range("2015-02-02", "2025-07-24", freq="30D")
    for intraday in (False, True):
        res_w, dds = [], []
        for s in starts:
            e = s + pd.Timedelta(days=30)
            i0 = int(np.searchsorted(b.index, s.tz_localize(NY)))
            i1 = int(np.searchsorted(b.index, e.tz_localize(NY)))
            if i1 <= i0 or b.index[-1] < e.tz_localize(NY):
                continue
            o, dd = evaluate(day, closed, worst, best, i0, i1, intraday)
            res_w.append(o)
            dds.append(dd)
        k = "intraday" if intraday else "eod"
        n = len(res_w)
        out[f"{k}_windows"] = n
        out[f"{k}_pass"] = sum(x == "pass" for x in res_w) / n
        out[f"{k}_fail"] = sum(x == "fail" for x in res_w) / n
        out[f"{k}_expiry"] = sum(x == "expiry" for x in res_w) / n
        out[f"{k}_worst_dd"] = max(dds)
    p = np.array([x.pnl for x in tr])
    out["trades"] = len(p)
    out["win_rate"] = float((p > 0).mean())
    out["pf"] = float(p[p > 0].sum() / -p[p < 0].sum())
    out["largest_loss"] = float(p.min())
    cap = cfg.max_loss_per_trade
    out["losses_past_cap_50"] = int((p < -(cap + 50)).sum()) if cap > 0 else 0
    by_day = pd.Series(0.0, index=sessions).add(pd.Series(p, index=[x.exit_time.tz_convert(NY).strftime("%Y-%m-%d")
                                                                    for x in tr]).groupby(level=0).sum(), fill_value=0)
    eq = by_day.cumsum().to_numpy()
    mdd = float((np.maximum.accumulate(np.r_[0.0, eq])[1:] - eq).max())
    out["per_day_per_contract"] = float(by_day.mean()) / cfg.qty
    out["max_dd_per_contract"] = mdd / cfg.qty
    out["profit_dd"] = float(by_day.sum()) / mdd
    out["worst_day_per_contract"] = float(by_day.min()) / cfg.qty
    out["per_day"] = float(by_day.mean())
    out["max_dd"] = mdd
    out["reasons"] = ";".join(f"{r}:{n}" for r, n in pd.Series([x.reason for x in tr]).value_counts().items())
    return out


def init(data):
    B["bars"] = load(data)  # also sets BASE["skip_dates"] in this worker


def main() -> None:
    data, out, part = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "all")
    sets = {"gates": GATES, "grid": GRID, "sep": SEP}
    if part == "qty":
        src = {**GATES, **GRID, **SEP}[os.environ["QTY_OF"]]
        todo = {f"{os.environ['QTY_OF']} at {q} MNQ": {**src, "qty": q} for q in (1, 2, 3, 5, 8)}
    else:
        todo = {k: v for p in (sets if part == "all" else [part]) for k, v in sets[p].items()}
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=init, initargs=(data,)) as ex:
        rows = list(ex.map(job, todo.items()))
    d = pd.DataFrame(rows)
    d.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(d.drop(columns=["reasons"]).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
