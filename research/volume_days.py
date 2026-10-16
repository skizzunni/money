"""Round twenty-nine: does the bot do better on busier days? Daily NQ futures volume from Yahoo Finance.

    curl -A "Mozilla/5.0" -o nq_1d.json \
      "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=1d&period1=946684800&period2=1792125136"
    python research/volume_days.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" nq_1d.json

Reasoning, written before running. Momentum works because many participants push a move past the usual range;
on days when more of them are trading, breakouts may carry further. Yahoo's NQ=F daily bars carry the front
contract's volume (one number per CME session). Facts known before the 09:30 open of session D, each a
two-way split:
  1 heavy yesterday: volume of D-1 above the average of D-21 .. D-2
  2 active week:     average volume of D-5 .. D-1 above the average of D-60 .. D-1
  3 volume rising:   average volume of D-5 .. D-1 above the average of D-20 .. D-1
Quarterly contract rolls move volume from one contract to the next, so sessions from 10 calendar days before
to 3 after the third Friday of March, June, September and December have no facts and are left out of the tests.
The bot as it trades now (5-minute bars, 1.5-noise-unit take-profit, $116.67 max loss live from the fill),
1 contract, prices at today's level.
  Discovery 2011-2018: Welch t-test of $ per trade, one side of the split against the other; Benjamini-Hochberg
  5% false discovery rate over the three. Confirmation 2019-2022: same sign, one-sided p < 5%.
  The filter skips the losing side of every confirmed fact (roll sessions trade as usual). Final test 2023 - Sep
  2026, run once: a higher win rate, more $ per day per dollar of worst losing stretch, and at least 90% of the
  bot's $ per day.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402

from mnqbot.data import NY  # noqa: E402

FACTS = ["heavy yesterday", "active week", "volume rising"]


def daily_volume(path: str) -> pd.Series:
    r = json.loads(Path(path).read_text())["chart"]["result"][0]
    days = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(NY).tz_localize(None).normalize()
    vol = pd.Series(r["indicators"]["quote"][0]["volume"], index=days, dtype=float)
    vol = vol[~vol.index.duplicated(keep="last")].dropna()
    return vol[vol > 0]


def roll_window(day: pd.Timestamp) -> bool:
    for m in (3, 6, 9, 12):
        first = pd.Timestamp(day.year, m, 1)
        third_friday = first + pd.Timedelta(days=(4 - first.dayofweek) % 7 + 14)
        if -10 <= (day - third_friday).days <= 3:
            return True
    return False


def facts_for(vol: pd.Series, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    rows = {}
    for d in sessions:
        past = vol[vol.index < d]
        if len(past) < 60 or roll_window(d):
            continue
        v = past.to_numpy()
        rows[d] = {"heavy yesterday": v[-1] > v[-21:-1].mean(),
                   "active week": v[-5:].mean() > v[-60:].mean(),
                   "volume rising": v[-5:].mean() > v[-20:].mean()}
    return pd.DataFrame.from_dict(rows, orient="index")


def welch(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def main() -> None:
    bars = MT._bars(sys.argv[1])
    vol = daily_volume(sys.argv[2])
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    tf = MT.clean(P.simulate(bars, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True), first_sessions)
    facts = facts_for(vol, sessions)
    tf["day"] = tf.entry_time.dt.tz_localize(None).dt.normalize()
    tf = tf.join(facts, on="day")
    year = tf.entry_time.dt.year
    tested = tf.dropna(subset=FACTS)
    ty = tested.entry_time.dt.year
    parts = {"2011-18": tested[ty <= 2018], "2019-22": tested[(ty >= 2019) & (ty <= 2022)]}
    rows = []
    for f in FACTS:
        r = [f]
        for part in parts.values():
            yes, no = part[part[f].astype(bool)].pnl.to_numpy(), part[~part[f].astype(bool)].pnl.to_numpy()
            r += [len(yes), yes.mean(), no.mean(), welch(yes, no)]
        rows.append(r)
    df = pd.DataFrame(rows, columns=["fact", "n yes 11-18", "yes $ 11-18", "no $ 11-18", "t 11-18",
                                     "n yes 19-22", "yes $ 19-22", "no $ 19-22", "t 19-22"])
    df["p 11-18"] = D.two_sided_p(df["t 11-18"].to_numpy())
    df["luck filter"] = D.bh(df["p 11-18"], 0.05)
    df["confirmed"] = df["luck filter"] & (np.sign(df["t 11-18"]) == np.sign(df["t 19-22"])) & (
        df["t 19-22"].abs() >= 1.645)
    print(f"trades with volume facts: 2011-18 {len(parts['2011-18'])}, 2019-22 {len(parts['2019-22'])} "
          f"(roll sessions left out: {tf[FACTS[0]].isna().sum()} trades)")
    print(df.round(2).to_string(index=False))
    confirmed = df[df.confirmed]
    if confirmed.empty:
        print("\nNo fact passed the luck filter and confirmation: nothing goes to the final test.")
        return
    keep = pd.Series(True, index=tf.index)
    for _, r in confirmed.iterrows():
        good = r["t 11-18"] > 0
        has = tf[r.fact].notna()
        keep &= ~has | (tf[r.fact] == good)
    ss = sessions[sessions.year >= 2023]
    a, b = MT.stats(tf[keep & (year >= 2023)], ss), MT.stats(tf[year >= 2023], ss)
    for name, s in (("bot", b), ("filtered", a)):
        print(f"  2023-26 {name:9s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}")
    ok = (a["win %"] > b["win %"] and a["$/day"] / a["worst stretch"] > b["$/day"] / b["worst stretch"]
          and a["$/day"] >= 0.9 * b["$/day"])
    print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
