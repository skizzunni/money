"""Candidate G (docs/CANDIDATE_G.md): the daily candidate with its stop fitted to the $125 budget, by the protocol
pre-registered there.

    python research/eval_g.py dev <nq1m_scaled.pkl> <nq1m raw folder> <B sim.dll> <out folder> [family: 1 | a1]
    python research/eval_g.py holdout-nq <nq1m_scaled.pkl> <nq1m raw folder> <B sim.dll> <out folder>
    python research/eval_g.py holdout-mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <B sim.dll> <out folder>

dev: a development family (1: the six variants of section 3; a1: amendment 1, section 7) on NQ 2015-03 to 2019-12
against frozen B on the same sessions, and the selection rule's verdict. holdout-*: only the variant frozen in
verification/candidate_g/frozen.txt (written by the freeze step, after the development results and before any holdout
run), against frozen B, with every gate.
Everything else (costs, slippage, skip / FOMC / NFP dates, the evaluation replay, G1-G5) is research/eval_d.py's.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_d as ED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "verification" / "candidate_g" / "frozen.txt"
F1 = {"e1": True, "e_stop": "fvg"}
F2 = {"e1": True, "e2": True, "e_stop": "fvg"}
G_FAMILY = {f"G-{book} {fit}": {**kw, "stop_fit": fit}
            for book, kw in (("D", {}), ("F1", F1), ("F2", F2)) for fit in ("cap", "budget")}
G_AMEND1 = {f"G-{book} cap {name}": {**kw, "stop_fit": "cap", "runner_trail": trail}
            for book, kw in (("D", {}), ("F1", F1)) for name, trail in (("line", "line"), ("line+2R", "line_2r"))}
FAMILIES = {"1": G_FAMILY, "a1": G_AMEND1}
ALL = {k: v for f in FAMILIES.values() for k, v in f.items()}
PERIODS = {"dev": ("2015-03-01", "2019-12-31"), "holdout-nq": ("2020-01-01", "2025-06-30"),
           "holdout-mnq": ("2026-07-20", None)}


def participation_gates(comp: pd.DataFrame, name: str) -> list[dict]:
    """The pre-registered additions to G1-G5 (docs/CANDIDATE_G.md section 4), from comparison.csv."""
    c2, c3 = (comp[(comp.candidate == name) & (comp.slippage == s)].iloc[0] for s in (2, 3))
    b2 = comp[(comp.candidate == "B") & (comp.slippage == 2)].iloc[0]
    shares = [float(x) for x in c2["sessions with 0/1/2/3 entries %"].split(" / ")]
    two_plus = 100 - shares[0] - shares[1]
    rows = [("P1", "campaigns per eligible session (2 ticks)", ">= 2.0", c2["trades / eligible session"],
             c2["trades / eligible session"] >= 2.0),
            ("P2", "sessions with 2 or 3 campaigns (2 ticks)", ">= 50%", two_plus, two_plus >= 50),
            ("C1", "net at 3 ticks", "> $0", c3["net $"], c3["net $"] > 0),
            ("C2", "net / intraday DD at 2 ticks, against frozen B's", f">= {b2['net / intraday DD']:.2f}",
             c2["net / intraday DD"], c2["net / intraday DD"] >= b2["net / intraday DD"])]
    return [{"candidate": name, "gate": g, "measure": m, "threshold": t, "result": v,
             "verdict": "PASS" if ok else "FAIL"} for g, m, t, v, ok in rows]


def select(comp: pd.DataFrame, family: dict) -> str | None:
    """The development selection rule (docs/CANDIDATE_G.md section 3): among the variants with P1 and C1, the highest
    net / intraday DD at 2 ticks; none: None."""
    ok = []
    for name in family:
        g = {r["gate"]: r["verdict"] for r in participation_gates(comp, name)}
        if g["P1"] == "PASS" and g["C1"] == "PASS":
            ratio = comp[(comp.candidate == name) & (comp.slippage == 2)].iloc[0]["net / intraday DD"]
            ok.append((ratio, name))
    return max(ok)[1] if ok else None


def main() -> None:
    period, a1, a2, dll, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5])
    first, last = PERIODS[period]
    if period == "dev":
        candidates = FAMILIES[sys.argv[6] if len(sys.argv) > 6 else "1"]
        bars = ED.nq_bars(a1, a2, first=first, last=last)
    else:
        if not FROZEN.exists():
            raise SystemExit("no frozen variant: the holdout is run only after the freeze step")
        name = FROZEN.read_text().split()[0]
        candidates = {name: ALL[name]}
        bars = ED.nq_bars(a1, a2, first=first, last=last) if period == "holdout-nq" else ED.mnq_series(a1, a2)
    ED.evaluate(period, bars, dll, pd.Timestamp(first), candidates, (), out)
    comp = pd.read_csv(out / "comparison.csv")
    rows = [r for name in candidates for r in participation_gates(comp, name)]
    pd.DataFrame(rows).to_csv(out / "gates_g.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    if period == "dev":
        pick = select(comp, candidates)
        (out / "selection.txt").write_text(f"{pick}\n" if pick else "none\n")
        print("selected:", pick)


if __name__ == "__main__":
    main()
