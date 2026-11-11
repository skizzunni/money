"""docs/V2_STOPS.md, v3: the Test with no time limit (1/2/3 MNQ, noise-only and noise + Williams), PRO survival, and the
expected path at 2 MNQ. Data, costs and marks as research/v2_stops_eval.py.

    PROCS=4 python research/v3_eval.py <data dir>
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import combo_live as W  # noqa: E402
import v2_stops_eval as V  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

TARGET, DD, MIN_DAYS, SESS_PRO = 3000.0, 2000.0, 3, 252
STARTS = pd.date_range("2015-02-02", "2024-07-22", freq="30D")


@dataclass
class Leg:
    entry_bar: int
    exit_bar: int
    qty: int
    direction: int
    entry: float
    exit: float
    pnl: float
    reason: str
    sleeve: str = "noise"


def noise_legs(b, qty, extra=None):
    cfg = NoiseConfig(**{**V.BASE, "qty": qty, **(extra or {})})
    return [Leg(t.entry_bar, t.exit_bar, t.qty, t.direction, t.entry, t.exit, t.pnl, t.reason) for t in run(b, cfg,
        5).trades]


def williams_legs(b, qty):
    """combo_live's breakout at a fixed qty: per contract its points less $1.24 fees, one more tick a side (2 in
    all)."""
    skip = [x for x in V.BASE["skip_dates"].split(",") if x]
    out = []
    for a, x, d, en, ex, _, _ in W.williams_legs(b, month_skip=True, skip_dates=skip):
        pnl = qty * (d * (ex - en) * 2.0 - 1.24 - 2 * 0.25 * 2.0)
        out.append(Leg(a, x, qty, d, en, ex, pnl, "Stop" if pnl < 0 else "16:00 close", "williams"))
    return out


def combine(b, legs, max_losers=4):
    """One position at a time (the first entry owns the account until flat); the day's 4-loser limit counts both."""
    day = np.asarray(b.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    taken, busy = [], -1
    for leg in sorted(legs, key=lambda x: (x.entry_bar, x.exit_bar)):
        d = day[leg.entry_bar]
        done = sum(1 for t in taken if day[t.exit_bar] == d and t.exit_bar < leg.entry_bar and t.pnl < 0)
        if leg.entry_bar > busy and done < max_losers:
            taken.append(leg)
            busy = leg.exit_bar
    return taken


def test_run(day, closed, worst, i0, n):
    """A Test from bar i0 with no expiry: ('pass' | 'fail' | 'open', trading days used, worst EOD drawdown)."""
    eq, peak, dd, days, best, dpnl, cur, sessions = 0.0, 0.0, 0.0, set(), 0.0, 0.0, day[i0], 1
    for k in range(i0, n):
        if day[k] != cur:
            best = max(best, dpnl)
            peak = max(peak, eq)
            dd = max(dd, peak - eq)
            if eq >= TARGET and len(days) >= MIN_DAYS and best < 0.5 * eq:
                return "pass", sessions, dd
            cur, dpnl, sessions = day[k], 0.0, sessions + 1
        floor = min(peak - DD, 0.0)
        if eq + worst[k] <= floor or eq + closed[k] <= floor:
            return "fail", sessions, max(dd, peak - (eq + closed[k]))
        if closed[k] != 0.0:
            days.add(cur)
        eq += closed[k]
        dpnl += closed[k]
    return "open", sessions, dd


def pro_run(day, closed, worst, best, i0, n):
    """PRO from bar i0 for 252 sessions, intraday trail with open profit (worst order), stopping at the start."""
    eq, peak, cur, sessions = 0.0, 0.0, day[i0], 1
    for k in range(i0, n):
        if day[k] != cur:
            cur, sessions = day[k], sessions + 1
            if sessions > SESS_PRO:
                return True, eq
        peak = max(peak, eq + best[k])
        if eq + worst[k] <= min(peak - DD, 0.0) or eq + closed[k] <= min(peak - DD, 0.0):
            return False, eq + min(worst[k], closed[k])
        eq += closed[k]
    return None, eq


def gates(name, b, legs, qty):
    closed, worst, best = V.marks(b, legs)
    day = np.asarray(b.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    res = []
    for s in STARTS:
        i0 = int(np.searchsorted(b.index, s.tz_localize(V.NY)))
        res.append(test_run(day, closed, worst, i0, len(b)))
    p = np.array([x.pnl for x in legs])
    t = b.index.tz_convert(V.NY)
    m = t.hour * 60 + t.minute
    sessions = sorted(set(day[(m >= 570) & (m <= 960)]))
    per_day = p.sum() / len(sessions)
    passed = [r for r in res if r[0] == "pass"]
    return {"set": name, "qty": qty, "starts": len(res), "G1_pass": len(passed) / len(res),
            "fail": sum(r[0] == "fail" for r in res) / len(res), "still_open": sum(r[0] == "open" for r in res),
            "G2_median_days_to_pass": float(np.median([r[1] for r in passed])) if passed else np.nan,
            "G3_worst_dd": max(r[2] for r in res), "G4_pf": p[p > 0].sum() / -p[p < 0].sum(),
            "G5_largest_loss": p.min(), "per_day": per_day, "trades": len(p),
            "williams_trades": sum(x.sleeve == "williams" for x in legs)}


def job(a):
    kind, qty, extra = a
    b = V.load(DATA[0])
    if kind == "noise":
        return gates(f"noise-only, {qty} MNQ", b, noise_legs(b, qty), qty)
    if kind == "combo":
        legs = combine(b, noise_legs(b, qty) + williams_legs(b, qty))
        return gates(f"noise + Williams, {qty} MNQ", b, legs, qty)
    legs = noise_legs(b, 2, extra)  # PRO
    closed, worst, best = V.marks(b, legs)
    day = np.asarray(b.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    out = []
    for s in STARTS:
        i0 = int(np.searchsorted(b.index, s.tz_localize(V.NY)))
        out.append(pro_run(day, closed, worst, best, i0, len(b)))
    done = [o for o in out if o[0] is not None]
    p = np.array([x.pnl for x in legs])
    return {"set": f"PRO, 2 MNQ, daily limit {-extra['dll_v2'] if extra else 'off'}", "starts": len(done),
            "survived_12m": sum(o[0] for o in done) / len(done),
            "median_gain_12m_all": float(np.median([o[1] for o in done])),
            "median_gain_12m_survivors": float(np.median([o[1] for o in done if o[0]])),
            "worst_day": float(pd.Series(p, index=[day[x.exit_bar] for x in legs]).groupby(level=0).sum().min())}


DATA: list = []


def init(d):
    DATA.append(d)


def main() -> None:
    data = sys.argv[1]
    todo = [("noise", q, None) for q in (1, 2, 3)] + [("combo", q, None) for q in (1, 2, 3)]
    todo += [("pro", 2, None)] + [("pro", 2, {"dll_v2": x}) for x in (300.0, 400.0, 500.0)]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=init, initargs=(data,)) as ex:
        rows = list(ex.map(job, todo))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    tests = pd.DataFrame([r for r in rows if "G1_pass" in r])
    pro = pd.DataFrame([r for r in rows if "survived_12m" in r])
    print("The Test, no time limit:\n" + tests.round(3).to_string()
          + "\n\nPRO, 12 months:\n" + pro.round(3).to_string(), flush=True)
    tests.to_csv(Path(data) / "v3_tests.csv", index=False)
    pro.to_csv(Path(data) / "v3_pro.csv", index=False)


if __name__ == "__main__":
    main()
