"""Round eighteen: which of the bot's own trades lose, and can they be told apart at entry?

    python research/meta_label.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Every earlier round looked for new places to trade. This one keeps the bot's signal and asks whether facts
known at the moment of its signal separate the trades that lose from the ones that win (a second-opinion
filter on a working signal, "meta-labeling"). Fixed before running:
  Facts at the signal (the half-hour check that triggers the entry), each a two-way split:
    1 gap aligned: the trade goes the way of the overnight gap (09:30 open vs previous close)
    2 yesterday aligned: the way of the previous session's close-to-close move
    3 month aligned: the way of the last 20 sessions' close-to-close move
    4 wild market: 20-session volatility of daily returns above its median over the previous 250 sessions
    5 early: the signal check is at or before 11:30
    6 overshoot: how far the signal close is past the line, in noise units; above / below the 2011-2018 median
    7 range so far: the day's high-low so far over the open, in noise units; above / below the 2011-2018 median
    8 first trade of the day
    9 stretch: the signal close's distance from the day's average close so far, in noise units; above / below
      the 2011-2018 median
   10 long (vs short)
  The bot as it trades (5-minute bars, $116.67 max loss per contract, 1 contract, prices at today's level).
  Discovery 2011-2018: Welch t-test of the mean P&L per trade, one side of the split vs the other;
  Benjamini-Hochberg 5% false discovery rate over the ten.
  Confirmation 2019-2022: same sign, one-sided p < 5%.
  The filter skips the losing side of every confirmed fact. Final test 2023 - Sep 2026, run once: the
  filtered bot passes if its win rate is higher, its $ per day per dollar of worst losing stretch is higher,
  and its $ per day is at least 90% of the bot's.

Stage two, written after stage one had shown 2011-2022 (and nothing of 2023-2026). No single fact passed,
but five pointed the same way in both 2011-2018 and 2019-2022 with |t| >= 0.3 in each: gap aligned, month
aligned, wild market, overshoot, range so far. Score = how many of the five are on their better side (0-5).
The cutoff (trade only when the score is at least c, c in 1..4) is picked on 2011-2022 as the one with the
highest $ per day per dollar of worst losing stretch among cutoffs that keep a higher win rate and at least
90% of the bot's $ per day. That one filter is run once on 2023 - Sep 2026 with the stage-one pass bar.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import more_trades as MT  # noqa: E402

from mnqbot.data import NY  # noqa: E402

LOOKBACK, BUF, CAP_PTS = 14, 0.24, (350.0 / 3) / 2.0
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST, LAST = 570, 960, 600, 930
FACTS = ["gap aligned", "yesterday aligned", "month aligned", "wild market", "early", "overshoot",
         "range so far", "first trade", "stretch", "long"]
MEDIAN_SPLIT = ["overshoot", "range so far", "stretch"]


def simulate(bars: pd.DataFrame) -> pd.DataFrame:
    """The bot, with the facts known at each signal recorded on its trade."""
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
    closes: list[float] = []  # RTH session closes, for yesterday / month / volatility
    vols: list[float] = []
    pos, entry, ebar, pending, sig_facts, ntrades = 0, 0.0, 0, 0, None, 0
    facts_now = None
    day_hi = day_lo = math.nan
    sum_c, n_c = 0.0, 0
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append({"entry_time": idx[ebar], "exit_time": idx[i], "dir": pos, "pnl": pos * (px - entry) * PV - FEE,
                    "why": why, **facts_now})
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, entry, ebar = pending, o[i] + pending * TICK, i
                facts_now = sig_facts
                ntrades += 1
            pending = 0
        if pos and not math.isnan(upper):
            stop = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            if ebar != i:
                cap = entry - pos * CAP_PTS
                stop = max(stop, cap) if pos > 0 else min(stop, cap)
            if ebar == i:
                hit = l[i] <= stop if pos > 0 else h[i] >= stop
                px = (min(o[i], stop) if pos > 0 else max(o[i], stop)) - pos * TICK
            elif (pos > 0 and o[i] <= stop) or (pos < 0 and o[i] >= stop):
                hit, px = True, o[i] - pos * TICK
            else:
                hit, px = (l[i] <= stop if pos > 0 else h[i] >= stop), stop - pos * TICK
            if hit:
                close(i, px, "stop")
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * TICK, "session")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
            ntrades = 0
            day_hi, day_lo, sum_c, n_c = h[i], l[i], 0.0, 0
        if in_rth:
            last_close = c[i]
            day_hi, day_lo = max(day_hi, h[i]), min(day_lo, l[i])
            sum_c += c[i]
            n_c += 1
        if in_rth and not math.isnan(day_open) and end in kof:
            j = kof[end]
            today[j] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close) and len(closes) >= 251:
                sigma = ring[:, j].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                d = 1 if c[i] > upper else -1 if c[i] < lower else 0
                if pos == 0 and d:
                    pending = d
                    rets = np.diff(np.log(closes[-21:]))
                    line = upper if d > 0 else lower
                    sig_facts = {
                        "gap aligned": d * (day_open - prev_close) > 0,
                        "yesterday aligned": d * (closes[-1] - closes[-2]) > 0,
                        "month aligned": d * (closes[-1] - closes[-21]) > 0,
                        "wild market": rets.std() > np.median(vols[-250:]),
                        "early": end <= 690,
                        "overshoot": d * (c[i] / line - 1) / sigma,
                        "range so far": (day_hi - day_lo) / day_open / sigma,
                        "first trade": ntrades == 0,
                        "stretch": d * (c[i] / (sum_c / n_c) - 1) / sigma,
                        "long": d > 0,
                    }
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * TICK, "16:00")
            closes.append(c[i])
            if len(closes) >= 21:
                vols.append(np.diff(np.log(closes[-21:])).std())
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out)


def welch(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def main() -> None:
    bars = MT._bars(sys.argv[1])
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    tf = MT.clean(simulate(bars), first_sessions)
    year = tf.entry_time.dt.year
    disc, conf, final = tf[year <= 2018], tf[(year >= 2019) & (year <= 2022)], tf[year >= 2023]
    medians = {f: disc[f].median() for f in MEDIAN_SPLIT}
    for f in MEDIAN_SPLIT:
        tf[f] = tf[f] > medians[f]
    disc, conf, final = tf[year <= 2018], tf[(year >= 2019) & (year <= 2022)], tf[year >= 2023]
    rows = []
    for f in FACTS:
        r = [f]
        for part in (disc, conf, final):
            yes, no = part[part[f].astype(bool)].pnl.to_numpy(), part[~part[f].astype(bool)].pnl.to_numpy()
            r += [yes.mean(), no.mean(), welch(yes, no)]
        rows.append(r)
    df = pd.DataFrame(rows, columns=["fact", "yes $ 11-18", "no $ 11-18", "t 11-18", "yes $ 19-22", "no $ 19-22",
                                     "t 19-22", "yes $ 23-26", "no $ 23-26", "t 23-26"])
    df["p 11-18"] = D.two_sided_p(df["t 11-18"].to_numpy())
    df["luck filter"] = D.bh(df["p 11-18"], 0.05)
    df["confirmed"] = df["luck filter"] & (np.sign(df["t 11-18"]) == np.sign(df["t 19-22"])) & (
        df["t 19-22"].abs() >= 1.645)
    print(f"medians frozen on 2011-2018: {({k: round(v, 3) for k, v in medians.items()})}")
    print(f"trades: 2011-18 {len(disc)}, 2019-22 {len(conf)}, 2023-26 {len(final)}")
    print(df.drop(columns=["yes $ 23-26", "no $ 23-26", "t 23-26"]).round(2).to_string(index=False))
    confirmed = df[df.confirmed]
    if confirmed.empty:
        print("\nNo fact passed the luck filter and confirmation: no filter goes to the final test.")
        stage_two(tf, sessions)
        return
    keep = pd.Series(True, index=tf.index)
    for _, r in confirmed.iterrows():
        good = r["t 11-18"] > 0  # the 'yes' side is the better one
        keep &= tf[r.fact].astype(bool) == good
    print(f"\nFilter: skip the losing side of {list(confirmed.fact)}")
    print(df[df.confirmed][["fact", "yes $ 23-26", "no $ 23-26", "t 23-26"]].round(2).to_string(index=False))
    ss = sessions[sessions.year >= 2023]
    a, b = MT.stats(tf[keep & (year >= 2023)], ss), MT.stats(final, ss)
    for name, s in (("bot", b), ("filtered", a)):
        print(f"  2023-26 {name:9s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}  trades/day {s['trades/day']:.2f}")
    ok = (a["win %"] > b["win %"] and a["$/day"] / a["worst stretch"] > b["$/day"] / b["worst stretch"]
          and a["$/day"] >= 0.9 * b["$/day"])
    print(f"FINAL TEST: {'PASS' if ok else 'FAIL'}")


SCORE_FACTS = ["gap aligned", "month aligned", "wild market", "overshoot", "range so far"]


def passes(a: dict, b: dict) -> bool:
    return (a["win %"] > b["win %"] and a["$/day"] / a["worst stretch"] > b["$/day"] / b["worst stretch"]
            and a["$/day"] >= 0.9 * b["$/day"])


def stage_two(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> None:
    score = sum(tf[f].astype(int) for f in SCORE_FACTS)
    year = tf.entry_time.dt.year
    fit, test = year <= 2022, year >= 2023
    ss_fit, ss_test = sessions[sessions.year <= 2022], sessions[sessions.year >= 2023]
    base = MT.stats(tf[fit], ss_fit)
    print(f"\nStage two, 2011-2022: bot win {base['win %']:.1f}%  $/day {base['$/day']:.2f}  "
          f"worst stretch {base['worst stretch']:.0f}")
    best, best_eff = None, -math.inf
    for cut in (1, 2, 3, 4):
        s = MT.stats(tf[fit & (score >= cut)], ss_fit)
        eff = s["$/day"] / s["worst stretch"]
        ok = passes(s, base)
        print(f"  score >= {cut}: win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}  trades/day {s['trades/day']:.2f}  {'ok' if ok else '-'}")
        if ok and eff > best_eff:
            best, best_eff = cut, eff
    if best is None:
        print("  No cutoff qualifies on 2011-2022: nothing goes to the final test.")
        return
    a, b = MT.stats(tf[test & (score >= best)], ss_test), MT.stats(tf[test], ss_test)
    print(f"  Picked score >= {best}. Final test 2023 - Sep 2026, run once:")
    for name, s in (("bot", b), ("filtered", a)):
        print(f"    {name:9s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}  trades/day {s['trades/day']:.2f}")
    print(f"  FINAL TEST: {'PASS' if passes(a, b) else 'FAIL'}")


if __name__ == "__main__":
    main()
