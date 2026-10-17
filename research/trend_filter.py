"""Round ninety-one: trade with the multi-day trend only, or size with it, on one 50K Apex account.

    python research/trend_filter.py nsx1m_scaled.pkl nq1m_scaled.pkl

The user asks why the bot doesn't trade only clear uptrends and downtrends. The bot is an intraday trend strategy; a
multi-day trend was only one split in round eighteen (the trade the way of the last 20 sessions: no effect). Here it is
tested as a rule, on the account.

Trend at a session, from the daily closes of completed sessions only (the close of each session's last regular-hours
bar; nothing from the session itself), fixed before running:
  D1 the previous close above (up) / below (down) its 20-session simple moving average;
  D2 the same with 50 sessions;
  D3 D1 and D2 agree (both up = up, both down = down, else no clear trend);
  D4 the 20-session average rising (up) / falling (down) over the last 5 sessions.
Rules per definition: (a) with the trend only: longs only in an uptrend, shorts only in a downtrend, nothing when the
trend isn't clear (skipped trades are not placed but the bot's own state runs on, as research/wick_size.py's size 0);
(b) size tilt: 6 MNQ with the trend, 2 MNQ against it or when unclear. 8 rules, plus the bot as is (4 MNQ every trade).
Bot: v1.6 on 1-minute bars, 25-point max loss, take-profit 1.5 from the fill; evaluation 3 losers, lock 1.0 / +2.5;
funded 2 losers, lock 0.5 / +6.25 (as the NinjaTrader strategy trades now).
Measures, 2011-18, 2019-25 and NQ futures 2015-24 (machinery as research/wick_size.py, per-trade sizes, q = 1):
winners, $ a week, worst losing stretch, share of trades kept, the 50K intraday-trail evaluation pass / bust / timeout %
(apex25k.attempt, $3,000 target, $2,000 drawdown), payouts per evaluation (apex_payouts.pa_run, base caps), and the
funded account's first payout within 20 and 40 sessions (fast_payout.first_payout, no profit or loss stop).
Adoption bar, fixed before running: the rule with the highest payouts per evaluation on 2011-18 must beat the bot as is
by at least 10% in payouts per evaluation, with an evaluation pass rate no lower, on 2019-25 AND on NQ futures.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import fast_payout as F  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

A.TARGET, A.DD, A.DLL = 3000.0, 2000.0, 1000.0
CAP = 25.0
DEFS = ("D1", "D2", "D3", "D4")
RULES = ["bot"] + [f"{d} {k}" for d in DEFS for k in ("with-trend only", "tilt 6/2")]


def trades_for(bars, losers, lock_at, lock_plus):
    """lock_apex.trades_for plus each trade's direction: (session, pnl, max equity so far, minute equity, direction)."""
    cfg = NoiseConfig(qty=1, max_loss_per_trade=CAP * A.PV, max_losers=losers, fed_dates=A.FED, skip_dates="",
                      target_on_fill_bar=True, lock_at=lock_at, lock_plus=lock_plus)
    res = run(bars, cfg, minutes=1)
    h, lo = bars.high.to_numpy(float), bars.low.to_numpy(float)
    out = []
    for t in res.trades:
        a, b = t.entry_bar, t.exit_bar
        if t.direction > 0:
            hi_path, lo_path = h[a:b] - t.entry, lo[a:b] - t.entry
        else:
            hi_path, lo_path = t.entry - lo[a:b], t.entry - h[a:b]
        hi_path = np.append(hi_path * A.PV - A.FEE, t.pnl)
        lo_path = np.append(lo_path * A.PV - A.FEE, t.pnl)
        out.append((t.entry_time.tz_convert(A.NY).normalize().tz_localize(None), t.pnl,
                    np.maximum.accumulate(hi_path), lo_path, t.direction))
    return out


def trends(closes: pd.Series) -> dict[str, pd.Series]:
    """closes: each session's close, indexed by session date. Returns, per definition, the trend (+1, -1, 0) known at
    the START of each session, from earlier sessions only."""
    prev = closes.shift(1)
    sma20, sma50 = closes.rolling(20).mean().shift(1), closes.rolling(50).mean().shift(1)
    d1 = np.sign(prev - sma20).fillna(0.0)
    d2 = np.sign(prev - sma50).fillna(0.0)
    d3 = d1.where(d1 == d2, 0.0)
    d4 = np.sign(sma20 - sma20.shift(5)).fillna(0.0)
    return {"D1": d1, "D2": d2, "D3": d3, "D4": d4}


def size_for(rule: str, direction: int, trend: float) -> int:
    if rule == "bot":
        return 4
    agree = trend != 0 and np.sign(trend) == direction
    if rule.endswith("with-trend only"):
        return 4 if agree else 0
    return 6 if agree else 2


def sized(trades, rule, tr_map):
    out = []
    for day, pnl, hi, lo, d in trades:
        q = size_for(rule, d, tr_map[rule.split()[0]].get(day, 0.0) if rule != "bot" else 0.0)
        if q:
            out.append((day, q * pnl, q * hi, q * lo))
    return out


def job(args):
    path, label, first, last_start = args
    bars = A.rth(path)
    m = bars.index.tz_convert(A.NY)
    dates = m.normalize().tz_localize(None)
    closes = pd.Series(bars.close.to_numpy(float), index=dates).groupby(level=0).last()
    tr_map = trends(closes)
    ev_tr = trades_for(bars, 3, 1.0, 2.5)
    pa_tr = trades_for(bars, 2, 0.5, 6.25)
    all_sess = sorted(set(m[(m.hour * 60 + m.minute) == 570].normalize().tz_localize(None)))
    sess = [d for d in all_sess if d >= pd.Timestamp(first)]
    last = pd.Timestamp(last_start)
    starts = [s for s, d in enumerate(sess) if d <= last]
    in_p = [t for t in ev_tr if pd.Timestamp(first) <= t[0] <= last]
    rows = []
    for rule in RULES:
        ev_s, pa_s = sized(ev_tr, rule, tr_map), sized(pa_tr, rule, tr_map)
        ev_days, pa_days = P.by_day(ev_s, sess), P.by_day(pa_s, sess)
        n = passes = busts = 0
        paid, memo = [], {}
        for s in starts:
            n += 1
            res, used = A.attempt(ev_days[s:], 1, "intraday", 30)
            busts += res == "failed"
            if res != "passed":
                paid.append(0.0)
                continue
            passes += 1
            fp = s + used
            if fp not in memo:
                memo[fp] = sum(a for _, a in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
            paid.append(memo[fp])
        fp20 = [F.first_payout(pa_days[s:], 1, None, None, 40) for s in starts]
        kept = [t for t in in_p if size_for(rule, t[4], tr_map[rule.split()[0]].get(t[0], 0.0)
                                             if rule != "bot" else 0.0)]
        daily = pd.Series(0.0, index=pd.DatetimeIndex([d for d in sess if d <= last]))
        for day, pnl, _, _ in ev_s:
            if day in daily.index:
                daily[day] += pnl
        eq = daily.cumsum()
        win = [t[1] > 0 for t in kept]
        rows.append({"period": label, "rule": rule, "trades kept %": 100 * len(kept) / len(in_p),
                     "winners %": 100 * np.mean(win) if win else 0.0,
                     "$/week": daily.groupby(daily.index.to_period("W")).sum().mean(),
                     "worst stretch": float((eq.cummax() - eq).max()),
                     "eval pass %": 100 * passes / n, "eval bust %": 100 * busts / n,
                     "timeout %": 100 * (n - passes - busts) / n, "$ paid per eval": float(np.mean(paid)),
                     "1st pay in 20 %": 100 * np.mean([r[0] == "paid" and r[1] <= 20 for r in fp20]),
                     "1st pay in 40 %": 100 * np.mean([r[0] == "paid" for r in fp20])})
    return rows


def check_trends() -> None:
    """The trend at a session never uses that session's close."""
    idx = pd.date_range("2020-01-01", periods=80, freq="B")
    closes = pd.Series(np.arange(80, dtype=float), index=idx)
    a = trends(closes)
    bumped = closes.copy()
    bumped.iloc[60] = -1e6  # a crash on session 60 only
    b = trends(bumped)
    for k in DEFS:
        assert a[k].iloc[60] == b[k].iloc[60], k  # session 60's own close doesn't reach its trend
        assert a[k].iloc[61] != b[k].iloc[61] or k == "D4", k  # it does reach the next session's (D4 via the slope)
    assert a["D1"].iloc[30] == 1 and a["D3"].iloc[60] == 1 and a["D4"].iloc[60] == 1
    assert a["D2"].iloc[30] == 0  # not enough history for 50 sessions


def main() -> None:
    check_trends()
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, "2011-2018", "2011-01-01", "2018-12-31"), (nsx, "2019-2025", "2019-01-01", "2025-06-30"),
            (nq, "NQ 2015-2024", "2015-03-01", "2024-12-31")]
    with ProcessPoolExecutor(max_workers=3) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 250)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    disc = df[(df.period == "2011-2018") & (df.rule != "bot")].sort_values("$ paid per eval", ascending=False).iloc[0]
    print(f"\nbest on 2011-18: {disc.rule} (${disc['$ paid per eval']:.0f} per evaluation)")
    ok = True
    for label in ("2019-2025", "NQ 2015-2024"):
        d = df[df.period == label].set_index("rule")
        b, c = d.loc[disc.rule], d.loc["bot"]
        good = b["$ paid per eval"] >= 1.1 * c["$ paid per eval"] and b["eval pass %"] >= c["eval pass %"]
        ok &= good
        print(f"  {label}: ${b['$ paid per eval']:.0f} vs ${c['$ paid per eval']:.0f}, pass {b['eval pass %']:.1f}% vs "
              f"{c['eval pass %']:.1f}%: {'PASS' if good else 'FAIL'}")
    print(f"  {'ADOPT' if ok else 'NOT ADOPTED'}")


if __name__ == "__main__":
    main()
