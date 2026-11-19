# ruff: noqa: E402, E501, I001
"""G533 (docs/NINJATRADER_V38.md): Funded growth plus the trend pullback (research/patterns.py `trendpb`, mornings, 3R,
the one extra setup that held on held-out history) at 1 MNQ risking at most $187.50, on one 50K account.

Each 12-month start (the index 2011-18 quarterly: development; the index 2019-25 and NQ 2015-24 quarterly: unseen): Funded
growth runs from the start with its own $2,000 floor; the pullback's trades in the same window are added day by day; the
account is lost when a day ends at or below the floor (the highest end-of-day balance - $2,000, stopping at $50,000).
Funded growth alone is scored the same way. A screen: Funded growth does not see the pullback's P/L when it sizes.

    MNQ_DATA=<data dir> python research/g533_add_pullback_funded.py
"""
import os
import sys
import dataclasses
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE + '/v4_search', HERE, ROOT + '/tests', ROOT]
import numpy as np
import pandas as pd
import sets as S
import patterns as P
from win import grow, NY
from mnqbot.noise import run


def floor_test(daily: pd.Series) -> tuple[bool, float]:
    bal = high = 50000.0
    for p in daily:
        bal += p
        if bal <= min(high - 2000.0, 50000.0):
            return True, bal - 50000.0
        high = max(high, bal)
    return False, bal - 50000.0


def main() -> None:
    S.load()
    P.RISK = 187.5
    out = []
    for name, set_name, lo, hi in (("development", "IX", "2011-01-01", "2018-12-31"), ("unseen", "IX", "2019-01-01", "2025-12-31"),
                                   ("unseen", "NQ", "2015-04-01", "2024-09-30")):
        bars = S.SETS[set_name][0]
        pb = P.execute(P.prepare(bars, "trendpb"), True, True, True, 3.0, False)
        pb_daily = pb.groupby(pd.to_datetime(pb.exit_time).dt.tz_convert(NY).dt.date).pnl.sum()
        sess = pd.Index(sorted(set(bars.index.tz_convert(NY).date)))
        for q in pd.date_range(lo, hi, freq="QS"):
            later = sess[sess >= q.date()]
            if len(later) == 0:
                continue
            s0 = later[0]
            end = (pd.Timestamp(s0) + pd.DateOffset(months=12)).date()
            if sess[-1] < (pd.Timestamp(s0) + pd.DateOffset(months=11, days=25)).date():
                continue
            b = bars[(bars.index >= pd.Timestamp(s0, tz=NY) - pd.Timedelta(days=150)) & (bars.index < pd.Timestamp(end, tz=NY))]
            cfg = dataclasses.replace(grow(), trail_from=str(s0), gap_go_skip_month_first=True)
            tf = run(b, cfg, minutes=5).trades_frame()
            tf = tf[tf.entry_time >= pd.Timestamp(s0, tz=NY)]
            days = sess[(sess >= s0) & (sess < end)]
            fg = tf.groupby(tf.exit_time.dt.tz_convert(NY).dt.date).pnl.sum().reindex(days, fill_value=0.0)
            pbw = pb_daily.reindex(days, fill_value=0.0)
            l1, p1 = floor_test(fg)
            l2, p2 = floor_test(fg + pbw)
            out.append({"set": name, "start": s0, "fg_lost": l1, "fg_12m": p1, "both_lost": l2, "both_12m": p2,
                        "pb_trades": int((pb.exit_time.dt.tz_convert(NY).dt.date.isin(days)).sum()),
                        "pb_win": float((pb[pb.exit_time.dt.tz_convert(NY).dt.date.isin(days)].pnl > 0).mean())})
    d = pd.DataFrame(out)
    for name, g in d.groupby("set"):
        print(f"{name}: {len(g)} starts | Funded growth alone: lost {g.fg_lost.mean():.1%}, median ${g.fg_12m.median():,.0f}, "
              f"+$25K {np.mean(g.fg_12m >= 25000):.1%} | with the pullback: lost {g.both_lost.mean():.1%}, median "
              f"${g.both_12m.median():,.0f}, +$25K {np.mean(g.both_12m >= 25000):.1%} | pullback trades a start "
              f"{g.pb_trades.mean():.0f}, winners {g.pb_win.mean():.0%}")


if __name__ == "__main__":
    main()
