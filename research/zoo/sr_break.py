# ruff: noqa: E501
"""The MambaFx "2 minute strategy" (the user's video, 2026-11-24), made mechanical for research/zoo's bench.

His rules (the video's transcript): the 2-minute chart, NASDAQ / US30; support and resistance marked from levels price
has touched several times, drawn all the way through (a resistance can turn support); when a 2-minute candle breaks a
level, enter its way, the stop just past the level, a 1:4 target; try again after a loss but stop after 2-3 losses a
day. His "1:10" version: the stop to break-even at 1:2; at 1:4 no take-profit, the stop to 1:2, then trailed.
Here a level is a swing high or low (the highest / lowest of k bars each side) from the prior session or today, with
at least `touches` swing points (highs and lows alike) within `tol` of it; a break is a 2-minute close beyond it (the
last close at or inside it); in at the next bar's open plus a tick; stop `buf` past the level; risk measured from the
signal close plus a tick, skipped when over `cap` points; out at 15:58 at the latest.
"""
from __future__ import annotations

import numpy as np
from harness import prev  # noqa: F401


def _pivots(h, lo, k):
    out = []
    n = len(h)
    for j in range(k, n - k):
        if h[j] >= h[j - k:j + k + 1].max():
            out.append((h[j], j + k))
        if lo[j] <= lo[j - k:j + k + 1].min():
            out.append((lo[j], j + k))
    return out


def sr_break(days, i, tick, k=3, touches=2, tol=0.0005, buf=0.0002, r=4.0, mode="fixed", cap=60.0, max_losses=2,
             first=576, last=690, max_trades=6, prevday=True):
    if i < 1:
        return []
    d = days[i]
    o, h, lo, c, mm = d["o"], d["h"], d["l"], d["c"], d["mm"]
    piv = []
    if prevday:
        p = days[i - 1]
        sc = d["s"] / p["s"] if p["s"] else 1.0
        piv += [(x * sc, -1) for x, _ in _pivots(p["h"], p["l"], k)]
    piv += _pivots(h, lo, k)
    if not piv:
        return []
    px = np.array([x for x, _ in piv])
    known = np.array([b for _, b in piv])
    out, losses, b = [], 0, 1
    n = len(c)
    while b < n - 1:
        end = mm[b] + 2
        if end < first or end > last:
            if end > last:
                break
            b += 1
            continue
        if losses >= max_losses or len(out) >= max_trades:
            break
        kn = known <= b
        lv = px[kn]
        side, lvl = 0, np.nan
        up = lv[(lv >= c[b - 1]) & (lv < c[b])]
        dn = lv[(lv <= c[b - 1]) & (lv > c[b])]
        for cand, s in ((np.sort(up)[::-1], 1), (np.sort(dn), -1)):
            for L in cand:
                if np.sum(np.abs(lv - L) <= tol * L) >= touches:
                    side, lvl = s, L
                    break
            if side:
                break
        if not side:
            b += 1
            continue
        e_exp = c[b] + side * tick
        stop = lvl * (1 - side * buf)
        risk = side * (e_exp - stop)
        if risk > cap or risk < 4 * tick:
            b += 1
            continue
        stop = float(np.round(stop / tick) * tick)
        tgt = float(np.round((e_exp + side * r * risk) / tick) * tick) if mode != "trail" else np.nan
        e = o[b + 1] + side * tick
        st, best, xb, x, why = stop, e, None, None, ""
        for q in range(b + 1, n):
            if (side > 0 and lo[q] <= st) or (side < 0 and h[q] >= st):
                x, why = (min(o[q], st) if side > 0 else max(o[q], st)) - side * tick, "stop"
                xb = q
                break
            if not np.isnan(tgt) and q > b + 1 and ((side > 0 and h[q] >= tgt + tick) or (side < 0 and lo[q] <= tgt - tick)):
                x, why, xb = tgt, "target", q
                break
            if mm[q] >= 956:
                x, why, xb = c[q] - side * tick, "time", q
                break
            best = max(best, c[q]) if side > 0 else min(best, c[q])
            gain = side * (c[q] - e)
            if mode in ("trail", "be"):
                if gain >= 2 * risk:
                    st = max(st, e + tick) if side > 0 else min(st, e - tick)
                if mode == "trail" and side * (best - e) >= 4 * risk:
                    lock = best - side * 2 * risk
                    st = max(st, lock) if side > 0 else min(st, lock)
        if x is None:
            x, why, xb = c[-1] - side * tick, "time", n - 1
        out.append((side, b + 1, e, x, why, xb))
        if side * (x - e) < 0:
            losses += 1
        b = xb + 1
    return out


def sr_trend(days, i, tick, trend=20, **p):
    """sr_break's trades only in the direction of the close against the `trend`-session average of closes."""
    if i < trend + 1:
        return []
    sma = np.mean([prev(days, i, "c", j) for j in range(1, trend + 1)])
    side = 1 if prev(days, i, "c") > sma else -1
    return [t for t in sr_break(days, i, tick, **p) if t[0] == side]
