"""Round seventy-three: US jobs-report days (the Employment Situation, 08:30 New York) as a cue for the bot.

    python research/macro_days.py nsx1m_scaled.pkl nq1m_scaled.pkl

Reasoning, written before running. Big scheduled news makes trend days, and the noise-momentum bot earns on trend
days; the noise area, an average of ordinary days, may also be too narrow on a news day. FOMC days were tested in
round twenty-four (research/fomc.py); the jobs report and CPI never were.

Dates. bls.gov, FRED/ALFRED and the Wayback Machine all refuse this machine. The Philadelphia Fed's copy of the BLS
release-date file stops in 2010. So the jobs-report dates are DERIVED BY BLS'S PUBLISHED RULE: "typically released on
the third Friday following the conclusion of the reference week, i.e., the week which includes the 12th of the month"
(BLS Employment Situation schedule page, quoted in search results), moved to the Thursday before when that Friday is
the Independence Day holiday (July 3 or 4). Checked against dates the BLS calendars show (search results): 2019-02-01,
2023-01-06, 2023-02-03, 2023-04-07, 2023-05-05, 2023-08-04, 2023-09-01, 2026-03-06, 2026-04-03, 2026-05-08,
2026-06-05, 2026-07-02, 2026-08-07, 2026-09-04, 2026-10-02 all match; 2026-02-06 was announced and later listed as
February 11 (benchmark revision). Known misses the rule can't see: government shutdowns (October 2013, October-November
2025) and occasional schedule changes; a few of the ~190 dates are wrong, which can only dilute an effect. CPI dates
have no rule and no reachable source: CPI is dropped. The dates are written to research/nfp_dates.csv.

The bot: v1.6 rules, 4 MNQ, $200 max loss, 3 losers a day, take-profit from the fill, FOMC dates from
research/fomc_dates.csv, no skip list (as research/apex25k.py), on 5-minute bars resampled from the scaled 1-minute
data; trades on the first session of each month dropped (the month-by-month rescaling makes a fake gap there).
$1.24 fees a contract and a tick of slippage a fill.

1. Description, per period: the bot's $ a day, trades a day and win % on jobs-report days and on other days.
2. Rules (4), each compared with the bot alone on the daily P/L difference (t on the daily differences, every session):
   a. double: 8 MNQ and $400 max loss on jobs-report days (the same trades, P/L x 2);
   b. skip: no trades on jobs-report days;
   c. wider: on jobs-report days the noise area (sigma) is 1.25x wider (lines, line stop and take-profit all follow);
   d. news drive: on jobs-report days only, an extra trade at the 10:00 1-minute bar open in the direction of the
      08:30-09:59 move (08:30 bar open to 09:59 bar close) when that move is larger than the 10:00 noise (sigma);
      stop the 10:00 line stop (upper x (1 - 0.24 sigma) long, lower x (1 + 0.24 sigma) short) if it is on the right
      side of the entry and closer than the $200 cap (25 points), else the cap; take-profit 1.5 sigma from the fill;
      the stop counts first in any minute that reaches both; out at the 15:59 close. 4 MNQ, alongside the bot.
Protocol, fixed before running: discovery 2011-2018, Benjamini-Hochberg at q = 0.05 over the 4 rules (two-sided p from
the t of the daily differences). Survivors: one look at 2019 - Sep 2026 (same sign, t >= 2), then NQ futures 2015 -
July 2025 (same sign, t >= 1.5). A final survivor gets $/week, win %, worst losing stretch and the 50K intraday-trail
evaluation pass/bust rate against the bot alone.
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

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

FED = ",".join(pd.read_csv(Path(__file__).with_name("fomc_dates.csv")).date)
CFG = dict(qty=4, max_loss_per_trade=200.0, max_losers=3, target_on_fill_bar=True, fed_dates=FED, skip_dates="")
QTY, PV, FEE, TICK = 4, 2.0, 1.24, 0.25
WIDE = 1.25


def nfp_date(y: int, m: int) -> dt.date:
    """BLS's rule: the third Friday after the reference week (Sunday-Saturday, the week including the 12th of the
    previous month); the Thursday before when that Friday is the July 3/4 holiday."""
    ry, rm = (y, m - 1) if m > 1 else (y - 1, 12)
    d12 = dt.date(ry, rm, 12)
    sat = d12 + dt.timedelta(days=(5 - d12.weekday()) % 7)
    fri = sat + dt.timedelta(days=20)
    if fri.month == 7 and fri.day in (3, 4):
        fri -= dt.timedelta(days=1)
    return fri


def nfp_dates() -> list[str]:
    return [nfp_date(y, m).isoformat() for y in range(2010, 2027) for m in range(1, 13)]


def run_wide(bars: pd.DataFrame, cfg: NoiseConfig, wide: set[str], mult: float, minutes: int = 5):
    """mnqbot.noise.run (stop mode, no tighten_only), with sigma x mult on the dates in `wide`. Also returns, per
    session, the 10:00 check's sigma, upper and lower (for rule d). With wide empty it must equal noise.run."""
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
    skip_today = fed_today = wide_today = False
    pos = 0
    entry_px, entry_bar = 0.0, 0
    est_px = math.nan
    losers_today = 0
    locked = False
    pending = None
    trades = []
    ten = {}

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
            prev_close = last_rth_close
            day_open = o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            ds = t.strftime("%Y-%m-%d")
            skip_today = ds in cfg.skip_dates
            fed_today = cfg.fed_no_shorts and ds in cfg.fed_dates
            wide_today = ds in wide
        if in_rth:
            last_rth_close = c[i]
        if in_rth and not math.isnan(day_open) and FIRST_CHECK <= end <= LAST_CHECK and (end - FIRST_CHECK) % STEP == 0:
            k = (end - FIRST_CHECK) // STEP
            today[k] = abs(c[i] / day_open - 1)
            if filled >= lb_n and not math.isnan(prev_close):
                s = 0.0
                for d in range(lb_n):
                    s += ring[d * N_CHECKS + k]
                sigma = s / lb_n * (mult if wide_today else 1.0)
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if k == 0:
                    ten[t.strftime("%Y-%m-%d")] = (sigma, upper, lower)
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
    return trades, ten


def news_drive(one: pd.DataFrame, days: list[str], ten: dict) -> pd.Series:
    """Rule d's P/L per session ($, 4 MNQ), from 1-minute bars."""
    idx = one.index.tz_convert(NY)
    key = pd.Series(np.arange(len(one)), index=idx.tz_localize(None))
    o, h, l, c = (one[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    out = {}
    cap = 200.0 / QTY / PV
    for ds in days:
        if ds not in ten:
            continue
        try:
            i0 = key[pd.Timestamp(f"{ds} 08:30")]
            i1 = key[pd.Timestamp(f"{ds} 09:59")]
            ie = key[pd.Timestamp(f"{ds} 10:00")]
            iz = key[pd.Timestamp(f"{ds} 15:59")]
        except KeyError:
            continue
        sigma, upper, lower = ten[ds]
        move = c[i1] / o[i0] - 1
        if abs(move) <= sigma:
            continue
        d = 1 if move > 0 else -1
        entry = o[ie] + d * TICK
        line = upper * (1 - 0.24 * sigma) if d > 0 else lower * (1 + 0.24 * sigma)
        capstop = entry - d * cap
        stop = capstop
        if (d > 0 and line < entry and line > capstop) or (d < 0 and line > entry and line < capstop):
            stop = line
        tp = entry * (1 + d * 1.5 * sigma)
        exit_px = None
        for j in range(ie, iz + 1):
            if (d > 0 and o[j] <= stop) or (d < 0 and o[j] >= stop):
                exit_px = o[j] - d * TICK
                break
            if (d > 0 and l[j] <= stop) or (d < 0 and h[j] >= stop):
                exit_px = stop - d * TICK
                break
            if (d > 0 and h[j] >= tp + TICK) or (d < 0 and l[j] <= tp - TICK):
                exit_px = tp
                break
        if exit_px is None:
            exit_px = c[iz] - d * TICK
        out[pd.Timestamp(ds)] = d * (exit_px - entry) * QTY * PV - QTY * FEE
    return pd.Series(out, dtype=float)


def five(one: pd.DataFrame) -> pd.DataFrame:
    return one.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def daily(trades, sessions: pd.DatetimeIndex, first: set) -> tuple[pd.Series, pd.DataFrame]:
    tf = pd.DataFrame([t.__dict__ for t in trades])
    e = tf.entry_time.dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
    tf = tf[~e.isin(first)]
    e = e[tf.index]
    return tf.groupby(e).pnl.sum().reindex(sessions, fill_value=0.0), tf.assign(day=e)


def job(path: str):
    one = pd.read_pickle(path)
    bars = five(one)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sess = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == RTH_OPEN].normalize())))
    first = set(pd.Series(sess).groupby(sess.to_period("M")).min())
    sessions = sess[~sess.isin(list(first))]
    nfp = set(nfp_dates())
    base_trades, ten = run_wide(bars, NoiseConfig(**CFG), set(), 1.0)
    ref = run(bars, NoiseConfig(**CFG), minutes=5).trades
    same = len(ref) == len(base_trades) and all(
        (a.entry_bar, a.exit_bar, a.direction) == (b.entry_bar, b.exit_bar, b.direction) and abs(a.pnl - b.pnl) < 1e-9
        for a, b in zip(ref, base_trades, strict=True))
    wide_trades, _ = run_wide(bars, NoiseConfig(**CFG), nfp, WIDE)
    base, tf = daily(base_trades, sessions, first)
    wide, _ = daily(wide_trades, sessions, first)
    days = [d.strftime("%Y-%m-%d") for d in sessions if d.strftime("%Y-%m-%d") in nfp]
    drive = news_drive(one, days, ten).reindex(sessions, fill_value=0.0)
    is_nfp = pd.Series([d.strftime("%Y-%m-%d") in nfp for d in sessions], index=sessions)
    diffs = {"a double": base.where(is_nfp, 0.0), "b skip": -base.where(is_nfp, 0.0), "c wider": wide - base,
             "d news drive": drive}
    return path, same, base, tf, is_nfp, diffs


def t_of(x: pd.Series) -> float:
    return x.mean() / x.std(ddof=1) * math.sqrt(len(x)) if x.std(ddof=1) > 0 else 0.0


def p_two(t: float) -> float:
    return math.erfc(abs(t) / math.sqrt(2))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    pd.DataFrame({"date": nfp_dates(), "source": "BLS rule (third Friday after the week including the 12th; July 3/4 "
                  "-> Thursday); see research/macro_days.py"}).to_csv(Path(__file__).with_name("nfp_dates.csv"),
                                                                        index=False)
    with ProcessPoolExecutor(max_workers=2) as ex:
        res = {r[0]: r for r in ex.map(job, [nsx, nq])}
    periods = {"2011-2018": (nsx, "2011-01-01", "2018-12-31"), "2019-2026": (nsx, "2019-01-01", "2026-12-31"),
               "NQ 2015-2025": (nq, "2015-03-01", "2025-12-31")}
    print("engine copy equals mnqbot.noise.run:", {Path(p).name: res[p][1] for p in res})
    print("\n1. The bot on jobs-report days and other days (4 MNQ, $200)")
    rows = []
    for name, (path, a, b) in periods.items():
        _, _, base, tf, is_nfp, _ = res[path]
        m = (base.index >= a) & (base.index <= b)
        for flag, label in ((True, "jobs-report days"), (False, "other days")):
            sel = base[m & (is_nfp.to_numpy() == flag)]
            t_sel = tf[tf.day.isin(sel.index)]
            rows.append((name, label, len(sel), sel.mean(), len(t_sel) / max(len(sel), 1),
                         100 * (t_sel.pnl > 0).mean() if len(t_sel) else float("nan")))
    print(pd.DataFrame(rows, columns=["period", "days", "n", "$/day", "trades/day", "win %"]).round(2)
          .to_string(index=False))
    print("\n2. Rules: daily P/L difference against the bot alone")
    stage = {}
    for name, (path, a, b) in periods.items():
        diffs = res[path][5]
        for rule, x in diffs.items():
            x = x[(x.index >= a) & (x.index <= b)]
            stage[(name, rule)] = (x.mean(), t_of(x), p_two(t_of(x)), int((x != 0).sum()))
    cols = ["period", "rule", "$/day diff", "t", "p", "days changed"]
    print(pd.DataFrame([(n, r, *v) for (n, r), v in stage.items()], columns=cols).round(4).to_string(index=False))
    rules = list(res[nsx][5])
    ps = sorted((stage[("2011-2018", r)][2], r) for r in rules)
    k = max([i + 1 for i, (p, _) in enumerate(ps) if p <= 0.05 * (i + 1) / len(ps)], default=0)
    surv = [r for _, r in ps[:k]]
    print(f"\nDiscovery 2011-2018, Benjamini-Hochberg q 0.05 over {len(rules)} rules: {surv or 'none'}")
    for r in surv:
        s0 = np.sign(stage[("2011-2018", r)][0])
        ok1 = np.sign(stage[("2019-2026", r)][0]) == s0 and abs(stage[("2019-2026", r)][1]) >= 2
        ok2 = np.sign(stage[("NQ 2015-2025", r)][0]) == s0 and abs(stage[("NQ 2015-2025", r)][1]) >= 1.5
        print(f"  {r}: 2019-2026 {'PASS' if ok1 else 'FAIL'}; NQ futures {'PASS' if ok2 else 'FAIL'}")


if __name__ == "__main__":
    main()
