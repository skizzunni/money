"""G370 (docs/NINJATRADER_V38.md): U57 plus G368's fade (target 0.15 noise, stop past the day's extreme) at 1 or 2 MNQ,
its trades kept only where U57 has no position open between the fade's entry and exit. G253's Test measure and G364's
trade measures, plus the net a session.

    SESS=10 python research/g370_u57_plus_fade.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import g250_test_week as G
import g368_fade_levels as F
from g343_gap_trade import U57
from g367_fade import Res

VARIANTS = {"U57": None, "U57 + fade at 1 MNQ": 1, "U57 + fade at 2 MNQ": 2}
_run = G.run


def job(a):
    tag, name, start = a
    box = {}

    def spy(b, cfg, minutes):
        res = _run(b, cfg, minutes=minutes)
        if VARIANTS[tag]:
            F.P.clear()
            F.P.update({"tp": 0.15, "sl": "extreme", "entry_k": 0.7, "lookback": 18, "qty": VARIANTS[tag], "max_trades": 4})
            busy = [(t.entry_bar, t.exit_bar) for t in res.trades]
            fade = [t for t in F.fade_run(b, cfg, minutes).trades
                    if not any(e <= t.exit_bar and t.entry_bar <= x for e, x in busy)]
            res = Res(sorted(list(res.trades) + fade, key=lambda t: t.entry_bar))
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


if __name__ == "__main__":
    import g369_add_pullback as M
    M.VARIANTS, M.job = VARIANTS, job
    M.main()
