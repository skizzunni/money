"""Round eighty-six: on news days only, check every 15 minutes, or allow one more loser.

    python research/news_checks.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds seventy-three and eighty: the bot earns 2-3x its usual $ a day on jobs-report days (research/nfp_dates.csv)
and on the session after a mega-cap earnings report (research/megacap_earnings.csv, reaction session as research/
earnings_days.py: the first session on or after 'reaction_from'), in every period, under the bar. Sizing up on them
concentrates risk on a $2,000 trailing drawdown (rounds seventy-six, seventy-nine), and quarter-hour checks on every day
add swings, not money (round fifty-five, research/checks15.py). Untested: more chances on news days only, same size.

Variants, fixed before running (one 50K intraday-trail account; 4 MNQ, $200 max loss = 25 points, take-profit 1.5 from
the fill, Fed rule, 1-minute bars; evaluation 3 losers a day with the lock at 1.0 / +2.5, funded 2 losers a day with
the lock at 0.5 / +6.25, as the NinjaTrader strategy trades now):
  C0  every day as now: checks at 10:00, 10:30, ..., 15:30.
  V1  on news days (jobs-report days + mega-cap earnings reaction sessions) checks every 15 minutes, 10:00, 10:15, ...,
      15:30, each quarter hour with its own noise: the average of that time of day's |close / day open - 1| over the
      last 14 sessions that had all eleven :15/:45 checks (the half-hour checks keep their own history exactly as now).
      Other days as C0.
  V2  on news days the daily loser limit is one higher (4 in the evaluation, 3 funded); half-hour checks. Other days
      as C0.
Engine: a copy of mnqbot.noise.run with those two per-day options (checked first: C0 reproduces mnqbot.noise.run trade
for trade, and its evaluation pass rates 27.5 / 22.9 / 25.3 % from round eighty-four).
Measures (index 2011-18, 2019-25, NQ futures 2015-24; machinery as research/eval_lock_size.py): evaluation pass / bust /
timeout %, payouts per evaluation (apex_payouts.pa_run, base caps), $ a week and winners of the evaluation setting,
extra trades a week against C0.
Adoption bar, fixed before running: a variant is adopted only if its evaluation pass rate is >= C0's AND its payouts per
evaluation are higher than C0's, in ALL three periods.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402

from mnqbot.noise import FED_CUTOFF, RTH_CLOSE, RTH_OPEN, NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP, Q = 25.0, 4
EVAL = dict(losers=3, lock_at=1.0, lock_plus=2.5)
FUND = dict(losers=2, lock_at=0.5, lock_plus=6.25)
FIRST, LAST = 600, 930
VARIANTS = {"C0 now": (False, 0), "V1 15-min checks on news days": (True, 0), "V2 +1 loser on news days": (False, 1)}


def run_news(bars, cfg: NoiseConfig, news: set, quarter: bool, extra_losers: int):
    """mnqbot.noise.run (stop mode, 1-minute bars) with two options on news days: checks every 15 minutes (quarter) and
    extra_losers more losers allowed. Returns the trades as (entry_bar, exit_bar, direction, entry, pnl, entry_time)."""
    idx = bars.index.tz_convert(A.NY)
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    h, lo = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    dstr = idx.strftime("%Y-%m-%d")
    slip, lb_n, minutes = cfg.slippage_ticks * cfg.tick, cfg.lookback, 1
    n_h, n_q = 12, 11
    ring_h, ring_q = np.full(lb_n * n_h, np.nan), np.full(lb_n * n_q, np.nan)
    today = [math.nan] * 23
    fill_h = fill_q = slot_h = slot_q = 0
    day_open = prev_close = last_rth_close = math.nan
    upper = lower = sigma = math.nan
    skip_today = fed_today = news_today = False
    pos, entry_px, entry_bar, est_px = 0, 0.0, 0, math.nan
    losers_today, locked = 0, False
    pending = None
    trades = []
    cap_pts = cfg.max_loss_per_trade / cfg.qty / cfg.point_value

    def close_pos(i, price, reason):
        nonlocal pos, locked, losers_today
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - 2 * cfg.commission_per_side * cfg.qty
        trades.append((entry_bar, i, pos, entry_px, pnl, idx[entry_bar]))
        if pnl < 0 and reason != "Session ended":
            losers_today += 1
        pos, locked = 0, False

    for i in range(len(bars)):
        t_min = tmin[i]
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
            base = entry_px if entry_bar != i else est_px
            cap = base - pos * cap_pts
            if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                line, reason = cap, "Max loss"
            if locked:
                lk = entry_px + pos * cfg.lock_plus
                if (pos > 0 and lk > line) or (pos < 0 and lk < line):
                    line, reason = lk, "Lock"
            if entry_bar == i:
                hit = lo[i] <= line if pos > 0 else h[i] >= line
                price = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):
                hit, price = True, o[i] - pos * slip
            else:
                hit = lo[i] <= line if pos > 0 else h[i] >= line
                price = line - pos * slip
            if hit:
                close_pos(i, price, reason)
            elif cfg.take_profit > 0:
                tp = (entry_px if entry_bar != i else est_px) * (1 + pos * cfg.take_profit * sigma)
                if (pos > 0 and h[i] >= tp + cfg.tick) or (pos < 0 and lo[i] <= tp - cfg.tick):
                    close_pos(i, tp, "Target")
        if pos and not locked and cfg.lock_at > 0:
            locked = pos * ((h[i] if pos > 0 else lo[i]) - entry_px) >= cfg.lock_at * cap_pts
        if pos and (not in_rth or t_min == RTH_OPEN):
            close_pos(i, c[i] - pos * slip, "Session ended")
        if t_min == RTH_OPEN:
            prev_close, day_open = last_rth_close, o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * 23
            skip_today = dstr[i] in cfg.skip_dates
            fed_today = cfg.fed_no_shorts and dstr[i] in cfg.fed_dates
            news_today = dstr[i] in news
        if in_rth:
            last_rth_close = c[i]
        if in_rth and not math.isnan(day_open) and FIRST <= end <= LAST and (end - FIRST) % 15 == 0:
            k = (end - FIRST) // 15
            today[k] = abs(c[i] / day_open - 1)
            half = k % 2 == 0
            if half:
                ready, ring, n, kk = fill_h >= lb_n, ring_h, n_h, k // 2
            else:
                ready, ring, n, kk = fill_q >= lb_n, ring_q, n_q, k // 2
            if (half or (quarter and news_today)) and ready and not math.isnan(prev_close):
                s = 0.0
                for dd in range(lb_n):
                    s += ring[dd * n + kk]
                sigma = s / lb_n
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                short_ok = not (fed_today and end < FED_CUTOFF)
                limit = cfg.max_losers + (extra_losers if news_today else 0)
                fresh_ok = limit <= 0 or losers_today < limit
                d = 0
                if skip_today or pos:
                    d = 0
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
            if not math.isnan(day_open):
                hs = [today[k] for k in range(0, 23, 2)]
                qs = [today[k] for k in range(1, 23, 2)]
                if not any(math.isnan(x) for x in hs):
                    ring_h[slot_h * n_h:(slot_h + 1) * n_h] = hs
                    slot_h, fill_h = (slot_h + 1) % lb_n, fill_h + 1
                if not any(math.isnan(x) for x in qs):
                    ring_q[slot_q * n_q:(slot_q + 1) * n_q] = qs
                    slot_q, fill_q = (slot_q + 1) % lb_n, fill_q + 1
            day_open = math.nan
    return trades


def config(losers, lock_at, lock_plus):
    return NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                       target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus)


def paths(bars, trades):
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for a, b, d, entry, pnl, t0 in trades:
        if d > 0:
            hi, lp = h[a:b] - entry, lo[a:b] - entry
        else:
            hi, lp = entry - lo[a:b], entry - h[a:b]
        hi = np.append(hi * A.PV - A.FEE, pnl)
        lp = np.append(lp * A.PV - A.FEE, pnl)
        out.append((t0.tz_convert(A.NY).normalize().tz_localize(None), pnl, np.maximum.accumulate(hi), lp))
    return out


def news_days(bars) -> set:
    idx = bars.index.tz_convert(A.NY).tz_localize(None)
    sess = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == RTH_OPEN].normalize())))
    dates = pd.to_datetime(pd.read_csv(HERE / "megacap_earnings.csv").reaction_from)
    pos = np.searchsorted(sess.values, dates.values)
    react = {sess[p] for p in pos if p < len(sess)}
    nfp = set(pd.to_datetime(pd.read_csv(HERE / "nfp_dates.csv").date))
    return {d.strftime("%Y-%m-%d") for d in react | nfp}


def check_parity(path):
    """C0 must reproduce mnqbot.noise.run trade for trade (a 2017-18 slice, both settings)."""
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    sl = bars[(m >= pd.Timestamp("2017-01-01", tz=A.NY)) & (m < pd.Timestamp("2018-07-01", tz=A.NY))]
    for st in (EVAL, FUND):
        cfg = config(**st)
        ref = run(sl, cfg, minutes=1).trades
        mine = run_news(sl, cfg, set(), False, 0)
        assert len(ref) == len(mine), (len(ref), len(mine))
        for r, x in zip(ref, mine, strict=True):
            assert (r.entry_bar, r.exit_bar, r.direction) == x[:3] and abs(r.pnl - x[4]) < 1e-9, (r, x)
    return len(ref)


def job(args):
    path, periods, (quarter, extra) = args
    bars = A.rth(path)
    news = news_days(bars)
    ev_raw = run_news(bars, config(**EVAL), news, quarter, extra)
    pa_raw = run_news(bars, config(**FUND), news, quarter, extra)
    ev_tr, pa_tr = paths(bars, ev_raw), paths(bars, pa_raw)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == RTH_OPEN].normalize().tz_localize(None)))
    rows = []
    for label, first, last_start in periods:
        sess = [x for x in all_sess if x >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days, pa_days = P.by_day(ev_tr, sess), P.by_day(pa_tr, sess)
        n = passes = busts = 0
        paid, memo = [], {}
        for s, day in enumerate(sess):
            if day > last:
                break
            n += 1
            res, used = A.attempt(ev_days[s:], Q, "intraday", 30)
            busts += res == "failed"
            if res != "passed":
                paid.append(0.0)
                continue
            passes += 1
            fp = s + used
            if fp not in memo:
                memo[fp] = sum(a for _, a in P.pa_run(pa_days[fp:], Q, P.CAPS["base"])[0])
            paid.append(memo[fp])
        in_p = [x for x in ev_tr if pd.Timestamp(first) <= x[0] <= last]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in in_p:
            if day in daily.index:
                daily[day] += Q * pnl
        weeks = daily.groupby(daily.index.to_period("W")).sum()
        rows.append({"period": label, "quarter": quarter, "extra": extra,
                     "eval pass %": 100 * passes / n, "eval bust %": 100 * busts / n,
                     "timeout %": 100 * (n - passes - busts) / n, "$ paid per eval": float(np.mean(paid)),
                     "$/week": weeks.mean(), "winners %": 100 * np.mean([x[1] > 0 for x in in_p]),
                     "trades/week": len(in_p) / len(weeks)})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    print("C0 parity with mnqbot.noise.run:", check_parity(nsx), "trades (index slice),", check_parity(nq), "(NQ)")
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(path, per, v) for path, per in ((nsx, idx_p), (nq, nq_p)) for v in VARIANTS.values()]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = [r for rs in pool.map(job, jobs) for r in rs]
    names = {v: k for k, v in VARIANTS.items()}
    df = pd.DataFrame(rows)
    df.insert(1, "variant", [names[(q, e)] for q, e in zip(df.quarter, df.extra, strict=True)])
    df = df.drop(columns=["quarter", "extra"])
    pd.set_option("display.width", 200)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        d = df[df.period == label].drop(columns="period").copy()
        base = d[d.variant == "C0 now"].iloc[0]
        d["extra trades/week"] = d["trades/week"] - base["trades/week"]
        print(f"\n{label}")
        print(d.round(2).to_string(index=False))
    key = df.set_index(["period", "variant"])
    for name in VARIANTS:
        if name == "C0 now":
            continue
        ok = all(key.loc[(p, name), "eval pass %"] >= key.loc[(p, "C0 now"), "eval pass %"] and
                 key.loc[(p, name), "$ paid per eval"] > key.loc[(p, "C0 now"), "$ paid per eval"]
                 for p in ("2011-2018", "2019-2025", "NQ 2015-2024"))
        print(f"{name}: {'ADOPTED' if ok else 'not adopted'}")


if __name__ == "__main__":
    main()
