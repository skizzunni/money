"""Round sixty-nine: new price-action cues at the moment of the bot's signal, with a strict multiple-testing protocol.

    python research/cues.py nsx1m_scaled.pkl nq1m_scaled.pkl "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv" "nq1m/*.parquet"

The user trades MNQ only and asks for new ideas, clues and cues from the Nasdaq's own price that give more winning
trades. Round eighteen (research/meta_label.py) tested ten facts at the signal (gap direction, yesterday's move, the
20-session trend, volatility vs its 1-year normal, signal at or before 11:30, distance past the line, the day's range
so far, first trade of the day, distance from the day's average price, long or short) and rounds twenty-nine to
thirty-two tested volume and market mood. None held up. This round scans cues none of them looked at: levels, the
signal bar's shape, the day's path, and the calendar. Everything below was fixed before looking at any result.

The bot: mnqbot.noise v1.6 rules on 1-minute bars 09:30-16:00 (as research/apex25k.py runs it), 4 MNQ, $200 max loss,
3 losers a day, take-profit working from the fill, Fed days from research/fomc_dates.csv, no skip dates. Prices are
the month-by-month rescaled series (scaled to today's level); trades on the first session of each month (a fake gap
from the rescaling) are dropped from every statistic. Raw prices (HistData NSXUSD, NQ futures parquet) are used only
for round-number levels: raw = scaled / that month's factor (median of scaled/raw close over the month's RTH bars).
"u" is the noise unit at the signal in points: the upper line minus max(day open, previous close). A trade's signal
bar is the 1-minute bar before its fill (the check bar); "the 5-minute bar" is the 5 one-minute bars ending there,
5-minute bars counted from 09:30. Directions: "ahead" means further in the trade's direction; for a short, high and
low swap. Each cue is a two-way split of the trades (cue true vs false); trades where it isn't defined are left out.

Levels
  L1  yesterday's extreme (high for a long, low for a short) is ahead within 1 u
  L2  the signal close is already beyond yesterday's extreme
  L3  the signal close is beyond yesterday's close
  L4  the prior calendar week's extreme is ahead within 1 u
  L5  the signal close is beyond the prior week's extreme
  L6  the overnight extreme (18:00 the evening before to 09:30) is ahead within 1 u
  L7  the signal close is beyond the overnight extreme
  L8  a round 100-point level (raw price) is ahead within 0.5 u
  L9  a round 250-point level (raw price) is ahead within 1 u
  L10 price crossed a round 100-point level (raw) in the trade's direction over the last 30 minutes
  L11 today's opening gap had filled (traded back to the previous close) before the signal (days with a gap)
Signal bar
  B1  the 5-minute bar's body is at least 60% of its range
  B2  the 5-minute bar closed in its top quarter (long) / bottom quarter (short)
  B3  the 5-minute bar's range is more than 1.5x the average 5-minute range so far today
  B4  the last three 5-minute bars all closed in the trade's direction
  B5  the 30-minute move into the signal is more than 1 u in the trade's direction
  B6  the 30-minute move into the signal is against the trade's direction (a pullback, then the break)
  B7  the signal close is at the day's extreme so far in the trade's direction (within a tick)
  B8  the 5-minute bar's wick against the trade is more than half its range (a rejection)
Path
  P1  first breakout: no earlier check today closed beyond this line
  P2  three or more earlier checks today closed beyond this line
  P3  the day's extreme in the trade's direction was set in the last 5 minutes
  P4  the day's extreme in the trade's direction was set more than 60 minutes ago
  P5  an earlier check today closed beyond the opposite line
  P6  the bot's previous trade today won (vs lost; trades with a previous trade today only)
  P7  the bot's previous trade today was in the same direction (vs the opposite; same trades)
  P8  the signal close is beyond the 09:30-10:00 range's extreme (signals after 10:00)
  P9  the 09:30-10:00 range closed in the trade's direction (signals after 10:00)
Calendar
  C1  Monday
  C2  Friday
  C3  the last trading day of the month
  C4  the second or third trading day of the month
  C5  the day after a big day: the previous session's close-to-close move more than 2x its 14-session average
  C6  that big day went in the trade's direction (big-day-after trades only)
34 cues.

Protocol, fixed before running:
  Discovery, index data 2011-2018: for each cue, the mean P/L per trade with the cue against without (Welch t, normal
  p, two-sided; both groups at least 30 trades, else p = 1), and the win rates. Benjamini-Hochberg false discovery
  rate at q = 0.05 across all 34.
  Survivors only, one look: index 2019 - Sep 2026, same direction and |t| >= 2.0; then NQ futures 2015-2025, same
  direction and |t| >= 1.5.
  For each cue that survives all three: two rules, (a) skip the trades on the bad side, (b) 2x size on the good side;
  their win %, $ a week at 4 MNQ, worst losing stretch and the 50K intraday-trail evaluation pass rate in 30 days
  (research/apex25k.py attempt, $3,000 target, $2,000 drawdown trailing open profit) against the bot, on the
  holdout periods. Skipping a trade leaves the bot's later trades as they were (an approximation).
"""
from __future__ import annotations

import glob
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402

QTY, CAP_USD, LOSERS, PV, FEE = 4, 200.0, 3, 2.0, 1.24
TICK = 0.25
CUES = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "B1", "B2", "B3", "B4", "B5", "B6", "B7",
        "B8", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "C1", "C2", "C3", "C4", "C5", "C6"]
NAMES = {
    "L1": "yesterday's extreme ahead within 1u", "L2": "beyond yesterday's extreme", "L3": "beyond yesterday's close",
    "L4": "prior week's extreme ahead within 1u", "L5": "beyond prior week's extreme",
    "L6": "overnight extreme ahead within 1u", "L7": "beyond the overnight extreme",
    "L8": "round 100 ahead within 0.5u", "L9": "round 250 ahead within 1u", "L10": "crossed a round 100 in 30 min",
    "L11": "gap filled before the signal", "B1": "5-min body >= 60% of range", "B2": "5-min close in its far quarter",
    "B3": "5-min range > 1.5x today's average", "B4": "last 3 five-min bars with the trade",
    "B5": "30-min push > 1u with the trade", "B6": "30-min move against the trade", "B7": "close at the day's extreme",
    "B8": "rejection wick > half the 5-min bar", "P1": "first breakout of this line today",
    "P2": "3+ earlier checks beyond this line", "P3": "day's extreme set in the last 5 min",
    "P4": "day's extreme set > 60 min ago", "P5": "a check closed beyond the opposite line",
    "P6": "previous trade today won", "P7": "previous trade today same direction",
    "P8": "beyond the 09:30-10:00 range", "P9": "09:30-10:00 range closed with the trade", "C1": "Monday",
    "C2": "Friday", "C3": "last trading day of the month", "C4": "2nd or 3rd trading day of the month",
    "C5": "day after a big day", "C6": "the big day went with the trade"}


def load_nq_raw(pattern: str) -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(pattern))])
    d = d.drop_duplicates("timestamp").sort_values("timestamp")
    d.index = pd.DatetimeIndex(d.timestamp).tz_localize("UTC").tz_convert(NY)
    return d[["open", "high", "low", "close"]].astype(float)


def month_factors(rth: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.Series, float]:
    j = rth[["close"]].join(raw[["close"]].rename(columns={"close": "raw"}), how="inner")
    r = j.close / j.raw
    m = j.index.tz_convert(NY).tz_localize(None).to_period("M")
    g = r.groupby(m)
    return g.median(), float((g.std() / g.median()).median())


def build(args):
    """The bot's trades on one data set, with every cue, P/L and the minute equity path at 4 MNQ."""
    path, raw_pattern, kind = args
    full = pd.read_pickle(path)
    fidx = full.index.tz_convert(NY)
    ftmin = fidx.hour * 60 + fidx.minute
    bars = full[(ftmin >= 570) & (ftmin < 961)]  # as apex25k.rth
    raw = load_histdata(raw_pattern) if kind == "index" else load_nq_raw(raw_pattern)
    fac, disp = month_factors(bars, raw)
    del raw
    cfg = NoiseConfig(qty=QTY, max_loss_per_trade=CAP_USD, max_losers=LOSERS, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True)
    res = run(bars, cfg, minutes=1)
    idx = bars.index.tz_convert(NY)
    tmin = np.asarray(idx.hour * 60 + idx.minute)
    dates = np.asarray(idx.tz_localize(None).normalize())
    o, h, lo, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    months = idx.tz_localize(None).to_period("M")

    # sessions: days with a 09:30 bar; regular bars 09:30-15:59
    starts = np.flatnonzero(tmin == 570)
    sess = dates[starts]
    day_pos = {d: k for k, d in enumerate(sess)}
    ends = np.empty(len(starts), int)
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(tmin)
        reg = np.flatnonzero(tmin[s:e] <= 959)
        ends[k] = s + reg[-1]
    dh = np.array([h[s:e + 1].max() for s, e in zip(starts, ends, strict=True)])
    dl = np.array([lo[s:e + 1].min() for s, e in zip(starts, ends, strict=True)])
    dc = c[ends]
    do = o[starts]
    # prior calendar week's high and low
    wk = pd.DatetimeIndex(sess).isocalendar()
    wkey = (wk.year.to_numpy() * 100 + wk.week.to_numpy())
    wdf = pd.DataFrame({"k": wkey, "h": dh, "l": dl}).groupby("k").agg({"h": "max", "l": "min"})
    wprev = wdf.shift(1)
    pwh = wprev.h.reindex(wkey).to_numpy()
    pwl = wprev.l.reindex(wkey).to_numpy()
    # overnight high/low: 18:00 the evening of the previous session to 09:30
    fts = full.index.as_unit("ns").asi8  # the pickles store microseconds; compare in nanoseconds
    onh = np.full(len(sess), np.nan)
    onl = np.full(len(sess), np.nan)
    for k in range(1, len(sess)):
        a = np.searchsorted(fts, (pd.Timestamp(sess[k - 1]).tz_localize(NY) + pd.Timedelta(hours=18)).value)
        b = np.searchsorted(fts, idx[starts[k]].value)
        if b > a:
            onh[k] = full.high.iloc[a:b].max()
            onl[k] = full.low.iloc[a:b].min()
    del full
    # calendar
    sp = pd.Series(pd.DatetimeIndex(sess))
    nth = sp.groupby(sp.dt.to_period("M")).cumcount().to_numpy() + 1
    last_of_month = (sp.dt.to_period("M") != sp.shift(-1).dt.to_period("M")).to_numpy()
    ret = np.r_[np.nan, dc[1:] / dc[:-1] - 1]
    avg14 = pd.Series(np.abs(ret)).shift(1).rolling(14).mean().to_numpy()
    big = np.abs(ret) > 2 * avg14
    # 5-minute bars of each session
    bands = {i: (up, dn) for i, up, dn in res.bands}
    checks_by_day: dict[int, list[int]] = {}
    for i in bands:
        checks_by_day.setdefault(day_pos.get(dates[i], -1), []).append(i)
    orders = {r[0]: r for r in res.orders}

    out = []
    prev_trade: dict[int, tuple] = {}
    for t in res.trades:
        i = t.entry_bar - 1
        if i not in orders or orders[i][1] != t.direction or i not in bands:
            continue
        k = day_pos.get(dates[i])
        if k is None or k == 0:
            continue
        d = t.direction
        s0, ci = starts[k], c[i]
        pc = dc[k - 1]
        up, dn = bands[i]
        u = up - max(do[k], pc)
        if not (u > 0):
            continue
        f = fac.get(months[i], np.nan)
        cue = dict.fromkeys(CUES, np.nan)

        def ahead(level, width, ci=ci, d=d, u=u):
            x = d * (level - ci)
            return float(0 < x <= width * u)

        ext_y = dh[k - 1] if d > 0 else dl[k - 1]
        cue["L1"] = ahead(ext_y, 1)
        cue["L2"] = float(d * (ci - ext_y) > 0)
        cue["L3"] = float(d * (ci - pc) > 0)
        ext_w = pwh[k] if d > 0 else pwl[k]
        if not np.isnan(ext_w):
            cue["L4"] = ahead(ext_w, 1)
            cue["L5"] = float(d * (ci - ext_w) > 0)
        ext_o = onh[k] if d > 0 else onl[k]
        if not np.isnan(ext_o):
            cue["L6"] = ahead(ext_o, 1)
            cue["L7"] = float(d * (ci - ext_o) > 0)
        tm = tmin[s0:i + 1]  # minutes of the day so far (the data can miss minutes: go by the clock)
        j = int(np.searchsorted(tm, tm[-1] - 30, side="right")) - 1  # the last bar at or before 30 minutes ago
        c30 = c[s0 + j] if j >= 0 else do[k]
        if f == f and f > 0:
            rawp, raw30 = ci / f, c30 / f
            for name, step, width in (("L8", 100, 0.5), ("L9", 250, 1.0)):
                lvl = (math.floor(rawp / step) + 1) * step if d > 0 else (math.ceil(rawp / step) - 1) * step
                cue[name] = float(d * (lvl - rawp) * f <= width * u)
            cue["L10"] = float(d * (rawp - raw30) > 0 and math.floor(rawp / 100) != math.floor(raw30 / 100))
        gap = do[k] - pc
        if gap != 0:
            seg_l, seg_h = lo[s0:i + 1].min(), h[s0:i + 1].max()
            cue["L11"] = float((gap > 0 and seg_l <= pc) or (gap < 0 and seg_h >= pc))
        # the 5-minute bars up to the signal (the signal bar ends at the check, a 5-minute boundary)
        bucket = (tm - 570) // 5
        cuts = np.flatnonzero(np.diff(bucket)) + 1
        lo5, hi5, op5, cl5 = [], [], [], []
        for a0, a1 in zip(np.r_[0, cuts], np.r_[cuts, len(tm)], strict=True):
            op5.append(o[s0 + a0])
            cl5.append(c[s0 + a1 - 1])
            hi5.append(h[s0 + a0:s0 + a1].max())
            lo5.append(lo[s0 + a0:s0 + a1].min())
        H, L, O, C = hi5[-1], lo5[-1], op5[-1], cl5[-1]
        rng = H - L
        if rng > 0:
            cue["B1"] = float(abs(C - O) / rng >= 0.6)
            pos = (C - L) / rng
            cue["B2"] = float(pos >= 0.75 if d > 0 else pos <= 0.25)
            avg5 = float(np.mean(np.array(hi5) - np.array(lo5)))
            cue["B3"] = float(rng > 1.5 * avg5)
            wick = (H - C) / rng if d > 0 else (C - L) / rng
            cue["B8"] = float(wick > 0.5)
        if len(cl5) >= 3:
            cue["B4"] = float(all(d * (cl5[-m] - op5[-m]) > 0 for m in (1, 2, 3)))
        cue["B5"] = float(d * (ci - c30) > u)
        cue["B6"] = float(d * (ci - c30) < 0)
        ext_today = h[s0:i + 1].max() if d > 0 else lo[s0:i + 1].min()
        cue["B7"] = float(d * (ci - ext_today) >= -TICK)
        # path
        earlier = [j for j in checks_by_day.get(k, []) if j < i]
        same = sum(d * (c[j] - (bands[j][0] if d > 0 else bands[j][1])) > 0 for j in earlier)
        opp = sum(-d * (c[j] - (bands[j][1] if d > 0 else bands[j][0])) > 0 for j in earlier)
        cue["P1"] = float(same == 0)
        cue["P2"] = float(same >= 3)
        seg = h[s0:i + 1] if d > 0 else -lo[s0:i + 1]
        last_ext = s0 + len(seg) - 1 - int(np.argmax(seg[::-1]))
        cue["P3"] = float(tmin[i] - tmin[last_ext] <= 5)
        cue["P4"] = float(tmin[i] - tmin[last_ext] > 60)
        cue["P5"] = float(opp > 0)
        pt = prev_trade.get(k)
        if pt is not None:
            cue["P6"] = float(pt[0] > 0)
            cue["P7"] = float(pt[1] == d)
        if tmin[i] + 1 > 600:
            n_or = int(np.searchsorted(tm, 600))  # the 09:30-09:59 bars
            orh, orl = h[s0:s0 + n_or].max(), lo[s0:s0 + n_or].min()
            cue["P8"] = float(d * (ci - (orh if d > 0 else orl)) > 0)
            cue["P9"] = float(d * (c[s0 + n_or - 1] - do[k]) > 0)
        wd = pd.Timestamp(sess[k]).weekday()
        cue["C1"] = float(wd == 0)
        cue["C2"] = float(wd == 4)
        cue["C3"] = float(last_of_month[k])
        cue["C4"] = float(nth[k] in (2, 3))
        if not np.isnan(avg14[k - 1]):
            cue["C5"] = float(big[k - 1])
            if big[k - 1]:
                cue["C6"] = float(d * ret[k - 1] > 0)
        prev_trade[k] = (t.pnl, d)
        a, b = t.entry_bar, t.exit_bar
        hp = (h[a:b] - t.entry) if d > 0 else (t.entry - lo[a:b])
        lp = (lo[a:b] - t.entry) if d > 0 else (t.entry - h[a:b])
        hi_run = np.maximum.accumulate(np.append(hp * PV * QTY - FEE * QTY, t.pnl))
        lo_path = np.append(lp * PV * QTY - FEE * QTY, t.pnl)
        out.append({"day": pd.Timestamp(sess[k]), "nth": int(nth[k]), "pnl": t.pnl, "win": t.pnl > 0, **cue,
                    "hi": hi_run, "lo": lo_path})
    df = pd.DataFrame(out)
    df = df[df.nth != 1]  # the first session of each month carries the rescaling's fake gap
    return kind, df, list(pd.DatetimeIndex(sess)), disp


def welch(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    if len(a) < 30 or len(b) < 30:
        return 0.0, 1.0
    t = (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return t, math.erfc(abs(t) / math.sqrt(2))


def split_stats(df: pd.DataFrame, cue: str) -> dict:
    x = df[df[cue].notna()]
    yes, no = x[x[cue] == 1], x[x[cue] == 0]
    t, p = welch(yes.pnl.to_numpy(), no.pnl.to_numpy())
    return {"cue": cue, "n yes": len(yes), "n no": len(no), "$ yes": yes.pnl.mean(), "$ no": no.pnl.mean(),
            "win% yes": 100 * yes.win.mean(), "win% no": 100 * no.win.mean(), "t": t, "p": p}


def bh(pvals: list[float], q: float = 0.05) -> list[bool]:
    m = len(pvals)
    order = np.argsort(pvals)
    k_max = 0
    for rank, j in enumerate(order, 1):
        if pvals[j] <= rank / m * q:
            k_max = rank
    keep = [False] * m
    for rank, j in enumerate(order, 1):
        keep[j] = rank <= k_max
    return keep


def period(df, sessions, y0, y1):
    d = df[(df.day.dt.year >= y0) & (df.day.dt.year <= y1)]
    ss = [s for s in sessions if y0 <= s.year <= y1]
    return d, ss


def rule_effect(df, sessions, mult) -> dict:
    """mult: per-trade size multiplier (0 = skipped). Win %, $ a week, worst losing stretch, evaluation pass %."""
    m = np.asarray(mult, float)
    pnl = df.pnl.to_numpy() * m
    taken = m > 0
    daily = pd.Series(pnl, index=df.day).groupby(level=0).sum().reindex(sessions, fill_value=0.0)
    eq = daily.cumsum()
    worst = float((eq.cummax() - eq).max())
    by_day = {}  # A.attempt wants (pnl, hi_run, lo_path) per trade
    for day, hi, lo, p, k in zip(df.day, df.hi, df.lo, df.pnl, m, strict=True):
        if k > 0:
            by_day.setdefault(day, []).append((p * k, hi * k, lo * k))
    days = [(s, by_day.get(s, [])) for s in sessions]
    last = sessions[-1]
    outs = []
    for s in range(len(days)):
        r, _ = A.attempt(days[s:], 1, "intraday", 30)
        if r != "timeout" or (last - sessions[s]).days >= 30:
            outs.append(r)
    return {"win %": 100 * float((pnl[taken] > 0).mean()), "$/week": float(pnl.sum() / (len(sessions) / 5)),
            "worst stretch": worst, "eval pass %": 100 * outs.count("passed") / len(outs),
            "eval bust %": 100 * outs.count("failed") / len(outs)}


def main() -> None:
    nsx, nq, nsx_raw, nq_raw = sys.argv[1:5]
    A.TARGET, A.DD = 3000.0, 2000.0
    pd.set_option("display.width", 250)
    with ProcessPoolExecutor(max_workers=2) as pool:
        built = dict((k, (df, ss, disp)) for k, df, ss, disp in
                     pool.map(build, [(nsx, nsx_raw, "index"), (nq, nq_raw, "nq")]))
    for k, (df, _, disp) in built.items():
        print(f"{k}: {len(df)} trades; raw-price alignment, median within-month dispersion of the scale factor "
              f"{disp:.2e}")
    idx_df, idx_ss, _ = built["index"]
    nq_df, nq_ss, _ = built["nq"]
    disc, disc_ss = period(idx_df, idx_ss, 2011, 2018)
    hold, hold_ss = period(idx_df, idx_ss, 2019, 2026)
    nqp, nq_ss2 = period(nq_df, nq_ss, 2015, 2025)
    nq_ss2 = [s for s in nq_ss2 if s >= pd.Timestamp("2015-03-01")]
    nqp = nqp[nqp.day >= pd.Timestamp("2015-03-01")]

    rows = [split_stats(disc, cue) for cue in CUES]
    keep = bh([r["p"] for r in rows])
    tab = pd.DataFrame(rows)
    tab["name"] = tab.cue.map(NAMES)
    tab["FDR"] = ["survives" if k else "" for k in keep]
    print(f"\nDiscovery, index 2011-2018: {len(disc)} trades, 34 cues, Benjamini-Hochberg q = 0.05")
    print(tab[["cue", "name", "n yes", "n no", "$ yes", "$ no", "win% yes", "win% no", "t", "p", "FDR"]]
          .round(3).to_string(index=False))
    surv = [r for r, k in zip(rows, keep, strict=True) if k]
    print(f"\nFDR survivors: {[r['cue'] for r in surv] or 'none'}")
    final = []
    for r in surv:
        h2 = split_stats(hold, r["cue"])
        ok2 = np.sign(h2["t"]) == np.sign(r["t"]) and abs(h2["t"]) >= 2.0
        print(f"  {r['cue']} {NAMES[r['cue']]}: holdout 2019-2026 $ {h2['$ yes']:.2f} vs {h2['$ no']:.2f}, "
              f"t {h2['t']:.2f}: {'PASS' if ok2 else 'FAIL'}")
        if not ok2:
            continue
        h3 = split_stats(nqp, r["cue"])
        ok3 = np.sign(h3["t"]) == np.sign(r["t"]) and abs(h3["t"]) >= 1.5
        print(f"     NQ futures 2015-2025 $ {h3['$ yes']:.2f} vs {h3['$ no']:.2f}, t {h3['t']:.2f}: "
              f"{'PASS' if ok3 else 'FAIL'}")
        if ok3:
            final.append(r)
    print(f"\nCues that survive all three stages: {[r['cue'] for r in final] or 'none'}")
    for r in final:
        good = 1.0 if r["t"] > 0 else 0.0  # the cue's 'yes' side is the good side when t > 0
        for label, d, ss in (("index 2019-2026", hold, hold_ss), ("NQ 2015-2025", nqp, nq_ss2)):
            cue = d[r["cue"]].to_numpy()
            on_good = np.where(np.isnan(cue), np.nan, (cue == good).astype(float))
            base = rule_effect(d, ss, np.ones(len(d)))
            skip = rule_effect(d, ss, np.where(on_good == 0, 0.0, 1.0))
            dbl = rule_effect(d, ss, np.where(on_good == 1, 2.0, 1.0))
            print(f"\n{r['cue']} {NAMES[r['cue']]}, {label}")
            print(pd.DataFrame([base, skip, dbl], index=["bot", "skip the bad side", "2x the good side"])
                  .round(1).to_string())


if __name__ == "__main__":
    main()
