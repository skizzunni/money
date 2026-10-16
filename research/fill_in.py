"""Round fifteen: a trade every day. The bot trades on 57% of days; can the other 43% carry an edge too?

    python research/fill_in.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Reasoning, written before running. Noise-area momentum works because a move past the noise area, the
range price usually wanders in by that time of day, tends to keep going. The days it can't trade are the
days price stays inside that range. If escaping the range means trend, staying inside it may mean
two-way trade: a move toward the edge of the range that doesn't break out tends to come back toward the
middle. Rounds six and seven tested position-in-range linearly against the next 30-60 minutes and found
nothing; this tests the bounded trade itself, which has a different payoff: a loss limited by the noise
line, where the momentum bot takes over in the other direction. The two strategies hand off at the same
price. Second, the first half hour (09:30-10:00) is never traded by the bot; an overnight gap that is
large for the time of day may partly fill before 10:00.

Fixed before running. All on 5-minute bars, prices at today's level (timeframes.py), 1 MNQ, $1.24 fees +
1 tick on every market or stop fill, limit targets fill at the target when price trades 1 tick through.
The momentum bot is unchanged (resting stop 0.24 noise units past the line, $116.67 max loss, flat 16:00).
  A. Fade inside the noise area. At a half-hour check from 10:00 to 15:00, with the momentum bot flat and
     no fade open, and the close inside the lines: with U, L the lines, M = (U + L) / 2 and H = U - M,
     sell at the next open if the close >= U - z*H, buy if <= L + z*H. Stop: the current line (U for a
     short, L for a long), moving with it at each check, or $116.67 from the fill if closer (from the bar
     after the fill). Target: a limit at the current M ("mid"), or halfway from the entry to M ("half"),
     fixed at the fill. Flat at 16:00. One fade at a time; at most two fades a day.
     Variants: z in {0.5, 0.25} x target in {mid, half}.
  B. Gap fade, 09:30-10:00. g = 09:30 open / previous close - 1; s = the 10:00 noise (sigma) from the last
     14 sessions. If |g| > k*s, sell (gap up) or buy (gap down) at the 09:30 open; target the previous
     close (limit); max loss $116.67; out at the 10:00 close if neither filled. Variants: k in {0.5, 1.0}.
  Six candidates. Each is judged on its own stream and on the bot + it.
  Discovery 2011-2018: own stream t >= 2.64 (5% two-sided, Bonferroni over six); and bot + candidate vs the
  bot alone: more days with a trade, $ per day no lower, t no more than 0.3 lower, worst losing stretch no
  more than 20% larger. The passing candidate with the highest combined t goes on.
  Confirmation 2019-2022: own stream t >= 1.65 (one-sided 5%) and the same four tests.
  Final test 2023 - Sep 2026, run once: the same as confirmation. Only a pass changes the bot.
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
LAST_FADE = 900
CANDIDATES = [("fade", 0.5, "mid"), ("fade", 0.5, "half"), ("fade", 0.25, "mid"), ("fade", 0.25, "half"),
              ("gap", 0.5, None), ("gap", 1.0, None)]
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def simulate(bars: pd.DataFrame, kind: str | None, p: float, target: str | None) -> pd.DataFrame:
    """The bot (kind None), or the bot plus one candidate. Returns every trade, tagged by stream."""
    checks = list(range(FIRST, LAST + 1, 30))
    kof = {m: k for k, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ring = np.full((LOOKBACK, len(checks)), np.nan)
    today = np.full(len(checks), np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    out = []
    # momentum position
    pos, entry, ebar, pending = 0, 0.0, 0, 0
    # side position (fade or gap): direction, entry, entry bar, target, pending direction, fades today
    spos, sentry, sbar, starget, spending, fades = 0, 0.0, 0, math.nan, 0, 0

    def close_m(i, px, why):
        nonlocal pos
        out.append(("bot", idx[ebar], idx[i], pos, pos * (px - entry) * PV - FEE, why))
        pos = 0

    def close_s(i, px, why):
        nonlocal spos
        out.append((kind, idx[sbar], idx[i], spos, spos * (px - sentry) * PV - FEE, why))
        spos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
            fades = 0
            if kind == "gap" and filled >= LOOKBACK and not math.isnan(prev_close) and pos == 0:
                s10 = ring[:, 0].mean()
                g = o[i] / prev_close - 1
                if abs(g) > p * s10:
                    spos = -1 if g > 0 else 1
                    sentry, sbar, starget = o[i] + spos * TICK, i, prev_close
        if pending:
            if pos == 0 and spos == 0:
                pos, entry, ebar = pending, o[i] + pending * TICK, i
            pending = 0
        if spending:
            if pos == 0 and spos == 0:
                spos, sentry, sbar = spending, o[i] + spending * TICK, i
                mid = (upper + lower) / 2
                starget = mid if target == "mid" else sentry + (mid - sentry) / 2
                fades += 1
            spending = 0
        # momentum resting stop
        if pos and not math.isnan(upper):
            line = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            if ebar != i:
                cap = entry - pos * CAP_PTS
                line = max(line, cap) if pos > 0 else min(line, cap)
            if ebar == i:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                px = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * TICK
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= line if pos > 0 else h[i] >= line), line - pos * TICK
            if hit:
                close_m(i, px, "stop")
        # side position: stop first (worst case), then target
        if spos:
            if kind == "fade":
                stop = upper if spos < 0 else lower
            else:
                stop = math.nan
            if sbar != i:
                cap = sentry - spos * CAP_PTS
                stop = cap if math.isnan(stop) else (max(stop, cap) if spos > 0 else min(stop, cap))
            done = False
            if not math.isnan(stop):
                if sbar != i and ((spos > 0 and o[i] <= stop) or (spos < 0 and o[i] >= stop)):
                    close_s(i, o[i] - spos * TICK, "stop")
                    done = True
                elif (spos > 0 and l[i] <= stop) or (spos < 0 and h[i] >= stop):
                    px = stop if sbar != i else (min(o[i], stop) if spos > 0 else max(o[i], stop))
                    close_s(i, px - spos * TICK, "stop")
                    done = True
            if not done and ((spos > 0 and h[i] >= starget + TICK) or (spos < 0 and l[i] <= starget - TICK)):
                close_s(i, starget, "target")
                done = True
            if not done and kind == "gap" and end == FIRST:
                close_s(i, c[i] - spos * TICK, "10:00")
        if (pos or spos) and (not in_rth):
            if pos:
                close_m(i, c[i] - pos * TICK, "session")
            if spos:
                close_s(i, c[i] - spos * TICK, "session")
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            k = kof[end]
            today[k] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = ring[:, k].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending = 1
                elif pos == 0 and c[i] < lower:
                    pending = -1
                elif (kind == "fade" and pos == 0 and spos == 0 and end <= LAST_FADE and fades < 2
                      and lower <= c[i] <= upper):
                    half = upper - (upper + lower) / 2
                    if c[i] >= upper - p * half:
                        spending = -1
                    elif c[i] <= lower + p * half:
                        spending = 1
                if pending and spos:  # a breakout while a side trade is open: it gives way at the next open
                    spending = 0
        if pending and spos:
            close_s(i, c[i] - spos * TICK, "breakout")
        if in_rth and end == CLOSE:
            if pos:
                close_m(i, c[i] - pos * TICK, "16:00")
            if spos:
                close_s(i, c[i] - spos * TICK, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["stream", "entry_time", "exit_time", "dir", "pnl", "why"])


def stats(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict:
    s = MT.stats(tf, sessions) if len(tf) else {"$/day": 0.0, "t": 0.0, "worst stretch": 0.0}
    days = tf.entry_time.dt.tz_localize(None).dt.normalize()
    s["days traded %"] = 100 * sessions.isin(days).mean()
    return s


def _job(args):
    bars_path, cand = args
    bars = pd.read_pickle(bars_path)
    kind, p, target = cand if cand else (None, 0.0, None)
    return cand, simulate(bars, kind, p, target)


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
        runs = dict(ex.map(_job, [(str(cache), cand) for cand in [None, *CANDIDATES]]))
    runs = {k: MT.clean(v, first_sessions) for k, v in runs.items()}
    rows, table = [], {}
    for cand, tf in runs.items():
        name = "bot alone" if cand is None else f"bot + {cand[0]} {cand[1]} {cand[2] or ''}".strip()
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            yr = tf.entry_time.dt.year
            t = tf[(yr >= y0) & (yr <= y1)]
            comb = stats(t, ss)
            own = stats(t[t.stream != "bot"], ss) if cand else {"t": float("nan"), "$/day": float("nan")}
            table[(cand, label)] = (comb, own)
            rows.append((name, label, comb["days traded %"], comb["trades/day"], comb["$/day"], comb["t"],
                         comb["worst stretch"], comb["months up %"], own["$/day"], own["t"]))
    df = pd.DataFrame(rows, columns=["variant", "period", "days traded %", "trades/day", "$/day", "t",
                                     "worst stretch", "months up %", "side $/day", "side t"])
    print(df.round(2).to_string(index=False))

    def passes(cand, label, own_t):
        comb, own = table[(cand, label)]
        base = table[(None, label)][0]
        return (own["t"] >= own_t and comb["days traded %"] > base["days traded %"] and comb["$/day"] >= base["$/day"]
                and comb["t"] >= base["t"] - 0.3 and comb["worst stretch"] <= 1.2 * base["worst stretch"])

    cands = [c for c in CANDIDATES if passes(c, "2011-2018", 2.64)]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda c: table[(c, "2011-2018")][0]["t"])
    ok = passes(best, "2019-2022", 1.65)
    print(f"Best {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if ok:
        print(f"Final test 2023 - Sep 2026: {'PASS' if passes(best, '2023-2026', 1.65) else 'FAIL'}")


if __name__ == "__main__":
    main()
