"""Round forty-one: the exit for passing the $50K evaluation at 10 MNQ and $350 (a trailing lock).

    python research/eval_trail.py nsx_1m_scaled.pkl nq_1m_scaled.pkl

Reasoning, written before running, after round forty. A trailing stop that activates once a trade is A points up and
then trails B points behind the best price made about a third less per day than the fixed lock on 2011-2018 (the
trend days are cut short), but far smaller losing stretches, and passed more $50K evaluations at 10 MNQ: 43% against
32%. The evaluation is judged on the path ($3,000 before a $2,000 end-of-day drawdown), not on the money per day,
so this round asks the evaluation question directly. 2011-2018 has been seen for these variants (round forty) and
serves as discovery; the variant chosen there is the one with the most passes and the fewest fails, (12.5, 10).
Pass bar, fixed before running, against the bot as it trades now (v1.3) at 10 MNQ and $350, 125-trading-day window:
evaluation pass rate at least 5 points higher and fail rate lower, win rate no more than 2 points lower, daily t-stat
no more than 0.3 lower; on 2019-2022, then 2023 - Sep 2026 (run once), then on NQ futures 2015 - July 2025.
Also shown: $ per day, so the cost in money is on the table.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lock_more as L  # noqa: E402
import win_rate35 as W  # noqa: E402

BASE = {"lock": (17.5, 2.5), "lock_touch": True, "minutes": 1, "day_losers": 4}
CHOSEN = "trail 12.5/10"
VARIANTS = {"bot": BASE, CHOSEN: {**BASE, "lock": None, "trail_pts": (12.5, 10.0)}}


def check(path, start, label, y0, y1):
    sessions, first = L.five_min_sessions(path)
    sessions = sessions[sessions >= start]
    runs = W.runs_for(path, VARIANTS)
    table = W.table_for(runs, sessions, first, ((label, y0, y1),))
    W.show(table, VARIANTS, label)
    ev = L.evals(runs, sessions, first, y0, y1)
    print(f"$50K evaluation at 10 MNQ (pass %, fail %): {ev}")
    a, b = table[(CHOSEN, label)], table[("bot", label)]
    ok = (ev[CHOSEN][0] >= ev["bot"][0] + 5 and ev[CHOSEN][1] < ev["bot"][1] and a["win %"] >= b["win %"] - 2
          and a["t"] >= b["t"] - 0.3)
    print(f"{label}: {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    if not check(nsx, "2011-01-01", "2019-2022", 2019, 2022):
        return
    if not check(nsx, "2011-01-01", "2023-2026", 2023, 2026):
        return
    check(nq, "2015-03-01", "NQ 2015-2025", 2015, 2025)


if __name__ == "__main__":
    main()
