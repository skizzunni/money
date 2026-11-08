"""G369 (docs/NINJATRADER_V38.md): more trades in regular hours: U57 plus the trend pullback (research/patterns.py
`trendpb`, 3R target, its own position sized to a fixed dollar risk), both in one Test account. The pullback's trades
are added to U57's (two positions can be open at once; the pullback does not see U57's day rules). G253's Test measure
and G364's trade measures.

    SESS=10 python research/g369_add_pullback.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
import patterns as P
from g343_gap_trade import U57
from g367_fade import Res, Tr

VARIANTS = {"U57": None}
for morning in (True, False):
    for risk in (250.0, 500.0):
        VARIANTS[f"U57 + pullback {'to 12:00' if morning else 'to 15:30'}, ${risk:.0f} risk"] = (morning, risk)
_run = G.run


def job(a):
    tag, name, start = a
    box = {}

    def spy(b, cfg, minutes):
        res = _run(b, cfg, minutes=minutes)
        if VARIANTS[tag] is not None:
            morning, risk = VARIANTS[tag]
            P.RISK = risk
            f = P.execute(P.prepare(b, "trendpb"), False, False, morning, 3.0, False)
            pos = {t: k for k, t in enumerate(b.index)}
            extra = [Tr(r.time, r.exit_time, pos[r.time], pos[r.exit_time], int(r.qty), r.entry, int(r.dir), r.pnl)
                     for r in f.itertuples()]
            res = Res(sorted(list(res.trades) + extra, key=lambda t: t.entry_bar))
        box["res"], box["b"] = res, b
        return res

    G.run = spy
    r = G.one((name, start, 4, 1500.0, U57))
    if r is None:
        return None
    s0 = pd.Timestamp(start, tz=G.NY)
    bt = box["b"].index.tz_convert(G.NY)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute) if d >= s0.date() and 570 <= m < 960})[:G.SESS]
    tr = [t for t in box["res"].trades if t.entry_time >= s0 and t.exit_time.tz_convert(G.NY).date() <= days[-1]]
    return {"tag": tag, **r, "n": len(tr), "wins": sum(t.pnl > 0 for t in tr), "pnl": sum(t.pnl for t in tr),
            "days_traded": len({t.entry_time.tz_convert(G.NY).date() for t in tr})}


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    pd.set_option("display.width", 250)
    for label, starts in (("development (index 2011-18)", dev), ("unseen (NQ 2015-25 + index 2019-26)", conf)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            d = pd.DataFrame([r for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts], chunksize=16) if r])
        d["stuck"] = ~d.passed & ~d.failed & (d.room < 500)
        d["failed_or_stuck"] = d.failed | d.stuck
        g = d.groupby("tag")
        out = g.agg(weeks=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"),
                    failed_or_stuck=("failed_or_stuck", "mean"))
        out["win_rate"] = g.wins.sum() / g.n.sum()
        out["trades_per_session"] = g.n.sum() / (out.weeks * G.SESS)
        out["sessions_traded"] = g.days_traded.sum() / (out.weeks * G.SESS)
        out["avg_trade"] = g.pnl.sum() / g.n.sum()
        out["net_per_session"] = g.pnl.sum() / (out.weeks * G.SESS)
        print(label + ":\n" + out.round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
