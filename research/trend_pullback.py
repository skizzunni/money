"""Round ninety-two: intraday trend-pullback, a different strategy for clear trend days (MNQ, one 50K Apex account).

    python research/trend_pullback.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants a different strategy that trades clear trends. Untested family here: on a day already trending by
mid-morning, buy the pullback to a short moving average and ride the trend. Everything below is fixed before running.

Trend-day qualifier, New York time, on 1-minute bars of 09:30-16:00 (three variants, Q):
  V1030 / V1100: at 10:30 (or 11:00) at least 80% of the 1-minute closes since 09:45 were above the session's
    average price (VWAP on NQ futures, which have volume; a time-weighted average of the 1-minute closes on the index
    data, which have none) AND the day's high so far was made in the last 30 minutes: an uptrend. The mirror (below,
    the day's low in the last 30 minutes) is a downtrend.
  R1030: the 09:30-10:30 move is at least 1.0x the average absolute 09:30-10:30 move of the previous 14 sessions, and
    the 10:30 price is in the top 25% of the 09:30-10:30 range (uptrend) or the bottom 25% (downtrend).
Entry, after the qualifier time until 15:00, on 5-minute bars aligned to 09:30 (EMA of 5-minute closes from 09:30,
period 9 or 20): a bar whose low (high, in a downtrend) touches the EMA starts a pullback; the pullback's extreme is
the lowest low (highest high) from that bar on; the first later-or-same bar that closes back in the trend's direction
(close > open and close > EMA for a long; mirror for a short) is the signal, ending no later than 15:00; entry at the
next minute's open plus a tick. At most two trades a day; after an exit a new touch is needed.
Stop (two variants): one tick beyond the pullback's extreme, or 25 points from the entry; a trade is skipped when its
stop would be more than 40 points (or not beyond the entry).
Exit (two variants): a 2R take-profit limit (R = the stop distance; fills at the limit once a 1-minute bar trades a
tick through it), or a trailing stop under each new 5-minute higher low (above each lower high, short), never
loosened, from the bar after that 5-minute bar closes. Flat at the 15:59 close.
Rules: 3 qualifiers x 2 EMAs x 2 stops x 2 exits = 24.
Size for the account: contracts = floor($300 / (stop points x $2)), 1 to 10 MNQ.
Costs: $1.24 a contract a round trip, and a tick of slippage on every market and stop fill (the entry, a stop, the
15:59 exit); a take-profit limit fills at its price. When one minute reaches the stop and the target, the stop counts.
A gap through the stop fills at the minute's open.
Protocol: discovery 2011-2018 on the index data: per rule the daily P/L (0 on days without a trade), t = mean / sd x
sqrt(days), two-sided p (normal); Benjamini-Hochberg at q = 0.05 across all 24 rules. Survivors get one look at
2019 - Sep 2026 (same sign, t >= 2.0), then NQ futures 2015-2025 (same sign, t >= 1.5). For a final survivor: winners,
trades a week, $ a week, worst losing stretch, green / red days, the 50K intraday evaluation pass / bust % alone and
combined with the bot (research/lock_apex.trades_for(bars, 3, 1.0, 2.5) at 4 MNQ), and the funded first payout
within 20 / 40 sessions (research/fast_payout.first_payout).
"""
from __future__ import annotations

import itertools
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402

TICK, PV, FEE = 0.25, 2.0, 1.24
QUALS, EMAS, STOPS, EXITS = ("V1030", "V1100", "R1030"), (9, 20), ("swing", "fixed25"), ("2R", "trail")
RULES = list(itertools.product(QUALS, EMAS, STOPS, EXITS))
LAST_SIGNAL, FLAT = 900, 959  # signal bars end by 15:00; out at the 15:59 close


def sessions(path: str):
    """Per session: (date, minute-of-day, open, high, low, close, volume) arrays for 09:30-15:59."""
    bars = A.rth(path)
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    keep = tmin < 960
    bars, idx, tmin = bars[keep], idx[keep], tmin[keep]
    day = idx.normalize().tz_localize(None)
    out = []
    o, h, lo, c, v = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    cuts = np.flatnonzero(np.diff(day.asi8)) + 1
    for a, b in zip(np.r_[0, cuts], np.r_[cuts, len(bars)], strict=True):
        if tmin[a] != 570 or b - a < 300:  # a full-enough session that opens at 09:30
            continue
        out.append((day[a], tmin[a:b], o[a:b], h[a:b], lo[a:b], c[a:b], v[a:b]))
    return out


def qualifier(s, kind, prev_moves):
    """+1 uptrend, -1 downtrend, 0 none, judged with data up to the qualifier time."""
    _, t, o, h, lo, c, v = s
    q_t = 660 if kind == "V1100" else 630
    k = int(np.searchsorted(t, q_t))  # bars before q_t (minute q_t - 1 is the last one used)
    if k < 30:
        return 0, q_t
    if kind == "R1030":
        move = c[k - 1] - o[0]
        if not prev_moves or len(prev_moves) < 14:
            return 0, q_t
        avg = float(np.mean(prev_moves[-14:]))
        hi, low = h[:k].max(), lo[:k].min()
        rng = hi - low
        if rng <= 0 or abs(move) < avg:
            return 0, q_t
        pos = (c[k - 1] - low) / rng
        if move > 0 and pos >= 0.75:
            return 1, q_t
        if move < 0 and pos <= 0.25:
            return -1, q_t
        return 0, q_t
    w = v[:k] if v[:k].sum() > 0 else np.ones(k)
    typ = (h[:k] + lo[:k] + c[:k]) / 3 if v[:k].sum() > 0 else c[:k]
    vwap = np.cumsum(typ * w) / np.cumsum(w)
    since = t[:k] >= 585
    recent = t[:k] >= q_t - 30
    if not since.any() or not recent.any():  # a data gap: no judgement
        return 0, q_t
    above = np.mean(c[:k][since] > vwap[since])
    below = np.mean(c[:k][since] < vwap[since])
    if above >= 0.8 and h[:k][recent].max() >= h[:k].max():
        return 1, q_t
    if below >= 0.8 and lo[:k][recent].min() <= lo[:k].min():
        return -1, q_t
    return 0, q_t


def five(s):
    """5-minute bars aligned to 09:30: (end minute, first index, last index, open, high, low, close)."""
    _, t, o, h, lo, c, _ = s
    bucket = (t - 570) // 5
    cuts = np.flatnonzero(np.diff(bucket)) + 1
    out = []
    for a, b in zip(np.r_[0, cuts], np.r_[cuts, len(t)], strict=True):
        out.append((570 + 5 * (bucket[a] + 1), a, b - 1, o[a], h[a:b].max(), lo[a:b].min(), c[b - 1]))
    return out


def ema(x, n):
    a = 2.0 / (n + 1)
    e = np.empty(len(x))
    e[0] = x[0]
    for i in range(1, len(x)):
        e[i] = a * x[i] + (1 - a) * e[i - 1]
    return e


def day_trades(s, rule, d):
    """The rule's trades on one session in trend direction d: list of (dir, entry minute idx, exit idx, entry, exit,
    contracts, pnl $, minute path of the open P/L in $ [high-side running max, low side])."""
    _, t, o, h, lo, c, _ = s
    _, n_ema, stop_kind, exit_kind = rule
    q_t = 660 if rule[0] == "V1100" else 630
    bars5 = five(s)
    e = ema(np.array([b[6] for b in bars5]), n_ema)
    trades = []
    j = 0
    touched, extreme = False, None
    busy_until = -1  # 1-minute index of the last exit
    while j < len(bars5) and len(trades) < 2:
        end, a, b, bo, bh, bl, bc = bars5[j]
        if end <= q_t or a <= busy_until:  # only bars after the qualifier and after the last exit
            j += 1
            continue
        if end > LAST_SIGNAL:
            break
        if not touched and ((d > 0 and bl <= e[j]) or (d < 0 and bh >= e[j])):
            touched, extreme = True, (bl if d > 0 else bh)
        if touched:
            extreme = min(extreme, bl) if d > 0 else max(extreme, bh)
            if (d > 0 and bc > bo and bc > e[j]) or (d < 0 and bc < bo and bc < e[j]):
                i = b + 1  # the next minute's open
                touched = False
                if i >= len(t) or t[i] >= FLAT:
                    break
                entry = o[i] + d * TICK
                stop = extreme - d * TICK if stop_kind == "swing" else entry - d * 25.0
                dist = d * (entry - stop)
                if dist <= 0 or dist > 40:
                    j += 1
                    continue
                q = int(min(10, max(1, math.floor(300.0 / (dist * PV)))))
                target = entry + d * 2 * dist if exit_kind == "2R" else None
                tr = run_trade(s, bars5, i, d, entry, stop, target, exit_kind == "trail", q)
                trades.append(tr)
                busy_until = tr[2]
                continue
        j += 1
    return trades


def run_trade(s, bars5, i, d, entry, stop, target, trail, q):
    _, t, o, h, lo, c, _ = s
    # the 5-minute bars that close after the entry, for the trail: (end minute, low, high)
    closed = [(b[0], b[5], b[4]) for b in bars5]
    prev_ext = None
    k = i
    exit_px = None
    while k < len(t):
        if trail:  # a 5-minute bar that ended at or before this minute updates the stop from this minute on
            for end, bl, bh in closed:
                if end == t[k] and end > t[i]:
                    ext = bl if d > 0 else bh
                    if prev_ext is not None and ((d > 0 and ext > prev_ext) or (d < 0 and ext < prev_ext)):
                        new = ext - d * TICK
                        stop = max(stop, new) if d > 0 else min(stop, new)
                    prev_ext = ext
        if (d > 0 and o[k] <= stop) or (d < 0 and o[k] >= stop):
            exit_px = o[k] - d * TICK
            break
        if (d > 0 and lo[k] <= stop) or (d < 0 and h[k] >= stop):
            exit_px = stop - d * TICK
            break
        if target is not None and ((d > 0 and h[k] >= target + TICK) or (d < 0 and lo[k] <= target - TICK)):
            exit_px = target
            break
        if t[k] >= FLAT:
            exit_px = c[k] - d * TICK
            break
        k += 1
    if exit_px is None:
        k = len(t) - 1
        exit_px = c[k] - d * TICK
    pnl = d * (exit_px - entry) * PV * q - FEE * q
    hi_path = (d * ((h[i:k + 1] if d > 0 else lo[i:k + 1]) - entry)) * PV * q - FEE * q
    lo_path = (d * ((lo[i:k + 1] if d > 0 else h[i:k + 1]) - entry)) * PV * q - FEE * q
    hi_path, lo_path = np.append(hi_path, pnl), np.append(lo_path, pnl)
    return (d, i, k, entry, exit_px, q, pnl, np.maximum.accumulate(hi_path), lo_path)


def run_rule(args):
    path, rule = args
    ss = sessions(path)
    moves, out = [], []
    for s in ss:
        k = int(np.searchsorted(s[1], 630))
        d, _ = qualifier(s, rule[0], moves)
        if k >= 30:
            moves.append(abs(s[5][k - 1] - s[2][0]))
        trades = day_trades(s, rule, d) if d else []
        out.append((s[0], trades))
    return rule, out


def stats(days, y0, y1):
    sel = [(day, tr) for day, tr in days if y0 <= day.year <= y1]
    daily = np.array([sum(x[6] for x in tr) for _, tr in sel])
    pnl = np.array([x[6] for _, tr in sel for x in tr])
    n = len(daily)
    sd = daily.std(ddof=1)
    tval = daily.mean() / sd * math.sqrt(n) if sd > 0 else 0.0
    p = math.erfc(abs(tval) / math.sqrt(2))
    eq = np.cumsum(daily)
    return {"trades": len(pnl), "$/trade": pnl.mean() if len(pnl) else 0.0, "win %": 100 * (pnl > 0).mean()
            if len(pnl) else 0.0, "$/day": daily.mean(), "t": tval, "p": p,
            "trades/week": 5 * len(pnl) / n, "worst stretch": float((np.maximum.accumulate(eq) - eq).max()),
            "green %": 100 * (daily > 0).mean(), "red %": 100 * (daily < 0).mean()}


def bh(pvals, q=0.05):
    order = np.argsort(pvals)
    m = len(pvals)
    passed = np.zeros(m, bool)
    k = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            k = rank
    passed[order[:k]] = True
    return passed


def name(rule):
    return f"{rule[0]} EMA{rule[1]} {rule[2]} {rule[3]}"


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 220)
    with ProcessPoolExecutor(max_workers=3) as pool:
        idx = dict(pool.map(run_rule, [(nsx, r) for r in RULES]))
    disc = {r: stats(idx[r], 2011, 2018) for r in RULES}
    df = pd.DataFrame({name(r): v for r, v in disc.items()}).T
    print("Discovery 2011-2018 (index)")
    print(df.sort_values("t", ascending=False).round(3).to_string())
    passed = bh([disc[r]["p"] for r in RULES])
    surv = [r for r, ok in zip(RULES, passed, strict=True) if ok]
    print(f"\nBenjamini-Hochberg q=0.05 survivors: {[name(r) for r in surv] or 'none'}")
    final = []
    for r in surv:
        s2 = stats(idx[r], 2019, 2026)
        ok2 = np.sign(s2["t"]) == np.sign(disc[r]["t"]) and abs(s2["t"]) >= 2.0
        print(f"  {name(r)} 2019-2026: t {s2['t']:.2f}, $/day {s2['$/day']:.2f}: {'PASS' if ok2 else 'FAIL'}")
        if ok2:
            final.append(r)
    if final:
        with ProcessPoolExecutor(max_workers=3) as pool:
            nqr = dict(pool.map(run_rule, [(nq, r) for r in final]))
        final2 = []
        for r in final:
            s3 = stats(nqr[r], 2015, 2025)
            ok3 = np.sign(s3["t"]) == np.sign(disc[r]["t"]) and abs(s3["t"]) >= 1.5
            print(f"  {name(r)} NQ 2015-2025: t {s3['t']:.2f}, $/day {s3['$/day']:.2f}: {'PASS' if ok3 else 'FAIL'}")
            if ok3:
                final2.append(r)
        print(f"\nfinal survivors: {[name(r) for r in final2] or 'none'}")
    else:
        print("\nfinal survivors: none")


if __name__ == "__main__":
    main()
