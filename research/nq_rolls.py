"""The quarterly rolls of the NQ 1-minute file (mdelcristo/NQ-F_1min_OHLCV_Parquet) and a ratio back-adjusted series.

    python research/nq_rolls.py <nq1m parquet folder> <nsx1m_scaled.pkl> <out folder>

The file is the front month, unadjusted: at each roll the price jumps by the carry between the two contracts (about
+1.2% in 2023-2025, a few tenths of a percent either way in 2015-2021). There is no contract column, so the roll
session is found against the NSX 1-minute series (a Nasdaq-100 CFD, which itself rolls on the expiry Friday, so that
day is not a candidate). Candidates: the sessions from the third Friday minus 8 days to the Thursday before it.
Three detectors, each picking the candidate with the largest change of log(NQ / NSX):
  minute  the session's first NQ open against its previous session's last close, NSX at the same two minutes;
  median  the median over 18:00-03:59 of the session against 15:00-16:59 of the previous one;
  rth     the median over 10:00-15:29 of the session against the same hours of the previous one.
The roll session is the one at least two detectors agree on; with no agreement, the minute detector's pick if its jump
is at least twice the next candidate's; otherwise the quarter is undetermined and not adjusted.

The adjusted series multiplies every bar before a roll session by exp(jump) of that roll (the minute detector's jump),
then rescales each New York calendar month to 30,661 at its first close exactly as the unadjusted nq1m_scaled.pkl
(rebuilt from the raw files to the tick). Its "scale" column is the month's factor on the adjusted prices, so levels
the strategies carry across a roll or a month are converted in continuous units.
"""
from __future__ import annotations

import glob
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
REF, TICK = 30661.0, 0.25


def load_raw(folder: str) -> pd.DataFrame:
    raw = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{folder}/NQ_1min_*.parquet"))])
    raw.index = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(NY)
    raw = raw[~raw.index.duplicated()].sort_index()
    return raw[["open", "high", "low", "close", "volume"]]


def third_friday(y: int, m: int) -> pd.Timestamp:
    d = pd.Timestamp(y, m, 1)
    d += pd.Timedelta(days=(4 - d.weekday()) % 7)
    return d + pd.Timedelta(days=14)


def _largest(x: dict):
    return max(x, key=lambda s: abs(np.nan_to_num(x[s])))


def detect(raw: pd.DataFrame, nsx: pd.Series) -> pd.DataFrame:
    t = raw.index
    sess = (t + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    df = pd.DataFrame({"o": raw.open.to_numpy(), "c": raw.close.to_numpy(), "s": sess}, index=t)
    g = df.groupby("s")
    first_t, last_t = g.apply(lambda x: x.index[0]), g.apply(lambda x: x.index[-1])
    fo, lc = g.o.first(), g.c.last()
    nx = nsx.reindex(nsx.index.union(t)).ffill()
    j = pd.DataFrame({"nq": raw.close}).join(nsx.rename("nx"), how="inner")
    j["lb"] = np.log(j.nq / j.nx)
    j["sess"] = (j.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    tm = j.index.hour * 60 + j.index.minute
    late = j[(tm >= 900) & (tm < 1020)].groupby("sess").lb.median()
    eth = j[(tm >= 1080) | (tm < 240)].groupby("sess").lb.median()
    rth = j[(tm >= 600) & (tm < 930)].groupby("sess").lb.median()
    ss = list(fo.index)
    prev = dict(zip(ss[1:], ss[:-1], strict=True))
    rows = []
    for y in range(t[0].year, t[-1].year + 1):
        for m in (3, 6, 9, 12):
            exp = third_friday(y, m)
            cand = [s for s in ss if exp - pd.Timedelta(days=8) <= s < exp and s in prev]
            if not cand or exp > ss[-1]:
                continue
            a = {b: prev[b] for b in cand}
            mj = {b: np.log(fo[b] / nx.loc[first_t[b]]) - np.log(lc[a[b]] / nx.loc[last_t[a[b]]]) for b in cand}
            md = {b: eth.get(b, np.nan) - late.get(a[b], np.nan) for b in cand}
            rj = {b: rth.get(b, np.nan) - rth.get(a[b], np.nan) for b in cand}
            k = [_largest(mj), _largest(md), _largest(rj)]
            srt = sorted(abs(v) for v in mj.values())
            votes = pd.Series(k).value_counts()
            if votes.iloc[0] >= 2:
                date, rule = votes.index[0], f"{votes.iloc[0]} of 3 detectors agree"
            elif srt[-1] >= 2 * srt[-2]:
                date, rule = k[0], "minute jump at least twice the next"
            else:
                date, rule = None, "undetermined (not adjusted)"
            rows.append({"quarter": f"{y}-{m:02d}", "expiry": exp.date(), "minute": k[0].date(), "median": k[1].date(),
                         "rth": k[2].date(), "roll_session": date.date() if date is not None else None, "rule": rule,
                         "jump": mj[date] if date is not None else np.nan,
                         "rth_jump": rj[date] if date is not None else np.nan,
                         "largest_minute_jump": srt[-1], "next_minute_jump": srt[-2]})
    return pd.DataFrame(rows)


def scaled(raw: pd.DataFrame) -> pd.DataFrame:
    """Each New York calendar month multiplied by 30,661 / its first close, rounded to the tick; "scale" the factor."""
    month = raw.index.tz_localize(None).to_period("M")
    f = (REF / raw.close.groupby(month).transform("first")).to_numpy()
    out = raw[["open", "high", "low", "close", "volume"]].copy()
    for col in ("open", "high", "low", "close"):
        out[col] = ((raw[col].to_numpy() * f) / TICK).round() * TICK
    out["scale"] = f
    return out


def adjusted(raw: pd.DataFrame, rolls: pd.DataFrame) -> pd.DataFrame:
    sess = (raw.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    k = np.ones(len(raw))
    for r in rolls.dropna(subset=["roll_session"]).itertuples():
        k[sess < pd.Timestamp(r.roll_session)] *= np.exp(r.jump)
    out = raw.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = raw[col].to_numpy() * k
    return out


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    folder, nsx_pkl, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    raw = load_raw(folder)
    rolls = detect(raw, pd.read_pickle(nsx_pkl).close)
    rolls.to_csv(out / "nq_rolls.csv", index=False, float_format="%.6f")
    pd.set_option("display.width", 250)
    print(rolls.to_string(index=False))
    plain = scaled(raw)
    adj = scaled(adjusted(raw, rolls))
    plain.to_pickle(out / "nq1m_scaled_rebuilt.pkl")
    adj.to_pickle(out / "nq1m_scaled_roll_adjusted.pkl")
    for p in ("nq1m_scaled_rebuilt.pkl", "nq1m_scaled_roll_adjusted.pkl"):
        print(p, sha(out / p))
    # the size of the problem: the scaled series' jump at each roll session's first bar, before and after
    sess = (plain.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    for r in rolls.dropna(subset=["roll_session"]).itertuples():
        i = int(np.argmax(sess == pd.Timestamp(r.roll_session)))
        a = plain.open.iloc[i] / plain.close.iloc[i - 1] - 1
        b = adj.open.iloc[i] / adj.close.iloc[i - 1] - 1
        print(f"{r.roll_session}: session gap {a:+.4%} unadjusted, {b:+.4%} adjusted")


if __name__ == "__main__":
    main()
