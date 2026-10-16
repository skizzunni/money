"""Round nineteen: three ways at the losing trades themselves.

    python research/losers.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running.
  A. Time stop. Breakouts that work tend to work quickly; a trade still under water after N minutes is
     more likely one of the failures, and waiting for the line stop lets it lose the most it can. At the
     bar close N minutes after the fill, if the trade is losing, close it there (like the 16:00 close).
     Variants: N = 15, 30, 60.
  B. Two-check confirmation. Enter only when this check and the one before it both closed outside the
     same line (so no entries at 10:00). Fewer one-check fake breakouts, at the price of a later entry.
  C. Flip the failed breakout. When the bot's trade is stopped out (line or max loss) within M minutes of
     the fill, the traders who bought the breakout are trapped and their exits push price the other way.
     Trade the other direction at the next open: stop at the failed trade's extreme (or $116.67 from the
     fill if closer), target the middle of the noise area or the far line (limit, fixed at the fill), out at
     16:00, and closed at a check where the bot signals a new trade. Variants: M in {30, 60} x target in
     {mid, far line}.
The bot otherwise as it trades: 5-minute bars, half-hour checks, line stop 0.24 noise units past the line,
$116.67 max loss, flat at 16:00, 1 contract, $1.24 fees + 1 tick per fill, prices at today's level.
Pass bar, fixed before running, against the bot:
  Discovery 2011-2018: $ per day no lower; t-stat no more than 0.3 lower; $ per day per dollar of worst
  losing stretch higher. C's flip trades must also stand alone at t >= 2.73 (5% two-sided over eight).
  The passing variant with the most $ per day per dollar of worst stretch goes on.
  Confirmation 2019-2022: the same tests (C's flip trades at t >= 1.65).
  Final test 2023 - Sep 2026, run once, the same as confirmation.
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
VARIANTS = {"bot": {}, "time stop 15": {"time_stop": 15}, "time stop 30": {"time_stop": 30},
            "time stop 60": {"time_stop": 60}, "two checks": {"confirm": True},
            "flip 30 mid": {"flip": 30, "flip_target": "mid"}, "flip 30 far": {"flip": 30, "flip_target": "far"},
            "flip 60 mid": {"flip": 60, "flip_target": "mid"}, "flip 60 far": {"flip": 60, "flip_target": "far"}}
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def simulate(bars: pd.DataFrame, time_stop: int | None = None, confirm: bool = False, flip: int | None = None,
             flip_target: str = "mid") -> pd.DataFrame:
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
    pos, entry, ebar, pending, ext = 0, 0.0, 0, 0, math.nan
    prev_side = 0
    fpos, fentry, fbar, fstop, ftarget, fpending = 0, 0.0, 0, math.nan, math.nan, None
    out = []

    def close(i, px, why):
        nonlocal pos, fpending
        dur = (i - ebar + 1) * 5
        if flip is not None and why in ("line", "cap") and dur <= flip and fpos == 0:
            fpending = (-pos, ext)
        out.append(("bot", idx[ebar], idx[i], pos, pos * (px - entry) * PV - FEE, why))
        pos = 0

    def fclose(i, px, why):
        nonlocal fpos
        out.append(("flip", idx[fbar], idx[i], fpos, fpos * (px - fentry) * PV - FEE, why))
        fpos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0 and fpos == 0:
                pos, entry, ebar, ext = pending, o[i] + pending * TICK, i, math.nan
            pending = 0
        if fpending is not None:
            d, extreme = fpending
            fpending = None
            if pos == 0 and fpos == 0 and in_rth and t_min < LAST and not math.isnan(upper):
                fpos, fentry, fbar = d, o[i] + d * TICK, i
                fstop = extreme
                mid = (upper + lower) / 2
                ftarget = mid if flip_target == "mid" else (lower if d < 0 else upper)
                if (d < 0 and ftarget >= fentry) or (d > 0 and ftarget <= fentry):
                    ftarget = math.nan  # already past the target: no limit, stop or 16:00 only
        if pos:
            ext = (h[i] if math.isnan(ext) else max(ext, h[i])) if pos > 0 else \
                (l[i] if math.isnan(ext) else min(ext, l[i]))
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            why = "line"
            if ebar != i:
                cap = entry - pos * CAP_PTS
                if (pos > 0 and cap > stop) or (pos < 0 and cap < stop):
                    stop, why = cap, "cap"
            if ebar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if hit:
                close(i, px, why)
        if fpos:
            stop = fstop
            if fbar != i:
                cap = fentry - fpos * CAP_PTS
                stop = max(stop, cap) if fpos > 0 else min(stop, cap)
            done = False
            if fbar != i and ((fpos > 0 and o[i] <= stop) or (fpos < 0 and o[i] >= stop)):
                fclose(i, o[i] - fpos * TICK, "stop")
                done = True
            elif (fpos > 0 and l[i] <= stop) or (fpos < 0 and h[i] >= stop):
                px = stop if fbar != i else (min(o[i], stop) if fpos > 0 else max(o[i], stop))
                fclose(i, px - fpos * TICK, "stop")
                done = True
            if not done and not math.isnan(ftarget) and (
                    (fpos > 0 and h[i] >= ftarget + TICK) or (fpos < 0 and l[i] <= ftarget - TICK)):
                fclose(i, ftarget, "target")
        if (pos or fpos) and (not in_rth or t_min == OPEN):
            if pos:
                close(i, c[i] - pos * TICK, "session")
            if fpos:
                fclose(i, c[i] - fpos * TICK, "session")
            fpending = None
        if pos and time_stop is not None and (i - ebar + 1) * 5 == time_stop and pos * (c[i] - entry) < 0:
            close(i, c[i] - pos * TICK, "time")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
            prev_side = 0
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                side = 1 if c[i] > upper else -1 if c[i] < lower else 0
                ok = side != 0 and (not confirm or side == prev_side)
                prev_side = side
                if pos == 0 and ok:
                    pending = side
                    if fpos:  # the bot signals: the flip trade gives way
                        fclose(i, c[i] - fpos * TICK, "bot signal")
                    fpending = None
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            if fpos:
                fclose(i, c[i] - fpos * TICK, "16:00")
            fpending = None
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["stream", "entry_time", "exit_time", "dir", "pnl", "why"])


def _job(args):
    path, name = args
    return name, simulate(pd.read_pickle(path), **VARIANTS[name])


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
            if label == "2023-2026":
                continue  # the final test is read once, below
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            yr = tf.entry_time.dt.year
            t = tf[(yr >= y0) & (yr <= y1)]
            s = MT.stats(t, ss)
            s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
            fl = t[t.stream == "flip"]
            s["flip t"] = MT.stats(fl, ss)["t"] if len(fl) > 1 else float("nan")
            table[(name, label)] = s
            w, lo = t.pnl[t.pnl > 0], t.pnl[t.pnl <= 0]
            rows.append((name, label, s["win %"], w.mean(), lo.mean(), s["$/day"], s["t"], s["worst stretch"],
                         s["eff"], s["flip t"]))
    df = pd.DataFrame(rows, columns=["variant", "period", "win %", "avg win", "avg loss", "$/day", "t",
                                     "worst stretch", "$/day per $1k stretch", "flip t"])
    print(df.round(2).to_string(index=False))

    def passes(name, label, flip_t):
        a, b = table[(name, label)], table[("bot", label)]
        ok = a["$/day"] >= b["$/day"] and a["t"] >= b["t"] - 0.3 and a["eff"] > b["eff"]
        return ok and (not name.startswith("flip") or a["flip t"] >= flip_t)

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018", 2.73)]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["eff"])
    ok = passes(best, "2019-2022", 1.65)
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    ss = sessions[sessions.year >= 2023]
    for name in ("bot", best):
        t = runs[name][runs[name].entry_time.dt.year >= 2023]
        s = MT.stats(t, ss)
        s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
        fl = t[t.stream == "flip"]
        s["flip t"] = MT.stats(fl, ss)["t"] if len(fl) > 1 else float("nan")
        table[(name, "2023-2026")] = s
        print(f"  2023-26 {name:14s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}")
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026', 1.65) else 'FAIL'}")


if __name__ == "__main__":
    main()
