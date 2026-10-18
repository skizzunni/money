"""Round one hundred and eighteen: smaller bot trades before the day's breakout has touched.

    python research/touch_size.py nsx1m_scaled.pkl nq1m_scaled.pkl

The bot's trades split by the day's breakout (the strategy now; 4 MNQ, $200; $ a trade):
                         agree with an earlier touch    no touch yet           against (3-4% of trades)
  2011-18                +49.2 (t 5.40), 62%           +2.1 (t 0.18), 34%     -33.7
  2019-25                +29.4 (t 2.62), 55%           +26.9 (t 1.95), 42%    +86.7
  July 2025-2026         +22.3, 65%                    +56.0, 32%             -82.3
  NQ 2015-24             +37.8 (t 4.43), 57%           +8.6 (t 0.82), 39%     +33.9
2011-18 (the period kept for finding things) says the trades before any touch earn nothing. Variants, fixed before
running: those trades at 2 MNQ, or at 1 MNQ (the same 25-point cap; the bot's own decisions unchanged), in the
evaluation and funded. The user's intraday-trail evaluation (research/combo_more.evaluate).
Bar, fixed before running: adopted if, against now, the pass rate and payouts per evaluation are at least as high,
and one of them higher, on 2019-25 AND NQ 2015-24; the 13 months from July 2025 are reported too.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

SIZES = {"now": 4, "no-touch trades at 2": 2, "no-touch trades at 1": 1}


def no_touch(bars, bot, cands):
    """Entry bars of the bot's trades taken before the day's first breakout touch (or on days with none)."""
    first = {}
    for day_legs in cands:
        w = day_legs[0]
        first[bars.index[w["a"]].tz_convert(A.NY).normalize()] = w["a"] - 1
    out = set()
    for t in bot:
        day = t.entry_time.tz_convert(A.NY).normalize()
        if day not in first or first[day] >= t.entry_bar - 1:
            out.add(t.entry_bar)
    return out


def sized_legs(q_small, small):
    """trap_reversal.bot_legs with q_small contracts on the trades entered at the bars in `small`."""
    orig = T.bot_legs

    def legs(bars, trades, q):
        big = orig(bars, [t for t in trades if t.entry_bar not in small], q)
        little = orig(bars, [t for t in trades if t.entry_bar in small], q_small)
        return sorted(big + little, key=lambda x: x[1])
    return legs, orig


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    cands = M.w_candidates(bars, False)
    ev, pa = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    small = no_touch(bars, ev, cands) | no_touch(bars, pa, cands)
    rows = []
    for name, q in SIZES.items():
        legs, orig = sized_legs(q, small)
        T.bot_legs = legs
        try:
            rows += M.evaluate(bars, sess, ev, pa, cands, False, periods, name)
        finally:
            T.bot_legs = orig
    return rows


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    jobs = [(nsx, (("2011-2018", "2011-01-01", "2018-12-31"), ("2019-2025", "2019-01-01", "2025-06-30"),
                   ("Jul 2025-Aug 2026", "2025-07-01", "2026-08-14"))),
            (nq, (("NQ 2015-2024", "2015-03-01", "2024-12-31"),))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        df = pd.DataFrame([r for rows in pool.map(job, jobs) for r in rows])
    pd.set_option("display.width", 230)
    for label in df.period.unique():
        print(f"\n{label}")
        print(df[df.period == label].drop(columns="period").round(1).to_string(index=False))
    key = df.set_index(["setup", "period"])
    for name in list(SIZES)[1:]:
        ok = True
        for p in ("2019-2025", "NQ 2015-2024"):
            v, b = key.loc[(name, p)], key.loc[("now", p)]
            ok &= bool(v["eval pass %"] >= b["eval pass %"] and v["$ paid per eval"] >= b["$ paid per eval"] and
                       (v["eval pass %"] > b["eval pass %"] or v["$ paid per eval"] > b["$ paid per eval"]))
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
