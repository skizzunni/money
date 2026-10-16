"""The bot on real MNQ futures 5-minute bars from Yahoo Finance (the last 60 days), as a check against TradingView.

    curl -A "Mozilla/5.0" -o mnq_5m.json "https://query1.finance.yahoo.com/v8/finance/chart/MNQ=F?interval=5m&range=60d"
    python research/yahoo_forward.py mnq_5m.json [contracts] [max loss $] [first day]

Runs mnqbot.noise (the Python reference of pine/mnq_noise_momentum.pine) with its defaults and prints every
trade from the first day on, so the list can be laid next to TradingView's trade log for the same days.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnqbot.data import NY  # noqa: E402
from mnqbot.noise import NoiseConfig, run  # noqa: E402


def load(path: str) -> pd.DataFrame:
    r = json.loads(Path(path).read_text())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(NY)
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
    return df.dropna(subset=["open", "high", "low", "close"]).astype(float)


def main() -> None:
    bars = load(sys.argv[1])
    qty = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    max_loss = float(sys.argv[3]) if len(sys.argv) > 3 else 350.0
    first = pd.Timestamp(sys.argv[4] if len(sys.argv) > 4 else "2026-09-20", tz=NY)
    tf = run(bars, NoiseConfig(qty=qty, max_loss_per_trade=max_loss), minutes=5).trades_frame()
    tf = tf[tf.entry_time >= first]
    pd.set_option("display.width", 200)
    print(f"{len(bars)} bars, {bars.index[0]} to {bars.index[-1]}; {qty} MNQ, ${max_loss:,.0f} max loss")
    cols = ["entry_time", "direction", "entry", "exit_time", "exit", "reason", "pnl"]
    print(tf[cols].round({"entry": 2, "exit": 2, "pnl": 2}).to_string(index=False))
    day = tf.groupby(tf.exit_time.dt.date).pnl.sum()
    print(f"total ${tf.pnl.sum():,.2f} on {len(tf)} trades, {(tf.pnl > 0).sum()} winners; "
          f"{(day > 0).sum()} winning days of {len(day)}; worst day ${day.min():,.2f}")


if __name__ == "__main__":
    main()
