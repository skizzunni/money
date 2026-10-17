"""Round seventy-one: classic intraday setups on the Nasdaq, each on its own, with a strict multiple-testing protocol.

    python research/setups.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user trades MNQ only and wants more winning trades from new ideas. Seventy rounds tested the noise-momentum bot and
many variants, plus some classic setups: the opening-range retest and breakout-close, a gap fade before 10:00, the
last half hour's momentum, the afternoon trend, a VWAP trailing stop, a quiet-day fade, pullback limit entries. This
round scans nine classic intraday setups none of them tested, each as a standalone strategy. Everything below was
fixed before looking at any result.

Data: 1-minute bars 09:30-15:59 New York, month-by-month rescaled to today's price level (scratchpad
nsx1m_scaled.pkl: the Nasdaq-100 index 2011 - Sep 2026; nq1m_scaled.pkl: NQ futures 2015 - Jul 2025, with volume).
A session counts when it has at least 370 of its 390 RTH minutes (missing minutes repeat the last close); half days
and holed days are skipped. "Yesterday" is the previous counted session. Trades on the first session of each month
are dropped from every statistic (the rescaling puts a fake gap there), and those sessions' gaps are left out of the
14-day gap average. One trade per rule per day, 1 MNQ ($2 a point), $1.24 fees a round trip, 1 tick (0.25) of
slippage on every market and stop fill (entries and exits), take-profit limits fill at their price once price trades a
tick through. A stop entry fills at the level or the bar's open if it opened past it. On the bar a stop entry fills,
the stop counts if that bar reached it (worst case) and the target doesn't. On any bar that reaches both the stop and
the target, the stop counts. Time exits are at the close of the named bar (15:59 for "the close") minus slippage.
Two-sided stop entries: the first bar to reach either level; a bar that reaches both is a long that is stopped.

Setups (24 rules):
  NR7 / NR4 (Crabel): yesterday's RTH range was the narrowest of the last 7 (4) sessions. Today from 10:00, buy stop
    at the 09:30-09:59 high, sell stop at its low; stop at the opposite side; exit at the close.
      R01 NR7, stop opposite side   R02 NR4, stop opposite side   R03 NR7, stop at the 30-minute midpoint
  Inside day: yesterday's high <= the day before's high and its low >= the day before's low. Today from 10:00, stop
    entries at yesterday's high / low; exit at the close.
      R04 stop at yesterday's midpoint   R05 stop at the opposite side
  Initial balance: the 09:30-10:29 high/low. From 10:30, stop entries at them; stop at the IB midpoint.
      R06 target 1x the IB range past the entry level   R07 target 2x   R08 no target, exit at the close
  Opening drive: m = the 09:44 close minus the 09:30 open; if |m| > X times its 14-session average, enter in its
    direction at the 09:45 open; stop at the 09:30 open.
      R09 X 1.5, exit 10:59 close   R10 X 1.5, exit the close   R11 X 2.0, exit 10:59   R12 X 2.0, exit the close
  Gap and go: gap = the 09:30 open minus yesterday's 15:59 close; if |gap| > T times its 14-session average and the
    09:34 close is beyond the 09:30 open in the gap's direction, enter at the 09:35 open in the gap's direction; stop
    at the 09:30 open.
      R13 T 0.5, exit 10:29 close   R14 T 0.5, exit the close   R15 T 1.0, exit 10:29   R16 T 1.0, exit the close
  Prior-day breakout: the 09:30 open is inside yesterday's range. From 10:00, stop entries at yesterday's high / low;
    stop f x ATR14 (the 14-session average RTH range) from the entry level; exit at the close.
      R17 f 0.5   R18 f 0.25
  Three-day trend: the last three sessions all closed above their open (or all below), and the 09:30-09:59 move
    (09:59 close minus 09:30 open) agrees: enter at the 10:00 open in that direction; exit at the close.
      R19 no stop   R20 stop at the 09:30-09:59 low (long) / high (short)
  Lunch reversal: morning = the 11:29 close minus the 09:30 open; lunch = the 12:59 close minus the 11:29 close; if the
    lunch moved against the morning by more than half the morning's move, enter at the 13:00 open in the morning's
    direction; exit at the close.
      R21 no stop   R22 stop at the lunch extreme (11:30-12:59 low for a long, high for a short)
  VWAP band fade: VWAP and its standard deviation from 09:30, of the typical price (h+l+c)/3 weighted by volume (NQ
    futures) or equally (the index has no volume). From 10:30 to 14:29, the first 1-minute close beyond VWAP +/- k SD:
    fade it at the next open; target the VWAP at that moment; stop at VWAP +/- (k+1) SD; exit at the close.
      R23 k 2.0   R24 k 2.5

Protocol: discovery 2011-2018 (index): per rule, mean $ per trade and its t (trades are one per day, so this is the
t of the daily P/L on days it trades); Benjamini-Hochberg at q = 0.05 across all 24 rules, two-sided. A survivor is a
candidate edge only if its mean is positive. Candidates get one look at 2019 - Sep 2026 (index): same sign, t >= 2;
then NQ futures 2015 - Jul 2025: same sign, t >= 1.5. Any final survivor: its daily P/L's correlation with the
noise-momentum bot (v1.6, 4 MNQ, $200, 3 losers, take-profit from the fill), the bot + setup $ a week and worst losing
stretch at a size that keeps the setup's per-trade risk at or under $200, and the 50K intraday-trail evaluation pass
rate (research/apex25k.py attempt, $3,000 target, $2,000 drawdown) of the bot alone against the bot + setup.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

TICK, PV, FEE = 0.25, 2.0, 1.24
N = 390  # RTH minutes 09:30-15:59


def sessions(path: str):
    """[(date, nth session of its month, o, h, l, c, v)] for every session with >= 370 RTH minutes."""
    df = pd.read_pickle(path)
    m = df.index.hour * 60 + df.index.minute
    df = df[(m >= 570) & (m < 960)]
    out = []
    for day, g in df.groupby(df.index.date):
        if len(g) < 370:
            continue
        idx = (g.index.hour * 60 + g.index.minute - 570).to_numpy()
        a = np.full((5, N), np.nan)
        a[:, idx] = g[["open", "high", "low", "close", "volume"]].to_numpy().T
        if np.isnan(a[0, 0]):
            continue
        for j in range(1, N):  # a missing minute repeats the last close
            if np.isnan(a[3, j]):
                a[0:4, j] = a[3, j - 1]
                a[4, j] = 0.0
        out.append([pd.Timestamp(day), 0, *a])
    nth, prev_month = 0, None
    for s in out:
        key = (s[0].year, s[0].month)
        nth = nth + 1 if key == prev_month else 1
        prev_month = key
        s[1] = nth
    return out


def fill_from(o, h, lo, c, j0, d, entry, stop, target, exit_idx, stop_on_first=True):
    """Walk bars j0..exit_idx after an entry at `entry` (slippage already in). On bar j0 the target doesn't count when
    stop_on_first (a stop entry's fill bar). Returns the exit price."""
    for j in range(j0, exit_idx + 1):
        if stop is not None and ((d > 0 and lo[j] <= stop) or (d < 0 and h[j] >= stop)):
            px = min(o[j], stop) if d > 0 else max(o[j], stop)
            if j == j0 and stop_on_first:
                px = stop  # the fill bar: the stop was reached after the entry, at the stop
            return px - d * TICK
        if target is not None and not (j == j0 and stop_on_first):
            if (d > 0 and h[j] >= target + TICK) or (d < 0 and lo[j] <= target - TICK):
                return target
    return c[exit_idx] - d * TICK


def pnl(d, entry, exit_):
    return d * (exit_ - entry) * PV - FEE


def market(o, h, lo, c, i, d, stop, target, exit_idx):
    entry = o[i] + d * TICK
    return pnl(d, entry, fill_from(o, h, lo, c, i, d, entry, stop, target, exit_idx, stop_on_first=False))


def two_sided(o, h, lo, c, start, up, dn, stop_long, stop_short, target_long, target_short, exit_idx):
    """Stop entries at up (long) and dn (short) from bar `start`; the first triggered. None if neither by exit."""
    for j in range(start, exit_idx + 1):
        hit_up, hit_dn = h[j] >= up, lo[j] <= dn
        if not (hit_up or hit_dn):
            continue
        d = 1 if hit_up else -1
        lvl = up if d > 0 else dn
        entry = (max(o[j], lvl) if d > 0 else min(o[j], lvl)) + d * TICK
        stop = stop_long if d > 0 else stop_short
        if hit_up and hit_dn:  # both in one bar: a long that is stopped
            return pnl(1, entry, stop_long - TICK)
        target = target_long if d > 0 else target_short
        return pnl(d, entry, fill_from(o, h, lo, c, j, d, entry, stop, target, exit_idx))
    return None


def vwap_fade(o, h, lo, c, v, k):
    tp = (h + lo + c) / 3
    w = v if np.nansum(v) > 0 else np.ones_like(tp)
    cw = np.cumsum(w)
    vw = np.cumsum(w * tp) / cw
    sd = np.sqrt(np.maximum(np.cumsum(w * tp * tp) / cw - vw * vw, 0.0))
    for j in range(60, 300):
        if sd[j] <= 0:
            continue
        if c[j] > vw[j] + k * sd[j]:
            return market(o, h, lo, c, j + 1, -1, vw[j] + (k + 1) * sd[j], vw[j], N - 1)
        if c[j] < vw[j] - k * sd[j]:
            return market(o, h, lo, c, j + 1, 1, vw[j] - (k + 1) * sd[j], vw[j], N - 1)
    return None


def day_rules(S, k, gap_avg, m15_avg, atr14):
    """{rule: $} for session k (only the rules that trade)."""
    day, nth, o, h, lo, c, v = S[k]
    out = {}
    if k >= 1:
        _, _, po, ph, pl, pc, _ = S[k - 1]
        y_hi, y_lo, y_close = ph.max(), pl.min(), pc[-1]
    if k >= 7:
        rng = [S[j][3].max() - S[j][4].min() for j in range(k - 7, k)]
        f_hi, f_lo = h[:30].max(), lo[:30].min()
        mid30 = (f_hi + f_lo) / 2
        if rng[-1] <= min(rng):
            r = two_sided(o, h, lo, c, 30, f_hi, f_lo, f_lo, f_hi, None, None, N - 1)
            if r is not None:
                out["R01"] = r
            r = two_sided(o, h, lo, c, 30, f_hi, f_lo, mid30, mid30, None, None, N - 1)
            if r is not None:
                out["R03"] = r
        if rng[-1] <= min(rng[-4:]):
            r = two_sided(o, h, lo, c, 30, f_hi, f_lo, f_lo, f_hi, None, None, N - 1)
            if r is not None:
                out["R02"] = r
    if k >= 2:
        pph, ppl = S[k - 2][3].max(), S[k - 2][4].min()
        if y_hi <= pph and y_lo >= ppl:
            mid = (y_hi + y_lo) / 2
            r = two_sided(o, h, lo, c, 30, y_hi, y_lo, mid, mid, None, None, N - 1)
            if r is not None:
                out["R04"] = r
            r = two_sided(o, h, lo, c, 30, y_hi, y_lo, y_lo, y_hi, None, None, N - 1)
            if r is not None:
                out["R05"] = r
    ib_hi, ib_lo = h[:60].max(), lo[:60].min()
    ib, ib_mid = ib_hi - ib_lo, (ib_hi + ib_lo) / 2
    for rule, m in (("R06", 1.0), ("R07", 2.0), ("R08", None)):
        tl = ib_hi + m * ib if m else None
        ts = ib_lo - m * ib if m else None
        r = two_sided(o, h, lo, c, 60, ib_hi, ib_lo, ib_mid, ib_mid, tl, ts, N - 1)
        if r is not None:
            out[rule] = r
    if m15_avg is not None and m15_avg > 0:
        mv = c[14] - o[0]
        d = 1 if mv > 0 else -1
        for rule, x, ex in (("R09", 1.5, 89), ("R10", 1.5, N - 1), ("R11", 2.0, 89), ("R12", 2.0, N - 1)):
            if abs(mv) > x * m15_avg:
                out[rule] = market(o, h, lo, c, 15, d, o[0], None, ex)
    if k >= 1 and gap_avg is not None and gap_avg > 0:
        gap = o[0] - y_close
        d = 1 if gap > 0 else -1
        if gap != 0 and d * (c[4] - o[0]) > 0:
            for rule, t, ex in (("R13", 0.5, 59), ("R14", 0.5, N - 1), ("R15", 1.0, 59), ("R16", 1.0, N - 1)):
                if abs(gap) > t * gap_avg:
                    out[rule] = market(o, h, lo, c, 5, d, o[0], None, ex)
    if k >= 1 and atr14 is not None and y_lo < o[0] < y_hi:
        for rule, f in (("R17", 0.5), ("R18", 0.25)):
            r = two_sided(o, h, lo, c, 30, y_hi, y_lo, y_hi - f * atr14, y_lo + f * atr14, None, None, N - 1)
            if r is not None:
                out[rule] = r
    if k >= 3:
        dirs = [np.sign(S[j][5][-1] - S[j][2][0]) for j in range(k - 3, k)]
        f30 = np.sign(c[29] - o[0])
        if dirs[0] != 0 and dirs[0] == dirs[1] == dirs[2] == f30:
            d = int(dirs[0])
            out["R19"] = market(o, h, lo, c, 30, d, None, None, N - 1)
            out["R20"] = market(o, h, lo, c, 30, d, lo[:30].min() if d > 0 else h[:30].max(), None, N - 1)
    morning, lunch = c[119] - o[0], c[209] - c[119]
    if morning != 0 and np.sign(lunch) == -np.sign(morning) and abs(lunch) > 0.5 * abs(morning):
        d = 1 if morning > 0 else -1
        out["R21"] = market(o, h, lo, c, 210, d, None, None, N - 1)
        ext = lo[120:210].min() if d > 0 else h[120:210].max()
        out["R22"] = market(o, h, lo, c, 210, d, ext, None, N - 1)
    for rule, kk in (("R23", 2.0), ("R24", 2.5)):
        r = vwap_fade(o, h, lo, c, v, kk)
        if r is not None:
            out[rule] = r
    return out


RULES = [f"R{i:02d}" for i in range(1, 25)]


def run(path: str) -> pd.DataFrame:
    S = sessions(path)
    rows = []
    for k in range(len(S)):
        day, nth = S[k][0], S[k][1]
        gaps = [abs(S[j][2][0] - S[j - 1][5][-1]) for j in range(max(1, k - 14), k) if S[j][1] != 1]
        gap_avg = float(np.mean(gaps)) if len(gaps) >= 10 else None
        m15 = [abs(S[j][5][14] - S[j][2][0]) for j in range(max(0, k - 14), k)]
        m15_avg = float(np.mean(m15)) if len(m15) == 14 else None
        rng = [S[j][3].max() - S[j][4].min() for j in range(max(0, k - 14), k)]
        atr14 = float(np.mean(rng)) if len(rng) == 14 else None
        if k < 14:
            continue
        for rule, val in day_rules(S, k, gap_avg, m15_avg, atr14).items():
            rows.append((day, nth, rule, val))
    df = pd.DataFrame(rows, columns=["day", "nth", "rule", "pnl"])
    return df[df.nth != 1]


def tstat(x: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 30:
        return float(np.mean(x)) if len(x) else 0.0, 0.0, 1.0
    t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))
    return float(x.mean()), float(t), math.erfc(abs(t) / math.sqrt(2))


def bh(pvals: dict[str, float], q: float = 0.05) -> set[str]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, cut = len(items), 0
    for i, (_, p) in enumerate(items, 1):
        if p <= i / m * q:
            cut = i
    return {r for r, _ in items[:cut]}


def table(df: pd.DataFrame, y0, y1, years_per: float):
    d = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
    out = {}
    for r in RULES:
        x = d[d.rule == r].pnl.to_numpy()
        mean, t, p = tstat(x)
        win = 100 * np.mean(x > 0) if len(x) else 0.0
        out[r] = {"trades": len(x), "trades/week": len(x) / (years_per * 52), "win %": win, "$/trade": mean,
                  "$/week": x.sum() / (years_per * 52), "t": t, "p": p}
    return pd.DataFrame(out).T


def checks() -> None:
    """Hand-made bars for the fill rules."""
    o = np.full(N, 100.0)
    h, lo, c = o + 0.5, o - 0.5, o.copy()
    # long stop entry at 101 on bar 40, target 103 on bar 50, exit there
    h2, lo2, c2, o2 = h.copy(), lo.copy(), c.copy(), o.copy()
    h2[40], c2[40] = 101.5, 101.0
    o2[41:], c2[41:], h2[41:], lo2[41:] = 101.0, 101.0, 101.5, 100.5
    h2[50] = 103.5
    r = two_sided(o2, h2, lo2, c2, 30, 101.0, 98.0, 99.0, 102.0, 103.0, None, N - 1)
    assert abs(r - ((103.0 - 101.25) * PV - FEE)) < 1e-9, r
    # the fill bar also reaches the stop: stopped at the stop
    lo3 = lo2.copy()
    lo3[40] = 98.9
    r = two_sided(o2, h2, lo3, c2, 30, 101.0, 98.0, 99.0, 102.0, 103.0, None, N - 1)
    assert abs(r - ((99.0 - 0.25 - 101.25) * PV - FEE)) < 1e-9, r
    # one bar through both levels: a stopped long
    h4, lo4 = h.copy(), lo.copy()
    h4[35], lo4[35] = 101.5, 97.5
    r = two_sided(o, h4, lo4, c, 30, 101.0, 98.0, 99.0, 102.0, None, None, N - 1)
    assert abs(r - ((99.0 - 0.25 - 101.25) * PV - FEE)) < 1e-9, r
    # market entry, held to the close
    c5 = c.copy()
    c5[-1] = 104.0
    r = market(o, h, lo, c5, 15, 1, 90.0, None, N - 1)
    assert abs(r - ((104.0 - 0.25 - 100.25) * PV - FEE)) < 1e-9, r
    # market entry, stop and target in one bar: the stop
    h6, lo6 = h.copy(), lo.copy()
    h6[20], lo6[20] = 106.0, 95.0
    r = market(o, h6, lo6, c, 15, 1, 96.0, 105.0, N - 1)
    assert abs(r - ((96.0 - 0.25 - 100.25) * PV - FEE)) < 1e-9, r
    # a gap through the stop fills at the open
    o7, h7, lo7, c7 = o.copy(), h.copy(), lo.copy(), c.copy()
    o7[20], h7[20], lo7[20], c7[20] = 94.0, 94.5, 93.5, 94.0
    r = market(o7, h7, lo7, c7, 15, 1, 96.0, None, N - 1)
    assert abs(r - ((94.0 - 0.25 - 100.25) * PV - FEE)) < 1e-9, r
    # BH
    assert bh({"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5}) == {"a", "b"}
    print("rule checks pass")


def main() -> None:
    checks()
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=2) as pool:
        idx, fut = pool.map(run, [nsx, nq])
    disc = table(idx, 2011, 2018, 8.0)
    print("\nDiscovery 2011-2018 (index), 1 MNQ")
    print(disc.round(3).to_string())
    surv = bh(disc.p.to_dict())
    print(f"\nBenjamini-Hochberg q=0.05 over {len(RULES)} rules: {sorted(surv) or 'none'}")
    cands = [r for r in surv if disc.loc[r, "$/trade"] > 0]
    neg = [r for r in surv if disc.loc[r, "$/trade"] <= 0]
    print(f"positive (candidate edges): {cands or 'none'}; significantly negative: {neg or 'none'}")
    hold = table(idx, 2019, 2026, 7.75)
    nqt = table(fut, 2015, 2025, 10.5)
    print("\nHoldout 2019 - Sep 2026 (index), all rules for reference")
    print(hold.round(3).to_string())
    print("\nNQ futures 2015 - Jul 2025, all rules for reference")
    print(nqt.round(3).to_string())
    final = []
    for r in cands:
        ok1 = hold.loc[r, "$/trade"] > 0 and hold.loc[r, "t"] >= 2.0
        ok2 = ok1 and nqt.loc[r, "$/trade"] > 0 and nqt.loc[r, "t"] >= 1.5
        print(f"{r}: 2019-26 t {hold.loc[r, 't']:.2f} ({'PASS' if ok1 else 'FAIL'}); "
              f"NQ t {nqt.loc[r, 't']:.2f} ({'PASS' if ok2 else 'FAIL' if ok1 else 'not reached'})")
        if ok2:
            final.append(r)
    print(f"\nFinal survivors: {final or 'none'}")


if __name__ == "__main__":
    main()
