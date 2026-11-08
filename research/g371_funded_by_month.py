"""G371 (docs/NINJATRADER_V38.md): a measurement. The funded account's growth mode (U48's settings, the file's default
mode: 50K, $2,000 end-of-day trailing floor, $900 daily loss, 60-minute time stop, sizes growing with the account)
from a fresh start on the first Monday of every quarter, run 12 months. Per month since the start: $ per session (all
sessions), and the share of starts whose floor has been touched by then.

    python research/g371_funded_by_month.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import g250_test_week as G
from mnqbot.noise import NoiseConfig, run


def job(a):
    name, start = a
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=372))]
    if b.index[-1] < s0 + pd.Timedelta(days=360):
        return None
    cfg = NoiseConfig(**{**G.S.V23, **G.T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    bt = b.index.tz_convert(G.NY)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute) if d >= s0.date() and 570 <= m < 960})
    pnl = {d: 0.0 for d in days}
    for t in res.trades:
        d = t.exit_time.tz_convert(G.NY).date()
        if t.entry_time >= s0 and d in pnl:
            pnl[d] += t.pnl
    eod, peak, touched, rows = 0.0, 0.0, False, []
    for d in days:
        eod += pnl[d]
        touched = touched or eod <= min(peak - G.DD, 0.0)
        peak = max(peak, eod)
        month = (pd.Timestamp(d).year - s0.year) * 12 + pd.Timestamp(d).month - s0.month + 1
        if month <= 12:
            rows.append({"set": name, "start": start, "month": month, "pnl": pnl[d], "touched": touched})
    return rows


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    starts = [("index", d) for d in pd.date_range("2011-04-01", "2025-07-01", freq="QS")]
    starts += [("nq", d) for d in pd.date_range("2015-04-01", "2024-07-01", freq="QS")]
    starts = [(n, (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")) for n, d in starts]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        rows = [x for r in ex.map(job, starts) if r for x in r]
    d = pd.DataFrame(rows)
    out = d.groupby("month").agg(per_session=("pnl", "mean"), median_day=("pnl", "median"),
                                 days_750=("pnl", lambda x: (x >= 750).mean()), touched=("touched", "mean"))
    print(f"{d.groupby(['set', 'start']).ngroups} starts\n" + out.round(3).to_string())
    for s in ("index", "nq"):
        print(s, "per session over 12 months", round(d[d.set == s].pnl.mean(), 1))


if __name__ == "__main__":
    main()
