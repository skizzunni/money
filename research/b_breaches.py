"""Frozen B's evaluation breaches, trade by trade (docs/B_BREACHES.md).

    python research/b_breaches.py mnq <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>
    python research/b_breaches.py nq <nq1m_scaled.pkl> <sim.dll> <out folder>     (supplementary, NQ priced as MNQ)

The simulator's frozen B (4 MNQ / $200, 1 tick, $0.95 a side; reconciled with native NinjaTrader, docs/B_NATIVE.md),
replayed through research/eval_sim.py's rules on the worst-mix path. For every fully observed start: the outcome; for
each failed one, the trades from the start to the breach, with the account's equity and its highest equity (open
profit included) after each. The fall from the highest equity to the breach is split into:
- give-back: open profit reached in the trade that set the highest equity and not kept at its exit;
- the losing trades closed after it, and the open loss of the trade in which the breach came;
- the winning trades closed after it (they reduce the fall).
The trade that set the highest equity is also measured in noise units (its best open profit in points over the day's
noise in points, from its take-profit: 1.5 noise units from the fill), and each loser by its minutes in the trade.
Starts that breach in the same trade are one episode.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_sim as E  # noqa: E402
import runner_compare as RC  # noqa: E402

ENTRY = re.compile(r"(?:BUY|SELL) \d+ MNQ .*? at market\. Price ([\d.]+)\..*?take-profit ([\d.]+)")
PROPS = {"UseBreakout": False, "EvalQty": 4, "EvalMaxLoss": 200, "SimSlippageTicks": 1, "SimCommissionPerSide": E.FEE,
         "Diagnostics": True}
OFFSETS = {pd.Timedelta(hours=h, minutes=m) for h in range(3, 8) for m in (0, 1)}


def run(dll, csv, extra, when):
    """Trades, each with its noise unit in points (from the take-profit the strategy printed when it sent the entry)."""
    args = [f"{k}={v}" for k, v in {**PROPS, **extra}.items()]
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "1", *args], capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    lines = r.stdout.splitlines()
    t = [x.split(",")[1:] for x in lines if x.startswith("T,")]
    n = [x.split(",")[1:] for x in lines if x.startswith("TN,")]
    tps = [ENTRY.search(x) for x in lines if x.startswith("P,") and " at market. Price " in x]
    tr = pd.DataFrame([{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]),
                        "why": a[5], "pnl": float(a[6]), "q": int(b[1])} for a, b in zip(t, n, strict=True)])
    # Each entry line is stamped with its signal bar's time (the stand-in's clock is a fixed number of hours from the
    # bar file's); a line whose order never became a trade (none on MNQ, a few on NQ) is passed over.
    stamp = [pd.Timestamp(x[2:].split("  ", 1)[0]) for x in lines if x.startswith("P,") and " at market. Price " in x]
    noise, k = [], 0
    for eb in tr.eb:
        sig = when[int(eb) - 1]
        while k < len(tps) and (stamp[k] - sig) not in OFFSETS:
            k += 1
        if k == len(tps):
            raise RuntimeError(f"no entry line for the trade entered at bar {eb}")
        noise.append(abs(float(tps[k].group(2)) - float(tps[k].group(1))) / 1.5)
        k += 1
    tr["noise pts"] = noise
    return tr


def trace(trs, start_bar, end_bar, path="worst mix"):
    """eval_sim.evaluate_detail's arithmetic, logging each trade: (index, best equity in it, equity after, highest
    equity after, "pass" / "fail" / "")."""
    e = peak = 0.0
    log = []
    for ti, (eb, _xb, d, q, en, ex, kind, pnl, bo, bh, bl) in enumerate(trs):
        if eb < start_bar:
            continue
        if eb >= end_bar:
            break
        mult = q * 2.0
        tgt = E.TARGET + E.BUFFER + 0.25 * mult
        base = e - E.FEE * q
        best = -np.inf
        for k in range(len(bo)):
            last = k == len(bo) - 1
            prices = ([en] if k == 0 else []) + E._bar_points(d, bo[k], bh[k], bl[k], k == 0, last, kind,
                                                              E._order(path, kind if last else None)) + (
                [ex] if last else [])
            for px in prices:
                eq = base + d * (px - en) * mult
                best = max(best, eq)
                if eq >= tgt:
                    return log + [(ti, best, eq, peak, "pass")]
                peak = max(peak, eq)
                if eq <= peak - E.TRAIL:
                    return log + [(ti, best, eq, peak, "fail")]
        e += pnl
        peak = max(peak, e)
        res = "pass" if e >= E.TARGET else ("fail" if e <= peak - E.TRAIL else "")
        log.append((ti, max(best, e), e, peak, res))
        if res:
            return log
    return log


def analyse(mk, dll, extra):
    tmp = Path(tempfile.mkdtemp()) / "bars.csv"
    K.write_bars(mk.bars, tmp)
    tr = run(dll, tmp, extra, mk.t).sort_values("eb").reset_index(drop=True)
    trs = E.marks(tr, mk.o, mk.h, mk.lo, 1)
    rows, seq = [], []
    for s in range(mk.first_ok, len(mk.sessions)):
        d0 = mk.sessions[s]
        end_day = d0 + pd.Timedelta(days=E.DAYS)
        if end_day > mk.last + pd.Timedelta(days=1):
            break
        log = trace(trs, int(np.searchsorted(mk.bar_day, d0)), int(np.searchsorted(mk.bar_day, end_day)))
        outcome = log[-1][4] if log and log[-1][4] else "expired"
        row = {"start": d0.date(), "outcome": outcome, "trades": len(log)}
        if outcome == "fail":
            pi = max(range(len(log)), key=lambda i: log[i][3])
            before = log[pi - 1][2] if pi else 0.0
            ti, best, after, peak, _ = log[pi]
            pt = tr.iloc[ti]
            later = [tr.iloc[x[0]] for x in log[pi + 1:-1]]
            losers = [t for t in later if t.pnl < 0]
            last_eq = log[-1][2] - log[-2][2] if len(log) > 1 else log[-1][2]
            row.update({
                "breach trade": tr.iloc[log[-1][0]].eb, "highest equity $": peak,
                "fall $": peak - log[-1][2],
                "give-back $": peak - after if pi < len(log) - 1 else 0.0,
                "peak trade: best open profit $": peak - before, "peak trade: kept $": after - before,
                "peak trade: best, noise units": (peak - before + 2 * E.FEE * pt.q) / (pt.q * 2) / pt["noise pts"],
                "losers after $": sum(t.pnl for t in losers), "losers after": len(losers),
                "losers within 1 minute": sum(int(t.xb - t.eb <= 1) for t in losers),
                "winners after $": sum(t.pnl for t in later if t.pnl > 0), "breach trade open loss $": last_eq,
                "noise pts at the losers (median)": float(np.median([t["noise pts"] for t in losers]))
                if losers else np.nan})
            for i, (tj, b, eq, pk, res) in enumerate(log):
                t = tr.iloc[tj]
                seq.append({"start": d0.date(), "n": i + 1, "entry": mk.t[int(t.eb)].strftime("%Y-%m-%d %H:%M"),
                            "dir": int(t.d), "exit kind": t.why, "minutes": int(t.xb - t.eb),
                            "net $": round(t.pnl, 2) if not res else None, "noise pts": round(t["noise pts"], 2),
                            "best equity in trade $": round(b, 2), "equity after $": round(eq, 2),
                            "highest equity so far $": round(pk, 2),
                            "phase": "before the peak" if i < pi else ("sets the peak" if i == pi else
                                                                       "after the peak"), "result": res})
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(seq)


def summary(df):
    f = df[df.outcome == "fail"]
    out = {"fully observed starts": len(df), "pass": int((df.outcome == "pass").sum()), "fail": len(f),
           "expired": int((df.outcome == "expired").sum())}
    if len(f):
        fall = f["fall $"].sum()
        units = f["peak trade: best, noise units"]
        out.update({
            "episodes (distinct breach trades)": f["breach trade"].nunique(),
            "fall: give-back %": 100 * f["give-back $"].sum() / fall,
            "fall: losers after the peak %": 100 * -f["losers after $"].sum() / fall,
            "fall: the breach trade's open loss %": 100 * -f["breach trade open loss $"].sum() / fall,
            "fall: winners after the peak %": -100 * f["winners after $"].sum() / fall,
            "peak trade best, noise units: median / share >= 1.0": f"{units.median():.2f} / {(units >= 1).mean():.0%}",
            "losers after the peak within 1 minute %": 100 * f["losers within 1 minute"].sum()
                                                       / f["losers after"].sum(),
        })
    return out


def main():
    kind = sys.argv[1]
    if kind == "mnq":
        mk, dll, out = RC.mnq_market(sys.argv[2], sys.argv[3]), sys.argv[4], Path(sys.argv[5])
        extra = {}
    else:
        mk, dll, out = RC.nq_market(sys.argv[2], "2015-03-01", "2025-06-30"), sys.argv[3], Path(sys.argv[4])
        extra = {"SkipDates": mk.skip_dates}
    out.mkdir(parents=True, exist_ok=True)
    df, seq = analyse(mk, dll, extra)
    df.to_csv(out / "outcomes_by_start.csv", index=False)
    seq.to_csv(out / "breach_sequences.csv", index=False)
    for k, v in summary(df).items():
        print(f"{k}: {v:.1f}" if isinstance(v, float) else f"{k}: {v}")


if __name__ == "__main__":
    main()
