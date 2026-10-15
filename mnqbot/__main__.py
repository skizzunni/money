"""Command line: python -m mnqbot {backtest,setups,fetch,config} ..."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import BotConfig
from .data import annotate, fetch_yfinance, load_csv, resample
from .engine import backtest
from .report import format_report, summarize
from .strategy import scan


def _load_bars(args):
    bars = load_csv(args.csv, tz=args.tz)
    if args.resample:
        bars = resample(bars, args.resample)
    if args.start:
        bars = bars[bars.index >= args.start]
    if args.end:
        bars = bars[bars.index < args.end]
    if bars.empty:
        sys.exit("no bars left after filtering")
    return annotate(bars)


def _load_config(path: str | None) -> BotConfig:
    return BotConfig.load(path) if path else BotConfig()


def cmd_backtest(args) -> None:
    cfg = _load_config(args.config)
    bars = _load_bars(args)
    res = backtest(bars, cfg)
    summary = summarize(res, mc_sims=args.mc, mc_sessions=args.mc_sessions)
    print(format_report(summary))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res.trades_frame().to_csv(out / "trades.csv", index=False)
    res.daily.to_csv(out / "daily.csv")
    res.equity.to_csv(out / "equity.csv")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote trades.csv, daily.csv, equity.csv, summary.json to {out}/")


def cmd_setups(args) -> None:
    cfg = _load_config(args.config)
    bars = _load_bars(args)
    setups = scan(bars, cfg.strategy, cfg.instrument)
    for s in setups:
        side = "LONG " if s.direction > 0 else "SHORT"
        print(
            f"{bars.index[s.bar]}  {side} swept {s.level_name} {s.level_price:.2f}  "
            f"entry {s.entry:.2f} stop {s.stop:.2f} target {s.target:.2f} ({s.risk_points:.2f} pts risk)"
        )
    print(f"{len(setups)} setups")


def cmd_fetch(args) -> None:
    df = fetch_yfinance(args.symbol, args.interval, args.period)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index_label="time")
    print(f"saved {len(df)} bars to {args.out}")


def cmd_config(args) -> None:
    print(json.dumps(BotConfig().to_dict(), indent=2))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="mnqbot", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def data_args(p):
        p.add_argument("csv", help="bar CSV (TradingView export, NinjaTrader export, or `mnqbot fetch` output)")
        p.add_argument("--config", help="JSON settings file (see `mnqbot config`)")
        p.add_argument("--resample", help="aggregate bars first, e.g. 5min")
        p.add_argument("--start", help="first date to include, e.g. 2026-01-01")
        p.add_argument("--end", help="stop before this date")
        p.add_argument("--tz", default="America/New_York", help="timezone for naive timestamps")

    p = sub.add_parser("backtest", help="run the bot over historical bars")
    data_args(p)
    p.add_argument("--out", default="results", help="folder for trades/daily/equity CSVs")
    p.add_argument("--mc", type=int, default=5000, help="Monte Carlo eval simulations (0 = off)")
    p.add_argument("--mc-sessions", type=int, default=60, help="sessions allowed per simulated eval")
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("setups", help="list every setup the strategy sees, ignoring risk rails")
    data_args(p)
    p.set_defaults(func=cmd_setups)

    p = sub.add_parser("fetch", help="download recent bars from Yahoo Finance (pip install yfinance)")
    p.add_argument("--symbol", default="MNQ=F")
    p.add_argument("--interval", default="5m")
    p.add_argument("--period", default="59d")
    p.add_argument("--out", default="data/mnq_5m.csv")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("config", help="print default settings as JSON")
    p.set_defaults(func=cmd_config)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
