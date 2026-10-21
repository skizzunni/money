"""The daily opportunity audit (docs/DAILY_AUDIT.md): MnqCandidateD.cs's refusal lines on the NinjaTrader stand-in match
the Python model's audit records on the user's MNQ bars, positions are unchanged by the audit, and every qualified
setup of the daily table has exactly one outcome."""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import pandas as pd
from test_candidate_d import P, mnq, needs_dotnet  # noqa: F401
from test_ninjatrader import sim  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import controlled as K  # noqa: E402
import daily_audit as A  # noqa: E402

COMPARED = {"unaffordable", "not qualified: room", "not qualified: decision window", "blocked: position",
            "blocked: pending order", "blocked: daily entry budget exhausted", "blocked: after the entry window"}


@needs_dotnet
def test_ninjascript_refusals_match_the_python_audit(sim, mnq, tmp_path):  # noqa: F811
    csv = tmp_path / "bars.csv"
    K.write_bars(mnq, csv)
    kw = P.CONFIGS["D+F2"]
    nt, out = P.nt_positions(sim, csv, kw, 125.0)
    py, m = P.py_positions(mnq, kw, 125.0)
    assert len(nt) == len(py) and (nt.astype(str).values == py.astype(str).values).all()
    ntr = collections.Counter(tuple(x.split(",")[3:6:2]) for x in out.splitlines() if x.startswith("P,D refusal,"))
    pyr = collections.Counter((s, o) for _, s, _, o in m.audit if s in ("noise", "sweep") and o in COMPARED)
    pyr.update((s, o) for _, s, _, o in m.audit if s == "williams" and o == "unaffordable")
    assert ntr == pyr and sum(ntr.values()) > 100


def test_every_qualified_setup_has_one_outcome(mnq):  # noqa: F811
    """qualified = entered + limits placed + every refusal, session by session."""
    import eval_d as ED

    from mnqbot.candidate_d import DConfig
    bars = mnq.assign(scale=1.0)
    cfg = DConfig(skip_dates=frozenset(K.DEFAULT_SKIP.split(",")), fed_dates=ED.FOMC, nfp_dates=ED.NFP,
                  **ED.F_CANDIDATES["D+F2"])
    m, warm = A.run_with_snapshots(bars, cfg)
    t = A.daily_table(bars, m, warm, frozenset(K.DEFAULT_SKIP.split(",")), frozenset(), ED.FOMC, ED.NFP, "2026-07-20")
    au = pd.DataFrame(m.audit, columns=["bar", "sleeve", "d", "outcome"])
    entered = int((au.outcome == "entered").sum())
    refusals = sum(int(t[c].sum()) for c in A.REASONS[:-1])
    assert int(t.qualified.sum()) == entered + int(t["limits placed"].sum()) + refusals
    assert t.campaigns.sum() == len(m.campaigns)
