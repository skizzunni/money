"""The user's native MNQ 1-minute bars (NinjaTrader export) - loading, coverage, rollover (docs/MNQ_NATIVE.md).

NinjaTrader's export: "yyyyMMdd HHmmss;open;high;low;close;volume", time stamps in UTC, each the bar's END. Here each
bar gets its New York START time (end - 1 minute), as research/controlled.py's bars. The traded-contract series: MNQ
09-26 through the session of the roll date (9/10/2026, eight days before the 9/18 expiry), MNQ 12-26 from the 9/11
session; the earlier contract back-adjusted (additively, so point moves are unchanged) by the 12-26 minus 09-26
difference of the 16:00 close of 9/10, so the roll does not show as a price jump.
"""
from __future__ import annotations

import pandas as pd

NY = "America/New_York"
ROLL_DAY = pd.Timestamp("2026-09-10")


def load(path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", header=None, names=["t", "open", "high", "low", "close", "volume"])
    end = pd.to_datetime(df.t, format="%Y%m%d %H%M%S").dt.tz_localize("UTC")
    df.index = (end - pd.Timedelta(minutes=1)).dt.tz_convert(NY)
    return df.drop(columns="t")


def close_at(df, day, hhmm="15:59"):
    t = pd.Timestamp(f"{day.date()} {hhmm}", tz=NY)
    return float(df.loc[t, "close"])


def traded_series(sep, dec):
    """SEP26 to the roll date's session, DEC26 after; SEP26 back-adjusted by the roll-day 16:00 close difference."""
    diff = close_at(dec, ROLL_DAY) - close_at(sep, ROLL_DAY)
    cut = pd.Timestamp(f"{ROLL_DAY.date()} 18:00", tz=NY)  # the next session (9/11) starts at 18:00 on 9/10
    a = sep[sep.index < cut].copy()
    a[["open", "high", "low", "close"]] += diff
    b = dec[dec.index >= cut]
    return pd.concat([a, b]), diff


def coverage(bars, holidays=("2026-07-03",), early=("2026-09-07",)):
    """Per session (09:30-16:00 New York): minutes present of 390, and the first / last."""
    m = bars.index
    t = m.hour * 60 + m.minute
    rth = bars[(t >= 570) & (t < 960)]
    day = rth.index.normalize().tz_localize(None)
    per = rth.groupby(day).size()
    days = pd.bdate_range(per.index.min(), per.index.max())
    days = days[~days.isin(pd.to_datetime(list(holidays)))]
    rows = []
    for d in days:
        n = int(per.get(d, 0))
        note = "early close (holiday)" if str(d.date()) in early else ("no bars" if n == 0 else
                                                                        ("missing minutes" if n < 390 else ""))
        rows.append({"session": d.date(), "minutes": n, "note": note})
    return pd.DataFrame(rows)
