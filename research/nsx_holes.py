"""How much do the missing minutes in the free HistData files move nsx_study.py's results?

    python research/nsx_holes.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv"

A hole is a stretch of missing 1-minute bars. If price crosses a stop inside one, the
backtest can't see it and fills at the first price after the hole, which can be far past
the stop. This re-scores every variant with the trades that were open across a hole
removed. Removing trades after the fact is an approximation: in a re-run, later trades
on the same day could size or fire differently.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nsx_study import IN_SAMPLE, OUT_OF_SAMPLE, VARIANTS, load_histdata  # noqa: E402

from mnqbot.config import BotConfig  # noqa: E402
from mnqbot.data import annotate, resample  # noqa: E402
from mnqbot.engine import backtest  # noqa: E402


def main() -> None:
    raw = load_histdata(sys.argv[1])
    bars = annotate(resample(raw, "5min"))

    # holes are found on the 1-minute data: a 5-minute bar can look normal while minutes inside it are missing
    t = raw.index
    gap = pd.Series(t[1:] - t[:-1], index=t[1:])
    hole_ends = gap[gap > pd.Timedelta("1min")].index  # first minute after each hole
    hhmm = t.hour * 100 + t.minute
    rth = t[(hhmm >= 930) & (hhmm < 1600)]
    rg = pd.Series(rth[1:] - rth[:-1], index=rth[1:])
    rth_holes = rg[(rg > pd.Timedelta("1min")) & (rg < pd.Timedelta("6h"))]
    print(f"holes inside 09:30-16:00: {len(rth_holes)} on {len(set(rth_holes.index.date))} days, "
          f"by year {rth_holes.groupby(rth_holes.index.year).size().to_dict()}")

    def spans_hole(tr) -> bool:
        return bool(((hole_ends > tr.entry_time) & (hole_ends < tr.exit_time + pd.Timedelta("5min"))).any())

    def trades(sub: pd.DataFrame, overrides: dict, free: bool = False) -> tuple[pd.DataFrame, pd.Series]:
        cfg = BotConfig()
        for k, v in overrides.items():
            setattr(cfg.strategy, k, v)
        if free:
            cfg.costs.commission_per_side = 0.0
            cfg.costs.slippage_ticks = 0
            cfg.costs.limit_fill_through_ticks = 0
        tf = backtest(sub, cfg).trades_frame()
        return tf, tf.apply(spans_hole, axis=1).astype(bool)

    print("\nAs run vs holes removed (realistic costs)")
    for name, over in VARIANTS.items():
        for part, (a, b) in (("tuning", IN_SAMPLE), ("unseen", OUT_OF_SAMPLE)):
            tf, hit = trades(bars[(bars.index >= a) & (bars.index < b)], over)
            clean = tf[~hit]
            day, clean_day = tf.groupby("trade_date").pnl.sum(), clean.groupby("trade_date").pnl.sum()
            print(f"{name:36s} {part:6s} hole trades {int(hit.sum()):2d} ({tf[hit].pnl.sum():+9,.0f})  "
                  f"avg R {tf.r.mean():+.3f} -> {clean.r.mean():+.3f}  "
                  f"net {tf.pnl.sum():+9,.0f} -> {clean.pnl.sum():+9,.0f}  "
                  f"worst trade {tf.r.min():+.2f}R -> {clean.r.min():+.2f}R  "
                  f"worst day {day.min():+,.0f} -> {clean_day.min():+,.0f}", flush=True)

    print("\nFull period, best case (no fees, no slippage, limits fill on a touch), holes removed")
    for name, over in VARIANTS.items():
        tf, hit = trades(bars, over, free=True)
        clean = tf[~hit]
        yr = clean.groupby(clean.trade_date.map(lambda d: d.year)).r.mean()
        print(f"{name:36s} avg R {tf.r.mean():+.3f} -> {clean.r.mean():+.3f}  by year "
              + " / ".join(f"{y}: {v:+.2f}" for y, v in yr.items()), flush=True)


if __name__ == "__main__":
    main()
