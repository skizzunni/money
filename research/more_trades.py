"""Round fourteen: more trades a day, with the bot as it trades now (resting stop, $350 cap, 5-minute bars).

    python research/more_trades.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Round five (noise_tuning.py) tested more frequent checks and narrower bands with the paper's exit, a check
at the half hour. Since then the exit became a resting stop 0.24 noise units past the line plus a max loss,
which changes what an extra entry costs. So, fixed before running:
  * Variants: entry checks every 30, 15, 10 or 5 minutes (first at 10:00, last at 16:00 minus the
    interval), times a noise-band multiplier of 1.0, 0.8 or 0.6. Twelve variants; 30 minutes x 1.0 is
    the bot as it is. Noise for each check time = the average |close / open - 1| at that time over the
    last 14 complete sessions, as now. Exits as now: the resting stop at the current line (it moves at
    each check) and the max loss, $350 on 3 MNQ = $116.67 per contract. Flat at 16:00.
  * 1 MNQ, prices rescaled to today's level month by month (timeframes.py), $1.24 fees + 1 tick each way.
  * Discovery 2011-2018: a variant is a candidate if it makes at least 25% more trades per day than the
    bot as it is, its daily-P&L t-stat is no more than 0.3 lower, and its $ per day is no lower. The
    candidate with the highest t goes on.
  * Confirmation 2019-2022, the same three tests against the bot as it is.
  * Final test 2023 - Sep 2026, run once: the same three tests, and a worst losing stretch no more than
    20% larger. Only a variant passing all three periods replaces the bot.
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

import timeframes as TF  # noqa: E402
from nsx_study import load_histdata  # noqa: E402

from mnqbot.data import NY  # noqa: E402

INTERVALS = (30, 15, 10, 5)
BANDS = (1.0, 0.8, 0.6)
CURRENT = (30, 1.0)
LOOKBACK, BUF, CAP_PER_CONTRACT = 14, 0.24, 350.0 / 3
TICK, PV, FEE = 0.25, 2.0, 1.24
OPEN, CLOSE, FIRST = 570, 960, 600
PERIODS = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))


def simulate(bars: pd.DataFrame, step: int, band: float) -> pd.DataFrame:
    """The bot on 5-minute bars with entry checks every `step` minutes and the band times `band`."""
    checks = list(range(FIRST, CLOSE - step + 1, step))
    n_k = len(checks)
    kof = {m: k for k, m in enumerate(checks)}
    idx = bars.index.tz_convert(NY)
    mins = (idx.hour * 60 + idx.minute).to_numpy()
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    slip, cap_pts = TICK, CAP_PER_CONTRACT / PV
    ring = np.full((LOOKBACK, n_k), np.nan)
    today = np.full(n_k, np.nan)
    filled = slot = 0
    day_open = prev_close = last_close = math.nan
    upper = lower = sigma = math.nan
    pos, entry_px, entry_bar, pending = 0, 0.0, 0, 0
    out = []

    def close(i, px, why):
        nonlocal pos
        out.append((idx[entry_bar], idx[i], pos, pos * (px - entry_px) * PV - FEE, why))
        pos = 0

    for i in range(len(bars)):
        t_min = mins[i]
        end = t_min + 5
        in_rth = t_min >= OPEN and end <= CLOSE
        if pending:
            if pos == 0:
                pos, entry_px, entry_bar = pending, o[i] + pending * slip, i
            pending = 0
        if pos and not math.isnan(upper):
            line = upper * (1 - BUF * sigma) if pos > 0 else lower * (1 + BUF * sigma)
            why = "line"
            if entry_bar != i:
                cap = entry_px - pos * cap_pts
                if (pos > 0 and cap > line) or (pos < 0 and cap < line):
                    line, why = cap, "cap"
            if entry_bar == i:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                px = (min(o[i], line) if pos > 0 else max(o[i], line)) - pos * slip
            elif (pos > 0 and o[i] <= line) or (pos < 0 and o[i] >= line):
                hit, px = True, o[i] - pos * slip
            else:
                hit = l[i] <= line if pos > 0 else h[i] >= line
                px = line - pos * slip
            if hit:
                close(i, px, why)
        if pos and (not in_rth or t_min == OPEN):
            close(i, c[i] - pos * slip, "session")
        if t_min == OPEN:
            prev_close, day_open = last_close, o[i]
            upper = lower = sigma = math.nan
            today[:] = np.nan
        if in_rth:
            last_close = c[i]
        if in_rth and not math.isnan(day_open) and end in kof:
            k = kof[end]
            today[k] = abs(c[i] / day_open - 1)
            if filled >= LOOKBACK and not math.isnan(prev_close):
                sigma = band * ring[:, k].mean()
                upper = max(day_open, prev_close) * (1 + sigma)
                lower = min(day_open, prev_close) * (1 - sigma)
                if pos == 0 and c[i] > upper:
                    pending = 1
                elif pos == 0 and c[i] < lower:
                    pending = -1
        if in_rth and end == CLOSE:
            if pos:
                close(i, c[i] - pos * slip, "16:00")
            if not math.isnan(day_open) and not np.isnan(today).any():
                ring[slot] = today
                slot = (slot + 1) % LOOKBACK
                filled += 1
            day_open = math.nan
    return pd.DataFrame(out, columns=["entry_time", "exit_time", "dir", "pnl", "why"])


def stats(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict:
    d = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum().reindex(sessions).fillna(0.0)
    eq = d.cumsum()
    months = d.groupby(d.index.to_period("M")).sum()
    return {"trades/day": len(tf) / len(sessions), "$/day": d.mean(),
            "t": d.mean() / d.std(ddof=1) * math.sqrt(len(d)), "worst stretch": (eq.cummax() - eq).max(),
            "worst day": d.min(), "win %": 100 * (tf.pnl > 0).mean(), "months up %": 100 * (months > 0).mean()}


def _job(args):
    path, step, band = args
    bars = _bars(path)
    return step, band, simulate(bars, step, band)


_CACHE: dict[str, pd.DataFrame] = {}


def _bars(path: str) -> pd.DataFrame:
    if path not in _CACHE:
        raw = load_histdata(path)
        raw = TF.scaled(raw[raw.index >= pd.Timestamp("2010-11-01", tz=raw.index.tz)])
        _CACHE[path] = raw.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    return _CACHE[path]


def clean(tf: pd.DataFrame, first_sessions: set) -> pd.DataFrame:
    entry_day = tf.entry_time.dt.tz_localize(None).dt.normalize()
    same_month = (tf.entry_time.dt.tz_localize(None).dt.to_period("M")
                  == tf.exit_time.dt.tz_localize(None).dt.to_period("M"))
    return tf[~entry_day.isin(first_sessions) & same_month & (entry_day >= "2011-01-01")]


def main() -> None:
    path = sys.argv[1]
    bars = _bars(path)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == OPEN].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=6) as ex:
        runs = {(s, b): clean(tf, first_sessions)
                for s, b, tf in ex.map(_job, [(path, s, b) for s in INTERVALS for b in BANDS])}
    table = {}
    for (s, b), tf in runs.items():
        for label, y0, y1 in PERIODS:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            year = tf.entry_time.dt.year
            table[(s, b, label)] = stats(tf[(year >= y0) & (year <= y1)], ss)
    df = pd.DataFrame(table).T
    df.index.names = ["check min", "band", "period"]
    print(df.round(2).to_string())

    def passes(v, label, final=False):
        a, base = table[(*v, label)], table[(*CURRENT, label)]
        ok = a["trades/day"] >= 1.25 * base["trades/day"] and a["t"] >= base["t"] - 0.3 and a["$/day"] >= base["$/day"]
        return ok and (not final or a["worst stretch"] <= 1.2 * base["worst stretch"])

    cands = [v for v in runs if v != CURRENT and passes(v, "2011-2018")]
    print(f"\nDiscovery 2011-2018 candidates: {cands or 'none'}")
    if not cands:
        return
    best = max(cands, key=lambda v: table[(*v, "2011-2018")]["t"])
    conf = passes(best, "2019-2022")
    print(f"Best: every {best[0]} min, band x{best[1]}. Confirmation 2019-2022: {'PASS' if conf else 'FAIL'}")
    if conf:
        fin = passes(best, "2023-2026", final=True)
        print(f"Final test 2023 - Sep 2026: {'PASS' if fin else 'FAIL'}")


if __name__ == "__main__":
    main()
