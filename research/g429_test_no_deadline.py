"""G429 (docs/NINJATRADER_V38.md): the Test with no time limit (TPT's real rule), U57 (the Test sprint) against U58
(the funded mode's sizing, 1 MNQ growing with profit). The 116 starts of docs/V2_STOPS.md's v3 replay (every 30 days,
Feb 2015 - Jul 2024, NQ 5-minute, closures skipped), $0.62 a side and 2 ticks, each run until it passes (+$3,000, 3
days, best day under half the profit) or fails (the balance, open trades at their bars' worst prices, touches the
highest end-of-day balance less $2,000, at most the start). The configurations are the NinjaTrader tests' (GROW, SPRINT).

    PROCS=4 python research/g429_test_no_deadline.py <data dir>
"""
from __future__ import annotations

import dataclasses
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import v2_stops_eval as V  # noqa: E402
import v3_eval as E  # noqa: E402
from test_ninjatrader_v38 import GROW, SPRINT  # noqa: E402

from mnqbot.noise import run  # noqa: E402

B: dict = {}


def job(a):
    tag, start = a
    b = B["b"]
    s0 = pd.Timestamp(start, tz=V.NY)
    w = b[b.index >= s0 - pd.Timedelta(days=150)]  # to the end of the data, as registered
    base = {"trail_from": start, "slippage_ticks": 2, "skip_dates": V.BASE["skip_dates"], "fed_dates": V.FOMC}
    if tag.startswith("U58, squeeze "):  # G430: the smallest cut-to-the-room stop, points
        base["squeeze_min"] = float(tag.split()[-1])
    cfg = dataclasses.replace(GROW, **base) if tag.startswith("U58") else dataclasses.replace(GROW, **{**SPRINT, **base})
    tr = [t for t in run(w, cfg, 5).trades if t.entry_time >= s0]
    closed, worst, _ = V.marks(w, tr)
    day = np.asarray(w.index.tz_convert(V.NY).strftime("%Y-%m-%d"))
    i0 = int(np.searchsorted(w.index, s0))
    out, sessions, dd = E.test_run(day, closed, worst, i0, len(w))
    return {"tag": tag, "start": start, "outcome": out, "sessions": sessions, "dd": dd}


def init(d):
    B["b"] = V.load(d)


def main() -> None:
    tags = os.environ.get("TAGS", "U57,U58").split(",")  # G430: "U58,U58, squeeze 10,..." (separated by ;)
    if os.environ.get("TAGS_SEP"):
        tags = os.environ["TAGS"].split(os.environ["TAGS_SEP"])
    jobs = [(t, s.strftime("%Y-%m-%d")) for t in tags for s in E.STARTS]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4")), initializer=init, initargs=(sys.argv[1],)) as ex:
        d = pd.DataFrame(list(ex.map(job, jobs, chunksize=4)))
    d.to_csv(Path(sys.argv[1]) / "g429.csv", index=False)
    for tag, g in d.groupby("tag"):
        p = g[g.outcome == "pass"]
        print(f"{tag}: starts {len(g)}, passed {len(p) / len(g):.1%}, failed {(g.outcome == 'fail').mean():.1%}, "
              f"open {(g.outcome == 'open').sum()}, median trading days to pass {p.sessions.median():.0f}, "
              f"passed within 10 days {(p.sessions <= 10).sum() / len(g):.1%}, worst drawdown ${g.dd.max():,.0f}", flush=True)


if __name__ == "__main__":
    main()
