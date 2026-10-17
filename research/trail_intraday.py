"""Round eighty-five: a trailing stop instead of the fixed lock, for the 50K intraday-trail account.

    python research/trail_intraday.py nsx1m_scaled.pkl nq1m_scaled.pkl

On an intraday trailing drawdown the threshold follows the open-profit peak. A trade that runs to the lock trigger
(+25 points at 4 MNQ, $200) and is then stopped at entry + 2.5 adds about $10 but lifts the threshold about $180: the
open profit given back costs cushion for good. A stop that, once activated, trails the best price gives back less.
Rounds forty and forty-one tested trailing locks at 10 MNQ, $350 on an end-of-day $50K evaluation; never on the
intraday-trail objective at 4 MNQ with the payout simulation.

Rules, fixed before running. The bot at 4 MNQ, $200 (25-point cap), take-profit 1.5 noise units from the fill, 3 losers
a day in the evaluation, 2 in the funded account, 1-minute bars. The fixed lock is replaced by a trailing stop: once a
1-minute bar's high (long) or low (short) is A points past the entry, from the next minute the stop sits B points behind
the best price so far (it never moves back; the line stop and max loss still apply if closer). Stops are checked every
minute, the stop first when stop and target share a minute. Variants (A, B) in points: (25, 22.5), (25, 15), (12.5, 10),
(12.5, 6.25), (37.5, 25), and the current fixed lock (25 -> entry + 2.5) in the evaluation. The funded account two
ways: as the strategy trades it now (fixed lock at 12.5 points -> entry + 6.25) for every variant ("funded now"), and
separately with the same trailing stop as the evaluation ("funded trail").
The engine below is a copy of mnqbot/noise.py's run() (stop mode) with the trailing option; with the trail off it must
reproduce mnqbot.noise.run trade for trade (checked on a slice before the full run).
Measures (index 2011-18, 2019-25, NQ futures 2015-24; machinery as research/eval_lock_size.py): winners %, $ a week,
evaluation pass / bust / timeout %, payouts per evaluation (apex_payouts.pa_run, base caps), funded busts %.
Adoption bar, fixed before running: the variant with the highest evaluation pass rate on 2011-18 must beat the current
by at least 2 points of pass rate on 2019-25 AND on NQ futures, with payouts per evaluation (funded now) no lower on
both.
"""
from __future__ import annotations

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

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import (  # noqa: E402
    FED_CUTOFF,
    FIRST_CHECK,
    LAST_CHECK,
    N_CHECKS,
    RTH_CLOSE,
    RTH_OPEN,
    STEP,
    NoiseConfig,
    run,
)

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP, Q = 25.0, 4
TRAILS = {"fixed lock (now)": None, "trail 25/22.5": (25.0, 22.5), "trail 25/15": (25.0, 15.0),
          "trail 12.5/10": (12.5, 10.0), "trail 12.5/6.25": (12.5, 6.25), "trail 37.5/25": (37.5, 25.0)}
CURRENT = "fixed lock (now)"


def run_trail(bars, cfg, trail):
    """mnqbot.noise.run (stop mode, 1-minute bars) with the lock replaced by a trailing stop when trail = (A, B)."""
    minutes = 1
    idx = bars.index.tz_convert(NY)
    o, c = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    h, lo = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
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
    best = math.nan  # trailing: the best price since activation
    pending = None
    trades = []

    def close_pos(i, price, reason):
        nonlocal pos, locked, losers_today, best
        pnl = pos * (price - entry_px) * cfg.qty * cfg.point_value - 2 * cfg.commission_per_side * cfg.qty
        trades.append((pos, entry_bar, idx[entry_bar], entry_px, i, price, reason, pnl))
        if pnl < 0 and reason != "Session ended":
            losers_today += 1
        pos, locked, best = 0, False, math.nan

    for i in range(len(bars)):
        t = idx[i]
        t_min = t.hour * 60 + t.minute
        end = t_min + minutes
        in_rth = t_min >= RTH_OPEN and end <= RTH_CLOSE
        if pending is not None:
            kind, d = pending
            pending = None
            if kind == "entry" and pos == 0:
                pos, entry_px, entry_bar = d, o[i] + d * slip, i
        if pos and not math.isnan(upper):
            line = upper * (1 - cfg.stop_buffer * sigma) if pos > 0 else lower * (1 + cfg.stop_buffer * sigma)
            reason = "Back inside"
            base = entry_px if entry_bar != i else est_px
            cap = base - pos * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
            if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                line, reason = cap, "Max loss"
            if locked:
                lk = entry_px + pos * cfg.lock_plus if trail is None else best - pos * trail[1]
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
        if pos:
            ext = h[i] if pos > 0 else lo[i]
            if trail is None:
                if not locked:
                    trigger = cfg.lock_at * cfg.max_loss_per_trade / cfg.qty / cfg.point_value
                    locked = pos * (ext - entry_px) >= trigger
            else:
                if locked:
                    best = max(best, ext) if pos > 0 else min(best, ext)
                elif pos * (ext - entry_px) >= trail[0]:
                    locked, best = True, ext
        if pos and (not in_rth or t_min == RTH_OPEN):
            close_pos(i, c[i] - pos * slip, "Session ended")
        if t_min == RTH_OPEN:
            prev_close = last_rth_close
            day_open = o[i]
            losers_today = 0
            upper = lower = sigma = math.nan
            today = [math.nan] * N_CHECKS
            skip_today = t.strftime("%Y-%m-%d") in cfg.skip_dates
            fed_today = cfg.fed_no_shorts and t.strftime("%Y-%m-%d") in cfg.fed_dates
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
                short_ok = not (fed_today and end < FED_CUTOFF)
                fresh_ok = cfg.max_losers <= 0 or losers_today < cfg.max_losers
                if skip_today or pos:
                    pass
                elif c[i] > upper and fresh_ok:
                    pending = ("entry", 1)
                elif c[i] < lower and short_ok and fresh_ok:
                    pending = ("entry", -1)
                if pending is not None:
                    est_px = c[i] + pending[1] * slip
        if in_rth and end == RTH_CLOSE:
            if pos:
                close_pos(i, c[i] - pos * slip, "16:00 close")
            if not math.isnan(day_open) and not any(math.isnan(x) for x in today):
                ring[slot * N_CHECKS:(slot + 1) * N_CHECKS] = today
                slot = (slot + 1) % lb_n
                filled += 1
            day_open = math.nan
    return trades


def config(losers, lock_at=1.0, lock_plus=2.5):
    return NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                       target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus)


def trades_for(bars, losers, trail, lock_at=1.0, lock_plus=2.5):
    """(session, pnl, running max of minute equity, minute equity) per trade, 1 contract (as apex25k.trades_for)."""
    tr = run_trail(bars, config(losers, lock_at, lock_plus), trail)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for d, a, et, en, b, _, _, pnl in tr:
        if d > 0:
            hi_path, lo_path = h[a:b] - en, lo[a:b] - en
        else:
            hi_path, lo_path = en - lo[a:b], en - h[a:b]
        hi_path = np.append(hi_path * A.PV - A.FEE, pnl)
        lo_path = np.append(lo_path * A.PV - A.FEE, pnl)
        out.append((et.tz_convert(A.NY).normalize().tz_localize(None), pnl, np.maximum.accumulate(hi_path), lo_path))
    return out


def check_parity(path):
    """With the trail off, the copy must trade exactly like mnqbot.noise.run."""
    bars = A.rth(path)
    bars = bars[(bars.index >= "2017-01-01") & (bars.index < "2018-07-01")]
    for losers, la, lp in ((3, 1.0, 2.5), (2, 0.5, 6.25)):
        ref = run(bars, config(losers, la, lp), minutes=1).trades
        mine = run_trail(bars, config(losers, la, lp), None)
        assert len(ref) == len(mine), (len(ref), len(mine))
        for r, m in zip(ref, mine, strict=True):
            assert (r.direction, r.entry_bar, r.exit_bar, r.reason) == (m[0], m[1], m[4], m[6]), (r, m)
            assert abs(r.entry - m[3]) < 1e-9 and abs(r.exit - m[5]) < 1e-9 and abs(r.pnl - m[7]) < 1e-6
    return len(ref)


def job(args):
    path, name, periods = args
    trail = TRAILS[name]
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    ev_tr = trades_for(bars, 3, trail)
    pa_now = trades_for(bars, 2, None, 0.5, 6.25)
    pa_trail = pa_now if trail is None else trades_for(bars, 2, trail)
    rows = []
    for label, first, last_start in periods:
        sess = [x for x in all_sess if x >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        ev_days = P.by_day(ev_tr, sess)
        outcomes = []
        for s, day in enumerate(sess):
            if day > last:
                break
            outcomes.append(A.attempt(ev_days[s:], Q, "intraday", 30))
        n = len(outcomes)
        row = {"period": label, "variant": name,
               "winners %": 100 * np.mean([x[1] > 0 for x in ev_tr if pd.Timestamp(first) <= x[0] <= last])}
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in ev_tr:
            if day in daily.index:
                daily[day] += Q * pnl
        row["$/week"] = daily.groupby(daily.index.to_period("W")).sum().mean()
        row["pass %"] = 100 * sum(r == "passed" for r, _ in outcomes) / n
        row["bust %"] = 100 * sum(r == "failed" for r, _ in outcomes) / n
        row["timeout %"] = 100 - row["pass %"] - row["bust %"]
        for tag, pa_tr in (("funded now", pa_now), ("funded trail", pa_trail)):
            pa_days = P.by_day(pa_tr, sess)
            memo, paid, fb = {}, [], []
            for (res, used), s in zip(outcomes, range(n), strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    pp, end, _ = P.pa_run(pa_days[fp:], Q, P.CAPS["base"])
                    memo[fp] = (sum(a for _, a in pp), end == "failed")
                paid.append(memo[fp][0])
                fb.append(memo[fp][1])
            row[f"$/eval ({tag})"] = float(np.mean(paid))
            row[f"funded bust % ({tag})"] = 100 * np.mean(fb) if fb else float("nan")
        rows.append(row)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    print(f"parity with mnqbot.noise.run, trail off: {check_parity(nsx)} trades on index 2017 - mid 2018, "
          f"{check_parity(nq)} on NQ 2017 - mid 2018: identical")
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    jobs = [(nsx, n, idx_p) for n in TRAILS] + [(nq, n, nq_p) for n in TRAILS]
    with ProcessPoolExecutor(max_workers=4) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["period", "variant"])
    best = df[df.period == "2011-2018"].sort_values("pass %", ascending=False).iloc[0].variant
    print(f"\nbest on 2011-18 by pass rate: {best}")
    ok = best != CURRENT
    for p in ("2019-2025", "NQ 2015-2024"):
        b, c = key.loc[(p, best)], key.loc[(p, CURRENT)]
        good = b["pass %"] >= c["pass %"] + 2 and b["$/eval (funded now)"] >= c["$/eval (funded now)"]
        ok &= good
        print(f"  {p}: pass {b['pass %']:.1f}% vs {c['pass %']:.1f}%, paid ${b['$/eval (funded now)']:.0f} vs "
              f"${c['$/eval (funded now)']:.0f}: {'PASS' if good else 'FAIL'}")
    print(f"  {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
