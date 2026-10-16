"""Round thirty: market mood (VIX, S&P 500) and hourly futures volume at the signal, from Yahoo Finance.

    D=yahoo; Y="https://query1.finance.yahoo.com/v8/finance/chart"
    curl -A "Mozilla/5.0" -o $D/VIX_1d.json   "$Y/%5EVIX?interval=1d&period1=946684800&period2=1792125136"
    curl -A "Mozilla/5.0" -o $D/VIX3M_1d.json "$Y/%5EVIX3M?interval=1d&period1=946684800&period2=1792125136"
    curl -A "Mozilla/5.0" -o $D/VIX9D_1d.json "$Y/%5EVIX9D?interval=1d&period1=946684800&period2=1792125136"
    curl -A "Mozilla/5.0" -o $D/ES_1d.json    "$Y/ES%3DF?interval=1d&period1=946684800&period2=1792125136"
    curl -A "Mozilla/5.0" -o $D/NQ_1d.json    "$Y/NQ%3DF?interval=1d&period1=946684800&period2=1792125136"
    curl -A "Mozilla/5.0" -o $D/NQ_60m.json   "$Y/NQ%3DF?interval=60m&range=730d"
    python research/fear_volume.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" $D

Fixed before running. The bot as it trades now (5-minute bars, 1.5-noise-unit take-profit, $116.67 max loss
live from the fill), 1 contract, prices at today's level.
Part A, market mood, facts known before the 09:30 open of session D (from closes of D-1 and before):
  1 fearful:          VIX above its median of the previous 250 closes
  2 inverted:         VIX at or above VIX3M (near-term fear above 3-month fear)
  3 short-term stress: VIX9D at or above VIX
  4 fear rising:      VIX closed higher than the day before
  5 Nasdaq leading:   NQ's 20-session return above ES's
  Discovery 2011-2018: Welch t-test of $ per trade, yes against no, Benjamini-Hochberg 5% over the five.
  Confirmation 2019-2022: same sign, one-sided p < 5%. Final test 2023 - Sep 2026, once, for a filter that
  skips the losing side of every confirmed fact: higher win rate, more $ per day per dollar of worst losing
  stretch, at least 90% of the bot's $ per day.
Part B, hourly volume at the signal, NQ futures 60-minute bars (Yahoo keeps about two years):
  busy hour: the volume of the last full hour that ended at or before the signal, against the average volume of
  the bars at the same clock time over the previous 20 sessions; above 1 or not. Quarterly roll weeks (10 days
  before to 3 after expiry) are left out. The trades are split in two halves by date; a pass needs the same sign
  and a one-sided t >= 1.65 in each half. Two years leave no third period, so a pass makes it a candidate for
  forward testing, not a change to the bot.
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
import volume_days as V  # noqa: E402

from mnqbot.data import NY  # noqa: E402

FACTS = ["fearful", "inverted", "short-term stress", "fear rising", "Nasdaq leading"]


def closes(path: Path) -> pd.Series:
    r = json.loads(path.read_text())["chart"]["result"][0]
    days = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(NY).tz_localize(None).normalize()
    s = pd.Series(r["indicators"]["quote"][0]["close"], index=days, dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")]


def hourly(path: Path) -> pd.DataFrame:
    r = json.loads(path.read_text())["chart"]["result"][0]
    idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(NY)
    df = pd.DataFrame({"volume": r["indicators"]["quote"][0]["volume"]}, index=idx).dropna()
    return df[df.volume > 0]


def mood(d: Path, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    vix, vix3, vix9 = closes(d / "VIX_1d.json"), closes(d / "VIX3M_1d.json"), closes(d / "VIX9D_1d.json")
    nq, es = closes(d / "NQ_1d.json"), closes(d / "ES_1d.json")
    rows = {}
    for day in sessions:
        v, v3, v9 = vix[vix.index < day], vix3[vix3.index < day], vix9[vix9.index < day]
        n, e = nq[nq.index < day], es[es.index < day]
        if len(v) < 251 or v3.empty or v9.empty or len(n) < 21 or len(e) < 21:
            continue
        rows[day] = {"fearful": v.iloc[-1] > v.iloc[-251:-1].median(),
                     "inverted": v.iloc[-1] >= v3.iloc[-1],
                     "short-term stress": v9.iloc[-1] >= v.iloc[-1],
                     "fear rising": v.iloc[-1] > v.iloc[-2],
                     "Nasdaq leading": n.iloc[-1] / n.iloc[-21] > e.iloc[-1] / e.iloc[-21]}
    return pd.DataFrame.from_dict(rows, orient="index")


def welch(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def busy_hour(h: pd.DataFrame, signal: pd.Timestamp) -> float:
    """True/False for the last full hour before the signal vs the same clock hour over 20 sessions; nan if unknown."""
    done = h[h.index + pd.Timedelta(minutes=60) <= signal]
    if done.empty or (signal - done.index[-1]) > pd.Timedelta(hours=2):
        return math.nan
    last = done.index[-1]
    same = done[(done.index.hour == last.hour) & (done.index.minute == last.minute) & (done.index < last)]
    if len(same) < 20:
        return math.nan
    return float(done.volume.iloc[-1] > same.volume.iloc[-20:].mean())


def main() -> None:
    bars = MT._bars(sys.argv[1])
    d = Path(sys.argv[2])
    idx = bars.index.tz_convert(NY).tz_localize(None)
    sessions = pd.DatetimeIndex(sorted(set(idx[(idx.hour * 60 + idx.minute) == 570].normalize())))
    first_sessions = set(pd.Series(sessions).groupby(sessions.to_period("M")).min())
    sessions = sessions[(sessions >= "2011-01-01") & ~sessions.isin(list(first_sessions))]
    tf = MT.clean(P.simulate(bars, target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True), first_sessions)
    tf["day"] = tf.entry_time.dt.tz_localize(None).dt.normalize()

    # ---- Part A
    tf = tf.join(mood(d, sessions), on="day")
    year = tf.entry_time.dt.year
    tested = tf.dropna(subset=FACTS)
    ty = tested.entry_time.dt.year
    parts = {"11-18": tested[ty <= 2018], "19-22": tested[(ty >= 2019) & (ty <= 2022)]}
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
    print(f"Part A, market mood. Trades with facts: 2011-18 {len(parts['11-18'])}, 2019-22 {len(parts['19-22'])}")
    print(df.round(2).to_string(index=False))
    confirmed = df[df.confirmed]
    if confirmed.empty:
        print("No fact passed the luck filter and confirmation: nothing goes to the final test.")
    else:
        keep = pd.Series(True, index=tf.index)
        for _, r in confirmed.iterrows():
            has = tf[r.fact].notna()
            keep &= ~has | (tf[r.fact] == (r["t 11-18"] > 0))
        ss = sessions[sessions.year >= 2023]
        a, b = MT.stats(tf[keep & (year >= 2023)], ss), MT.stats(tf[year >= 2023], ss)
        for name, s in (("bot", b), ("filtered", a)):
            print(f"  2023-26 {name:9s} win {s['win %']:.1f}%  $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
                  f"worst stretch {s['worst stretch']:.0f}")
        ok = (a["win %"] > b["win %"] and a["$/day"] / a["worst stretch"] > b["$/day"] / b["worst stretch"]
              and a["$/day"] >= 0.9 * b["$/day"])
        print(f"FINAL TEST 2023 - Sep 2026: {'PASS' if ok else 'FAIL'}")

    # ---- Part B
    h = hourly(d / "NQ_60m.json")
    recent = tf[(tf.entry_time >= h.index[0] + pd.Timedelta(days=35))].copy()
    recent = recent[~recent.day.map(V.roll_window)]
    recent["busy hour"] = [busy_hour(h, t) for t in recent.entry_time]
    recent = recent.dropna(subset=["busy hour"])
    half = recent.entry_time.iloc[len(recent) // 2]
    print(f"\nPart B, hourly volume at the signal: {len(recent)} trades, {recent.entry_time.iloc[0].date()} to "
          f"{recent.entry_time.iloc[-1].date()}, split at {half.date()}")
    ok_all, signs = True, []
    halves = (("first half", recent[recent.entry_time < half]), ("second half", recent[recent.entry_time >= half]))
    for name, part in halves:
        yes, no = part[part["busy hour"] == 1].pnl.to_numpy(), part[part["busy hour"] == 0].pnl.to_numpy()
        t = welch(yes, no)
        signs.append(np.sign(t))
        ok_all &= abs(t) >= 1.645
        print(f"  {name:11s} busy {len(yes):4d} trades ${yes.mean():7.2f}  "
              f"quiet {len(no):4d} trades ${no.mean():7.2f}  t {t:+.2f}")
    ok_all &= signs[0] == signs[1]
    print(f"Part B: {'CANDIDATE for forward testing' if ok_all else 'FAIL'}")


if __name__ == "__main__":
    main()
