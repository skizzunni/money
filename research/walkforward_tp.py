"""Round twenty-six: the take-profit lead from round seventeen, judged walk-forward.

    python research/walkforward_tp.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

Round seventeen found that a take-profit about 2 noise units from the entry looked better in every period,
but it was found after all 16 years had been seen, so it had no untouched data left. Walk-forward is the
standard way to judge a parameter then: each year from 2015, pick the setting with the highest daily-P&L
t-stat over 2011 up to the year before, and trade that year with it. The choice never sees the year it trades.
Candidates: no take-profit (the bot), or a limit at 1.0, 1.5, 2.0, 2.5 or 3.0 noise units from the entry.
1 contract, $116.67 max loss, the bot otherwise as it trades, prices at today's level.
Pass, fixed before running: over 2015 - Sep 2026 the stitched walk-forward record beats the bot on $ per day
and on t-stat, with a worst losing stretch no larger.
"""
from __future__ import annotations

import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402

CANDIDATES = [None, 1.0, 1.5, 2.0, 2.5, 3.0]


def _job(args):
    path, tg = args
    # the limit works from the bar after the fill, as the Pine script places it (stricter than round seventeen)
    return tg, P.simulate(pd.read_pickle(path), target=tg, target_on_fill_bar=False)


def tstat(d: pd.Series) -> float:
    return d.mean() / d.std(ddof=1) * math.sqrt(len(d))


def stretch(d: pd.Series) -> float:
    eq = d.cumsum()
    return (eq.cummax() - eq).max()


def main() -> None:
    bars = MT._bars(sys.argv[1])
    cache = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("bars5_scaled.pkl")
    if not cache.exists():
        bars.to_pickle(cache)
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    with ProcessPoolExecutor(max_workers=4) as ex:
        runs = dict(ex.map(_job, [(str(cache), tg) for tg in CANDIDATES]))
    daily = {}
    for tg, tf in runs.items():
        tf = MT.clean(tf, first_sessions)
        daily[tg] = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum().reindex(sessions).fillna(0.0)
    picks, parts = [], []
    for year in range(2015, 2027):
        past = {tg: tstat(d[d.index.year < year]) for tg, d in daily.items()}
        pick = max(past, key=past.get)
        picks.append((year, "none" if pick is None else pick, round(past[pick], 2), round(past[None], 2)))
        parts.append(daily[pick][daily[pick].index.year == year])
    wf = pd.concat(parts)
    bot = daily[None][daily[None].index.year >= 2015]
    print("year, setting picked from the years before, its t on them, the bot's t on them:")
    for p in picks:
        print("  ", p)
    for name, d in (("bot", bot), ("walk-forward", wf)):
        yr = d.groupby(d.index.year).sum()
        print(f"{name:13s} 2015-2026  $/day {d.mean():.2f}  t {tstat(d):.2f}  worst stretch {stretch(d):.0f}  "
              f"years up {(yr > 0).sum()}/{len(yr)}  2023-26 $/day {d[d.index.year >= 2023].mean():.2f}")
    ok = wf.mean() > bot.mean() and tstat(wf) > tstat(bot) and stretch(wf) <= stretch(bot)
    print(f"WALK-FORWARD TEST: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
