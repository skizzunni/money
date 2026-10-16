"""Round thirty-six: more winners at the user's own setting, 10 MNQ and a $350 max loss ($35 a contract).

    python research/win_rate35.py nsx_5m_scaled.pkl nq_5m_scaled.pkl

Reasoning, written before running. Every exit setting so far was tuned at $117 a contract. At $35 a contract (17.5
points) the bot wins about 14% of trades and trades twice a day: normal 5-minute noise hits the stop, and the bot
re-enters at the next check while price is still outside the line, so losers come in strings (seven on 22 September
2026). Sizes stay as they are: 10 contracts, $350 for the trade. Levers, fixed before running:
  take-profit closer: 0.5, 0.75 or 1.0 noise units from the fill instead of 1.5 (more trades reach it);
  lock a small win: once a bar closes 17.5 points (1R) or 35 points (2R) in profit, the stop moves to the entry plus
    2.5 points ($5 a contract, more than the round-trip fees and slippage), so the trade can't turn into a loser;
  fewer repeat losers: no new entries today after 1 or after 2 losing trades; or no new entry on a side that already
    lost today.
Stage 2, only if no single lever passes: each take-profit with each lock and each repeat-loser rule, in pairs.
Pass bar against the bot at $35 a contract, fixed before running: on the index data 2011-2018 the win rate at least
10 points higher, $ per day no lower, t-stat no more than 0.3 lower, $ per day per dollar of worst losing stretch no
lower. The passing variant with the most $ per day must do the same on 2019-2022, then on 2023 - Sep 2026 (run once),
and on the independent NQ futures data 2015 - July 2025 (win rate 10 points higher and $ per day no lower).
1 contract with a 17.5-point max loss stands for 10 MNQ at $350 (multiply $ by 10); $1.24 fees and 1 tick slippage
per contract, prices at today's level.
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import more_trades as MT  # noqa: E402
import profit_levers as P  # noqa: E402
import stress as S  # noqa: E402

CAP = 35.0 / 2.0  # points: $350 over 10 MNQ
BASE = dict(target=1.5, target_on_fill_bar=False, cap_on_fill_bar=True, cap_pts=CAP)
TPS = {"tp 0.5": {"target": 0.5}, "tp 0.75": {"target": 0.75}, "tp 1.0": {"target": 1.0}}
LOCKS = {"lock at 1R": {"lock": (CAP, 2.5)}, "lock at 2R": {"lock": (2 * CAP, 2.5)}}
REPEATS = {"stop after 1 loser": {"day_losers": 1}, "stop after 2 losers": {"day_losers": 2},
           "no side twice": {"side_once": True}}
SINGLES = {"bot": {}, **TPS, **LOCKS, **REPEATS}
PAIRS = {f"{a} + {b}": {**TPS[a], **o[b]} for a in TPS for o in (LOCKS, REPEATS) for b in o}
PAIRS.update({f"{a} + {b}": {**LOCKS[a], **REPEATS[b]} for a, b in itertools.product(LOCKS, REPEATS)})


def _job(args):
    path, name, kw = args
    return name, P.simulate(pd.read_pickle(path), **{**BASE, **kw})


def runs_for(path, variants):
    with ProcessPoolExecutor(max_workers=4) as ex:
        return dict(ex.map(_job, [(path, n, kw) for n, kw in variants.items()]))


def stats(tf, sessions):
    s = MT.stats(tf, sessions)
    s["eff"] = 1000 * s["$/day"] / s["worst stretch"]
    return s


def table_for(runs, sessions, first, periods):
    out = {}
    for name, tf in runs.items():
        tf = MT.clean(tf, first)
        for label, y0, y1 in periods:
            ss = sessions[(sessions.year >= y0) & (sessions.year <= y1)]
            yr = tf.entry_time.dt.year
            out[(name, label)] = stats(tf[(yr >= y0) & (yr <= y1)], ss)
    return out


def show(table, names, label):
    rows = [(n, table[(n, label)]["trades/day"], table[(n, label)]["win %"], table[(n, label)]["$/day"],
             table[(n, label)]["t"], table[(n, label)]["worst stretch"], table[(n, label)]["eff"]) for n in names]
    print(f"\n{label}, per contract at $35 (x10 for 10 MNQ at $350)")
    print(pd.DataFrame(rows, columns=["variant", "trades/day", "win %", "$/day", "t", "worst stretch",
                                      "$/day per $1k stretch"]).round(2).to_string(index=False))


def passes(table, name, label, need_t=True):
    a, b = table[(name, label)], table[("bot", label)]
    ok = a["win %"] >= b["win %"] + 10 and a["$/day"] >= b["$/day"]
    return ok and (not need_t or (a["t"] >= b["t"] - 0.3 and a["eff"] >= b["eff"]))


def main() -> None:
    nsx, nq = sys.argv[1], sys.argv[2]
    sessions, first = S.sessions_of(pd.read_pickle(nsx))
    sessions = sessions[sessions >= "2011-01-01"]
    periods = (("2011-2018", 2011, 2018), ("2019-2022", 2019, 2022))
    runs = runs_for(nsx, SINGLES)
    table = table_for(runs, sessions, first, periods)
    show(table, SINGLES, "2011-2018")
    cands = [n for n in SINGLES if n != "bot" and passes(table, n, "2011-2018")]
    print(f"\nDiscovery 2011-2018, single levers: {cands or 'none pass'}")
    if not cands:
        runs.update(runs_for(nsx, PAIRS))
        table = table_for(runs, sessions, first, periods)
        show(table, ["bot", *PAIRS], "2011-2018")
        cands = [n for n in PAIRS if passes(table, n, "2011-2018")]
        print(f"\nDiscovery 2011-2018, pairs: {cands or 'none pass'}")
        if not cands:
            return
    best = max(cands, key=lambda n: table[(n, "2011-2018")]["$/day"])
    show(table, ["bot", best], "2019-2022")
    ok = passes(table, best, "2019-2022")
    print(f"Best: {best}. Confirmation 2019-2022: {'PASS' if ok else 'FAIL'}")
    if not ok:
        return
    table.update(table_for({n: runs[n] for n in ("bot", best)}, sessions, first, (("2023-2026", 2023, 2026),)))
    show(table, ["bot", best], "2023-2026")
    final = passes(table, best, "2023-2026")
    print(f"Final test 2023 - Sep 2026: {'PASS' if final else 'FAIL'}")
    if not final:
        return
    variants = {"bot": {}, best: {**SINGLES, **PAIRS}[best]}
    q_sessions, q_first = S.sessions_of(pd.read_pickle(nq))
    q_sessions = q_sessions[q_sessions >= "2015-03-01"]
    q = table_for(runs_for(nq, variants), q_sessions, q_first, (("NQ 2015-2025", 2015, 2025),))
    show(q, ["bot", best], "NQ 2015-2025")
    print(f"Replication on NQ futures: {'PASS' if passes(q, best, 'NQ 2015-2025', need_t=False) else 'FAIL'}")


if __name__ == "__main__":
    main()
