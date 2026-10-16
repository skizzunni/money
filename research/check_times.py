"""Round thirty-four: are the first and last half-hour checks worth trading?

    python research/check_times.py nsx_5m_scaled.pkl nq_5m_scaled.pkl

Reasoning, written before running. A 15:30 entry has 25 minutes before the 16:00 exit to pay for its risk and
costs; a 15:00 entry 55. A 10:00 entry is judged against a noise area built from the first, noisiest half hour.
Variants, fixed before running (no new entries at these checks; everything else as the bot trades now):
  A no entries at 15:30;  B no entries at 15:00 or 15:30;  C no entries at 10:00;  D no entries at 10:00 or 15:30.
1 contract, $116.67 max loss live from the fill, 1.5-noise-unit take-profit, prices at today's level.
Pass bar, fixed before running, against the bot: on the index data 2011-2018 $ per day no lower, t-stat no more than
0.3 lower, more $ per day per dollar of worst losing stretch; the best passing variant must do the same on 2019-2022,
then on 2023 - Sep 2026 (run once), and also beat the bot on $ per day and on $ per day per dollar of worst stretch
on the independent NQ futures data 2015 - July 2025.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import stress as S  # noqa: E402

VARIANTS = {"bot": frozenset(), "A no 15:30": frozenset({930}), "B no 15:00, 15:30": frozenset({900, 930}),
            "C no 10:00": frozenset({600}), "D no 10:00, 15:30": frozenset({600, 930})}


def _job(args):
    path, name = args
    return name, P.simulate(pd.read_pickle(path), target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True,
                            no_entry_checks=VARIANTS[name])


def stats(tf: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict:
    s = MT.stats(tf, sessions)
    s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
    return s


def runs_for(path: str) -> dict:
    with ProcessPoolExecutor(max_workers=4) as ex:
        return dict(ex.map(_job, [(path, n) for n in VARIANTS]))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = S.sessions_of(pd.read_pickle(nsx))
    sessions = sessions[sessions >= "2011-01-01"]
    runs = {n: MT.clean(tf, first) for n, tf in runs_for(nsx).items()}
    # descriptive: $ per trade by the check that opened it (bot, 2011-2022)
    bot = runs["bot"]
    fit = bot[bot.entry_time.dt.year <= 2022]
    by_check = fit.groupby(fit.entry_time.dt.strftime("%H:%M")).pnl.agg(["count", "mean", "sum"]).round(2)
    print("the bot's trades by fill time, 2011-2022 (fill = the bar after the check):")
    print(by_check.to_string())
    table, rows = {}, []
    for name, tf in runs.items():
        for label, y0, y1 in (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022)):
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            s = stats(tf[(tf.entry_time.dt.year >= y0) & (tf.entry_time.dt.year <= y1)], ss)
            table[(name, label)] = s
            rows.append((name, label, s["trades/day"], s["win %"], s["$/day"], s["t"], s["worst stretch"], s["eff"]))
    print(pd.DataFrame(rows, columns=["variant", "period", "trades/day", "win %", "$/day", "t", "worst stretch",
                                      "$/day per $1k stretch"]).round(2).to_string(index=False))

    def passes(name, label):
        a, b = table[(name, label)], table[("bot", label)]
        return a["$/day"] >= b["$/day"] and a["t"] >= b["t"] - 0.3 and a["eff"] > b["eff"]

    cands = [n for n in VARIANTS if n != "bot" and passes(n, "2011-2018")]
    print(f"\nDiscovery 2011-2018: {cands or 'none pass'}")
    if not cands:
        return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["eff"])
    ok = passes(best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    ss = sessions[sessions.year >= 2023]
    for name in ("bot", best):
        table[(name, "2023-2026")] = stats(runs[name][runs[name].entry_time.dt.year >= 2023], ss)
        s = table[(name, "2023-2026")]
        print(f"  2023-26 {name:18s} $/day {s['$/day']:.2f}  t {s['t']:.2f}  worst stretch {s['worst stretch']:.0f}")
    final = passes(best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    q_sessions, q_first = S.sessions_of(pd.read_pickle(nq))
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q_runs = {n: MT.clean(tf, q_first) for n, tf in runs_for(nq).items() if n in ("bot", best)}
    a, b = (stats(q_runs[n][q_runs[n].entry_time.dt.tz_localize(None) >= q_sessions[0]], q_sessions)
            for n in (best, "bot"))
    for name, s in (("bot", b), (best, a)):
        print(f"  NQ futures 2015-25 {name:18s} $/day {s['$/day']:.2f}  t {s['t']:.2f}  "
              f"worst stretch {s['worst stretch']:.0f}")
    ok = a["$/day"] >= b["$/day"] and a["eff"] > b["eff"]
    print(f"Replication on NQ futures: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
