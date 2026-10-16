"""Round forty-four: drop trades that lose on average (options-expiration Fridays; checks that lost in past years).

    python research/drop_losers.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running. Over the first minutes after the entry, price is a coin flip (docs/RESULTS.md), so
the win rate can't be raised by a better entry at the same money; it can by not taking trades that lose on average,
which raises winners and money together. Two ideas, fixed before running:
  options expiration: no entries on the third Friday of the month, when dealers' hedging of expiring options tends to
    pin the index and breakouts should fail more often;
  walk-forward checks: each year, no entries at the half-hour checks whose trades lost money on average over all
    earlier years (from 2011 on the index, 2015 on NQ futures; judged from 2013 / 2017, after two years of history),
    using only the past.
Baseline: v1.3 on 1-minute bars, 10 MNQ and $350. Pass bar against it, fixed before running: win rate higher, $ per
day no lower, t-stat no more than 0.3 lower, $ per day per dollar of worst losing stretch no lower, on the index
2013-2018 (discovery), then 2019-2022, then 2023 - Sep 2026 (run once), then NQ futures 2017 - July 2025 (win rate
higher, $ per day no lower).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"target": 1.5, "target_on_fill_bar": False, "cap_on_fill_bar": True, "cap_pts": 17.5,
        "lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}


def third_fridays(y0: int, y1: int) -> frozenset:
    days = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="WOM-3FRI")
    return frozenset(d.date() for d in days)


def walk_forward_blocks(trades: pd.DataFrame, first_year: int, last_year: int) -> dict:
    """{year: checks whose trades lost on average over every earlier year}; checks keyed by the fill minute."""
    t = trades.assign(year=trades.entry_time.dt.year,
                      check=trades.entry_time.dt.hour * 60 + trades.entry_time.dt.minute)
    out = {}
    for y in range(first_year, last_year + 1):
        past = t[t.year < y].groupby("check").pnl.mean()
        out[y] = frozenset(int(m) for m, v in past.items() if v < 0)
    return out


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] > b["win %"] and a["$/day"] >= b["$/day"]
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def variants_for(path, start_year, judge_year, end_year):
    base = MT.clean(P.simulate(pd.read_pickle(path), **BASE), set())
    blocks = walk_forward_blocks(base[base.entry_time.dt.year >= start_year], judge_year, end_year)
    for y in (judge_year, end_year):
        print(f"  {y}: checks skipped {sorted(f'{m // 60}:{m % 60:02d}' for m in blocks[y])}")
    return {"bot": BASE, "no options-expiry Fridays": {**BASE, "skip_days": third_fridays(start_year, end_year)},
            "walk-forward checks": {**BASE, "checks_by_year": blocks}}


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = L.five_min_sessions(nsx)
    sessions = sessions[sessions >= "2011-01-01"]
    variants = variants_for(nsx, 2011, 2013, 2026)
    runs = W.runs_for(nsx, variants)
    periods = (("2013-2018", 2013, 2018), ("2019-2022", 2019, 2022), ("2023-2026", 2023, 2026))
    table = W.table_for(runs, sessions, first, periods[:2])
    W.show(table, variants, "2013-2018")
    cands = [n for n in variants if n != "bot" and passes(table, n, "2013-2018")]
    print(f"\nDiscovery 2013-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2013-2018")]["$/day"])
    W.show(table, ["bot", best], "2019-2022")
    ok = passes(table, best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    table.update(W.table_for({n: runs[n] for n in ("bot", best)}, sessions, first, periods[2:]))
    W.show(table, ["bot", best], "2023-2026")
    final = passes(table, best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    q_sessions, q_first = L.five_min_sessions(nq)
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q_variants = variants_for(nq, 2015, 2017, 2025)
    q_runs = W.runs_for(nq, {n: q_variants[n] for n in ("bot", best)})
    q = W.table_for(q_runs, q_sessions, q_first, (("NQ 2017-2025", 2017, 2025),))
    W.show(q, ["bot", best], "NQ 2017-2025")
    print(f"Replication on NQ futures: {'PASS' if passes(q, best, 'NQ 2017-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
