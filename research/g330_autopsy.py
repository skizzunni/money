"""G330 (docs/NINJATRADER_V38.md): why U56's Tests fail. A measurement on the development weeks only (the index's
Monday starts 2011-18): for each failed two-week Test, its trades from the start to the failure, by exit reason, by
trade type (the bot or the 09:35 gap trade), by the day of the Test and by how the floor was reached.

    SESS=10 python research/g330_autopsy.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import sys

import pandas as pd
import g250_test_week as G
import t1_eval as T
from g321b_confirm import U56

from mnqbot.noise import NoiseConfig, run

NY = "America/New_York"


def trades_of(name, start):
    bars, _, skip = G.S.D[name]
    s0 = pd.Timestamp(start, tz=NY)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s0 + pd.Timedelta(days=21))]
    extra = dict(U56)
    cfg = NoiseConfig(**{**G.S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": G.DD, "time_stop": 60,
                         **G.BASE, "daily_loss_limit": 2000.0, "early_daily_loss": 0.0, **extra})
    cfg.sprint_qty, cfg.sprint_days, cfg.sprint_target = 4, 10, extra.get("sprint_target", 3000.0)
    cfg.day_stop_profit = 1500.0
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=G.S.MIN[0])
    return [t for t in res.trades if t.entry_time >= s0]


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    G.SESS = 10
    dev = [d.strftime("%Y-%m-%d") for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    rows, days = [], []
    for s in dev:
        r = G.one(("index", s, 4, 1500.0, U56))
        if not r or not r["failed"]:
            continue
        tr = trades_of("index", s)
        fd = r["fail day"]
        tdays = sorted({t.exit_time.tz_convert(NY).date() for t in tr})
        bydate = {}
        for t in tr:
            d = t.exit_time.tz_convert(NY).date()
            bydate[d] = bydate.get(d, 0.0) + t.pnl
        last = sorted(bydate)[:fd] if bydate else []
        for t in tr:
            d = t.exit_time.tz_convert(NY).date()
            if last and d > last[-1]:
                continue
            gap = t.reason.startswith("Gap")
            rows.append({"start": s, "kind": "gap" if gap else "bot", "reason": t.reason, "pnl": t.pnl, "qty": t.qty,
                         "hour": t.entry_time.tz_convert(NY).hour, "dir": t.direction})
        worst = min(bydate.values()) if bydate else 0
        days.append({"start": s, "fail day": fd, "worst day": round(worst), "losing days": sum(v < 0 for v in bydate.values()),
                     "net": round(sum(v for d, v in bydate.items() if not last or d <= last[-1]))})
    t = pd.DataFrame(rows)
    d = pd.DataFrame(days)
    print(f"failed Tests: {len(d)} of {len(dev)} development weeks")
    print("\nby exit reason (the trades up to the failure):\n" + t.groupby("reason").pnl.agg(["count", "sum", "mean"]).round(0).sort_values("sum").to_string())
    print("\nbot vs gap trade:\n" + t.groupby("kind").pnl.agg(["count", "sum"]).round(0).to_string())
    print("\nby entry hour:\n" + t.groupby("hour").pnl.agg(["count", "sum", "mean"]).round(0).to_string())
    print("\nby side:\n" + t.groupby("dir").pnl.agg(["count", "sum", "mean"]).round(0).to_string())
    print("\nthe failed Tests:\n" + d.describe().round(0).to_string())
    print("\nworst single day below -$1,000 in", int((d["worst day"] <= -1000).sum()), "of", len(d))


if __name__ == "__main__":
    main()
