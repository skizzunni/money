"""Candidates D / E: the NinjaScript strategy on the stand-in against the Python model, position by position.

    python research/d_parity.py <bars.pkl> <sim.dll> [budget ...]

Both on the same bars (full electronic session), $0.95 a side, 2 ticks, the strategy's default date lists, NFP dates
from research/nfp_dates.csv. Configurations: D, D + E1, D + E2, at each budget given (default 125). Prints, per
configuration, the positions on each side and the first differences.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controlled as K  # noqa: E402

from mnqbot.candidate_d import DConfig, run  # noqa: E402
from mnqbot.noise import FED_DATES, SKIP_DATES  # noqa: E402

NFP = ",".join(pd.read_csv(Path(__file__).with_name("nfp_dates.csv")).date)
CONFIGS = {"D": {}, "D+E1": {"e1": True}, "D+E2": {"e1": True, "e2": True},
           "E only (code coverage)": {"noise": False, "williams": False, "e1": True, "e2": True}}
COLS = ["sleeve", "d", "kind", "signal_bar", "entry_bar", "exit_bar", "runner_fill", "runner_exit", "runner_why",
        "half_fill", "half_exit", "half_why", "stop0", "r", "planned", "pnl"]


def nt_positions(dll, csv, cfg_kw, budget, slip=2, extra=()):
    props = {"UseNoise": cfg_kw.get("noise", True), "UseWilliams": cfg_kw.get("williams", True), "UseE1": bool(cfg_kw.get("e1")), "UseE2": bool(cfg_kw.get("e2")),
             "RiskBudget": budget, "SimSlippageTicks": slip, "SimCommissionPerSide": 0.95, "SimExitExecutions": True,
             "EvalTarget": 0, "EvalTrail": 0, "NfpDates": NFP, **dict(extra)}
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "1", "Strategy=D", *[f"{k}={v}" for k, v in props.items()]],
                       capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:])
    rows = [x[2:].split(",")[1:] for x in r.stdout.splitlines() if x.startswith("P,D position,")]
    out = []
    for a in rows:
        out.append({"sleeve": a[0], "d": int(a[1]), "kind": a[2], "signal_bar": int(a[3]), "entry_bar": int(a[4]),
                    "exit_bar": int(a[5]), "runner_fill": a[6], "runner_exit": a[7], "runner_why": a[8],
                    "half_fill": a[9], "half_exit": a[10], "half_why": a[11], "stop0": a[12], "r": a[13],
                    "planned": a[14], "pnl": a[15]})
    return pd.DataFrame(out, columns=COLS), r.stdout


def f2(x):
    return "-" if x != x else f"{x:.2f}"


def py_positions(bars, cfg_kw, budget, slip=2):
    cfg = DConfig(budget=budget, slippage_ticks=slip, skip_dates=frozenset(SKIP_DATES.split(",")),
                  fed_dates=frozenset(FED_DATES.split(",")), nfp_dates=frozenset(NFP.split(",")), **cfg_kw)
    m = run(bars, cfg)
    out = []
    for c in m.campaigns:
        lots = {lt.name: lt for lt in c.lots}
        ru, ha = lots.get("runner"), lots.get("half")
        out.append({"sleeve": c.sleeve, "d": c.d, "kind": c.kind, "signal_bar": c.signal_bar,
                    "entry_bar": min(lt.fill_bar for lt in c.lots), "exit_bar": max(lt.exit_bar for lt in c.lots),
                    "runner_fill": f2(ru.fill) if ru else "-", "runner_exit": f2(ru.exit) if ru else "-",
                    "runner_why": ru.why if ru else "", "half_fill": f2(ha.fill) if ha else "-",
                    "half_exit": f2(ha.exit) if ha else "-", "half_why": ha.why if ha else "", "stop0": f2(c.stop0),
                    "r": f2(c.r), "planned": f2(c.planned), "pnl": f2(c.pnl)})
    return pd.DataFrame(out, columns=COLS), m


def compare(bars, dll, budgets=(125.0,), slip=2):
    csv = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(bars, csv)
    result = {}
    for budget in budgets:
        for name, kw in CONFIGS.items():
            nt, _ = nt_positions(dll, csv, kw, budget, slip)
            py, _ = py_positions(bars, kw, budget, slip)
            same = len(nt) == len(py) and (nt.astype(str).values == py.astype(str).values).all()
            result[(name, budget)] = (nt, py, same)
    return result


def main():
    bars = pd.read_pickle(sys.argv[1])
    dll = sys.argv[2]
    budgets = tuple(float(x) for x in sys.argv[3:]) or (125.0,)
    for (name, budget), (nt, py, same) in compare(bars, dll, budgets).items():
        print(f"{name} budget {budget:g}: NinjaScript {len(nt)} positions, Python {len(py)}; identical: {same}; "
              f"sleeves {py.sleeve.value_counts().to_dict()}")
        if not same:
            n = min(len(nt), len(py))
            for k in range(n):
                a, b = nt.iloc[k].astype(str), py.iloc[k].astype(str)
                if (a != b).any():
                    print("   first difference at position", k)
                    print(pd.DataFrame({"NinjaScript": a, "Python": b})[a != b].to_string())
                    break


if __name__ == "__main__":
    main()
