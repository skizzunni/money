"""G250 (docs/NINJATRADER_V38.md): Take Profit Trader's 50K Test in one week. A measurement.

A fresh Test started every Monday (NQ 2015-25, the index 2011-26), 5 sessions. The rules (TPT help center, 2026-11):
+$3,000 to pass with the best day under 50% of the profit and at least 3 trading days; a $2,000 trailing floor from
the highest end-of-day balance, stopping at the start, which fails the Test when the balance touches it at any time,
open losses included (each open trade marked at its bars' worst prices); no daily loss limit; at most 60 MNQ.
U48 with `sprint_qty` (every trade at that size in the first 5 sessions until +$3,000, cut to the room above the
floor) and the day's budget at $2,000 (none in effect: the floor's room binds first).

    SPRINTS=0,5,10,15,20 python research/g250_test_week.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import t1_eval as T
import v24_scan as S

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"
DD, TARGET, PV = 2000.0, 3000.0, 2.0
SESS = int(os.environ.get("SESS", "5"))  # G251: 10 (two weeks)
BASE: dict = {}


def with_1600(bars: pd.DataFrame, m: int) -> pd.DataFrame:
    t = bars.index.tz_convert(NY)
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    for k in ("open", "high", "low"):
        add[k] = add["close"]
    return pd.concat([bars, add]).sort_index()


def one(job):
    name, start, sq, ds = job
    bars, _, skip = S.D[name]
    s0 = pd.Timestamp(start, tz=NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=7 + 7 * ((SESS + 4) // 5)))]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": DD, "time_stop": 60,
                         **BASE, "daily_loss_limit": 2000.0, "early_daily_loss": 0.0})
    if sq:
        cfg.sprint_qty, cfg.sprint_days, cfg.sprint_target = sq, SESS, TARGET
    cfg.day_stop_profit = ds  # G251: no new entries once the day is up this much (0 = off)
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=S.MIN[0])
    bt = b.index.tz_convert(NY)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute) if d >= s0.date() and 570 <= m < 960})[:SESS]
    if len(days) < SESS:
        return None
    last = days[-1]
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    adv = np.zeros(len(b))
    closed = np.zeros(len(b))
    day_pnl = {d: 0.0 for d in days}
    for t in res.trades:
        if t.entry_time < s0 or t.exit_time.tz_convert(NY).date() > last:
            continue
        sl = slice(t.entry_bar + 1, t.exit_bar + 1)
        adv[sl] += t.qty * ((lo[sl] - t.entry) if t.direction > 0 else (t.entry - hi[sl])) * PV
        closed[t.exit_bar] += t.pnl
        day_pnl[t.exit_time.tz_convert(NY).date()] += t.pnl
    before = np.r_[0.0, np.cumsum(closed)[:-1]]
    # the floor: the highest end-of-day balance so far less $2,000, at most the start
    eod, peak, floor_by_day = 0.0, 0.0, {}
    for d in days:
        floor_by_day[d] = min(peak - DD, 0.0)
        eod += day_pnl[d]
        peak = max(peak, eod)
    bd = np.array([d for d in bt.date])
    failed = passed = False
    fail_day = pass_day = None
    cum, best, traded = 0.0, 0.0, 0
    for d in days:
        m = bd == d
        fl = floor_by_day[d]
        if (before[m] + adv[m] <= fl).any() or (before[m] + closed[m] <= fl).any():
            failed, fail_day = True, days.index(d) + 1
            break
        cum += day_pnl[d]
        traded += day_pnl[d] != 0
        best = max(best, day_pnl[d])
        if cum >= TARGET and best < 0.5 * cum and traded >= 3:
            passed, pass_day = True, days.index(d) + 1
            break
    return {"set": name, "start": start, "sprint": sq, "day stop": ds, "passed": passed, "failed": failed, "pass day": pass_day,
            "fail day": fail_day, "net": round(cum)}


def main() -> None:
    S.init({}, *sys.argv[1:4])
    S.D = {k: (with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items() if k != "win"}
    BASE.update(json.load(open(sys.argv[4])))
    sprints = [int(x) for x in os.environ.get("SPRINTS", "0,5,10,15,20").split(",")]
    starts = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    starts += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2026-08-31", freq="W-MON")]
    stops = [float(x) for x in os.environ.get("DAYSTOPS", "0").split(",")]
    jobs = [(n, s, q, ds) for q in sprints for ds in stops for n, s in starts]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        rows = [r for r in ex.map(one, jobs, chunksize=8) if r]
    d = pd.DataFrame(rows)
    d.to_csv(f"verification/noise_v2/g25{0 if SESS == 5 else 1}_test_{SESS}sessions.csv", index=False)
    for (q, ds, n), g in d.groupby(["sprint", "day stop", "set"]):
        print(f"sprint {q:>2} day stop {ds:>6.0f} {n:>5}: weeks {len(g)}, passed {100 * g.passed.mean():.1f}%, failed "
              f"{100 * g.failed.mean():.1f}%, still open {100 * (~g.passed & ~g.failed).mean():.1f}%, "
              f"median week ${int(g.net.median())}", flush=True)


if __name__ == "__main__":
    main()
