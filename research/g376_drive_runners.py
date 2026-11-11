"""G376 (docs/NINJATRADER_V38.md): the funded mode (U48) with the trades in the opening drive's direction taking a
farther
take-profit or none (`drive_tp`, `drive_size_k`). when 09:30-10:00 moves
more than k x the average of the last sessions' ranges, entries with that move take a multiple of the contracts and
entries against it another (`drive_size_k`, `drive_mult`, `drive_against_mult`). The measure of G372.

    python research/g376_drive_runners.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import numpy as np
import pandas as pd

from mnqbot.noise import NoiseConfig, run

VARIANTS = {"U48": {}}
for k in (0.25, 0.5):
    for tp in (3.0, 0.0):
        VARIANTS[f"drive past {k}: take-profit {tp or 'none'} with it"] = {"drive_size_k": k, "drive_tp": tp}


def job(a):
    tag, name, start = a
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=372))]
    if b.index[-1] < s0 + pd.Timedelta(days=360):
        return None
    cfg = NoiseConfig(**{**G.S.V23, **G.T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE, **VARIANTS[tag]})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    bt = b.index.tz_convert(G.NY)
    bd = np.array(bt.date)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute,
        strict=False) if d >= s0.date() and 570 <= m < 960})
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    adv, closed = np.zeros(len(b)), np.zeros(len(b))
    pnl = {d: 0.0 for d in days}
    for t in res.trades:
        d = t.exit_time.tz_convert(G.NY).date()
        if t.entry_time < s0 or d not in pnl:
            continue
        sl = slice(t.entry_bar + 1, t.exit_bar + 1)
        adv[sl] += t.qty * ((lo[sl] - t.entry) if t.direction > 0 else (t.entry - hi[sl])) * G.PV
        closed[t.exit_bar] += t.pnl
        pnl[d] += t.pnl
    before = np.r_[0.0, np.cumsum(closed)[:-1]]
    eod, peak, lost, rows = 0.0, 0.0, False, []
    for d in days:
        fl = min(peak - G.DD, 0.0)
        m = bd == d
        lost = lost or bool((before[m] + adv[m] <= fl).any() or (before[m] + closed[m] <= fl).any())
        eod += pnl[d]
        peak = max(peak, eod)
        month = (pd.Timestamp(d).year - s0.year) * 12 + pd.Timestamp(d).month - s0.month + 1
        if month <= 12:
            rows.append({"tag": tag, "set": name, "start": start, "month": month, "pnl": 0.0 if lost else pnl[d],
                         "lost": lost})
    return rows


def table(d):
    g = d.groupby("tag")
    out = pd.DataFrame({"per_session": g.pnl.mean(),
                        "months_1_3": d[d.month <= 3].groupby("tag").pnl.mean(),
                        "months_10_12": d[d.month >= 10].groupby("tag").pnl.mean(),
                        "best_month": d.groupby(["tag", "month"]).pnl.mean().groupby("tag").max(),
                        "lost": d[d.month == 12].groupby("tag").lost.mean()})
    return out.sort_values("per_session", ascending=False)


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    dev = [("index", mon(d)) for d in pd.date_range("2011-04-01", "2018-10-01", freq="QS")]
    unseen = [("index", mon(d)) for d in pd.date_range("2019-01-01", "2025-07-01", freq="QS")]
    unseen += [("nq", mon(d)) for d in pd.date_range("2015-04-01", "2024-07-01", freq="QS")]
    pd.set_option("display.width", 250)
    for label, starts in (("development (index 2011-18 starts)", dev), ("unseen (index 2019-25 + NQ 2015-24)", unseen)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            rows = [x for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts]) if r for x in r]
        print(label + ":\n" + table(pd.DataFrame(rows)).round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
