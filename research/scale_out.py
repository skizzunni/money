"""Round twenty-five: take half off at a profit, let the rest run. Can the win rate rise without the profit falling?

    python research/scale_out.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. A full take-profit (round seventeen) raised the share of winning trades
but cut the trend days the profit comes from. Scaling out keeps half the position on those days: half is
closed at a limit k noise units in profit; the other half runs to the line stop, the max loss or 16:00,
optionally with its stop moved to the entry once the first half is banked.
Variants, fixed before running: k in {0.5, 1.0} x the other half's stop in {breakeven, as before}.
2 contracts per trade (one per half), reported per contract; $116.67 max loss per contract from the fill;
the bot otherwise as it trades; $1.24 fees + 1 tick per contract per fill; prices at today's level.
A trade wins if the two halves together made money.
Pass bar against the bot: on 2011-2018 a win rate at least 10 points higher, $ per day at least 90% of the
bot's, a t-stat no more than 0.3 lower, a worst losing stretch no more than 10% larger. The passing variant
with the most $ per day goes on; the same on 2019-2022; then 2023 - Sep 2026, run once.
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

import more_trades as MT  # noqa: E402

from mnqbot.data import NY  # noqa: E402

LOOKBACK, BUF, CAP_PTS = 14, 0.24, (350.0 / 3) / 2.0
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
VARIANTS = {"bot": None, "half at +0.5, rest to breakeven": (0.5, True), "half at +0.5, rest as before": (0.5, False),
            "half at +1.0, rest to breakeven": (1.0, True), "half at +1.0, rest as before": (1.0, False)}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))


def simulate(bars: pd.DataFrame, k: float | None = None, breakeven: bool = False) -> pd.DataFrame:
    """Per trade: P&L per contract (the average of the two halves; the bot when k is None)."""
    checks = list(range(FIRST, LAST + 1, 30))
    kof = {m: j for j, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((LOOKBACK, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, entry, ebar, pending = 0, 0.0, 0, 0
    halves = 0  # contracts still open: 2, or 1 after the first half is banked
    banked = 0.0
    tp = math.nan
    out = []

    def close(i, px, why):
        nonlocal pos, banked
        rest = halves * (pos * (px - entry) * PV - FEE)
        out.append((idx[ebar], idx[i], pos, (banked + rest) / 2, why, halves == 1))
        pos, banked = 0, 0.0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, entry, ebar, halves, banked = pending, o[i] + pending * TICK, i, 2, 0.0
                tp = entry * (1 + pos * k * sigma) if k is not None else math.nan
            pending = 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            if ebar != i:
                cap = entry - pos * CAP_PTS
                stop = max(stop, cap) if pos > 0 else min(stop, cap)
                if breakeven and halves == 1:
                    stop = max(stop, entry) if pos > 0 else min(stop, entry)
            if ebar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if hit:
                close(i, px, "stop")
            elif halves == 2 and not math.isnan(tp) and (
                    (pos > 0 and h[i] >= tp + TICK) or (pos < 0 and l[i] <= tp - TICK)):
                banked = pos * (tp - entry) * PV - FEE  # the first half, at the limit
                halves = 1
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * TICK, "session")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending = 1
                elif pos == 0 and c[i] < lower:
                    pending = -1
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why", "half banked"])


def _job(args):
    path, name = args
    v = VARIANTS[name]
    return name, simulate(pd.read_pickle(path)) if v is None else simulate(pd.read_pickle(path), *v)


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = {n: MT.clean(tf, first_sessions) for n, tf in ex.map(_job, [(str(cache), n) for n in VARIANTS])}
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            t = tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)]
            s = MT.stats(t, ss)
            table[(name, label)] = s
            w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
            rows.append((name, label, s["win %"], w.mean(), lo.mean(), s["$/day"], s["t"], s["worst stretch"],
                         s["months up %"]))
    df = pd.DataFrame(rows, columns=["variant", "period", "win %", "avg win", "avg loss", "$/day", "t",
                                     "worst stretch", "months up %"])
    print(df.round(2).to_string(index=False))

    def passes(name, label):
        a, b = table[(name, label)], table[("bot", label)]
        return (a["win %"] >= b["win %"] + 10 and a["$/day"] >= 0.9 * b["$/day"] and a["t"] >= b["t"] - 0.3
                and a["worst stretch"] <= 1.1 * b["worst stretch"])

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    ok = passes(best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    ss = sessions[sessions.year >= 2023]
    for name in ("bot", best):
        t = runs[name][runs[name].entry_time.dt.year >= 2023]
        s = MT.stats(t, ss)
        table[(name, "2023-2026")] = s
        print(f"  2023-26 {name:34s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026') else 'FAIL'}")


if __name__ == "__main__":
    main()
