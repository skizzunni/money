"""Round seventy-four: scheduled macro news days, a replication of round seventy-three on releases it didn't use.

    python research/news_days.py nsx1m_scaled.pkl nq1m_scaled.pkl \
        "histdata_raw/*/DAT_ASCII_NSXUSD_M1_*.csv" "nq1m/*.parquet"

Round seventy-three found the bot earns 2.5-3.4x its usual $ a day on jobs-report days, the same way on 2011-18,
2019-26 and NQ futures, but under its bar (t 1.3-1.8, about 12 days a year). Hypothesis, fixed before running:
scheduled macro news days make trend days, so the bot earns more on them. A replication on OTHER scheduled releases,
then, only if it replicates, a sizing rule on one 50K Apex account. Everything below was fixed before running.

Dates (none typed from memory):
- ISM Manufacturing PMI, 10:00 New York. Rule (ISM's own calendar page, quoted in search results): the first business
  day of the month. Checked against release dates confirmed in search results: Feb 3, Mar 3 and Apr 1 2025 (first
  business days). JANUARY IS EXCLUDED: confirmed January releases fall on the first business day in 2015 (Jan 2) but
  the second in 2018 (Jan 3), 2020 (Jan 3), 2023 (Jan 4), 2024 (Jan 3) and 2026 (Jan 5, "an ISM holiday"), so January
  has no reliable rule; the first two sessions of January are left out of every group. Business day: a weekday that
  isn't Labor Day (the only federal holiday that can fall on the 1st-3rd of February-December). Written to
  research/ism_dates.csv. ismworld.org's calendar page returns a captcha to this machine.
- FOMC statement days: research/fomc_dates.csv (already in the repo).
- Jobs-report days: research/nfp_dates.csv (round seventy-three); excluded from every group here.
Retail sales and PPI: no rule could be verified; skipped. CPI: no source (round seventy-three).

Data and the bot: v1.6 rules, 4 MNQ, $200 max loss, 3 losers a day, take-profit from the fill, Fed days from
research/fomc_dates.csv, no skip list, on 5-minute bars resampled from the scaled 1-minute data (as
research/macro_days.py), $1.24 fees a contract and a tick of slippage a fill. ISM days are the first session of a
month, which the month-by-month rescaling turns into a fake gap (round seventy-three dropped first sessions). Here
the gap is repaired instead: at the first session of a month the previous close is multiplied by f_m / f_(m-1), where
f is the month's scale factor (median of scaled / raw close over the month's regular-hours minutes, raw = HistData
NSXUSD or the NQ futures parquet files, as research/cues.py). Checks: with no repair the engine copy equals
mnqbot.noise.run; with the repair the first-session gaps equal the raw gaps (reported).

Replication (pass bar fixed before running): per period (2011-2018 index, 2019 - Sep 2026 index, NQ futures 2015 -
2025), the bot's mean $ a day on ISM days and on FOMC days against non-news days (not a jobs-report, ISM or FOMC day,
nor one of January's first two sessions); every session counts, days without a trade at $0. PASS if, on ISM days AND
on FOMC days, the mean $ a day is higher than on non-news days in all three periods, AND the pooled index 2011 - Sep
2026 one-sided Welch t (news > non-news) is >= 2.0 for at least one of the two.

Only if PASS, the sizing rule: on scheduled news days (jobs report, ISM, FOMC) 8 MNQ at $400 max loss (the same
25-point cap, so every amount doubles), other days 4 MNQ at $200. Per period: $ a week, worst losing stretch, the 50K
intraday-trail evaluation pass / bust % in 30 days (research/apex25k.py attempt, $3,000 target, $2,000 drawdown
trailing the open-profit peak; the per-contract minute paths of each trade are scaled by that day's contracts) and
payouts per evaluation (research/apex_payouts.py rules, base caps, the funded account at the same rule), against
flat 4 MNQ. Minute paths: each trade's 1-minute highs and lows from its fill minute to the start of its exit bar,
then its P/L (the exit bar's inside is covered by the P/L), fees at entry.
"""
from __future__ import annotations

import datetime as dt
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
import apex_payouts as P  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import (  # noqa: E402
    FIRST_CHECK,
    LAST_CHECK,
    N_CHECKS,
    RTH_CLOSE,
    RTH_OPEN,
    STEP,
    NoiseConfig,
    NoiseTrade,
    run,
)

HERE = Path(__file__).resolve().parent
FED = ",".join(pd.read_csv(HERE / "fomc_dates.csv").date)
FOMC = set(pd.read_csv(HERE / "fomc_dates.csv").date)
NFP = set(pd.read_csv(HERE / "nfp_dates.csv").date)
CFG = dict(qty=4, max_loss_per_trade=200.0, max_losers=3, target_on_fill_bar=True, fed_dates=FED, skip_dates="")
QTY, PV, FEE = 4, 2.0, 1.24
A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
PERIODS = {"2011-2018": ("index", "2011-01-01", "2018-12-31"), "2019-2026": ("index", "2019-01-01", "2026-12-31"),
           "NQ 2015-2025": ("nq", "2015-03-01", "2025-12-31")}
EVAL_LAST = {"2011-2018": "2018-12-31", "2019-2026": "2025-06-30", "NQ 2015-2025": "2024-12-31"}


def labor_day(y: int) -> dt.date:
    d = dt.date(y, 9, 1)
    return d + dt.timedelta(days=(0 - d.weekday()) % 7)


def ism_dates() -> list[str]:
    out = []
    for y in range(2010, 2027):
        for m in range(2, 13):
            d = dt.date(y, m, 1)
            while d.weekday() >= 5 or d == labor_day(y):
                d += dt.timedelta(days=1)
            out.append(d.isoformat())
    return out


ISM = set(ism_dates())


def run_fixed(bars: pd.DataFrame, cfg: NoiseConfig, prev_mult: dict, minutes: int = 5):
    """mnqbot.noise.run (stop mode), with the previous close multiplied by prev_mult[date] at that session's open.
    With prev_mult empty it must equal noise.run. Also returns the gap (open / previous close - 1) per session."""
    idx = bars.index.tz_convert(NY)
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    h, l = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    slip = cfg.slippage_ticks * cfg.tick
    lb_n = cfg.lookback
    ring = np.full(lb_n * N_CHECKS, np.nan)
    today = [math.nan] * N_CHECKS
    filled = slot = 0
    day_open = prev_close = last_rth_close = math.nan
    upper = lower = sigma = math.nan
    skip_today = fed_today = False
    pos = 0
    entry_px, entry_bar = 0.0, 0
    est_px = math.nan
    losers_today = 0
    locked = False
    pending = None
    trades, gaps = [], {}

    def close_pos(i, price, reason):
        nonlocal pos, locked, losers_today
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - 2 * cfg.commission_per_side * cfg.qty
        trades.append(NoiseTrade(pos, cfg.qty, entry_bar, idx[entry_bar], entry_px, i, idx[i], price, reason, pnl))
        if pnl < 0 and reason != "Session ended":
            losers_today += 1
        pos, locked = 0, False

    for i in range(len(bars)):
        t = idx[i]
        t_min = t.hour * 60 + t.minute
        end = t_min + minutes
        in_rth = t_min >= RTH_OPEN and end <= RTH_CLOSE
        if pending is not None:
            d = pending
            pending = None
            if pos == 0:
                pos, entry_px, entry_bar = d, o[i] + d * slip, i
        if pos and not math.isnan(upper):
            line = upper * (1 - cfg.stop_buffer * sigma) if pos > 0 else lower * (1 + cfg.stop_buffer * sigma)
            reason = "Back inside"
            if cfg.max_loss_per_trade > 0:
                base = entry_px if entry_bar != i else est_px
                cap = base - pos * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
                if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                    line, reason = cap, "Max loss"
            if locked:
                lk = entry_px + pos * cfg.lock_plus
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
            elif cfg.take_profit > 0 and (entry_bar != i or cfg.target_on_fill_bar):
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * cfg.take_profit * sigma)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and l[i] <= tp - cfg.tick):
                    close_pos(i, tp, "Target")
        if pos and not locked and cfg.lock_at > 0 and cfg.max_loss_per_trade > 0:
            trigger = cfg.lock_at * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
            locked = pos * ((h[i] if pos > 0 else l[i]) - entry_px) >= trigger
        if pos and (not in_rth or t_min == RTH_OPEN):
            close_pos(i, c[i] - pos * slip, "Session ended")
        if t_min == RTH_OPEN:
            ds = t.strftime("%Y-%m-%d")
            prev_close = last_rth_close * prev_mult.get(ds, 1.0)
            day_open = o[i]
            gaps[ds] = day_open / prev_close - 1 if prev_close == prev_close else math.nan
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            skip_today = ds in cfg.skip_dates
            fed_today = cfg.fed_no_shorts and ds in cfg.fed_dates
        if in_rth:
            last_rth_close = c[i]
        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            k = (end - FIRST_CHECK) // STEP
            today[k] = abs(c[i] / day_open - 1)
            if filled >= lb_n and not math.isnan(prev_close):
                s = 0.0
                for d in range(lb_n):
                    s += ring[d * N_CHECKS + k]
                sigma = s / lb_n
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                short_ok = not (fed_today and end < 840)
                fresh_ok = cfg.max_losers <= 0 or losers_today < cfg.max_losers
                d = 0
                if skip_today or pos:
                    pass
                elif c[i] > upper and fresh_ok:
                    d = 1
                elif c[i] < lower and short_ok and fresh_ok:
                    d = -1
                if d:
                    pending = d
                    est_px = c[i] + d * slip
        if in_rth and end == RTH_CLOSE:
            if pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS : (slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan
    return trades, gaps


def five(one: pd.DataFrame) -> pd.DataFrame:
    return one.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def load_nq_raw(pattern: str) -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(pattern))])
    d = d.drop_duplicates("timestamp").sort_values("timestamp")
    d.index = pd.DatetimeIndex(d.timestamp).tz_localize("UTC").tz_convert(NY)
    return d[["open", "high", "low", "close"]].astype(float)


def raw_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw 09:30 open and 15:59 close per session (for the gap check)."""
    m = raw.index.tz_convert(NY)
    tmin = m.hour * 60 + m.minute
    day = m.tz_localize(None).normalize()
    op = raw.open[tmin == 570].groupby(day[tmin == 570]).first()
    cl = raw.close[(tmin >= 570) & (tmin < 960)].groupby(day[(tmin >= 570) & (tmin < 960)]).last()
    return pd.DataFrame({"open": op, "close": cl}).dropna()


def job(args):
    path, raw_pattern, kind = args
    one = pd.read_pickle(path)
    bars = five(one)
    idx1 = one.index.tz_convert(NY)
    t1 = idx1.hour * 60 + idx1.minute
    rth1 = one[(t1 >= 570) & (t1 < 960)]
    raw = load_histdata(raw_pattern) if kind == "index" else load_nq_raw(raw_pattern)
    j = rth1[["close"]].join(raw[["close"]].rename(columns={"close": "raw"}), how="inner")
    r = j.close / j.raw
    mon = j.index.tz_convert(NY).tz_localize(None).to_period("M")
    fac = r.groupby(mon).median()
    disp = float((r.groupby(mon).std() / fac).median())
    rd = raw_daily(raw)
    del raw, j
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sess = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == RTH_OPEN].normalize())))
    first = pd.Series(sess).groupby(sess.to_period("M")).min()
    mult = {}
    for p, d in first.items():
        if p in fac.index and (p - 1) in fac.index:
            mult[d.strftime("%Y-%m-%d")] = fac[p] / fac[p - 1]
    cfg = NoiseConfig(**CFG)
    plain, _ = run_fixed(bars, cfg, {})
    ref = run(bars, NoiseConfig(**CFG), minutes=5).trades
    same = len(ref) == len(plain) and all(
        (a.entry_bar, a.exit_bar, a.direction) == (b.entry_bar, b.exit_bar, b.direction) and abs(a.pnl - b.pnl) < 1e-9
        for a, b in zip(ref, plain, strict=True))
    trades, gaps = run_fixed(bars, cfg, mult)
    # the gap check on first sessions: repaired scaled gap vs the raw gap
    raw_gap = rd.open / rd.close.shift(1) - 1
    diffs = []
    for ds in mult:
        ts = pd.Timestamp(ds)
        if ts in raw_gap.index and ds in gaps and raw_gap[ts] == raw_gap[ts]:
            # the raw gap only counts when the previous raw session is the previous scaled session
            k = rd.index.get_loc(ts)
            if k > 0 and sess.get_loc(ts) > 0 and rd.index[k - 1] == sess[sess.get_loc(ts) - 1]:
                diffs.append(abs(gaps[ds] - raw_gap[ts]))
    tf = pd.DataFrame([t.__dict__ for t in trades])
    tf["day"] = tf.entry_time.dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
    daily = tf.groupby("day").pnl.sum().reindex(sess, fill_value=0.0)
    # per-contract minute paths for the evaluation and payout simulation
    o1, h1, l1 = (one[k].to_numpy(float) for k in ("open", "high", "low"))
    pos1 = pd.Series(np.arange(len(one)), index=one.index)
    paths = []
    for t in trades:
        a = pos1.get(t.entry_time)
        b = pos1.get(t.exit_time)
        pnl1 = t.pnl / QTY
        if a is None or b is None or b < a:
            hi, lo = np.array([pnl1]), np.array([pnl1])
        elif t.direction > 0:
            hi, lo = (h1[a:b] - t.entry) * PV - FEE, (l1[a:b] - t.entry) * PV - FEE
        else:
            hi, lo = (t.entry - l1[a:b]) * PV - FEE, (t.entry - h1[a:b]) * PV - FEE
        hi = np.maximum.accumulate(np.append(hi, pnl1))
        lo = np.append(lo, pnl1)
        day = t.entry_time.tz_convert(NY).tz_localize(None).normalize()
        paths.append((day, pnl1, hi, lo))
    gap_check = (float(np.median(diffs)) if diffs else float("nan"), len(diffs), disp)
    return kind, same, len(mult), gap_check, daily, paths, sess


def groups(sess: pd.DatetimeIndex) -> pd.DataFrame:
    ds = [d.strftime("%Y-%m-%d") for d in sess]
    jan2 = set()
    for y in sorted(set(sess.year)):
        jan2 |= {d.strftime("%Y-%m-%d") for d in sorted(sess[(sess.year == y) & (sess.month == 1)])[:2]}
    nfp = np.array([d in NFP for d in ds])
    ism = np.array([d in ISM for d in ds]) & ~nfp
    fomc = np.array([d in FOMC for d in ds]) & ~nfp
    jan = np.array([d in jan2 for d in ds])
    news = nfp | ism | fomc
    return pd.DataFrame({"nfp": nfp, "ism": ism, "fomc": fomc, "jan": jan, "news": news,
                         "plain": ~news & ~jan}, index=sess)


def welch_one_sided(a: pd.Series, b: pd.Series) -> float:
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    return (a.mean() - b.mean()) / math.sqrt(va + vb)


def eval_and_payouts(paths, sess, g, period, sized):
    """Evaluation pass/bust % (30 days) and payouts per evaluation, flat 4 MNQ or 8 on news days."""
    a, b = PERIODS[period][1], PERIODS[period][2]
    ss = [d for d in sess if pd.Timestamp(a) <= d]
    mult = {d: (8 if (sized and g.news.get(d, False)) else 4) for d in ss}
    scaled = [(d, q * pnl, q * hi, q * lo) for d, pnl, hi, lo in paths if d in mult for q in (mult[d],)]
    days = P.by_day(scaled, ss)
    last = pd.Timestamp(EVAL_LAST[period])
    res, paid = [], []
    for s, day in enumerate(ss):
        if day > last:
            break
        r, used = A.attempt(days[s:], 1, "intraday", 30)
        res.append(r)
        if r == "passed":
            pd_, _, _ = P.pa_run(days[s + used:], 1, P.CAPS["base"])
            paid.append(sum(x for _, x in pd_))
        else:
            paid.append(0.0)
    daily = pd.Series({d: 0.0 for d in ss if d <= pd.Timestamp(b)})
    for d, pnl, _, _ in scaled:
        if d in daily.index:
            daily[d] += pnl
    week = daily.groupby(daily.index.to_period("W")).sum()
    eq = daily.cumsum()
    return {"$/week": week.mean(), "worst stretch": float((eq.cummax() - eq).max()),
            "eval pass %": 100 * res.count("passed") / len(res), "eval bust %": 100 * res.count("failed") / len(res),
            "$ paid per eval": float(np.mean(paid))}


def main() -> None:
    nsx, nq, nsx_raw, nq_raw = sys.argv[1:5]
    pd.DataFrame({"date": ism_dates(), "source": "ISM rule: first business day of the month, 10:00 New York "
                  "(February-December; January excluded); see research/news_days.py"}).to_csv(
        HERE / "ism_dates.csv", index=False)
    with ProcessPoolExecutor(max_workers=2) as ex:
        out = {r[0]: r for r in ex.map(job, [(nsx, nsx_raw, "index"), (nq, nq_raw, "nq")])}
    for kind, (_, same, nm, (gd, ng, disp), *_rest) in out.items():
        print(f"{kind}: engine copy equals mnqbot.noise.run: {same}; first sessions repaired: {nm}; "
              f"median |repaired gap - raw gap| on {ng} first sessions: {gd:.2e}; within-month factor dispersion "
              f"{disp:.1e}")
    print("\nReplication: the bot's $ a day (4 MNQ, $200), every session, days without a trade at $0")
    rows = []
    for name, (kind, a, b) in PERIODS.items():
        _, _, _, _, daily, _, sess = out[kind]
        g = groups(sess)
        m = (daily.index >= a) & (daily.index <= b)
        for col in ("ism", "fomc", "nfp", "plain"):
            x = daily[m & g[col].to_numpy()]
            rows.append((name, col, len(x), x.mean(), 100 * (x > 0).mean()))
    rep = pd.DataFrame(rows, columns=["period", "days", "n", "$/day", "% days up"])
    print(rep.round(2).to_string(index=False))
    _, _, _, _, daily, paths, sess = out["index"]
    g = groups(sess)
    m = (daily.index >= "2011-01-01") & (daily.index <= "2026-12-31")
    plain = daily[m & g.plain.to_numpy()]
    t_ism = welch_one_sided(daily[m & g.ism.to_numpy()], plain)
    t_fomc = welch_one_sided(daily[m & g.fomc.to_numpy()], plain)
    mean = rep.set_index(["period", "days"])["$/day"]
    higher = all(mean[(p, k)] > mean[(p, "plain")] for p in PERIODS for k in ("ism", "fomc"))
    ok = higher and max(t_ism, t_fomc) >= 2.0
    print(f"\nISM and FOMC above non-news days in all three periods: {higher}")
    print(f"pooled index 2011 - Sep 2026, one-sided Welch t: ISM {t_ism:.2f}, FOMC {t_fomc:.2f}")
    print(f"Replication: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    print("\nSizing rule: 8 MNQ / $400 on news days (jobs report, ISM, FOMC), 4 MNQ / $200 otherwise")
    rows = []
    for name, (kind, _, _) in PERIODS.items():
        _, _, _, _, _, paths, sess = out[kind]
        g = groups(sess)
        for sized in (False, True):
            r = eval_and_payouts(paths, sess, g, name, sized)
            rows.append({"period": name, "rule": "news 2x" if sized else "flat 4", **r})
    print(pd.DataFrame(rows).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
