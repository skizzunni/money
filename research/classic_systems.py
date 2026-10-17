"""Round ninety-seven: classic named daytrade systems on MNQ, each on its own, with a strict multiple-testing protocol.

    python research/classic_systems.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user wants a different strategy. Rounds seventy-one, ninety-two and ninety-six tested the opening range, NR7/NR4,
inside days, the initial balance, the opening drive, gap and go, prior-day breakouts, three-day trends, the lunch
reversal, VWAP fades, trend pullbacks and Market Profile. This round tests four named systems none of them covered.
Everything below was fixed before looking at any result.

Data and fills as research/setups.py (its sessions(), fill_from() and checks are reused): 1-minute bars 09:30-15:59 New
York, rescaled month by month to today's price level; a session counts with >= 370 of its 390 minutes; trades on the
first session of each month are dropped (the rescaling puts a fake gap there). Daily bars = each counted session's
open, high, low, close. One trade per rule per day; entries by 15:00 (bar 330); flat at 15:59 at the close less a
tick. $1.24 fees a contract and a tick of slippage on every market and stop fill; limits fill at their price once
traded a tick through; a stop entry fills at its level or the bar's open if it opened past it; on the fill bar of a
stop entry the stop counts if reached; on any bar reaching stop and target, the stop counts.
Size: contracts = floor($300 / (stop distance in points x $2)), between 1 and 10; a trade whose stop is more than 40
points away is skipped (Turtle Soup, 80-20, Holy Grail). Williams' range-based stops are 90-300 points at today's price
level, so the 40-point skip would remove every trade: its range-stop rules trade 1 contract and are not skipped, and
its fixed-stop rules trade 4 MNQ with a 25-point stop, as the directive asks.

Rules (18):
  Larry Williams volatility breakout. R = yesterday's high - low. Buy stop at today's open + k x R, sell stop at
  open - k x R, from 09:30 to 15:00; the first side triggered only; exit at the close.
    W1-W3  k 0.3 / 0.5 / 0.7, stop at today's open (1 MNQ)
    W4-W6  k 0.3 / 0.5 / 0.7, stop k x R the other side of the open, i.e. at the opposite entry level (1 MNQ)
    W7-W9  k 0.3 / 0.5 / 0.7, fixed 25-point stop, 4 MNQ
  Linda Raschke's Turtle Soup. L20 / H20 = the lowest low / highest high of the previous 20 sessions; only when that
  extreme was set 4 or more sessions ago. From 10:00 to 15:00: once a 1-minute bar trades below L20 (above H20), the
  first 1-minute close back above L20 (below H20) -> buy (sell) at the next minute's open; stop a tick beyond the
  day's low (high) so far.
    T1  target 1R    T2  target 2R    T3  exit at the close
  Raschke's 80-20. Yesterday opened in the top 20% of its range and closed in the bottom 20% (or the mirror). Today
  from 09:30 to 15:00: once price trades 5 points or more below yesterday's low (above its high), the first 1-minute
  close back above yesterday's low (below its high) -> buy (sell) at the next open; stop a tick beyond the day's
  extreme so far.
    E1  target 1R    E2  target 2R    E3  exit at the close
  Holy Grail (Raschke). 5-minute bars of the regular session, chained across sessions for the indicators: ADX(14) with
  Wilder smoothing, +DI / -DI, EMA(20) of the close. From a 5-minute close at 10:00 or later: ADX >= 30 and above the
  previous bar's -> trend up if +DI > -DI, else down. The first 5-minute bar of the day whose low (high) touches the
  EMA(20) in an up (down) trend is the pullback bar; buy (sell) stop a tick above its high (below its low), valid for
  the next three 5-minute bars, by 15:00; stop a tick beyond the pullback bar's other extreme.
    G1  target: the highest high (lowest low) of the 20 five-minute bars before the pullback (if not beyond the entry,
        2R)    G2  target 2R    G3  exit at the close

Protocol: discovery 2011-2018 (index): per rule $ per trade, winners, t of the daily P/L on the days it trades
(one trade a day), Benjamini-Hochberg at q = 0.05 across all 18 rules. A positive survivor gets one look at 2019 - Sep
2026 (index): same sign, t >= 2; then NQ futures 2015 - Jul 2025: same sign, t >= 1.5. For a final survivor: alone and
with the bot (research/lock_apex.trades_for(bars, 3, 1.0, 2.5) at 4 MNQ, overlapping minute equity summed per day):
winners, $ a week, worst losing stretch, green / red days, the 50K intraday-trail evaluation pass / bust %
(research/apex25k.py attempt), payouts per evaluation (research/apex_payouts.py) and the funded first payout within 20 /
40 sessions (research/fast_payout.first_payout).
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import setups as SU  # noqa: E402

TICK, PV, FEE, N = SU.TICK, SU.PV, SU.FEE, SU.N
LAST_ENTRY = 330  # 15:00
RULES = [f"W{i}" for i in range(1, 10)] + ["T1", "T2", "T3", "E1", "E2", "E3", "G1", "G2", "G3"]


def size(stop_pts: float, skip: bool = True) -> int:
    if stop_pts <= 0 or (skip and stop_pts > 40):
        return 0
    return int(min(10, max(1, math.floor(300 / (stop_pts * PV)))))


def trade(o, h, lo, c, j, d, entry, stop, target, q, stop_entry):
    """P/L of q contracts entered at `entry` (slippage in) on bar j, managed to the close."""
    exit_ = SU.fill_from(o, h, lo, c, j, d, entry, stop, target, N - 1, stop_on_first=stop_entry)
    return q * (d * (exit_ - entry) * PV - FEE)


def williams(o, h, lo, c, rng, k, mode):
    up, dn = o[0] + k * rng, o[0] - k * rng
    for j in range(0, LAST_ENTRY + 1):
        hit_up, hit_dn = h[j] >= up, lo[j] <= dn
        if not (hit_up or hit_dn):
            continue
        d = 1 if hit_up else -1
        lvl = up if d > 0 else dn
        entry = (max(o[j], lvl) if d > 0 else min(o[j], lvl)) + d * TICK
        if mode == "open":
            stop, q = o[0], 1
        elif mode == "range":
            stop, q = (dn if d > 0 else up), 1
        else:
            stop, q = lvl - d * 25.0, 4
        if hit_up and hit_dn:  # both levels in one bar: a long that is stopped
            stop_l = o[0] if mode == "open" else dn if mode == "range" else up - 25.0
            return q * ((stop_l - TICK - entry) * PV - FEE)
        return trade(o, h, lo, c, j, d, entry, stop, None, q, True)
    return None


def reclaim(o, h, lo, c, start, level, d, pierce, mode):
    """Price trades beyond `level` against direction d by `pierce` points, then the first 1-minute close back on the d
    side -> enter d at the next open; stop a tick beyond the day's extreme so far."""
    beyond = False
    for j in range(start, LAST_ENTRY + 1):
        if not beyond:
            beyond = (lo[j] <= level - pierce) if d > 0 else (h[j] >= level + pierce)
            if not beyond:
                continue
        if (d > 0 and c[j] > level) or (d < 0 and c[j] < level):
            i = j + 1
            if i >= N:
                return None
            ext = lo[:i].min() if d > 0 else h[:i].max()
            stop = ext - d * TICK
            entry = o[i] + d * TICK
            risk = d * (entry - stop)
            q = size(risk)
            if q == 0:
                return None
            target = None if mode == "close" else entry + d * (1 if mode == "1R" else 2) * risk
            return trade(o, h, lo, c, i, d, entry, stop, target, q, False)
    return None


def five_minute(S):
    """5-minute OHLC of every session chained, with ADX(14), +DI, -DI, EMA(20): {session index: arrays}."""
    rows = []
    for k, s in enumerate(S):
        o, h, lo, c = s[2], s[3], s[4], s[5]
        for b in range(78):
            a, z = 5 * b, 5 * b + 5
            rows.append((k, b, o[a], h[a:z].max(), lo[a:z].min(), c[z - 1]))
    df = pd.DataFrame(rows, columns=["k", "b", "o", "h", "l", "c"])
    hh, ll, cc = df.h.to_numpy(), df.l.to_numpy(), df.c.to_numpy()
    up = np.r_[0.0, hh[1:] - hh[:-1]]
    dn = np.r_[0.0, ll[:-1] - ll[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.r_[hh[0] - ll[0], np.maximum.reduce([hh[1:] - ll[1:], np.abs(hh[1:] - cc[:-1]),
                                                  np.abs(ll[1:] - cc[:-1])])]
    n = 14

    def wilder(x):
        out = np.empty_like(x)
        out[0] = x[0]
        for i in range(1, len(x)):
            out[i] = out[i - 1] + (x[i] - out[i - 1]) / n
        return out

    atr = wilder(tr)
    pdi = 100 * wilder(pdm) / np.where(atr > 0, atr, np.nan)
    mdi = 100 * wilder(mdm) / np.where(atr > 0, atr, np.nan)
    dx = 100 * np.abs(pdi - mdi) / np.where(pdi + mdi > 0, pdi + mdi, np.nan)
    df["adx"] = wilder(np.nan_to_num(dx))
    df["pdi"], df["mdi"] = pdi, mdi
    df["ema"] = df.c.ewm(span=20, adjust=False).mean()
    return {k: g.reset_index(drop=True) for k, g in df.groupby("k")}


def holy_grail(o, h, lo, c, f, mode):
    """f: this session's 5-minute frame. The first EMA touch in an ADX >= 30 rising trend from 10:00."""
    for b in range(6, 72):  # the bar ending 10:00 is b = 5; pullback bars from 10:00 on
        prev = f.loc[b - 1]
        if not (prev.adx >= 30 and prev.adx > f.loc[b - 2].adx):
            continue
        d = 1 if prev.pdi > prev.mdi else -1
        bar = f.loc[b]
        if not ((d > 0 and bar.l <= bar.ema) or (d < 0 and bar.h >= bar.ema)):
            continue
        lvl = bar.h + TICK if d > 0 else bar.l - TICK
        stop = bar.l - TICK if d > 0 else bar.h + TICK
        start, end = 5 * (b + 1), min(5 * (b + 4) - 1, LAST_ENTRY)
        for j in range(start, end + 1):
            if (d > 0 and h[j] >= lvl) or (d < 0 and lo[j] <= lvl):
                entry = (max(o[j], lvl) if d > 0 else min(o[j], lvl)) + d * TICK
                risk = d * (entry - stop)
                q = size(risk)
                if q == 0:
                    return None
                if mode == "swing":
                    w = f.loc[max(0, b - 20):b - 1]
                    sw = w.h.max() if d > 0 else w.l.min()
                    target = sw if d * (sw - entry) > 0 else entry + d * 2 * risk
                elif mode == "2R":
                    target = entry + d * 2 * risk
                else:
                    target = None
                return trade(o, h, lo, c, j, d, entry, stop, target, q, True)
        return None  # the first pullback didn't trigger: no trade today
    return None


def day_rules(S, k, five):
    o, h, lo, c = S[k][2], S[k][3], S[k][4], S[k][5]
    yh, yl, yo, yc = S[k - 1][3].max(), S[k - 1][4].min(), S[k - 1][2][0], S[k - 1][5][-1]
    out = {}
    for i, kk in enumerate((0.3, 0.5, 0.7)):
        out[f"W{i + 1}"] = williams(o, h, lo, c, yh - yl, kk, "open")
        out[f"W{i + 4}"] = williams(o, h, lo, c, yh - yl, kk, "range")
        out[f"W{i + 7}"] = williams(o, h, lo, c, yh - yl, kk, "fixed")
    lows = [S[j][4].min() for j in range(k - 20, k)]
    highs = [S[j][3].max() for j in range(k - 20, k)]
    l20, h20 = min(lows), max(highs)
    old_l, old_h = (19 - int(np.argmin(lows))) >= 3, (19 - int(np.argmax(highs))) >= 3  # set >= 4 sessions ago
    for name, mode in (("T1", "1R"), ("T2", "2R"), ("T3", "close")):
        r = None
        if old_l:
            r = reclaim(o, h, lo, c, 30, l20, 1, 0.0, mode)
        if r is None and old_h:
            r = reclaim(o, h, lo, c, 30, h20, -1, 0.0, mode)
        out[name] = r
    rng = yh - yl
    pos_o, pos_c = (yo - yl) / rng if rng > 0 else 0.5, (yc - yl) / rng if rng > 0 else 0.5
    for name, mode in (("E1", "1R"), ("E2", "2R"), ("E3", "close")):
        r = None
        if pos_o >= 0.8 and pos_c <= 0.2:
            r = reclaim(o, h, lo, c, 0, yl, 1, 5.0, mode)
        elif pos_o <= 0.2 and pos_c >= 0.8:
            r = reclaim(o, h, lo, c, 0, yh, -1, 5.0, mode)
        out[name] = r
    f = five[k]
    for name, mode in (("G1", "swing"), ("G2", "2R"), ("G3", "close")):
        out[name] = holy_grail(o, h, lo, c, f, mode)
    return {r: v for r, v in out.items() if v is not None}


def run(path: str) -> pd.DataFrame:
    S = SU.sessions(path)
    five = five_minute(S)
    rows = []
    for k in range(20, len(S)):
        for rule, val in day_rules(S, k, five).items():
            rows.append((S[k][0], S[k][1], rule, val))
    df = pd.DataFrame(rows, columns=["day", "nth", "rule", "pnl"])
    return df[df.nth != 1]


def table(df, y0, y1, years):
    d = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
    out = {}
    for r in RULES:
        x = d[d.rule == r].pnl.to_numpy()
        mean, t, p = SU.tstat(x)
        win = 100 * np.mean(x > 0) if len(x) else 0.0
        out[r] = {"trades": len(x), "trades/week": len(x) / (years * 52), "win %": win,
                  "$/trade": mean, "$/week": x.sum() / (years * 52), "t": t, "p": p}
    return pd.DataFrame(out).T


def checks() -> None:
    SU.checks()
    o = np.full(N, 100.0)
    h, lo, c = o + 0.5, o - 0.5, o.copy()
    # Williams: range 10, k 0.5 -> buy stop 105; bar 40 trades 105.5; fixed 25-pt stop, 4 MNQ, exit at the close 108
    h1, c1 = h.copy(), c.copy()
    h1[40] = 105.5
    c1[41:] = 106.0
    h1[41:] = 106.5
    c1[-1] = 108.0
    r = williams(o, h1, lo, c1, 10.0, 0.5, "fixed")
    assert abs(r - 4 * ((108.0 - TICK - 105.25) * PV - FEE)) < 1e-9, r
    lo1 = lo.copy()
    lo1[40:] = 104.0  # stays above the open, the stop
    r = williams(o, h1, lo1, c1, 10.0, 0.5, "open")
    assert abs(r - 1 * ((108.0 - TICK - 105.25) * PV - FEE)) < 1e-9, r
    assert williams(o, h1, lo, c1, 10.0, 0.5, "open") < 0  # back through the open: stopped
    # reclaim: trades below 95 on bar 50, closes back above 95 on bar 52 -> buy bar 53 open (100), stop day low - tick
    o2, h2, lo2, c2 = o.copy(), h.copy(), lo.copy(), c.copy()
    lo2[50], c2[50] = 94.0, 94.5
    c2[51], c2[52] = 94.8, 95.2
    o2[53:], c2[53:], h2[53:], lo2[53:] = 96.0, 96.0, 96.5, 95.5
    c2[-1] = 97.0
    r = reclaim(o2, h2, lo2, c2, 30, 95.0, 1, 0.0, "close")
    stop, entry = 94.0 - TICK, 96.0 + TICK
    q = size(entry - stop)
    assert q == 10 and abs(r - q * ((97.0 - TICK - entry) * PV - FEE)) < 1e-9, (r, q)
    # 1R target: entry + risk = 96.25 + 2.5 = 98.75, traded through on bar 60
    h3 = h2.copy()
    h3[60] = 99.5
    r = reclaim(o2, h3, lo2, c2, 30, 95.0, 1, 0.0, "1R")
    assert abs(r - q * ((98.75 - entry) * PV - FEE)) < 1e-9, r
    # a stop more than 40 points away: skipped
    lo4 = lo2.copy()
    lo4[40] = 50.0
    assert reclaim(o2, h2, lo4, c2, 30, 95.0, 1, 0.0, "close") is None
    # the 80-20 pierce: 4 points below doesn't arm it, 5 does
    lo5 = lo2.copy()
    lo5[50] = 90.0
    assert reclaim(o2, h2, lo2, c2, 0, 98.0, 1, 5.0, "close") is None  # low 94 is only 4 below 98
    assert reclaim(o2, h2, lo2, c2, 0, 95.0, 1, 5.0, "close") is None  # low 94 is only 1 below 95
    assert reclaim(o2, h2, lo5, c2, 0, 95.0, 1, 5.0, "close") is not None  # low 90 is 5 below 95
    print("system checks pass")


def main() -> None:
    checks()
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=2) as pool:
        idx, fut = pool.map(run, [nsx, nq])
    disc = table(idx, 2011, 2018, 8.0)
    print("\nDiscovery 2011-2018 (index)")
    print(disc.round(3).to_string())
    surv = SU.bh(disc.p.to_dict())
    print(f"\nBenjamini-Hochberg q=0.05 over {len(RULES)} rules: {sorted(surv) or 'none'}")
    cands = [r for r in surv if disc.loc[r, "$/trade"] > 0]
    print(f"positive survivors: {cands or 'none'}")
    hold = table(idx, 2019, 2026, 7.75)
    nqt = table(fut, 2015, 2025, 10.5)
    print("\n2019 - Sep 2026 (index), all rules for reference")
    print(hold.round(3).to_string())
    print("\nNQ futures 2015 - Jul 2025, all rules for reference")
    print(nqt.round(3).to_string())
    final = [r for r in cands if hold.loc[r, "t"] >= 2 and nqt.loc[r, "t"] >= 1.5]
    for r in cands:
        print(f"{r}: 2019-26 t {hold.loc[r, 't']:.2f}, NQ t {nqt.loc[r, 't']:.2f}")
    print(f"\nfinal survivors: {final or 'none'}")


if __name__ == "__main__":
    main()
