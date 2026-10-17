"""Round one hundred and three: manage the Williams breakout trade (lock, take-profit) to win more often.

    python research/w_manage.py nsx1m_scaled.pkl nq1m_scaled.pkl

The breakout as the NinjaTrader strategy trades it (round one hundred and one: the bot first, Williams in its gaps)
wins only 34-36% of its trades and lifts red days from a third to half. The bot's own lock (stop to entry + a little
once the trade is up 1 max loss) raised its winners a lot (rounds 82-83). The same for the breakout, in units of the
breakout's own stop R (a quarter of yesterday's range): lock at 0.5R, 1R or 1.5R, the stop then to entry + 0.1R from
the next bar; a take-profit at 2R or 4R or none; and each take-profit without a lock: 11 variants plus the strategy
now (research/combo_more.w_candidates, mgmt; measured as research/combo_more.evaluate).
Pick and bar, fixed before running: on 2011-18, the variant with the most $ paid per evaluation among those with $ a
week at least the strategy's now. On 2019-25 and NQ futures 2015-24 it is adopted if, against the strategy now: $ paid
per evaluation and the evaluation pass rate at least as high, $ a week at least 95% as high, and fewer red days.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

R = 0.25  # the stop, in yesterday's ranges
VARIANTS = {"now": None}
for lk, tg in itertools.product((0.5, 1.0, 1.5), (None, 2.0, 4.0)):
    VARIANTS[f"lock {lk}R" + (f", target {tg:g}R" if tg else "")] = (lk * R, 0.1 * R, tg * R if tg else None)
for tg in (2.0, 4.0):
    VARIANTS[f"target {tg:g}R"] = (99.0, 0.0, tg * R)  # a lock that never arms


def job(args):
    path, periods, names = args
    bars = A.rth(path)
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    sess = list(T.sessions_of(bars))
    rows = []
    for name in names:
        cands = M.w_candidates(bars, False, VARIANTS[name])
        rows += M.evaluate(bars, sess, ev_bot, pa_bot, cands, False, periods, name)
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    idx_p = (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"))
    nq_p = (("NQ 2015-2024", "2015-03-01", "2024-12-31"),)
    names = list(VARIANTS)
    chunks = [names[i::2] for i in range(2)]
    jobs = [(path, per, ch) for path, per in ((nsx, idx_p), (nq, nq_p)) for ch in chunks]
    with ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 220)
    for label in ("2011-2018", "2019-2025", "NQ 2015-2024"):
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    now = key.xs("now", level="setup")
    disc = df[(df.period == "2011-2018") & (df.setup != "now") & (df["$/week"] >= now.loc["2011-2018", "$/week"])]
    if disc.empty:
        print("no variant makes as much a week on 2011-18: NOT ADOPTED")
        return
    pick = disc.sort_values("$ paid per eval", ascending=False).iloc[0].setup
    print(f"\npick on 2011-18: {pick}")
    ok = True
    for p in ("2019-2025", "NQ 2015-2024"):
        v, b = key.loc[(pick, p)], now.loc[p]
        good = bool(v["$ paid per eval"] >= b["$ paid per eval"] and v["eval pass %"] >= b["eval pass %"] and
                    v["$/week"] >= 0.95 * b["$/week"] and v["red %"] < b["red %"])
        ok &= good
        print(f"  {p}: {'PASS' if good else 'FAIL'}")
    print("ADOPT" if ok else "NOT ADOPTED")


if __name__ == "__main__":
    main()
