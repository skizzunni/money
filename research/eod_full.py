"""Round one hundred and eight: the whole EOD route (EOD evaluation, then an EOD funded account), and the add-ons
that failed on the intraday trail, again on it.

    python research/eod_full.py nsx1m_scaled.pkl nq1m_scaled.pkl

Round one hundred and seven: the EOD-trail evaluation passes 1.6-1.8 times as often, but the funded account after it
was still modelled with the intraday trail. Apex's 2026 EOD funded account (third-party summaries of Apex's docs;
check Apex's own): the threshold is $2,000 under the highest END-OF-DAY balance (intraday profit doesn't move it),
enforced in real time, and stops at +$100 once the highest close reaches +$2,100; payouts after five days of $250 or
more (EOD; $200 intraday), a $52,600 balance, no day above 50% of the profit since the last payout, $500 minimum,
caps $1,500 ... $3,000, six payouts. The daily loss limit as research/apex_payouts.py ($1,000 / $2,000 / $3,000).

Round 102's "together" (a same-direction breakout taken while the bot is in, at most 10 MNQ) and round 105's
overnight long (1 MNQ, 18:01 to the 09:30 open, stop 100) both failed on the intraday trail because they add size
and swings that open profit drags the threshold up with; an end-of-day threshold doesn't see those swings.
Setups, fixed before running (the evaluation side at round sixty's EOD setting, 6 MNQ / $300 / 3 losers; funded
as now, 4 MNQ / $200 / 2 losers; funded 6 MNQ / $300 is the third):
  base         the strategy now on the EOD route
  together     + together, in the evaluation and funded
  overnight    + the overnight long, in the evaluation and funded
  funded 6     base, but the funded side at 6 MNQ, $300 (2 losers, lock 0.5 / +6.25)
Bar, fixed before running: a setup is adopted if, against base, it pays more per evaluation in all three periods
with a pass rate and a first payout within 20 sessions at least as often; if several, the one paying most in sum.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_more as M  # noqa: E402
import overnight_combo as O  # noqa: E402
import trap_reversal as T  # noqa: E402

QUAL_EOD = 250.0
SETUPS = ("base", "together", "overnight", "funded 6")


def pa_eod(days, caps):
    """An EOD funded account from days[0]: (payouts [(session, $)], 'closed' | 'failed' | 'alive', sessions)."""
    bal = close_peak = 0.0
    paid, cycle = [], []
    for n, (_, trades) in enumerate(days):
        thr = min(close_peak - P.PA_DD, P.PA_LOCK)
        day_start, dll = bal, P.dll_for(bal)
        for pnl, _, lo_path in trades:
            eq = bal + lo_path
            bust, stop = np.flatnonzero(eq <= thr), np.flatnonzero(eq - day_start <= -dll)
            if bust.size and (not stop.size or bust[0] < stop[0] or
                              (bust[0] == stop[0] and thr >= day_start - dll)):
                return paid, "failed", n + 1
            if stop.size:
                bal = day_start - dll
                if bal <= thr:
                    return paid, "failed", n + 1
                break
            bal += pnl
        close_peak = max(close_peak, bal)
        cycle.append(bal - day_start)
        prof = sum(cycle)
        if sum(x >= QUAL_EOD for x in cycle) >= 5 and bal >= P.MIN_BAL and prof > 0 and max(cycle) <= 0.5 * prof:
            amt = min(caps[len(paid)], bal - P.SAFETY)
            if amt >= P.MIN_PAY:
                paid.append((n, amt))
                bal -= amt
                cycle = []
                if len(paid) == 6:
                    return paid, "closed", n + 1
    return paid, "alive", len(days)


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    cands = M.w_candidates(bars, False)
    night = O.overnight(path, 1, 100.0, delay=1)

    def legs(bot, q, together):
        M.BOTQ = q
        out = T.leg_paths(bars, M.combine(bars, bot, cands, together)[0])
        M.BOTQ = 4
        return out

    ev6, ev6_tog = legs(ev_bot, 6, False), legs(ev_bot, 6, True)
    pa4, pa4_tog, pa6 = legs(pa_bot, 4, False), legs(pa_bot, 4, True), legs(pa_bot, 6, False)
    plan = {"base": (ev6, pa4), "together": (ev6_tog, pa4_tog), "overnight": (night + ev6, night + pa4),
            "funded 6": (ev6, pa6)}
    rows = []
    for label, first, last_start in periods:
        ss = [d for d in sess if d >= pd.Timestamp(first)]
        last = pd.Timestamp(last_start)
        starts = [s for s, d in enumerate(ss) if d <= last]
        for name in SETUPS:
            ev_days, pa_days = P.by_day(plan[name][0], ss), P.by_day(plan[name][1], ss)
            outs = [A.attempt(ev_days[s:], 1, "eod", 30) for s in starts]
            memo, paid, six = {}, [], 0
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = pa_eod(pa_days[fp:], P.CAPS["base"])
                paid.append(sum(a for _, a in memo[fp][0]))
                six += memo[fp][1] == "closed"
            firsts = [pa_eod(pa_days[s:s + 20], P.CAPS["base"]) for s in starts]
            r = [o for o, _ in outs]
            rows.append({"period": label, "setup": name, "pass %": 100 * r.count("passed") / len(r),
                         "bust %": 100 * r.count("failed") / len(r),
                         "sessions to pass": float(np.median([u for o, u in outs if o == "passed"])),
                         "$ paid per eval": float(np.mean(paid)), "all 6 %": 100 * six / len(starts),
                         "paid in 10 %": 100 * np.mean([bool(f[0]) and f[0][0][0] < 10 for f in firsts]),
                         "paid in 20 %": 100 * np.mean([bool(f[0]) for f in firsts]),
                         "funded bust in 20 %": 100 * np.mean([f[1] == "failed" for f in firsts])})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    wins = []
    for name in SETUPS[1:]:
        ok = True
        for p in ("2011-2018", "2019-2025", "NQ 2015-2024"):
            v, b = key.loc[(name, p)], key.loc[("base", p)]
            ok &= bool(v["$ paid per eval"] > b["$ paid per eval"] and v["pass %"] >= b["pass %"] and
                       v["paid in 20 %"] >= b["paid in 20 %"])
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in df.period.unique()), name))
    print(f"ADOPT {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
