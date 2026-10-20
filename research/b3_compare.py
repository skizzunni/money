"""Frozen B against candidate B3 (the noise lock), as pre-registered in docs/B_BREACHES.md section 2.

    python research/b3_compare.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <B sim.dll> <B3 sim.dll> <out folder>
    python research/b3_compare.py nq <nq1m_scaled.pkl> <B sim.dll> <B3 sim.dll> <out folder>    (supplementary)

B: the frozen files' simulator. B3: the simulator built from a copy with verification/candidate_b3.patch applied, run
with NoiseLockAt 1.0 / NoiseLockKeep 0.5 (with NoiseLockAt 0 it reproduces B trade for trade). Complete reruns, same
bars, warm-up, settings and costs ($0.95 a side; 1 and 2 ticks). Per arm: the continuous statistics over the eligible
sessions (research/candidate_c.stats), by part (MNQ: 7/20-8/31 and 9/1-10/16; NQ: years) the net and the net over
the intraday drawdown, and the evaluation replay from every start (research/eval_sim.py), paired start by start. The
trades whose result changed are listed with both arms' P/L.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_c as CC  # noqa: E402
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import runner_compare as RC  # noqa: E402

ARMS = {"B": {}, "B3": {"NoiseLockAt": 1.0, "NoiseLockKeep": 0.5}}
LATER = pd.Timestamp("2026-09-01")


def part_stats(tr, mk, slip, label, mask):
    sub = tr[mask].reset_index(drop=True)
    trs = E.marks(sub, mk.o, mk.h, mk.lo, slip)
    dd = CC.intraday_dd(trs, 0, mk.day_of) if len(sub) else 0.0
    return {"part": label, "trades": len(sub), "net $": round(sub.pnl.sum(), 2), "intraday DD $": round(dd, 2),
            "net / intraday DD": sub.pnl.sum() / dd if dd else np.nan}


def main():
    kind = sys.argv[1]
    if kind == "mnq":
        mk = RC.mnq_market(sys.argv[2], sys.argv[3])
        dlls, out = {"B": sys.argv[4], "B3": sys.argv[5]}, Path(sys.argv[6])
    else:
        mk = RC.nq_market(sys.argv[2], "2015-03-01", "2025-06-30")
        dlls, out = {"B": sys.argv[3], "B3": sys.argv[4]}, Path(sys.argv[5])
    out.mkdir(parents=True, exist_ok=True)
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(mk.bars, csv)
    extra = {"SkipDates": mk.skip_dates} if mk.skip_dates else {}
    skip = set(pd.to_datetime((mk.skip_dates or K.DEFAULT_SKIP).split(",")))
    opens = pd.DatetimeIndex(sorted(set(mk.bar_day[(mk.t.hour == 9) & (mk.t.minute == 30)])))
    eligible = pd.DatetimeIndex([d for d in opens if d >= mk.sessions[mk.first_ok] and d not in skip])
    rows, parts, wins, trades = [], [], {}, {}
    for slip in (1, 2):
        for arm, props in ARMS.items():
            tr = K.run(dlls[arm], csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=E.FEE,
                       **extra, **props)
            s, tr = CC.stats(tr, mk, eligible, slip)
            trades[(arm, slip)] = tr
            tr.to_csv(out / f"trades_{arm}_{slip}t.csv", index=False)
            day = mk.bar_day[tr.eb.to_numpy(dtype=int)]
            labels = ([("7/20-8/31", day < LATER), ("9/1-10/16", day >= LATER)] if kind == "mnq" else
                      [(str(y), day.year == y) for y in sorted(set(day.year))])
            for label, mask in [("all", np.ones(len(tr), bool)), *labels]:
                parts.append({"arm": arm, "slippage": slip, **part_stats(tr, mk, slip, label, np.asarray(mask))})
            trs = E.marks(tr, mk.o, mk.h, mk.lo, slip)
            w = E.run_windows(trs, mk.sessions, mk.first_ok, mk.day_of, mk.bar_day)
            wins[(arm, slip)] = w.set_index("start")
            fo = w[w["fully observed"]]
            sm = E.summarize(fo, "")
            rows.append({"arm": arm, "slippage": slip, **{k: s[k] for k in (
                "eligible sessions", "trades", "trades / session", "net $", "profit factor", "win %", "avg win",
                "avg loss", "intraday DD $", "losing streak", "worst day $")},
                "net / intraday DD": s["net $"] / s["intraday DD $"],
                "eval full starts": len(fo), "pass": sm["pass"], "fail": sm["fail"], "expired": sm["expired"],
                "path-dependent": sm["outcome depends on path"], "pass %": sm["pass %"], "fail %": sm["fail %"],
                "median days to pass": sm["median days to pass"]})
    res = pd.DataFrame(rows)
    res.to_csv(out / "comparison.csv", index=False)
    pt = pd.DataFrame(parts)
    pt.to_csv(out / "by_part.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(res.round(2).T.to_string())
    print(pt.pivot_table(index=["part"], columns=["slippage", "arm"], values=["net $", "net / intraday DD"])
          .round(2).to_string())
    for slip in (1, 2):
        a, b = wins[("B", slip)], wins[("B3", slip)]
        full = a["fully observed"]
        pair = pd.DataFrame({"B": a.outcome[full], "B3": b.outcome[full]})
        pair.to_csv(out / f"paired_starts_{slip}t.csv")
        print(f"\nslippage {slip}: paired fully observed starts (B -> B3)")
        print(pd.crosstab(pair.B, pair.B3).to_string())
        if kind == "mnq":
            later = pair[pd.to_datetime(pair.index) >= LATER]
            print(f"later starts ({len(later)}): B {later.B.value_counts().to_dict()}, "
                  f"B3 {later.B3.value_counts().to_dict()}")
        x, y = trades[("B", slip)], trades[("B3", slip)]
        m = x.merge(y, on=["eb", "d"], how="outer", suffixes=("_B", "_B3"), indicator=True)
        both = m[m._merge == "both"]
        ch = both[(both.pnl_B - both.pnl_B3).abs() > 1e-9]
        lost, gained = ch[ch.pnl_B3 < ch.pnl_B], ch[ch.pnl_B3 > ch.pnl_B]
        only_b, only_b3 = m[m._merge == "left_only"], m[m._merge == "right_only"]
        print(f"changed trades {len(ch)}: winners sacrificed (B3 made less) {len(lost)}, "
              f"${(lost.pnl_B3 - lost.pnl_B).sum():,.2f} (B made ${lost.pnl_B.sum():,.2f} on them, B3 "
              f"${lost.pnl_B3.sum():,.2f}); B3 made more {len(gained)}, +${(gained.pnl_B3 - gained.pnl_B).sum():,.2f}; "
              f"knock-on: B only {len(only_b)} ${only_b.pnl_B.sum():,.2f}, B3 only {len(only_b3)} "
              f"${only_b3.pnl_B3.sum():,.2f}")
        ch.assign(entry=mk.t[ch.eb.to_numpy(dtype=int)]).to_csv(out / f"changed_trades_{slip}t.csv", index=False)
        pd.concat([only_b.assign(arm="B only"), only_b3.assign(arm="B3 only")]).assign(
            entry=lambda d: mk.t[d.eb.to_numpy(dtype=int)]).to_csv(out / f"knock_on_{slip}t.csv", index=False)


if __name__ == "__main__":
    main()
