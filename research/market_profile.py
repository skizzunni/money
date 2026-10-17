"""Round ninety-six: Market Profile (TPO) setups on the Nasdaq, with a strict multiple-testing protocol.

    python research/market_profile.py nsx1m_scaled.pkl nq1m_scaled.pkl

A strategy family not tested in the earlier rounds: yesterday's regular-session Market Profile. Everything below was
fixed before looking at any result.

Data and fills: research/setups.py's sessions (1-minute bars 09:30-15:59 New York, rescaled month by month to today's
level; a session counts with >= 370 of its 390 minutes, missing minutes repeat the last close) and its fill rules (1
tick of slippage on market and stop fills, $1.24 fees a contract a round trip, take-profits fill at their price once
price trades a tick through, a bar reaching both stop and target counts the stop, a gap through the stop fills at the
open). Trades on the first session of each month are dropped (the rescaling moves yesterday's profile there).

Profile of the previous counted session (09:30-15:59, nothing from today): every minute adds one TPO to each 1-point
price bin from its low to its high. POC = the bin with the most TPOs (ties: the one nearest the session's mid-range).
Value area = grown from the POC one bin at a time toward the side with more TPOs (ties: up) until it holds >= 70% of
all TPOs; VAL = its lowest bin's floor, VAH = its highest bin's floor + 1. VA height = VAH - VAL. Prices are the
scaled series (the profile and today share one scale factor except across a month boundary, which is dropped).

Today's bars: 30-minute bars b = 0..12 (b covers minutes 30b..30b+29; close = minute 30b+29). Entries are market
orders at the next minute's open, only up to 15:00 (minute 330); everything is flat at 15:59. Size: floor($300 / (stop
distance in points x $2)), 1 to 10 MNQ; no trade if the stop is more than 40 points away or on the wrong side, or the
target on the wrong side. At most one trade per rule per day.
  80% rule (open outside yesterday's VA, then back inside):
    R01  two consecutive 30-minute closes inside the VA; target the far VA edge; stop a tick beyond the second bar's
         extreme (its high for a short, its low for a long)
    R02  as R01, stop 25 points
    R03  one 30-minute close inside the VA; target the far edge; stop beyond that bar's extreme
    R04  as R03, stop 25 points
    R13  as R01, target yesterday's POC
    R14  as R03, target yesterday's POC
  Fade to the POC (open outside the VA, the first 15 / 30 minutes close back toward the VA, i.e. below the open when
  the open is above the VAH, above it when below the VAL): enter toward the POC; stop a tick beyond the session's
  extreme so far; target the POC
    R05  after the first 15 minutes      R06  after the first 30 minutes
  Acceptance breakout (open inside the VA, then closes outside it, the first time):
    R07  two consecutive 30-minute closes above the VAH (below the VAL): trade that way; stop VAH - 5 (VAL + 5);
         target 1 x VA height from the entry
    R08  as R07, held to the close
    R09  one 30-minute close outside; target 1 x VA height
    R10  as R09, held to the close
  POC magnet (at 11:00, the 10:59 close more than 1 x VA height from yesterday's POC and the last 30 minutes moving
  toward it): trade toward the POC; target the POC
    R11  stop 25 points          R12  stop a tick beyond the session's extreme on the far side so far
A volume-profile variant needs volume, which the index data doesn't have, so it can't be discovered here: left out.

Protocol: discovery on the index 2011-2018: for each rule $ a trade, winners %, and the t-stat of the daily P/L (every
session, 0 on days without a trade); Benjamini-Hochberg at q = 0.05 across all 14 rules. Survivors with a positive mean
get one look at the index 2019 - Sep 2026 (t >= 2, same sign), then NQ futures 2015 - Jul 2025 (t >= 1.5). A final
survivor would then be measured alone and with the bot on one 50K Apex intraday-trail account (winners, $ a week, worst
losing stretch, green / red days, the evaluation pass / bust rate, payouts per evaluation, the funded first payout
within 20 / 40 sessions).
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import setups as S  # noqa: E402

N, TICK = S.N, S.TICK
RULES = [f"R{i:02d}" for i in range(1, 15)]
LAST_ENTRY = 330  # minute index of 15:00
RISK = 300.0


def profile(h, lo):
    """(POC, VAL, VAH) of one session from its 1-minute highs and lows (1-point bins)."""
    base = math.floor(np.nanmin(lo))
    top = math.floor(np.nanmax(h))
    tpo = np.zeros(top - base + 1)
    for hi_, lo_ in zip(h, lo, strict=True):
        tpo[math.floor(lo_) - base: math.floor(hi_) - base + 1] += 1
    mid = (np.nanmax(h) + np.nanmin(lo)) / 2 - base
    best = np.flatnonzero(tpo == tpo.max())
    poc = int(best[np.argmin(np.abs(best + 0.5 - mid))])
    a = b = poc
    held, total = tpo[poc], tpo.sum()
    while held < 0.7 * total:
        up = tpo[b + 1] if b + 1 < len(tpo) else -1.0
        dn = tpo[a - 1] if a - 1 >= 0 else -1.0
        if up >= dn:
            b += 1
            held += up
        else:
            a -= 1
            held += dn
    return base + poc + 0.5, float(base + a), float(base + b + 1)


def size(entry, stop):
    dist = abs(entry - stop)
    if dist <= 0 or dist > 40:
        return 0
    return int(min(10, max(1, math.floor(RISK / (dist * S.PV)))))


def trade(o, h, lo, c, i, d, stop, target):
    """A market entry at minute i in direction d; $ for the sized position, or None if not taken."""
    if i > LAST_ENTRY:
        return None
    entry = o[i] + d * TICK
    if d * (entry - stop) <= 0 or (target is not None and d * (target - entry) <= 0):
        return None
    n = size(entry, stop)
    if n == 0:
        return None
    return n * S.pnl(d, entry, S.fill_from(o, h, lo, c, i, d, entry, stop, target, N - 1, stop_on_first=False))


def day_rules(o, h, lo, c, poc, val, vah):
    out = {}
    hgt = vah - val
    cl30 = [c[30 * b + 29] for b in range(13)]
    hi30 = [h[30 * b: 30 * b + 30].max() for b in range(13)]
    lo30 = [lo[30 * b: 30 * b + 30].min() for b in range(13)]
    op = o[0]
    inside = [val <= x <= vah for x in cl30]
    # the 80% rule
    if op > vah or op < val:
        d = -1 if op > vah else 1
        far = val if d < 0 else vah
        for need, rules in ((2, ("R01", "R02", "R13")), (1, ("R03", "R04", "R14"))):
            for b in range(need - 1, LAST_ENTRY // 30):  # entries at minute 30b + 30 <= 15:00
                if all(inside[b - k] for k in range(need)):
                    i = 30 * b + 30
                    ext = hi30[b] + TICK if d < 0 else lo30[b] - TICK
                    out[rules[0]] = trade(o, h, lo, c, i, d, ext, far)
                    out[rules[1]] = trade(o, h, lo, c, i, d, o[i] - d * 25.0, far)
                    out[rules[2]] = trade(o, h, lo, c, i, d, ext, poc)
                    break
        # fade to the POC
        for rule, m in (("R05", 14), ("R06", 29)):
            back = c[m] < op if op > vah else c[m] > op
            if back:
                i = m + 1
                ext = h[:m + 1].max() + TICK if d < 0 else lo[:m + 1].min() - TICK
                out[rule] = trade(o, h, lo, c, i, d, ext, poc)
    else:
        # acceptance breakout
        for need, (r_tgt, r_close) in ((2, ("R07", "R08")), (1, ("R09", "R10"))):
            for b in range(need - 1, LAST_ENTRY // 30):
                up = all(cl30[b - k] > vah for k in range(need))
                dn = all(cl30[b - k] < val for k in range(need))
                if up or dn:
                    d = 1 if up else -1
                    i = 30 * b + 30
                    stop = vah - 5 if d > 0 else val + 5
                    out[r_tgt] = trade(o, h, lo, c, i, d, stop, o[i] + d * TICK + d * hgt)
                    out[r_close] = trade(o, h, lo, c, i, d, stop, None)
                    break
    # POC magnet at 11:00
    m = 89  # the 10:59 bar's close
    if abs(c[m] - poc) > hgt and hgt > 0:
        d = 1 if c[m] < poc else -1
        if d * (c[m] - c[m - 30]) > 0:
            i = m + 1
            out["R11"] = trade(o, h, lo, c, i, d, o[i] - d * 25.0, poc)
            ext = h[:m + 1].max() + TICK if d < 0 else lo[:m + 1].min() - TICK
            out["R12"] = trade(o, h, lo, c, i, d, ext, poc)
    return {r: v for r, v in out.items() if v is not None}


def run(path: str) -> pd.DataFrame:
    sess = S.sessions(path)
    rows = []
    for k in range(1, len(sess)):
        day, nth, o, h, lo, c, _ = sess[k]
        if nth == 1:
            continue  # yesterday's profile is on another month's scale
        poc, val, vah = profile(sess[k - 1][3], sess[k - 1][4])
        res = day_rules(o, h, lo, c, poc, val, vah)
        for r in RULES:
            rows.append((day, r, res.get(r, 0.0), r in res))
    return pd.DataFrame(rows, columns=["day", "rule", "pnl", "traded"])


def table(df, y0, y1):
    d = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
    weeks = d.day.nunique() / 5
    out = {}
    for r in RULES:
        x = d[d.rule == r]
        tr = x[x.traded].pnl.to_numpy()
        daily = x.pnl.to_numpy()
        t = daily.mean() / (daily.std(ddof=1) / math.sqrt(len(daily))) if daily.std() > 0 else 0.0
        out[r] = {"trades": len(tr), "trades/week": len(tr) / weeks, "win %": 100 * np.mean(tr > 0) if len(tr) else 0,
                  "$/trade": tr.mean() if len(tr) else 0.0, "$/week": daily.sum() / weeks, "t": t,
                  "p": math.erfc(abs(t) / math.sqrt(2))}
    return pd.DataFrame(out).T


def checks() -> None:
    # profile: 390 minutes; 300 of them inside 104-106, the rest spread 95-115
    h = np.full(390, 105.6)
    lo = np.full(390, 104.4)
    h[:45], lo[:45] = 115.5, 110.2
    h[45:90], lo[45:90] = 99.5, 95.2
    poc, val, vah = profile(h, lo)
    # ties at 104 and 105 -> the bin nearer the mid-range (105.35): 105; grown down to 104 (300 TPOs), then up through
    # the empty bins to 110-113 (45 each) until 70% of 1,095 TPOs
    assert (poc, val, vah) == (105.5, 104.0, 114.0), (poc, val, vah)
    # the 80% rule, short: open above the VA (VAL 100, VAH 110, POC 105), two 30-minute closes inside, target 100
    o = np.full(N, 112.0)
    hh, ll, cc = o + 0.5, o - 0.5, o.copy()
    for j in range(30, 90):
        o[j], hh[j], ll[j], cc[j] = 108.0, 108.5, 107.5, 108.0
    for j in range(90, N):
        o[j], hh[j], ll[j], cc[j] = 108.0, 108.5, 107.5, 108.0
    ll[200] = 99.0  # a tick through the target later
    r = day_rules(o, hh, ll, cc, 105.0, 100.0, 110.0)
    entry = 108.0 - TICK
    stop = 108.5 + TICK  # the second inside bar's high + a tick
    n = size(entry, stop)
    assert abs(r["R01"] - n * ((entry - 100.0) * S.PV - S.FEE)) < 1e-9, (r["R01"], n)
    assert abs(r["R13"] - n * ((entry - 105.0) * S.PV - S.FEE)) < 1e-9, r["R13"]
    assert "R07" not in r and "R05" not in r  # opened outside: no breakout trade; the first 15 minutes didn't come back
    # acceptance breakout, long: open inside, two closes above the VAH 110, stop 105, target 1 x VA height
    o2 = np.full(N, 106.0)
    h2, l2, c2 = o2 + 0.5, o2 - 0.5, o2.copy()
    for j in range(30, N):
        o2[j], h2[j], l2[j], c2[j] = 111.0, 111.5, 110.5, 111.0
    h2[150] = 125.0
    r = day_rules(o2, h2, l2, c2, 105.0, 100.0, 110.0)
    e = 111.0 + TICK
    n = size(e, 105.0)
    assert abs(r["R07"] - n * ((e + 10.0 - e) * S.PV - S.FEE)) < 1e-9, r["R07"]
    assert abs(r["R08"] - n * ((111.0 - TICK - e) * S.PV - S.FEE)) < 1e-9, r["R08"]
    # sizing: 10-point stop -> floor(300 / 20) = 15 -> 10; 40.25 points -> skipped
    assert size(100.0, 90.0) == 10 and size(100.0, 59.75) == 0 and size(100.0, 70.0) == 5
    print("profile and rule checks pass")


def main() -> None:
    checks()
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=2) as pool:
        idx, fut = pool.map(run, [nsx, nq])
    disc = table(idx, 2011, 2018)
    print("\nDiscovery 2011-2018 (index), sized $300 a trade")
    print(disc.round(3).to_string())
    surv = S.bh(disc.p.to_dict())
    print(f"\nBenjamini-Hochberg q=0.05 over {len(RULES)} rules: {sorted(surv) or 'none'}")
    cands = [r for r in surv if disc.loc[r, "$/trade"] > 0]
    print(f"positive: {cands or 'none'}; negative: {[r for r in surv if r not in cands] or 'none'}")
    hold, nqt = table(idx, 2019, 2026), table(fut, 2015, 2025)
    print("\nIndex 2019 - Sep 2026, for reference")
    print(hold.round(3).to_string())
    print("\nNQ futures 2015 - Jul 2025, for reference")
    print(nqt.round(3).to_string())
    final = []
    for r in cands:
        ok1 = hold.loc[r, "$/trade"] > 0 and hold.loc[r, "t"] >= 2.0
        ok2 = ok1 and nqt.loc[r, "$/trade"] > 0 and nqt.loc[r, "t"] >= 1.5
        print(f"{r}: 2019-26 t {hold.loc[r, 't']:.2f} ({'PASS' if ok1 else 'FAIL'}); NQ t {nqt.loc[r, 't']:.2f}")
        if ok2:
            final.append(r)
    print(f"\nFinal survivors: {final or 'none'}")


if __name__ == "__main__":
    main()
