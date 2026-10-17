"""Round one hundred and eleven: breakout trades lost to the bot's timing: a late entry, and a smaller "together".

    python research/combo_late.py nsx1m_scaled.pkl nq1m_scaled.pkl

The strategy now (round 101): a breakout trade only if its first touch comes while the bot is flat; a touch while
the bot is in a trade ends the breakout's day. Both are momentum setups, so the touch often comes while the bot is in.
Variants, fixed before running:
  late      when the first touch came while the bot was in a trade, the breakout re-arms once the bot is flat: the
            first bar closing beyond that level, same side, starting 15:00 at the latest and while the bot is flat,
            enters at the next bar's open (stop, size, exit and the bot-first cut as now).
  together6 round 102's "together" (a same-direction touch while the bot is in is taken too; a same-direction bot
            entry keeps the breakout trade) but at most 6 MNQ in all, so the breakout carries at most 2 beside the
            bot's 4 (round 102 allowed 10 and busted more).
  both      late + together6 (late applies to opposite-direction touches only, together6 to same-direction ones).
Measured as round 102 (research/combo_more.evaluate, the user's intraday-trail evaluation, threshold never stopping).
Bar, fixed before running: against the strategy now, more $ a week, a pass rate and payouts per evaluation at least as
high, and a first payout within 20 sessions at least as often, in all three periods.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apex25k as A  # noqa: E402
import combo_live as C  # noqa: E402
import combo_more as M  # noqa: E402
import trap_reversal as T  # noqa: E402

SETUPS = ("now", "late", "together6", "both")


def late_candidates(bars, bot, cands):
    """For each session whose first breakout touch came while the bot was in a trade: the late entry, if any, as a
    candidate like combo_more.w_candidates's."""
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, lo, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    spans = sorted((t.entry_bar, t.exit_bar, t.direction) for t in bot)
    starts = np.array([s for s, _, _ in spans])
    ends = np.array([e for _, e, _ in spans])
    out = {}
    for day_legs in cands:
        w = day_legs[0]
        a, d = w["a"], w["d"]
        k = int(np.searchsorted(starts, a, side="right")) - 1
        if not (k >= 0 and spans[k][0] <= a <= spans[k][1]):
            continue  # taken at its first touch (or not at all): nothing late
        lvl, q, dist, last = w["level"], w["q"], w["dist"], w["last"]
        j = ends[k]  # the bot is flat at the close of its exit bar
        while j < last and tmin[j] <= C.LAST_ENTRY:
            kk = int(np.searchsorted(starts, j + 1, side="right")) - 1
            if kk >= 0 and spans[kk][0] <= j + 1 <= spans[kk][1]:
                j = spans[kk][1] + 1  # the bot is in again: wait until it is flat
                continue
            if (d > 0 and c[j] >= lvl) or (d < 0 and c[j] <= lvl):
                e = j + 1
                entry = o[e] + d * C.TICK
                stop = entry - d * dist
                x, px = last, c[last] - d * C.TICK
                for m in range(e, last + 1):
                    if (d > 0 and lo[m] <= stop) or (d < 0 and h[m] >= stop):
                        x, px = m, (min(o[m], stop) if d > 0 else max(o[m], stop)) - d * C.TICK
                        break
                out[id(day_legs)] = {"a": e, "x": x, "d": d, "entry": entry, "px": px, "q": q, "stopped": False}
                break
            j += 1
    return out


def with_levels(bars, cands):
    """Add each first candidate's level, stop distance and last bar (combo_more.w_candidates doesn't keep them)."""
    idx = bars.index.tz_convert(A.NY)
    tmin = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o, h, lo = (bars[x].to_numpy(float) for x in ("open", "high", "low"))
    starts = np.flatnonzero(tmin == 570)
    info, prev = {}, None
    for n, a in enumerate(starts):
        b = starts[n + 1] if n + 1 < len(starts) else len(bars)
        b = a + int(np.searchsorted(day[a:b], day[a], side="right"))
        if prev is not None and prev > 0:
            info[a] = (o[a] + C.K * prev, o[a] - C.K * prev, C.S * prev, b - 1 if tmin[b - 1] < 960 else b - 2)
        prev = h[a:b].max() - lo[a:b].min()
    open_of = np.maximum.accumulate(np.where(tmin == 570, np.arange(len(bars)), 0))
    for day_legs in cands:
        w = day_legs[0]
        up, dn, dist, last = info[open_of[w["a"]]]
        w.update(level=up if w["d"] > 0 else dn, dist=dist, last=last)
    return cands


def combine(bars, bot, cands, late, together6):
    """combo_more.combine with the late entries (late: {id(day_legs): candidate}) and together6."""
    if together6:
        old = M.MAXQ
        M.MAXQ = 6
    if not late:
        legs, trades = M.combine(bars, bot, cands, together6)
    else:
        # a day whose first touch is skipped gets its late candidate in its place (same rules from there on)
        new = [[late[id(dl)]] if id(dl) in late and not (together6 and _same(bot, dl[0])) else dl for dl in cands]
        legs, trades = M.combine(bars, bot, new, together6)
    if together6:
        M.MAXQ = old
    return legs, trades


def _same(bot, w):
    for t in bot:
        if t.entry_bar <= w["a"] <= t.exit_bar:
            return t.direction == w["d"]
    return False


def job(args):
    path, periods = args
    bars = A.rth(path)
    sess = list(T.sessions_of(bars))
    ev_bot, pa_bot = T.bot_trades(bars, 3, 1.0, 2.5), T.bot_trades(bars, 2, 0.5, 6.25)
    cands = with_levels(bars, M.w_candidates(bars, False))
    late_ev, late_pa = late_candidates(bars, ev_bot, cands), late_candidates(bars, pa_bot, cands)
    rows = []
    for name in SETUPS:
        lt, tg = name in ("late", "both"), name in ("together6", "both")
        ev_legs, ev_tr = combine(bars, ev_bot, cands, late_ev if lt else None, tg)
        pa_legs, _ = combine(bars, pa_bot, cands, late_pa if lt else None, tg)
        rows += M.evaluate_legs(bars, sess, ev_legs, ev_tr, pa_legs, periods, name)
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
    for name in SETUPS[1:]:
        ok = all(key.loc[(name, p)]["$/week"] > key.loc[("now", p)]["$/week"] and
                 key.loc[(name, p)]["eval pass %"] >= key.loc[("now", p)]["eval pass %"] and
                 key.loc[(name, p)]["$ paid per eval"] >= key.loc[("now", p)]["$ paid per eval"] and
                 key.loc[(name, p)]["paid in 20 %"] >= key.loc[("now", p)]["paid in 20 %"]
                 for p in df.period.unique())
        print(f"{name}: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
