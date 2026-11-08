"""G364 (docs/NINJATRADER_V38.md): U57 with small take-profits and wider stops, for a high share of winners. Per
variant: the Tests' passed / failed / near-frozen (G253's measure) and, over all 10 sessions of each Test, the share of
winning trades, trades a session, the share of sessions with a trade, and the average trade.

    SESS=10 python research/g364_win_rate_grid.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
from g343_gap_trade import U57

VARIANTS = {"U57": (U57, 1500.0, 4)}
for tp in (0.1, 0.15, 0.2, 0.3):
    for sb in (0.24, 0.5):
        for mf in (1.0, 1.5):
            VARIANTS[f"tp {tp} / stop buffer {sb} / max loss {mf}x"] = (
                {**U57, "take_profit": tp, "stop_buffer": sb, "max_loss_frac": mf}, 1500.0, 4)
_run = G.run


def job(a):
    tag, name, start = a
    settings, ds, sq = VARIANTS[tag]
    box = {}

    def spy(b, cfg, minutes):
        res = _run(b, cfg, minutes=minutes)
        box["res"], box["b"] = res, b
        return res

    G.run = spy
    r = G.one((name, start, sq, ds, settings))
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
        g = d.groupby("tag")
        out = g.agg(weeks=("passed", "size"), passed=("passed", "mean"), failed=("failed", "mean"), stuck=("stuck", "mean"))
        out["win_rate"] = g.wins.sum() / g.n.sum()
        out["trades_per_session"] = g.n.sum() / (out.weeks * G.SESS)
        out["sessions_traded"] = g.days_traded.sum() / (out.weeks * G.SESS)
        out["avg_trade"] = g.pnl.sum() / g.n.sum()
        print(label + ":\n" + out.round(3).sort_values("win_rate", ascending=False).to_string(), flush=True)


if __name__ == "__main__":
    main()
