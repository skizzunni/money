"""G368 (docs/NINJATRADER_V38.md): G367's fade with the stop past the day's extreme or the target at the day's open
(`stop` "extreme": the day's high (short) / low (long) so far + 0.1 noise; `tp` "open": the session's 09:30 open, when it
lies the target's way, else 0.3 noise). G367 docstring follows.

G367: a new strategy for a high win rate, the failed-breakout fade.

At a 30-minute check (10:00-15:30, the bar closing then), after the previous check closed past the noise area's entry
line (U57's: the paper's area at entry width 0.7 over 18 sessions) and this check closes back inside it, the bot fades
the failed breakout: short after a failed upside one, long after a failed downside one, at the next bar's open. Target:
tp_k x the check's noise (sigma x the close) away; stop: sl_k x the noise on the other side; out at 16:00 otherwise.
One position at a time, at most max_trades a day, no new entry once the day is up $1,500 or down $1,200 (closed).
4 MNQ, $0.62 a side a contract, 1 tick of slippage on market and stop fills (none on the target's limit); if a bar
reaches both the stop and the target, the stop (the worse case). G253's two-week Test measure (via g250_test_week.one,
its trades in place of the noise bot's) and G364's trade measures.

    SESS=10 python research/g368_fade_levels.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
import g250_test_week as G

PV, FEE, TICK = 2.0, 0.62, 0.25
CHECKS = list(range(600, 931, 30))  # bar end minutes 10:00 .. 15:30
VARIANTS = {}
for tp in (0.15, 0.3, "open"):
    for sl in (1.0, "extreme"):
        VARIANTS[f"fade, target {tp} / stop {sl}"] = {"tp": tp, "sl": sl, "entry_k": 0.7, "lookback": 18,
                                                      "qty": 4, "max_trades": 4}
P = {}


@dataclass
class Tr:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_bar: int
    exit_bar: int
    qty: int
    entry: float
    direction: int
    pnl: float


class Res:
    def __init__(self, trades):
        self.trades = trades


def fade_run(b, cfg, minutes=5):
    p = P
    t = b.index.tz_convert(G.NY)
    mins = t.hour.to_numpy() * 60 + t.minute.to_numpy() + minutes  # bar end minute
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    dates = t.date
    trades = []
    hist = []  # per past session: {check: |close / open - 1|}
    prev_close = math.nan
    i, n = 0, len(b)
    while i < n:
        d = dates[i]
        j = i
        while j < n and dates[j] == d:
            j += 1
        day = range(i, j)
        rth = [k for k in day if 570 < mins[k] <= 965]
        if not rth:
            i = j
            continue
        day_open = o[rth[0]]
        moves = {}
        for k in rth:
            if mins[k] in CHECKS:
                moves[mins[k]] = abs(c[k] / day_open - 1)
        ok = len(hist) >= p["lookback"] and not math.isnan(prev_close)
        if ok:
            sig = {m: np.mean([hh[m] for hh in hist[-p["lookback"]:] if m in hh] or [np.nan]) for m in CHECKS}
            up_base, lo_base = max(day_open, prev_close), min(day_open, prev_close)
            prev_side = 0
            dhi = dlo = math.nan
            pos, day_pnl, n_tr = 0, 0.0, 0
            entry = tgt = stp = 0.0
            ebar = 0
            pending = None
            for k in rth:
                m = mins[k]
                if pending is not None and pos == 0:  # fill at this bar's open
                    dirn, s_px = pending
                    pending = None
                    entry = o[k] + dirn * TICK  # a market fill, 1 tick worse
                    pos, ebar = dirn, k
                    if p["tp"] == "open" and (day_open - entry) * dirn > 0:
                        tgt = day_open
                    else:
                        tgt = entry + dirn * (0.3 if p["tp"] == "open" else p["tp"]) * s_px
                    if p["sl"] == "extreme":
                        stp = (dlo - 0.1 * s_px) if dirn > 0 else (dhi + 0.1 * s_px)
                        if (entry - stp) * dirn <= 0:  # the open is already past it: no trade
                            pos = 0
                    else:
                        stp = entry - dirn * p["sl"] * s_px
                dhi = h[k] if math.isnan(dhi) else max(dhi, h[k])
                dlo = l[k] if math.isnan(dlo) else min(dlo, l[k])
                if pos:
                    hit_stop = l[k] <= stp if pos > 0 else h[k] >= stp
                    hit_tgt = h[k] >= tgt if pos > 0 else l[k] <= tgt
                    px = None
                    if hit_stop:
                        gap = o[k] < stp if pos > 0 else o[k] > stp
                        px = (o[k] if gap else stp) - pos * TICK
                    elif hit_tgt:
                        gap = o[k] > tgt if pos > 0 else o[k] < tgt
                        px = o[k] if gap else tgt
                    elif m >= 960:
                        px = c[k] - pos * TICK
                    if px is not None:
                        pnl = pos * (px - entry) * PV * p["qty"] - 2 * FEE * p["qty"]
                        trades.append(Tr(b.index[ebar], b.index[k], ebar, k, p["qty"], entry, pos, pnl))
                        day_pnl += pnl
                        pos = 0
                if m in CHECKS and not math.isnan(sig[m]):
                    s = sig[m]
                    up, lo = up_base * (1 + p["entry_k"] * s), lo_base * (1 - p["entry_k"] * s)
                    side = 1 if c[k] > up else -1 if c[k] < lo else 0
                    if (pos == 0 and pending is None and prev_side != 0 and side == 0 and n_tr < p["max_trades"]
                            and -1200 < day_pnl < 1500 and m < 960):
                        pending = (-prev_side, s * c[k])
                        n_tr += 1
                    prev_side = side
        hist.append(moves)
        prev_close = c[rth[-1]]
        i = j
    return Res(trades)


def job(a):
    tag, name, start = a
    P.clear()
    P.update(VARIANTS[tag])
    box = {}

    def spy(b, cfg, minutes):
        res = fade_run(b, cfg, minutes)
        box["res"], box["b"] = res, b
        return res

    G.run = spy
    r = G.one((name, start, 4, 1500.0, {}))
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
        if os.environ.get("DEV_ONLY") and label.startswith("unseen"):
            break
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
