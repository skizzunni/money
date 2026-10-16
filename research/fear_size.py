"""Round thirty-one: trade more when the market is scared. Picked after seeing 2011-2022, tested once on 2023-2026.

    python research/fear_size.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" yahoo_dir   (files as in fear_volume.py)

Three separate rounds point the same way: cutting size on wild days hurt (round eight), trades on days wilder
than normal made more in both periods (round eighteen), and trades on days with VIX above its 1-year median made
more in both periods (round thirty: $27.77 vs $8.62 a trade on 2011-2018, $25.90 vs $19.19 on 2019-2022). The
calm days still make money, so skipping them costs profit; trading more on the scared days is the rule that
follows. It was chosen after seeing 2011-2022; 2023-2026 was not looked at for it.
Rule: 2 units on sessions whose previous VIX close is above the median of the 250 closes before it, 1 unit
otherwise (and on sessions with no VIX history). The bot as it trades now, per unit: 1 contract, $116.67 max
loss live from the fill, 1.5-noise-unit take-profit, prices at today's level.
Pass, fixed before the 2023-2026 run: against flat sizing, a higher daily-P&L t-stat and more $ per day per dollar
of worst losing stretch (both ratios are the same for flat sizing at any number of contracts, so this is a fair
comparison of risk, not of size).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fear_volume as F  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402


def summary(d: pd.Series) -> dict:
    eq = d.cumsum()
    stretch = (eq.cummax() - eq).max()
    return {"$/day": d.mean(), "t": d.mean() / d.std(ddof=1) * math.sqrt(len(d)), "worst stretch": stretch,
            "eff": 1000 * d.mean() / stretch, "worst day": d.min()}


def main() -> None:
    bars = MT._bars(sys.argv[1])
    d = Path(sys.argv[2])
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    tf = MT.clean(P.simulate(bars, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True), first_sessions)
    vix = F.closes(d / "VIX_1d.json")
    units = pd.Series(1.0, index=sessions)
    for day in sessions:
        v = vix[vix.index < day]
        if len(v) >= 251 and v.iloc[-1] > v.iloc[-251:-1].median():
            units[day] = 2.0
    day_pnl = tf.groupby(tf.exit_time.dt.tz_localize(None).dt.normalize()).pnl.sum().reindex(sessions).fillna(0.0)
    flat, fear = day_pnl, day_pnl * units
    for label, y0, y1 in (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026)):
        m = (sessions.year >= y0) & (sessions.year <= y1)
        a, b = summary(fear[m]), summary(flat[m])
        print(f"{label}  share of days at 2 units {units[m].eq(2).mean():.0%}")
        for name, s in (("flat 1 unit", b), ("2 units when scared", a)):
            print(f"  {name:20s} $/day {s['$/day']:6.2f}  t {s['t']:.2f}  worst stretch {s['worst stretch']:6.0f}  "
                  f"$/day per $1k stretch {s['eff']:.2f}  worst day {s['worst day']:.0f}")
        if label == "2023-2026":
            ok = a["t"] > b["t"] and a["eff"] > b["eff"]
            print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
