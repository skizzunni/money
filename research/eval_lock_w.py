"""Round one hundred and twelve: the evaluation's lock again, now that the breakout trades in the bot's gaps.

    python research/eval_lock_w.py nsx1m_scaled.pkl nq1m_scaled.pkl

Rounds 82 and 84: arming the bot's lock earlier in the evaluation (0.5 max loss instead of 1.0) cut evaluation busts
by 6-12 points but more evaluations ran out of their 30 days, so the evaluation kept (1.0, +2.5). The breakout (round
101) now adds trades and money a week, which is what the timeouts lacked.
Evaluation locks, fixed before running: (1.0, +2.5) now, (0.5, +2.5), (0.5, +6.25) (the funded account's), and
(0.75, +4); 4 MNQ, $200, 3 losers; the funded account as now. The user's intraday trail, threshold never stopping
(research/combo_more.evaluate), and as a second reading with the threshold stopping at the start (round 109).
Bar, fixed before running: adopted if, against (1.0, +2.5), the pass rate is higher and payouts per evaluation at least
as high in all three periods, on the never-stopping reading; if several, the most paid in sum.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import apex_payouts as P  # noqa: E402
import combo_more as M  # noqa: E402
import eval_lock as EL  # noqa: E402
import trap_reversal as T  # noqa: E402

LOCKS = ((1.0, 2.5), (0.5, 2.5), (0.5, 6.25), (0.75, 4.0))


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    pa_bot = T.bot_trades(bars, 2, 0.5, 6.25)
    pa_legs, _ = M.combine(bars, pa_bot, cands, False)
    pa = T.leg_paths(bars, pa_legs)
    rows = []
    for lk in LOCKS:
        ev_legs, ev_tr = M.combine(bars, T.bot_trades(bars, 3, *lk), cands, False)
        name = f"lock {lk[0]} / +{lk[1]}"
        rows += M.evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name)
        ev = T.leg_paths(bars, ev_legs)
        for label, first, last_start in periods:  # the second reading: the threshold stops at the start
            ss = [d for d in sess if d >= pd.Timestamp(first)]
            ev_days, pa_days = P.by_day(ev, ss), P.by_day(pa, ss)
            starts = [s for s, d in enumerate(ss) if d <= pd.Timestamp(last_start)]
            outs = [EL.attempt_lock(ev_days[s:], 0.0, 1.0) for s in starts]
            memo, paid = {}, []
            for s, (res, used) in zip(starts, outs, strict=True):
                if res != "passed":
                    paid.append(0.0)
                    continue
                fp = s + used
                if fp not in memo:
                    memo[fp] = sum(x for _, x in P.pa_run(pa_days[fp:], 1, P.CAPS["base"])[0])
                paid.append(memo[fp])
            r = [o for o, _ in outs]
            rows.append({"period": label, "setup": name + " (threshold stops)",
                         "eval pass %": 100 * r.count("passed") / len(r),
                         "eval bust %": 100 * r.count("failed") / len(r),
                         "$ paid per eval": sum(paid) / len(paid)})
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 230)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    base = f"lock {LOCKS[0][0]} / +{LOCKS[0][1]}"
    wins = []
    for lk in LOCKS[1:]:
        name = f"lock {lk[0]} / +{lk[1]}"
        ok = all(key.loc[(name, p)]["eval pass %"] > key.loc[(base, p)]["eval pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[(base, p)]["$ paid per eval"]
                 for p in df.period.unique())
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if ok:
            wins.append((sum(key.loc[(name, p)]["$ paid per eval"] for p in df.period.unique()), name))
    print(f"ADOPT {max(wins)[1]}" if wins else "NOT ADOPTED")


if __name__ == "__main__":
    main()
