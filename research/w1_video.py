"""Candidate W1, pre-registered in docs/CANDIDATE_W1.md: the user's screen-recorded NQ trade as rules.

A 5-minute bar that trades above the previous session's high and closes back below it is shorted at the next open. The
stop sits 2 ticks above the spike's high, there is no target, and the trade is held to 15:55. If stopped, one more
attempt is allowed that day on that side. Longs mirror this at the previous low. 1 MNQ, $0.62 a side, a tick on
market and stop fills.

    python research/w1_video.py <data dir> <out.csv>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h1_dip as H  # noqa: E402

TICK, PV, FEE, LEVEL = H.TICK, H.PV, H.FEE, H.LEVEL
WINDOWS = [("proxy", "2025-01-02", "2026-12-31"), ("nq", "2015-01-01", "2025-07-31"), ("index", "2011-01-01", "2026-09-30")]


def simulate(sess: list, start: str, end: str, scaled: bool) -> tuple[pd.DataFrame, dict]:
    days = [s[0] for s in sess]
    first = int(np.searchsorted(days, start))
    last = int(np.searchsorted(days, end, side="right"))
    rows, marks = [], []
    for i in range(max(first, 1), last):
        day, _pc, mi, o, h, lo, c = sess[i]
        prev = sess[i - 1]
        if (pd.Timestamp(day) - pd.Timestamp(prev[0])).days > 4:
            continue
        ph, pl = prev[4].max(), prev[5].min()
        f = LEVEL / o[0] if scaled else 1.0
        spike = {-1: -np.inf, 1: np.inf}
        crossed = {-1: False, 1: False}
        tries = {-1: 0, 1: 0}
        pos = None
        for j in range(len(mi)):
            if pos is not None:
                d, entry, stop = pos["d"], pos["entry"], pos["stop"]
                hit = h[j] * f >= stop if d < 0 else lo[j] * f <= stop
                out = reason = None
                if hit:
                    out, reason = (max(o[j] * f, stop) + TICK if d < 0 else min(o[j] * f, stop) - TICK), "stop"
                elif j == len(mi) - 1:
                    out, reason = c[j] * f - d * TICK, "close"
                if out is not None:
                    pnl = (out - entry) * d * PV - 2 * FEE
                    rows.append({"day": day, "d": d, "reason": reason, "pnl": pnl, "gross": pnl + 2 * FEE + 2 * TICK * PV,
                                 "i_exit": i, "j_exit": j, "sessions": 0})
                    pos = None
                else:
                    worst = h[j] if d < 0 else lo[j]
                    marks.append((i, j, (worst * f - entry) * d * PV - FEE, (c[j] * f - entry) * d * PV - FEE))
            # the spike's extremes since the level was first crossed (tracked whether or not in a trade)
            if h[j] > ph:
                crossed[-1] = True
                spike[-1] = max(spike[-1], h[j])
            if lo[j] < pl:
                crossed[1] = True
                spike[1] = min(spike[1], lo[j])
            if pos is not None or j + 1 >= len(mi) or not 575 <= mi[j] <= 900:
                continue
            for d in (-1, 1):
                lvl = ph if d < 0 else pl
                sig = (h[j] > lvl and c[j] < lvl) if d < 0 else (lo[j] < lvl and c[j] > lvl)
                if sig and tries[d] < 2:
                    tries[d] += 1
                    entry = o[j + 1] * f + d * TICK
                    stop = spike[d] * f - d * 2 * TICK
                    pos = {"d": d, "entry": entry, "stop": stop}
                    break
            # an entry fills at the next bar's open: that bar is checked on the next pass of the loop
    return pd.DataFrame(rows), {"marks": marks, "sess": sess, "first": first, "last": last}


def longest_losing_run(p: np.ndarray) -> int:
    run = best = 0
    for x in p:
        run = run + 1 if x <= 0 else 0
        best = max(best, run)
    return best


def main() -> None:
    data, out = Path(sys.argv[1]), sys.argv[2]
    sets, _closes = H.load(data)
    rows = []
    for name, a, b in WINDOWS:
        tf, book = simulate(sets[name], a, b, scaled=name != "proxy")
        n_sess = sum(a <= s[0] <= b for s in sets[name])
        r = {"set": name, "from": a, "to": min(b, sets[name][-1][0]), "sessions": n_sess,
             **H.stats(tf, book, n_sess / 252)}
        p = tf.pnl.to_numpy()
        r.update({"stopped %": round(100 * float((tf.reason == "stop").mean()), 1),
                  "largest winner $": round(float(p.max())), "longest losing run": longest_losing_run(p),
                  "shorts": int((tf.d < 0).sum()), "longs": int((tf.d > 0).sum())})
        if name == "proxy":
            r.update({"pass net": r["net $"] >= 75000, "pass win": r["net win %"] >= 80, "pass pf": r["pf"] >= 2.0,
                      "pass marked dd": r["marked dd $"] < 4000})
        rows.append(r)
        print(r, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
