"""Multi-year study on free Nasdaq-100 1-minute data (HistData.com NSXUSD).

    python research/nsx_study.py "path/to/DAT_ASCII_NSXUSD_M1_*.csv" [--out results/nsx_study.json]

Design, fixed before looking at any results:
  * In-sample (tuning)  : 2023-01-01 .. 2024-12-31
  * Out-of-sample (test): 2025-01-01 .. end of data, run once
  * A small, pre-declared set of variants (VARIANTS below)
  * Selection rule: among variants with >= 100 in-sample trades, pick the highest
    in-sample expectancy in R. If none is positive in-sample, there is no edge to test.
  * The picked variant is judged on out-of-sample only. All variants' out-of-sample
    numbers are reported too, so nothing is hidden.

Data notes: NSXUSD is a CFD on the Nasdaq-100 cash index (bid prices), not MNQ
futures. Intraday moves are nearly identical; levels differ by the futures basis.
The file clock is New York time with daylight saving (verified: the 09:30 open,
08:30 and 10:00 data spikes sit at the same clock time in winter and summer).
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.config import BotConfig  # noqa: E402
from mnqbot.data import NY, annotate, resample  # noqa: E402
from mnqbot.engine import backtest  # noqa: E402
from mnqbot.report import summarize  # noqa: E402

IN_SAMPLE = ("2023-01-01", "2025-01-01")
OUT_OF_SAMPLE = ("2025-01-01", "2100-01-01")
MIN_TRADES = 100

# name -> StrategyConfig overrides (everything else = repo defaults)
VARIANTS = {
    "A both (defaults)": {},
    "B sweep only": {"use_orb": False},
    "C breakout retest, 5m range": {"use_sweep": False},
    "D breakout retest, 15m range": {"use_sweep": False, "or_minutes": 15},
    "E breakout retest, far-side stop": {"use_sweep": False, "or_stop_frac": 1.0},
    "F breakout close entry, 5m range": {"use_sweep": False, "orb_entry": "close"},
    "G breakout close entry, 15m range": {"use_sweep": False, "orb_entry": "close", "or_minutes": 15},
}


def load_histdata(pattern: str) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(pattern)):
        df = pd.read_csv(f, sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
        frames.append(df)
    if not frames:
        raise SystemExit(f"no files match {pattern}")
    df = pd.concat(frames).drop_duplicates("ts").sort_values("ts").set_index("ts")
    idx = df.index.tz_localize(NY, ambiguous="NaT", nonexistent="shift_forward")
    df.index = idx
    return df[~df.index.isna()].astype(float)


def run(bars: pd.DataFrame, overrides: dict) -> dict:
    cfg = BotConfig()
    for k, v in overrides.items():
        setattr(cfg.strategy, k, v)
    res = backtest(bars, cfg)
    s = summarize(res, mc_sims=2000)
    tf = res.trades_frame()
    by_year = tf.groupby(tf.trade_date.map(lambda d: d.year)).pnl.agg(["count", "sum"]) if len(tf) else None
    return {
        "trades": s["trades"].get("count", 0),
        "win_rate": s["trades"].get("win_rate"),
        "profit_factor": s["trades"].get("profit_factor"),
        "avg_r": s["trades"].get("avg_r"),
        "net": s["trades"].get("net_pnl", 0.0),
        "max_drawdown": s["risk"]["max_drawdown"],
        "worst_day": s["risk"]["worst_day"],
        "evals_sequential": s["prop_attempts_sequential"],
        "evals_monte_carlo": s["prop_monte_carlo"],
        "funnel": s["funnel"],
        "exits": s["trades"].get("exit_reasons", {}),
        "by_year": {int(y): {"trades": int(r["count"]), "net": float(r["sum"])} for y, r in by_year.iterrows()}
        if by_year is not None
        else {},
        "buy_hold_1_contract": s["benchmark_buy_hold_1_contract"]["net_pnl"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern", help="glob for the HistData DAT_ASCII_NSXUSD_M1_*.csv files")
    ap.add_argument("--out", default="results/nsx_study.json")
    args = ap.parse_args()

    raw = load_histdata(args.pattern)
    bars = annotate(resample(raw, "5min"))
    print(f"{len(raw):,} 1-minute bars -> {len(bars):,} 5-minute bars, {bars.index[0]} .. {bars.index[-1]}")

    split = {
        "in_sample": bars[(bars.index >= IN_SAMPLE[0]) & (bars.index < IN_SAMPLE[1])],
        "out_of_sample": bars[(bars.index >= OUT_OF_SAMPLE[0]) & (bars.index < OUT_OF_SAMPLE[1])],
    }
    results = {name: {k: run(b, over) for k, b in split.items()} for name, over in VARIANTS.items()}

    eligible = {n: r for n, r in results.items() if r["in_sample"]["trades"] >= MIN_TRADES}
    pick = max(eligible, key=lambda n: eligible[n]["in_sample"]["avg_r"]) if eligible else None
    edge_in_sample = pick is not None and eligible[pick]["in_sample"]["avg_r"] > 0

    def row(name, part):
        r = results[name][part]
        pf = r["profit_factor"]
        return (
            f"{name:36s} {r['trades']:5d}  {100 * (r['win_rate'] or 0):5.1f}%  "
            f"{(pf if pf is not None else 0):5.2f}  {(r['avg_r'] or 0):+6.3f}R  "
            f"{r['net']:>11,.0f}  {r['max_drawdown']:>9,.0f}  "
            f"{r['evals_sequential']['passed']:>3d}/{r['evals_sequential']['failed']:<3d}"
        )

    head = (f"{'variant':36s} {'trades':>5s}  {'win':>6s}  {'PF':>5s}  {'avg R':>7s}  "
            f"{'net $':>11s}  {'max DD':>9s}  {'evals P/F'}")
    parts = (("in_sample", "IN-SAMPLE 2023-2024 (tuning)"), ("out_of_sample", "OUT-OF-SAMPLE 2025-2026 (unseen)"))
    for part, label in parts:
        print(f"\n{label}\n{head}")
        for name in VARIANTS:
            print(row(name, part))
    print(f"\nPicked on in-sample expectancy: {pick}  (positive in-sample: {edge_in_sample})")
    if pick:
        oos = results[pick]["out_of_sample"]
        print(f"Its out-of-sample result: {oos['trades']} trades, avg {oos['avg_r']:+.3f}R, net ${oos['net']:,.0f}, "
              f"max DD ${oos['max_drawdown']:,.0f}, by year {oos['by_year']}")
        print(f"Monte Carlo eval odds out-of-sample: {oos['evals_monte_carlo']}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = {"pick": pick, "edge_in_sample": edge_in_sample, "results": results}
    out.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
