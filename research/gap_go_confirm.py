"""Round seventy-two: a pre-registered confirmation of 'gap and go' on markets it was never tuned on.

    python research/gap_go_confirm.py

Round seventy-one (research/setups.py) found 'gap and go' on the Nasdaq positive on 2011-18, 2019-26 and NQ futures
(R14: t 2.0 / 3.4 / 3.5) but not past its multiple-testing bar, and it was picked out of 24 rules, so the Nasdaq's
periods are used up. A fair test needs data the rule has never touched: other stock indexes, each in its own cash
session. Everything below is fixed before running.

Rule (R14 of research/setups.py, unchanged): gap = the session's first-minute open minus the previous session's
last-minute close. Its 14-session average |gap| (past sessions only, at least 10 of them). If |gap| > 0.5 x that average
and the close of the session's 5th minute (minute index 4) is beyond the first-minute open in the gap's direction:
enter at the 6th minute's open (index 5) in the gap's direction (plus slippage), stop at the first-minute open (a bar
reaching it fills at the stop, or at the bar's open if it opened past it, minus slippage), otherwise exit at the close
of the session's last minute (minus slippage). One trade a day at most.

Markets and cash sessions (from the 1-minute CFD data, converted to each exchange's own time; the files are stamped in
New York time, as rounds sixty-eight and sixty-nine established):
  S&P 500 (scratchpad spx1m.pkl, unscaled): 09:30-15:59 New York, 390 minutes.
  DAX (HistData GRXEUR): 09:00-17:29 Frankfurt, 510 minutes.
  Nikkei 225 (HistData JPXJPY): 09:00-11:29 and 12:30-14:59 Tokyo, 300 minutes (the morning and afternoon sessions;
    the Tokyo close moved to 15:30 in November 2024; 14:59 is kept throughout as the session's last minute so the rule
    is the same in every year).
A session counts when at least 95% of its minutes have a bar; a missing minute repeats the last close (as setups.py).
"Yesterday" is the previous counted session. The data is unscaled, so there are no monthly rescaling gaps and every
session's trade counts (round seventy-one dropped the first session of each month only because of its rescaling).

Costs: the same as MNQ's at today's level, as a share of price. On MNQ a round trip costs $1.24 (0.62 points) plus a
tick (0.25 points) of slippage on entry and exit, at about 31,900 (the Nasdaq-100 at the end of the data): slippage is
0.25 / 31,900 = 0.078 bps of price a side and fees 0.62 / 31,900 = 0.194 bps, 0.351 bps a round trip. Each day's
slippage in points is that share of the previous close. Results are in dollars for one MNQ-sized position at today's
Nasdaq level: P/L share of price x 31,900 x $2, minus $1.24.

Period: 2011-01-01 to 2026-09-30, all at once (the rule is fixed, nothing is fitted).
Pass bar (fixed before running): t >= 2.0 with a positive mean in at least 2 of the 3 markets, and no market with
t <= -2.0. t is the mean trade over its standard error (one trade a day at most).
Check before running: the same code on the Nasdaq (scratchpad nsx1m_scaled.pkl, first sessions of each month dropped
as setups.py does) must reproduce setups.py's R14 trades.

Only if it passes: MNQ gap and go sized so the stop risks at most $200 (contracts = floor(200 / (stop distance x $2)),
1 to 10), combined with the bot (v1.6, 4 MNQ, $200, 3 losers, take-profit from the fill) on one 50K account:
trades a week, winners, $ a week, worst losing stretch, the 50K intraday evaluation's 30-day pass/bust rate and the
payouts per evaluation, bot alone against bot + gap and go, on 2011-18, 2019-26 and NQ futures.
"""
from __future__ import annotations

import glob
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

SP = "/tmp/claude-0/-home-user-money/b0ea31b5-d9fc-525a-a114-db6430eff3ed/scratchpad"
NY = "America/New_York"
P_REF, PV, FEE, TICK_PTS = 31900.0, 2.0, 1.24, 0.25
SLIP_FRAC = TICK_PTS / P_REF  # a side
MARKETS = {
    "S&P 500": ("spx", NY, [(570, 960)]),
    "DAX": ("GRXEUR", "Europe/Berlin", [(540, 1050)]),
    "Nikkei 225": ("JPXJPY", "Asia/Tokyo", [(540, 690), (750, 900)]),
}


def load(name: str) -> pd.DataFrame:
    src, tz, _ = MARKETS[name]
    if src == "spx":
        df = pd.read_pickle(f"{SP}/spx1m.pkl")[["open", "high", "low", "close"]]
    else:
        frames = []
        for f in sorted(glob.glob(f"{SP}/histdata_markets/{src}/raw/DAT_ASCII_{src}_M1_*.csv")):
            d = pd.read_csv(f, sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"])
            d["ts"] = pd.to_datetime(d["ts"], format="%Y%m%d %H%M%S")
            frames.append(d)
        df = pd.concat(frames).drop_duplicates("ts").sort_values("ts").set_index("ts")
        df.index = df.index.tz_localize(NY, ambiguous="NaT", nonexistent="shift_forward")
        df = df[~df.index.isna()][["open", "high", "low", "close"]].astype(float)
    return df.tz_convert(tz)


def sessions(df: pd.DataFrame, windows) -> list:
    """[(date, o, h, l, c)] arrays on the session's minute grid, for sessions with >= 95% of minutes."""
    mins = np.concatenate([np.arange(a, b) for a, b in windows])
    pos = {m: i for i, m in enumerate(mins)}
    n = len(mins)
    m = df.index.hour * 60 + df.index.minute
    keep = np.isin(m, mins)
    d = df[keep]
    mm = m[keep]
    out = []
    for day, idx in pd.Series(np.arange(len(d)), index=d.index.tz_localize(None).normalize()).groupby(level=0):
        rows = idx.to_numpy()
        if len(rows) < 0.95 * n:
            continue
        a = np.full((4, n), np.nan)
        a[:, [pos[x] for x in mm[rows]]] = d.iloc[rows][["open", "high", "low", "close"]].to_numpy().T
        if np.isnan(a[0, 0]):
            continue
        for j in range(1, n):
            if np.isnan(a[3, j]):
                a[0:4, j] = a[3, j - 1]
        out.append((pd.Timestamp(day), *a))
    return out


def trade(o, h, lo, c, d, slip):
    """Market entry at o[5], stop at o[0], exit at the last close: P/L in points (slippage in)."""
    entry = o[5] + d * slip
    stop = o[0]
    for j in range(5, len(c)):
        if (d > 0 and lo[j] <= stop) or (d < 0 and h[j] >= stop):
            px = min(o[j], stop) if d > 0 else max(o[j], stop)
            return d * (px - d * slip - entry)
    return d * (c[-1] - d * slip - entry)


def gap_go(S, drop_first_of_month=False, slip_points=None):
    """[(date, $ for one MNQ-sized position at today's Nasdaq level, direction, stop distance share)]."""
    nth = []
    prev = None
    for s in S:
        key = (s[0].year, s[0].month)
        nth.append(nth[-1] + 1 if nth and key == prev else 1)
        prev = key
    rows = []
    for k in range(14, len(S)):  # as setups.py: from the 15th session on
        gaps = [abs(S[j][1][0] - S[j - 1][4][-1]) for j in range(max(1, k - 14), k)
                if not (drop_first_of_month and nth[j] == 1)]
        if len(gaps) < 10:
            continue
        avg = float(np.mean(gaps))
        day, o, h, lo, c = S[k]
        y_close = S[k - 1][4][-1]
        gap = o[0] - y_close
        if avg <= 0 or gap == 0 or abs(gap) <= 0.5 * avg:
            continue
        d = 1 if gap > 0 else -1
        if d * (c[4] - o[0]) <= 0:
            continue
        if drop_first_of_month and nth[k] == 1:
            continue
        if slip_points is not None:  # MNQ points (the Nasdaq check)
            pts = trade(o, h, lo, c, d, slip_points)
            usd = pts * PV - FEE
        else:
            slip = SLIP_FRAC * y_close
            pts = trade(o, h, lo, c, d, slip)
            usd = pts / y_close * P_REF * PV - FEE
        rows.append((day, usd, d, abs(o[5] - o[0]) / y_close))
    return pd.DataFrame(rows, columns=["day", "usd", "dir", "stop_share"])


def check_against_setups() -> None:
    import setups
    nas = setups.run(f"{SP}/nsx1m_scaled.pkl")
    r14 = nas[nas.rule == "R14"].set_index("day").pnl
    S = [(s[0], s[2], s[3], s[4], s[5]) for s in setups.sessions(f"{SP}/nsx1m_scaled.pkl")]
    mine = gap_go(S, drop_first_of_month=True, slip_points=TICK_PTS).set_index("day").usd
    assert len(mine) == len(r14) and (mine.index == r14.index).all(), (len(mine), len(r14))
    assert np.allclose(mine.to_numpy(), r14.to_numpy(), atol=1e-9)
    print(f"check: reproduces setups.py R14 on the Nasdaq ({len(mine)} trades)")


def stats(x: np.ndarray) -> tuple[float, float]:
    t = x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 else 0.0
    return float(x.mean()), float(t)


def market_job(name: str):
    _, _, windows = MARKETS[name]
    df = load(name)
    df = df[(df.index >= pd.Timestamp("2010-11-01", tz=df.index.tz)) &
            (df.index < pd.Timestamp("2026-10-01", tz=df.index.tz))]
    S = sessions(df, windows)
    tr = gap_go(S)
    tr = tr[(tr.day >= "2011-01-01") & (tr.day <= "2026-09-30")]
    return name, tr, len(S)


def main() -> None:
    check_against_setups()
    with ProcessPoolExecutor(max_workers=3) as pool:
        res = list(pool.map(market_job, list(MARKETS)))
    pd.set_option("display.width", 200)
    rows, passed, bad = [], 0, 0
    for name, tr, n_sess in res:
        x = tr.usd.to_numpy()
        mean, t = stats(x)
        years = (tr.day.max() - tr.day.min()).days / 365.25 if len(tr) else 0
        rows.append({"market": name, "sessions": n_sess, "trades": len(x), "trades/year": len(x) / years,
                     "$/trade": mean, "t": t, "win %": 100 * np.mean(x > 0),
                     "t 2011-18": stats(tr[tr.day.dt.year <= 2018].usd.to_numpy())[1],
                     "t 2019-26": stats(tr[tr.day.dt.year >= 2019].usd.to_numpy())[1],
                     "median stop, % of price": 100 * tr.stop_share.median()})
        passed += t >= 2.0 and mean > 0
        bad += t <= -2.0
    print(f"\ncosts: {1e4 * SLIP_FRAC:.3f} bps a side slippage + {1e4 * FEE / PV / P_REF:.3f} bps fees "
          f"= {1e4 * (2 * SLIP_FRAC + FEE / PV / P_REF):.3f} bps a round trip; $ for one MNQ at {P_REF:,.0f}")
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    ok = passed >= 2 and bad == 0
    verdict = "PASS" if ok else "FAIL"
    print(f"\n{passed} of 3 markets with t >= 2.0 and a positive mean; {bad} with t <= -2.0: {verdict}")


if __name__ == "__main__":
    main()
