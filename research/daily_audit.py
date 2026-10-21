"""The daily opportunity audit of the daily MNQ candidate (docs/DAILY_AUDIT.md): one row per session.

    python research/daily_audit.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <out folder> [book ...]
    python research/daily_audit.py nq <nq1m_scaled.pkl> <nq1m raw folder> <out folder> [book ...]

Books: research/eval_d.py's F_CANDIDATES names (default D+F1 and D+F2), the Python model of MnqCandidateD.cs at 2 ticks
with the evaluation's skip, FOMC and NFP dates.

Each row: the session's data coverage (09:30-16:00 minutes of 390, electronic-session minutes), its status
(eligible, holiday or half day, missing data, warm-up), the sleeves' warm-up, raw setups by sleeve (noise checks
closing past a line, Williams level touches, sweep penetrations), qualified setups (those passing every sleeve rule),
campaigns (entries that filled) and every refusal by reason: no valid setup, blocked by a position, blocked by a
pending order, unaffordable (over $125 planned), daily entry budget exhausted, same-bar priority, missing data. A
session's frequency is counted over every eligible session, zero-campaign sessions included.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controlled as K  # noqa: E402
import eval_d as ED  # noqa: E402

from mnqbot.candidate_d import RTH_OPEN, DConfig, Model  # noqa: E402

NY = "America/New_York"
FIRST = {"mnq": "2026-07-20", "nq": "2015-03-01"}
REASONS = ["unaffordable", "blocked: position", "blocked: pending order", "blocked: daily entry budget exhausted",
           "same-bar priority", "blocked: after the entry window", "skip day"]
NOT_QUALIFIED = ["not qualified: FOMC-morning short", "not qualified: both levels", "not qualified: decision window",
                 "not qualified: room"]


def run_with_snapshots(bars: pd.DataFrame, cfg: DConfig):
    """The model over every bar (as mnqbot.candidate_d.run), with each session's warm-up state at 10:00."""
    m = Model(cfg)
    idx = bars.index.tz_convert(NY)
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    sc = bars["scale"].to_numpy(float) if "scale" in bars else np.ones(len(bars))
    warm = {}
    for i in range(len(bars)):
        t = idx[i]
        m.step(i, t, o[i], h[i], l[i], c[i], sc[i])
        if t.hour * 60 + t.minute == 600:
            day = (t + pd.Timedelta(hours=6)).strftime("%Y-%m-%d")
            warm[day] = {"noise ready": bool(m.noise.ready), "Williams ready": not np.isnan(m.wb.prev_raw),
                         "E1 pools ready": m.sweep is not None and "PWL" in m.sweep.pools and "PDL" in m.sweep.pools}
    return m, warm


def daily_table(bars, m, warm, skip_holiday, missing, fomc, nfp, first) -> pd.DataFrame:
    idx = bars.index.tz_convert(NY)
    tmin = idx.hour * 60 + idx.minute
    sess = (idx + pd.Timedelta(hours=6)).strftime("%Y-%m-%d")
    rth = (tmin >= RTH_OPEN) & (tmin < 960)
    cov = pd.DataFrame({"s": sess, "rth": rth}).groupby("s").agg(eth_minutes=("rth", "size"),
                                                                  rth_minutes=("rth", "sum"))
    weekdays = [d for d in cov.index if pd.Timestamp(d).weekday() < 5]
    au = pd.DataFrame(m.audit, columns=["bar", "sleeve", "d", "outcome"])
    au["day"] = np.asarray(sess)[au.bar.to_numpy()] if len(au) else []
    camps = pd.Series([np.asarray(sess)[min(lt.fill_bar for lt in c.lots)] for c in m.campaigns], dtype=object)
    rows = []
    for d in weekdays:
        a = au[au.day == d]
        w = warm.get(d, {"noise ready": False, "Williams ready": False, "E1 pools ready": False})
        if d < first:
            status = "warm-up (before the first tested session)"
        elif d in missing:
            status = "missing data"
        elif d in skip_holiday:
            status = "holiday or half day"
        elif not w["noise ready"]:
            status = "warm-up"
        else:
            status = "eligible"
        decided = a[a.outcome != "raw: penetration"]
        raw = {"noise": int((a.sleeve == "noise").sum()), "williams": int((a.sleeve == "williams").sum()),
               "sweep": int((a.outcome == "raw: penetration").sum())}
        qualified = decided[~decided.outcome.isin(NOT_QUALIFIED + ["skip day"])]
        n_camp = int((camps == d).sum())
        row = {"session": d, "status": status, "rth minutes (of 390)": int(cov.rth_minutes.get(d, 0)),
               "eth minutes": int(cov.eth_minutes.get(d, 0)), **w, "FOMC / NFP day (no sweep setups)":
               d in fomc or d in nfp, "raw noise": raw["noise"], "raw williams": raw["williams"],
               "raw sweep (penetrations)": raw["sweep"], "qualified": len(qualified),
               "limits placed": int((decided.outcome == "entered (limit placed)").sum()),
               "campaigns": n_camp}
        for r in REASONS[:-1]:
            row[r] = int((decided.outcome == r).sum())
        skipped = int((decided.outcome == "skip day").sum())
        row["missing data"] = skipped if d in missing else 0
        row["skip day (holiday / half day)"] = 0 if d in missing else skipped
        for r in NOT_QUALIFIED:
            row[r] = int((decided.outcome == r).sum())
        row["sweep chains incomplete"] = max(0, raw["sweep"] - int((decided.sleeve == "sweep").sum()))
        row["no valid setup"] = status == "eligible" and len(qualified) == 0
        rows.append(row)
    return pd.DataFrame(rows).fillna(0)


def frequency(table: pd.DataFrame) -> dict:
    el = table[table.status == "eligible"]
    n = len(el)
    out = {"eligible sessions": n, "campaigns": int(el.campaigns.sum()),
           "campaigns per eligible session": el.campaigns.sum() / n if n else np.nan,
           "campaigns per active session": el.campaigns[el.campaigns > 0].mean() if (el.campaigns > 0).any() else 0}
    for k in range(4):
        out[f"sessions with {k} campaigns %"] = 100 * (el.campaigns == k).mean() if n else np.nan
    out["sessions with no valid setup %"] = 100 * el["no valid setup"].mean() if n else np.nan
    out["missing-data sessions"] = int((table.status == "missing data").sum())
    out["holiday / half-day sessions"] = int((table.status == "holiday or half day").sum())
    out["warm-up sessions"] = int(table.status.str.startswith("warm-up").sum())
    return out


def main() -> None:
    kind, a1, a2, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    books = sys.argv[5:] or ["D+F1", "D+F2"]
    out.mkdir(parents=True, exist_ok=True)
    bars = ED.mnq_series(a1, a2) if kind == "mnq" else ED.nq_bars(a1, a2)
    missing = frozenset(K.incomplete_sessions(K.rth(bars[["open", "high", "low", "close"]])))
    holiday = frozenset(K.DEFAULT_SKIP.split(","))
    skip = holiday | missing
    summary = []
    for book in books:
        cfg = DConfig(slippage_ticks=2, skip_dates=skip, fed_dates=ED.FOMC, nfp_dates=ED.NFP, **ED.F_CANDIDATES[book])
        m, warm = run_with_snapshots(bars, cfg)
        t = daily_table(bars, m, warm, holiday, missing, ED.FOMC, ED.NFP, FIRST[kind])
        t.to_csv(out / f"daily_audit_{book}.csv", index=False)
        el = t[t.status == "eligible"]
        f = frequency(t)
        skip_cols = ("rth minutes (of 390)", "eth minutes")
        counts = [c for c in el.columns if el[c].dtype.kind in "iu" and c not in skip_cols]
        totals = {c: int(el[c].sum()) for c in counts}
        summary.append({"book": book, **f, **{f"total {k}": v for k, v in totals.items()}})
        print(f"{kind} {book}: " + ", ".join(f"{k} {v:.2f}" if isinstance(v, float) else f"{k} {v}"
                                             for k, v in f.items()))
    pd.DataFrame(summary).to_csv(out / "daily_audit_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(summary).T.to_string())


if __name__ == "__main__":
    main()
