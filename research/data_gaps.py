"""Missing data in the controlled comparison's bars, and the trades it touches (the audit's verification, item 7).

    python research/data_gaps.py <bars.pkl> <first> <last> [<sim.dll> ...]

Per dataset: weekday sessions with no 09:30-16:00 bars, sessions with missing minutes inside 09:30-16:00 (how many,
where), sessions whose last bar is before 15:59 (an early end: a half day or a hole), the overnight price jumps at the
month boundaries (the data is rescaled each month to today's price level), and, for each strategy build given, the
trades that are not closed on their entry session (they cross a gap: their exit fills at a later session's open).
Nothing is removed: the treatment is reported, not applied silently.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controlled as K  # noqa: E402


def scan(bars):
    m = bars.index.tz_convert(K.NY)
    t = (m.hour * 60 + m.minute).to_numpy()
    day = m.normalize()
    inside = (t >= 570) & (t < 960)
    per_day = pd.Series(inside, index=day).groupby(level=0).sum()
    last = pd.Series(np.where(inside, t, -1), index=day).groupby(level=0).max()
    weekdays = pd.bdate_range(per_day.index[0].tz_localize(None), per_day.index[-1].tz_localize(None))
    have = set(per_day.index.tz_localize(None).normalize())
    absent = [d.date() for d in weekdays if d not in have]
    short = per_day[per_day < 390]
    early = last[(last >= 0) & (last < 959)]
    # month-boundary jumps: the first open of a month against the last close before it
    first_open = bars.open.groupby(day).first()
    last_close = bars.close.groupby(day).last()
    gap = (first_open / last_close.shift(1) - 1).dropna()
    month_first = gap[gap.index.to_period("M") != pd.Index(gap.index).shift(-1, freq="D").to_period("M")]
    return {"sessions": len(per_day), "weekdays with no bars": len(absent), "absent (first 10)": absent[:10],
            "sessions missing minutes": len(short), "missing minutes": int((390 - short).sum()),
            "sessions ending before 15:59": len(early), "early ends (first 10)": [d.date() for d in early.index[:10]],
            "largest overnight jump %": float(100 * gap.abs().max()),
            "median month-boundary jump %": float(100 * month_first.abs().median()) if len(month_first) else 0.0}


def crossing(dll, bars):
    tmp = Path(tempfile.mkdtemp()) / "b.csv"
    K.write_bars(bars, tmp)
    tr = K.run(dll, tmp, UseBreakout=True, SimSlippageTicks=1, SimCommissionPerSide=0.95)
    day = bars.index.tz_convert(K.NY).normalize()
    x = tr[day[tr.eb.to_numpy()] != day[tr.xb.to_numpy()]]
    return x.assign(entry_day=[d.date() for d in day[x.eb.to_numpy()]],
                    exit_day=[d.date() for d in day[x.xb.to_numpy()]])


def main() -> None:
    data, first, last = sys.argv[1:4]
    bars = K.rth(pd.read_pickle(data))
    m = bars.index.tz_convert(K.NY)
    bars = bars[(m >= pd.Timestamp(first, tz=K.NY)) & (m < pd.Timestamp(last, tz=K.NY) + pd.Timedelta(days=1))]
    for k, v in scan(bars).items():
        print(f"{k}: {v}")
    for dll in sys.argv[4:]:
        x = crossing(dll, bars)
        print(f"\n{dll}: {len(x)} trades not closed on their entry session, net ${x.pnl.sum():,.2f}")
        if len(x):
            print(x[["entry_day", "exit_day", "name", "d", "q", "why", "pnl"]].to_string(index=False))


if __name__ == "__main__":
    main()
