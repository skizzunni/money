"""G363 (docs/NINJATRADER_V38.md): a measurement. U57's trades in each two-week Test: the share of winners, trades a
session, the average winner and loser. All 10 sessions of each start (not cut at the pass or fail).

    SESS=10 python research/g363_win_rate.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import g250_test_week as G
import pandas as pd
from g343_gap_trade import U57

VARIANTS = {"U57": (U57, 1500.0, 4)}
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
        return []
    s0 = pd.Timestamp(start, tz=G.NY)
    bt = box["b"].index.tz_convert(G.NY)
    days = sorted({d for d, m in zip(bt.date, bt.hour * 60 + bt.minute,
        strict=False) if d >= s0.date() and 570 <= m < 960})[:G.SESS]
    return [{"tag": tag, "set": name, "start": start, "pnl": t.pnl, "qty": t.qty}
            for t in box["res"].trades if t.entry_time >= s0 and t.exit_time.tz_convert(G.NY).date() <= days[-1]]


def main() -> None:
    G.S.init({}, *sys.argv[1:4])
    G.S.D = {k: (G.with_1600(b, G.S.MIN[0]), f, s) for k, (b, f, s) in G.S.D.items() if k != "win"}
    G.BASE.update(json.load(open(sys.argv[4])))
    dev = [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-04", "2018-12-31", freq="W-MON")]
    conf = [("nq", d.strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-06", "2025-06-30", freq="W-MON")]
    conf += [("index", d.strftime("%Y-%m-%d")) for d in pd.date_range("2019-01-07", "2026-08-31", freq="W-MON")]
    for label, starts in (("development (index 2011-18)", dev), ("unseen (NQ 2015-25 + index 2019-26)", conf)):
        with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
            rows = [x for r in ex.map(job, [(t, n, s) for t in VARIANTS for n, s in starts], chunksize=16) for x in r]
        d = pd.DataFrame(rows)
        n_tests = len({(r["set"], r["start"]) for r in rows})
        out = d.groupby("tag").agg(trades=("pnl", "size"), win_rate=("pnl", lambda x: (x > 0).mean()),
                                   avg_win=("pnl", lambda x: x[x > 0].mean()), avg_loss=("pnl",
                                       lambda x: x[x <= 0].mean()),
                                   avg_trade=("pnl", "mean"))
        out["trades_per_session"] = out.trades / (n_tests * G.SESS)
        print(label + f" ({n_tests} Tests):\n" + out.round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
