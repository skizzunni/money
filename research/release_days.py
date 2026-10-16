"""Round forty-six: no 10:00 entry when a major economic report comes out at 10:00.

    python research/release_days.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running the tests below, after a look at 2011-2018. The 10:00 check fires at the second the
10:00 reports come out, so its entry lands in the release whipsaw, and a 17.5-point stop (10 MNQ, $350) can't sit
through it. On 2011-2018, v1.3's 10:00 entries on ISM Manufacturing days (first business day of the month) won 40% and
lost $43 a trade, on ISM Services days (third business day) 37% and -$50, against 48.5% and +$94 on other days (20
and 19 trades). Rule, fixed before running: no entry at the 10:00 check on those days; later checks trade as usual.
Variants: ISM days only; ISM days and the Conference Board's consumer confidence (last Tuesday of the month, 10:00).
Days are from the schedule rules (US federal holidays are not business days), not from a release calendar.
2011-2018 found it and picks the variant with more $ per day among those meeting the bar; the tests are 2019-2022,
then 2023 - Sep 2026 (run once), then NQ futures 2015 - July 2025.
Pass bar against v1.3 on 1-minute bars, fixed before running: win rate higher, $ per day no lower, t-stat no more
than 0.3 lower, $ per day per dollar of worst losing stretch no lower (on NQ: win rate higher, $ per day no lower).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"target": 1.5, "target_on_fill_bar": False, "cap_on_fill_bar": True, "cap_pts": 17.5,
        "lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
TEN = frozenset({600})


def ism_days(y0: int, y1: int) -> set:
    bd = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq=CustomBusinessDay(calendar=USFederalHolidayCalendar()))
    by_month = pd.Series(bd).groupby(bd.to_period("M"))
    return set(by_month.nth(0).dt.date) | set(by_month.nth(2).dt.date)


def confidence_days(y0: int, y1: int) -> set:
    return {d.date() for d in pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="BME")
            for d in [d - pd.Timedelta(days=(d.weekday() - 1) % 7)]}  # the last Tuesday on or before month end


def variants(y0: int, y1: int) -> dict:
    ism = {d: TEN for d in ism_days(y0, y1)}
    both = {**ism, **{d: TEN for d in confidence_days(y0, y1)}}
    return {"bot": BASE, "no 10:00 on ISM days": {**BASE, "skip_checks_on": ism},
            "no 10:00 on ISM and confidence days": {**BASE, "skip_checks_on": both}}


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] > b["win %"] and a["$/day"] >= b["$/day"]
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = L.five_min_sessions(nsx)
    sessions = sessions[sessions >= "2011-01-01"]
    v = variants(2010, 2026)
    runs = W.runs_for(nsx, v)
    periods = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))
    table = W.table_for(runs, sessions, first, periods)
    W.show(table, v, "2011-2018")
    cands = [n for n in v if n != "bot" and passes(table, n, "2011-2018")]
    print(f"\n2011-2018 (where it was found): {cands or 'none meet the bar'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    for label in ("2019-2022", "2023-2026"):
        W.show(table, ["bot", best], label)
        ok = passes(table, best, label)
        print(f"{best}, {label}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            return
    q_sessions, q_first = L.five_min_sessions(nq)
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q_runs = W.runs_for(nq, {n: variants(2015, 2025)[n] for n in ("bot", best)})
    q = W.table_for(q_runs, q_sessions, q_first, (("NQ 2015-2025", 2015, 2025),))
    W.show(q, ["bot", best], "NQ 2015-2025")
    print(f"Replication on NQ futures: {'PASS' if passes(q, best, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
