"""Round sixty-six: the bot's rules on other markets Apex trades on the same account (gold, silver, crude, euro).

    python -I research/other_markets.py <scratchpad>

The user wants more money a week from one 50K Apex account. Every variation of the Nasdaq bot has been tried (rounds
59-65). Intraday momentum is documented across many futures markets, and gold's, oil's and the euro's trend days are
not the Nasdaq's: if the same rules have an edge there, a second market adds trades on days the Nasdaq bot sits out,
on the same account, without adding size to the same moves.

Data: HistData free 1-minute bars (CFD and spot prices, New York clock: data releases sit at 08:30 and the oil
inventory report at 10:30 in January and July alike), XAUUSD, XAGUSD, WTIUSD, EURUSD, 2010 - Sep 2026; HistData has
no WTIUSD files for Jan 2024 - May 2026. Prices rescaled month by month to the Sep 2026 level and rounded to the tick
(as research/timeframes.py does for the Nasdaq); trades entered on a month's first session are dropped (the fake gap
from rescaling). Crude: sessions with any price at or below $5 before rescaling are dropped (April 2020).

Rules: mnqbot/noise.py v1.6 exactly (14-session noise at each check, line stop 0.24 noise units past the line, max loss
from the fill, take-profit 1.5 noise units working from the fill, lock at +1 max loss to entry + 2 ticks, no new
entries after 3 losers a day, market orders at the next bar's open, stop first when a bar reaches stop and target,
flat at the session close), on 1-minute bars, with each market's regular session (New York time):
  gold MGC ($10 a point, tick 0.10) and silver SIL ($1,000 a point, tick 0.005): 08:20-13:30, checks 09:00-13:00;
  crude MCL ($100 a point, tick 0.01): 09:00-14:30, checks 09:30-14:00;
  euro M6E ($12,500 a point, tick 0.0001): 08:20-15:00, checks 09:00-14:30.
No Fed rule and no skip dates for these markets. Costs a contract: $1.24 round trip (MGC, M6E), $1.50 (SIL, MCL), and
a tick of slippage on every market and stop fill.
Size, fixed before any P/L is looked at: $200 max loss a trade, the account's size. Contracts chosen so the max loss
sits at the same distance in noise units as the Nasdaq bot's (25 points at 4 MNQ), using each market's typical move
at the checks on 2011-2018 (median over days of the mean |check close / session open - 1|), between 1 and 20.
The engine is checked against mnqbot.noise.run on the Nasdaq data before anything else (identical trades).

Pass bar, fixed before running, strict because four markets are tried:
  1. 2011-2018, the market alone: t >= 2.5 on daily P/L (every session, zero days included) and $ a day > 0;
  2. 2019 - Sep 2026, one look: t >= 1.5 and $ a day > 0;
  3. a market that passes both, traded with the Nasdaq bot on one account (evaluation: 4 MNQ, $200, 3 losers; funded:
     4 MNQ, $200, 2 losers; the market at its size, 3 losers), merged minute by minute (open profit and loss of both
     summed when they overlap), on 2019 - mid 2025 starts: expected payouts per 50K evaluation (research/
     apex_payouts.py rules, base caps) and $ a week both at least 10% above the Nasdaq bot alone, with a 30-day
     evaluation pass rate no lower.
"""
from __future__ import annotations

import glob
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL, A.DAYS = 3000.0, 2000.0, 1000.0, 30  # the 50K evaluation, set before the workers fork
FED = ",".join(pd.read_csv(Path(__file__).with_name("fomc_dates.csv")).date)
MAX_LOSS = 200.0


@dataclass(frozen=True)
class Spec:
    name: str
    symbol: str
    open_: int  # minutes after midnight, New York
    close: int
    first_check: int
    last_check: int
    point_value: float
    tick: float
    commission_side: float
    lock_plus: float  # points
    fed: bool = False


SPECS = {
    "NQ": Spec("NQ", "NSX", 570, 960, 600, 930, 2.0, 0.25, 0.62, 2.5, True),
    "gold": Spec("gold", "XAUUSD", 500, 810, 540, 780, 10.0, 0.10, 0.62, 0.20),
    "silver": Spec("silver", "XAGUSD", 500, 810, 540, 780, 1000.0, 0.005, 0.75, 0.010),
    "crude": Spec("crude", "WTIUSD", 540, 870, 570, 840, 100.0, 0.01, 0.75, 0.02),
    "euro": Spec("euro", "EURUSD", 500, 900, 540, 870, 12500.0, 0.0001, 0.62, 0.0002),
}
MARKETS = ("gold", "silver", "crude", "euro")
PERIODS = (("2011-2018", 2011, 2018), ("2019-2026", 2019, 2026))


# ── data
def load_histdata(sp: str, symbol: str) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(f"{sp}/histdata_markets/{symbol}/raw/DAT_ASCII_{symbol}_M1_*.csv")):
        df = pd.read_csv(f, sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
        frames.append(df)
    df = pd.concat(frames).drop_duplicates("ts").sort_values("ts").set_index("ts")
    df.index = df.index.tz_localize(NY, ambiguous="NaT", nonexistent="shift_forward")
    return df[~df.index.isna()][["open", "high", "low", "close"]].astype(float)


def session_bars(df: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    m = df.index.hour * 60 + df.index.minute
    return df[(m >= spec.open_) & (m <= spec.close)]  # the session, and its closing minute's bar


def rescale(df: pd.DataFrame, tick: float) -> pd.DataFrame:
    month = df.index.tz_localize(None).to_period("M")
    first = df.close.groupby(month).transform("first")
    ref = df.close[month == month.max()].iloc[0]
    f = (ref / first).to_numpy()
    out = df.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = np.round(df[col].to_numpy() * f / tick) * tick
    return out


def market_bars(sp: str, spec: Spec) -> pd.DataFrame:
    if spec.name == "NQ":
        return A.rth(f"{sp}/nsx1m_scaled.pkl")
    raw = session_bars(load_histdata(sp, spec.symbol), spec)
    raw = raw[raw.index >= pd.Timestamp("2010-06-01", tz=NY)]
    if spec.name == "crude":  # April 2020: the CFD went to and below zero
        day = raw.index.tz_localize(None).normalize()
        bad = set(day[raw.low.to_numpy() <= 5.0])
        raw = raw[~day.isin(bad)]
    return rescale(raw, spec.tick)


# ── the engine: mnqbot.noise.run (stop mode, take-profit from the fill) with the session as parameters
def run_market(bars: pd.DataFrame, spec: Spec, qty: int, max_loss: float, max_losers: int, lookback: int = 14):
    idx = bars.index
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    dates = idx.strftime("%Y-%m-%d").to_numpy()
    o, h, l, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    checks = list(range(spec.first_check, spec.last_check + 1, 30))
    n_checks = len(checks)
    slot_of = {m: k for k, m in enumerate(checks)}
    slip = spec.tick
    fed_days = set(FED.split(",")) if spec.fed else set()
    cap_pts = max_loss / qty / spec.point_value if max_loss > 0 else math.nan
    ring = np.full(lookback * n_checks, np.nan)
    today = [math.nan] * n_checks
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    fed_today = False
    pos, entry_px, entry_bar, est_px = 0, 0.0, 0, math.nan
    losers, locked, pending = 0, False, None
    trades = []

    def close_pos(i, price, reason):
        nonlocal pos, locked, losers
        pnl = pos * (price - entry_px) * qty * spec.point_value - 2 * spec.commission_side * qty
        trades.append((pos, entry_bar, entry_px, i, price, pnl, reason))
        if pnl < 0 and reason != "Session ended":
            losers += 1
        pos, locked = 0, False

    for i in range(len(o)):
        t = tmin[i]
        end = t + 1
        in_rth = t >= spec.open_ and end <= spec.close
        if pending is not None:
            d = pending
            pending = None
            if pos == 0:
                pos, entry_px, entry_bar = d, o[i] + d * slip, i
        if pos and not math.isnan(upper):
            line = upper * (1 - 0.24 * sigma) if pos > 0 else lower * (1 + 0.24 * sigma)
            reason = "Back inside"
            base = entry_px if entry_bar != i else est_px
            cap = base - pos * cap_pts
            if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                line, reason = cap, "Max loss"
            if locked:
                lk = entry_px + pos * spec.lock_plus
                if (pos > 0 and lk > line) or (pos < 0 and lk < line):
                    line, reason = lk, "Lock"
            if entry_bar == i:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):
                hit, price = True, o[i] - pos * slip
            else:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            if hit:
                close_pos(i, price, reason)
            else:  # the take-profit, working from the fill (from the expected fill on the fill bar)
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * 1.5 * sigma)
                if (pos > 0 and h[i] >= tp + spec.tick) or (pos < 0 and l[i] <= tp - spec.tick):
                    close_pos(i, tp, "Target")
        if pos and not locked:
            locked = pos * ((h[i] if pos > 0 else l[i]) - entry_px) >= cap_pts
        if pos and (not in_rth or t == spec.open_):
            close_pos(i, c[i] - pos * slip, "Session ended")
        if t == spec.open_:
            prev_close, day_open, losers = last_close, o[i], 0
            upper = lower = sigma = math.nan
            today = [math.nan] * n_checks
            fed_today = dates[i] in fed_days
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in slot_of:
            k = slot_of[end]
            today[k] = abs(c[i] / day_open - 1)
            if filled >= lookback and not math.isnan(prev_close):
                s = 0.0
                for d in range(lookback):
                    s += ring[d * n_checks + k]
                sigma = s / lookback
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                short_ok = not (fed_today and end < 840)
                fresh = losers < max_losers
                if pos == 0 and c[i] > upper and fresh:
                    pending = 1
                elif pos == 0 and c[i] < lower and short_ok and fresh:
                    pending = -1
                if pending is not None:
                    est_px = c[i] + pending * slip
        if in_rth and end == spec.close:
            if pos:
                close_pos(i, c[i] - pos * slip, "Session close")
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * n_checks:(slot + 1) * n_checks] = today
                slot = (slot + 1) % lookback
                filled += 1
            day_open = math.nan
    return trades


def check_engine(sp: str) -> None:
    """The engine against mnqbot.noise.run on the Nasdaq data, 2011-2014: the same trades."""
    bars = A.rth(f"{sp}/nsx1m_scaled.pkl")
    bars = bars[bars.index < pd.Timestamp("2015-01-01", tz=NY)]
    ref = run(bars, NoiseConfig(qty=4, max_loss_per_trade=200.0, max_losers=3, fed_dates=FED, skip_dates="",
                                target_on_fill_bar=True), minutes=1).trades
    mine = run_market(bars, SPECS["NQ"], 4, 200.0, 3)
    assert len(ref) == len(mine), (len(ref), len(mine))
    for a, b in zip(ref, mine, strict=True):
        assert (a.direction, a.entry_bar, a.exit_bar) == (b[0], b[1], b[3]), (a, b)
        assert abs(a.entry - b[2]) < 1e-9 and abs(a.exit - b[4]) < 1e-9 and abs(a.pnl - b[5]) < 1e-6, (a, b)
    print(f"engine check: {len(ref)} Nasdaq trades 2011-2014 identical to mnqbot.noise.run")


# ── sizing, before any P/L
def typical_move(bars: pd.DataFrame, spec: Spec) -> float:
    b = bars[(bars.index.year >= 2011) & (bars.index.year <= 2018)]
    m = b.index.hour * 60 + b.index.minute
    day = b.index.tz_localize(None).normalize()
    opens = b.open[m == spec.open_].groupby(day[m == spec.open_]).first()
    checks = [x - 1 for x in range(spec.first_check, spec.last_check + 1, 30)]  # bars ending at the checks
    cl = b.close[np.isin(m, checks)]
    mv = (cl / opens.reindex(cl.index.tz_localize(None).normalize()).to_numpy() - 1).abs()
    return float(mv.groupby(cl.index.tz_localize(None).normalize()).mean().median())


# ── per market: trades, minute equity paths, stats
def first_sessions(bars: pd.DataFrame, spec: Spec) -> set:
    m = bars.index.hour * 60 + bars.index.minute
    d = pd.Series(bars.index[m == spec.open_].tz_localize(None).normalize()).drop_duplicates()
    return set(d.groupby(d.dt.to_period("M")).min())


def sessions_of(bars: pd.DataFrame, spec: Spec) -> pd.DatetimeIndex:
    m = bars.index.hour * 60 + bars.index.minute
    return pd.DatetimeIndex(sorted(set(bars.index[m == spec.open_].tz_localize(None).normalize())))


def paths(bars: pd.DataFrame, spec: Spec, qty: int, trades, drop_first: bool):
    """(session day, minute times, $ high-equity path, $ low-equity path, pnl) per trade, at the trade's size."""
    h, l = bars.high.to_numpy(float), bars.low.to_numpy(float)
    times = bars.index.tz_localize(None).to_numpy()
    skip = first_sessions(bars, spec) if drop_first else set()
    fee = 2 * spec.commission_side * qty
    out = []
    for d, a, entry, b, _, pnl, _ in trades:
        day = pd.Timestamp(times[a]).normalize()
        if day in skip:
            continue
        if d > 0:
            hi, lo = (h[a:b] - entry), (l[a:b] - entry)
        else:
            hi, lo = (entry - l[a:b]), (entry - h[a:b])
        hi = np.append(hi * spec.point_value * qty - fee, pnl)
        lo = np.append(lo * spec.point_value * qty - fee, pnl)
        out.append((day, times[a:b + 1], hi, lo, pnl))
    return out


def stats(trs, sess: pd.DatetimeIndex, y0: int, y1: int) -> dict:
    ss = sess[(sess.year >= y0) & (sess.year <= y1)]
    t = [x for x in trs if y0 <= x[0].year <= y1]
    daily = pd.Series(0.0, index=ss)
    for x in t:
        if x[0] in daily.index:
            daily[x[0]] += x[4]
    n = len(daily)
    sd = daily.std(ddof=1)
    return {"sessions": n, "trades/week": len(t) / (n / 5) if n else 0.0, "win %": 100 * np.mean([x[4] > 0 for x in t])
            if t else 0.0, "$/day": daily.mean(), "t": daily.mean() / sd * math.sqrt(n) if sd > 0 else 0.0,
            "$/week": 5 * daily.mean()}


def market_job(args):
    sp, name, qty, losers = args
    spec = SPECS[name]
    bars = market_bars(sp, spec)
    trs = paths(bars, spec, qty, run_market(bars, spec, qty, MAX_LOSS, losers), drop_first=spec.name != "NQ")
    return name, losers, trs, sessions_of(bars, spec)


def typical_job(args):
    sp, name = args
    spec = SPECS[name]
    bars = market_bars(sp, spec)
    price = bars.close.iloc[-1]
    return name, typical_move(bars, spec), price


# ── one account, both markets: flat-to-flat segments of summed minute equity
def segments(day_trades):
    """Merge one day's trades (any markets) into flat-to-flat pieces: (pnl, high-water $ path, low $ path)."""
    if not day_trades:
        return []
    timeline = np.unique(np.concatenate([x[1] for x in day_trades]))
    n = len(timeline)
    hi_sum, lo_sum, open_cnt = np.zeros(n), np.zeros(n), np.zeros(n, int)
    for _, tt, hi, lo, pnl in day_trades:
        a = np.searchsorted(timeline, tt[0])
        b = np.searchsorted(timeline, tt[-1])  # the exit minute
        pos = np.searchsorted(tt, timeline[a:b + 1], side="right") - 1  # forward fill inside the trade
        hi_sum[a:b + 1] += hi[pos]
        lo_sum[a:b + 1] += lo[pos]
        hi_sum[b + 1:] += pnl
        lo_sum[b + 1:] += pnl
        open_cnt[a:max(b, a + 1)] += 1  # a trade filled and closed in the same minute is open in that minute
    out, i = [], 0
    while i < n:
        if open_cnt[i] == 0:
            i += 1
            continue
        j = i
        while j < n and open_cnt[j] > 0:
            j += 1
        last = min(j, n - 1)  # j: the minute the piece's last trade exits, all closed there
        base = hi_sum[i - 1] if i > 0 else 0.0  # closed P/L before the piece (high = low = P/L when flat)
        hi_p, lo_p = hi_sum[i:last + 1] - base, lo_sum[i:last + 1] - base
        assert abs(hi_p[-1] - lo_p[-1]) < 1e-6, "flat at the end of a piece"
        out.append((float(lo_p[-1]), np.maximum.accumulate(hi_p), lo_p))
        i = last + 1
    assert abs(sum(x[0] for x in out) - sum(x[4] for x in day_trades)) < 1e-6, "every trade's P/L is in a piece"
    return out


def account_days(trade_sets, sessions):
    by = {}
    for trs in trade_sets:
        for x in trs:
            by.setdefault(x[0], []).append(x)
    return [(d, segments(by.get(d, []))) for d in sessions]


def payout_study(args):
    """Every start in [first, last_start]: the evaluation on eval_sets, then the funded account on pa_sets."""
    eval_sets, pa_sets, sessions, first, last_start, label = args
    ss = [d for d in sessions if d >= pd.Timestamp(first)]
    ev = account_days([[x for x in t if x[0] >= ss[0]] for t in eval_sets], ss)
    pa = account_days([[x for x in t if x[0] >= ss[0]] for t in pa_sets], ss)
    memo, res, passes, n = {}, [], 0, 0
    for s, day in enumerate(ss):
        if day > pd.Timestamp(last_start):
            break
        n += 1
        out, used = A.attempt(ev[s:], 1, "intraday", 30)
        if out != "passed":
            res.append(0.0)
            continue
        passes += 1
        f = s + used
        if f not in memo:
            paid, _, _ = P.pa_run(pa[f:], 1, P.CAPS["base"])
            memo[f] = sum(a for _, a in paid)
        res.append(memo[f])
    return label, 100 * passes / n, float(np.mean(res))


def main() -> None:
    sp = sys.argv[1]
    pd.set_option("display.width", 220)
    check_engine(sp)
    with ProcessPoolExecutor(max_workers=3) as pool:
        typ = {name: (mv, px) for name, mv, px in pool.map(typical_job, [(sp, n) for n in ("NQ", *MARKETS)])}
        nq_units = 25.0 / (typ["NQ"][1] * typ["NQ"][0])  # the Nasdaq bot's max loss in noise units
        qty = {"NQ": 4}
        for m in MARKETS:
            mv, px = typ[m]
            q = round(MAX_LOSS / (nq_units * px * mv * SPECS[m].point_value))
            qty[m] = int(min(20, max(1, q)))
        print(f"\nNasdaq max loss: 25 points = {nq_units:.2f} typical moves")
        for m in MARKETS:
            mv, px = typ[m]
            cap = MAX_LOSS / qty[m] / SPECS[m].point_value
            print(f"{m}: typical move {100 * mv:.3f}% at {px:g}; {qty[m]} contracts, max loss $200 = {cap:g} points = "
                  f"{cap / (px * mv):.2f} typical moves")
        runs = {(n, lz): (trs, ss) for n, lz, trs, ss in
                pool.map(market_job, [(sp, n, qty[n], lz) for n in ("NQ", *MARKETS) for lz in (2, 3)])}
    rows, passed = [], []
    for m in ("NQ", *MARKETS):
        trs, ss = runs[(m, 3)]
        st = {label: stats(trs, ss, y0, y1) for label, y0, y1 in PERIODS}
        for label, s in st.items():
            rows.append({"market": m, "period": label, **{k: round(v, 2) for k, v in s.items()}})
        if m == "NQ":
            continue
        s1, s2 = st["2011-2018"], st["2019-2026"]
        ok1 = s1["t"] >= 2.5 and s1["$/day"] > 0
        ok2 = ok1 and s2["t"] >= 1.5 and s2["$/day"] > 0
        print(f"{m}: 2011-2018 t {s1['t']:.2f}, ${s1['$/day']:.2f} a day: {'PASS' if ok1 else 'FAIL'}"
              + (f"; 2019-2026 t {s2['t']:.2f}, ${s2['$/day']:.2f} a day: {'PASS' if ok2 else 'FAIL'}" if ok1 else ""))
        if ok2:
            passed.append(m)
    print("\nEach market alone, $200 max loss, 3 losers a day")
    print(pd.DataFrame(rows).to_string(index=False))
    if not passed:
        print("\nNo market passed stages 1 and 2: nothing to combine. FAIL")
        return
    nq_e, nq_ss = runs[("NQ", 3)][0], runs[("NQ", 3)][1]
    nq_f = runs[("NQ", 2)][0]
    jobs = []
    for m in passed:
        mk, mss = runs[(m, 3)]
        sess = pd.DatetimeIndex(sorted(set(nq_ss) | set(mss)))
        for label, first, last in (("2011-2018", "2011-01-01", "2018-12-31"),
                                   ("2019-2025", "2019-01-01", "2025-06-30")):
            jobs.append(([nq_e], [nq_f], list(sess), first, last, f"NQ alone {label} ({m} sessions)"))
            jobs.append(([nq_e, mk], [nq_f, mk], list(sess), first, last, f"NQ + {m} {label}"))
    with ProcessPoolExecutor(max_workers=3) as pool:
        res = {lab: (p, v) for lab, p, v in pool.map(payout_study, jobs)}
    for m in passed:
        mk = runs[(m, 3)][0]
        for label, y0, y1 in (("2011-2018", 2011, 2018), ("2019-2025", 2019, 2026)):
            base, comb = res[f"NQ alone {label} ({m} sessions)"], res[f"NQ + {m} {label}"]
            wk_b = stats(nq_e, nq_ss, y0, y1)["$/week"]
            wk_c = wk_b + stats(mk, runs[(m, 3)][1], y0, y1)["$/week"]
            ok = comb[1] >= 1.1 * base[1] and wk_c >= 1.1 * wk_b and comb[0] >= base[0]
            print(f"{label}: NQ alone pass {base[0]:.1f}%, ${base[1]:.0f} per evaluation, ${wk_b:.0f} a week | "
                  f"NQ + {m}: "
                  f"pass {comb[0]:.1f}%, ${comb[1]:.0f} per evaluation, ${wk_c:.0f} a week"
                  + (f": {'PASS' if ok else 'FAIL'}" if label == "2019-2025" else ""))


if __name__ == "__main__":
    main()
