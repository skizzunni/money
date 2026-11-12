"""G489 (docs/NINJATRADER_V38.md), a measurement: what Funded green days' (G481) red days are made of, on G415's fresh
starts. Each traded day is classed by its closed trades: its trade count, whether its first trade lost, whether any
trade was ever up its lock trigger (lock_at x its max loss), whether the day's closed P/L was above $0 before it closed
red, and the entry minute of its first trade (09:35 gap slot or a check).

    python research/g489_red_day_anatomy.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd
from g423_wide_when_wild import U58

from mnqbot.noise import NoiseConfig, run

GD = {**U58, "giveback_brake": 0.25, "day_stop_late_from": 660, "day_stop_late": 1.0}


def job(a):
    name, start = a
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=372))]
    if b.index[-1] < s0 + pd.Timedelta(days=360):
        return []
    cfg = NoiseConfig(**{**G.S.V23, **G.T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE, **GD})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    days = {}
    for t in res.trades:
        if t.entry_time < s0 or t.entry_time >= s0 + pd.Timedelta(days=365):
            continue
        d = t.exit_time.tz_convert(G.NY).date()
        sl = slice(t.entry_bar, t.exit_bar + 1)
        fav = (hi[sl].max() - t.entry) if t.direction > 0 else (t.entry - lo[sl].min())
        et = t.entry_time.tz_convert(G.NY)
        days.setdefault(d, []).append((t.pnl, fav, et.hour * 60 + et.minute, t.reason))
    rows = []
    for _, ts in days.items():
        cum, up = 0.0, False
        for p, *_ in ts[:-1]:
            cum += p
            up = up or cum > 0
        tot = sum(p for p, *_ in ts)
        rows.append({"green": tot > 0, "n": len(ts), "first_lost": ts[0][0] <= 0, "best_fav": max(x[1] for x in ts),
                     "was_up": up, "gap_first": ts[0][2] < 600, "first_reason": ts[0][3]})
    return rows


if __name__ == "__main__":
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    mon = lambda d: (d + pd.offsets.Week(weekday=0)).strftime("%Y-%m-%d")  # noqa: E731
    fresh = [("nq", mon(d)) for d in pd.date_range("2023-01-01", "2024-04-01", freq="QS")]
    fresh += [("index", mon(d)) for d in pd.date_range("2024-01-01", "2025-07-01", freq="QS")]
    fresh += [("proxy", mon(d)) for d in pd.date_range("2025-04-01", "2025-10-01", freq="QS")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        d = pd.DataFrame([x for r in ex.map(job, fresh) for x in r])
    print(f"traded days: {len(d)}, green {d.green.mean():.1%}")
    r = d[~d.green]
    print(f"red days: {len(r)}")
    for k, v in {"one trade only": r.n == 1, "first trade lost": r.first_lost,
                 "first trade in the 09:35 gap slot": r.gap_first, "closed P/L above $0 before it closed red": r.was_up,
                 "no trade ever 10+ points its way": r.best_fav < 10,
                 "no trade ever 20+ points its way": r.best_fav < 20,
                 "a trade was 40+ points its way": r.best_fav >= 40}.items():
        print(f"  {k}: {v.mean():.1%}")
    print("  first trade's exit:", (r.first_reason.value_counts(normalize=True).round(3)).to_dict())
    g = d[d.green]
    print(f"green days: {len(g)}; one trade only {(g.n == 1).mean():.1%}; first trade in the gap slot "
          f"{g.gap_first.mean():.1%}; first trade lost {g.first_lost.mean():.1%}")
    print("  first trade's exit:", (g.first_reason.value_counts(normalize=True).round(3)).to_dict())
    print("by trade count (share green):", d.groupby("n").green.agg(["mean", "size"]).round(3).to_dict("index"))
