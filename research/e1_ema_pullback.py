"""Candidate E1, pre-registered in docs/CANDIDATE_E1.md: the pasted "Perfect Trading Strategy", tested only on its
objective rules.

The 09:30-10:00 bar sets the bias. The 30-minute EMA9 must be on the right side of the SMA20 and moving that way. A
5-minute bar that touches the 5-minute EMA9 and closes back on the trend side enters at the next open, from 10:00 to
10:55 and from 14:00 to 15:25. The stop is 1 tick outside the opening range, with $625 of risk and a 2.8R target. The
stop moves to breakeven at +1R, and the trade is out at 15:55. No new trade after a loss; at most one trade a window.

    python research/e1_ema_pullback.py <data dir> <out.csv>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h1_dip as H  # noqa: E402

TICK, PV, FEE, LEVEL = H.TICK, H.PV, H.FEE, H.LEVEL
RISK, TARGET_R = 625.0, 2.8
WINDOWS = [("proxy", "2025-01-02", "2026-12-31"), ("nq", "2015-01-01", "2025-07-31"), ("index", "2011-01-01", "2026-09-30")]


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def indicators(sess: list) -> tuple[list, np.ndarray, np.ndarray, np.ndarray]:
    """The 5-minute EMA9 per session, and the 30-minute EMA9 / SMA20 on the regular-hours 30-minute closes, each with a
    per-session list of (half-hour slot, global 30-minute index)."""
    c5 = np.concatenate([s[6] for s in sess])
    e5 = ema(c5, 9)
    off = np.r_[0, np.cumsum([len(s[2]) for s in sess])]
    c30, slots = [], []
    for s in sess:
        mi, c = s[2], s[6]
        g = (mi - 570) // 30
        sl = []
        for k in np.unique(g):
            sl.append((int(k), len(c30)))
            c30.append(c[np.flatnonzero(g == k)[-1]])
        slots.append(sl)
    c30 = np.array(c30)
    return [e5[off[i]:off[i + 1]] for i in range(len(sess))], ema(c30, 9), \
        pd.Series(c30).rolling(20).mean().to_numpy(), slots


def simulate(sess: list, start: str, end: str, scaled: bool) -> tuple[pd.DataFrame, dict]:
    e5s, e30, s30, slots = indicators(sess)
    days = [s[0] for s in sess]
    first = int(np.searchsorted(days, start))
    last = int(np.searchsorted(days, end, side="right"))
    rows, marks = [], []
    for i in range(first, last):
        day, _pc, mi, o, h, lo, c = sess[i]
        e5 = e5s[i]
        orb = np.flatnonzero(mi < 600)
        if len(orb) < 6:
            continue
        o_h, o_l = h[orb].max(), lo[orb].min()
        bias = int(np.sign(c[orb[-1]] - o[orb[0]]))
        if bias == 0:
            continue
        f = LEVEL / o[0] if scaled else 1.0
        used = {"am": False, "pm": False}
        lost = False
        pos = None
        for j in range(len(mi)):
            if pos is not None:
                d, entry, stop, tgt, q = pos["d"], pos["entry"], pos["stop"], pos["tgt"], pos["q"]
                out = reason = None
                if (lo[j] * f <= stop) if d > 0 else (h[j] * f >= stop):
                    out = (min(o[j] * f, stop) - TICK) if d > 0 else (max(o[j] * f, stop) + TICK)
                    reason = "breakeven" if pos["be"] else "stop"
                elif (h[j] * f >= tgt) if d > 0 else (lo[j] * f <= tgt):
                    out, reason = tgt, "target"
                elif j == len(mi) - 1:
                    out, reason = c[j] * f - d * TICK, "close"
                if out is not None:
                    pnl = q * ((out - entry) * d * PV - 2 * FEE)
                    slip = q * TICK * PV * (1 if reason == "target" else 2)
                    rows.append({"day": day, "d": d, "qty": q, "reason": reason, "pnl": pnl,
                                 "gross": pnl + q * 2 * FEE + slip, "i_exit": i, "j_exit": j, "sessions": 0})
                    lost = lost or pnl <= 0
                    pos = None
                else:
                    worst = lo[j] if d > 0 else h[j]
                    marks.append((i, j, q * ((worst * f - entry) * d * PV - FEE), q * ((c[j] * f - entry) * d * PV - FEE)))
                    if not pos["be"] and ((h[j] * f >= entry + pos["r"]) if d > 0 else (lo[j] * f <= entry - pos["r"])):
                        pos["be"], pos["stop"] = True, entry
                    continue
            if lost or j + 1 >= len(mi):
                continue
            win = "am" if 600 <= mi[j] <= 655 else "pm" if 840 <= mi[j] <= 925 else None
            if win is None or used[win]:
                continue
            done = (mi[j] + 5 - 570) // 30  # half-hour slots of today completed at this bar's close
            k = [g for slot, g in slots[i] if slot < done]
            if not k or k[-1] < 2 or np.isnan(s30[k[-1]]):
                continue
            k = k[-1]
            d = bias
            trend = (e30[k] > s30[k] and e30[k] > e30[k - 2]) if d > 0 else (e30[k] < s30[k] and e30[k] < e30[k - 2])
            pull = (lo[j] <= e5[j] < c[j]) if d > 0 else (h[j] >= e5[j] > c[j])
            if not (trend and pull):
                continue
            entry = o[j + 1] * f + d * TICK
            stop = (o_l * f - TICK) if d > 0 else (o_h * f + TICK)
            r = (entry - stop) * d
            if r <= 0:
                continue
            q = int(RISK // (r * PV + 2 * FEE + TICK * PV))
            if q < 1:
                continue
            used[win] = True
            pos = {"d": d, "entry": entry, "stop": stop, "tgt": entry + d * TARGET_R * r, "q": q, "r": r, "be": False}
    return pd.DataFrame(rows), {"marks": marks, "sess": sess, "first": first, "last": last}


def main() -> None:
    data, out = Path(sys.argv[1]), sys.argv[2]
    sets, _closes = H.load(data)
    rows = []
    for name, a, b in WINDOWS:
        tf, book = simulate(sets[name], a, b, scaled=name != "proxy")
        n_sess = sum(a <= s[0] <= b for s in sets[name])
        r = {"set": name, "from": a, "to": min(b, sets[name][-1][0]), "sessions": n_sess,
             **H.stats(tf, book, n_sess / 252)}
        if len(tf):
            days_with = tf.day.nunique()
            r.update({"days with a trade %": round(100 * days_with / n_sess, 1), "avg contracts": round(tf.qty.mean(), 1),
                      **{f"{k} %": round(100 * float((tf.reason == k).mean()), 1)
                         for k in ("target", "stop", "breakeven", "close")}})
        if name == "proxy":
            r.update({"pass net": r.get("net $", 0) >= 75000, "pass win": r.get("net win %", 0) >= 80,
                      "pass pf": r.get("pf", 0) >= 2.0, "pass marked dd": r.get("marked dd $", 1e9) < 4000})
        rows.append(r)
        print(r, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)


if __name__ == "__main__":
    main()
