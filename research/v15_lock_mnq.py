"""The user's Pine v1.5 (pine/reference/mnq_noise_momentum_v1.5_user.pine) on the user's MNQ bars at 10 MNQ and $350,
for lock triggers 1.0 (the default), 0.85 and 0.75, on 5-minute bars (the user's TradingView chart) and 1-minute bars
(the broker's auto-breakeven view).

    python research/v15_lock_mnq.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>

The script's own costs ($0.62 a side, 1 tick) and, beside them, $0.95 and 2 ticks. Bars: research/mnq_bars.py's traded
contracts, 09:30-16:00.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402
from pine_interpreter import PineRuntime, load_pine  # noqa: E402

from mnqbot.data import resample  # noqa: E402

PINE = ROOT / "pine" / "reference" / "mnq_noise_momentum_v1.5_user.pine"


def run(bars, minutes, lock, fee, slip):
    src = Path(tempfile.mkdtemp()) / "v15.pine"
    src.write_text(PINE.read_text(newline=""), newline="\n")
    rt = PineRuntime(load_pine(src), bars, {"Lock a small win: trigger, in max losses (0 = off)": lock},
                     timeframe_seconds=60 * minutes, commission=fee, slippage_ticks=slip)
    rt.run()
    t = pd.DataFrame(rt.strategy.closed)
    t["day"] = bars.index[t.entry_bar].strftime("%Y-%m-%d")
    eq = t.pnl.cumsum()
    return {"bars": f"{minutes} min", "lock": lock, "costs": f"${fee} / {slip}t", "trades": len(t),
            "winners": int((t.pnl > 0).sum()), "win %": round(100 * (t.pnl > 0).mean(), 1),
            "net $": round(t.pnl.sum(), 2), "max DD $ (closed trades)": round((eq.cummax() - eq).max(), 2),
            "profit factor": round(t.pnl[t.pnl > 0].sum() / -t.pnl[t.pnl < 0].sum(), 2),
            "winning days": f"{int((t.groupby('day').pnl.sum() > 0).sum())} / {t.day.nunique()}"}


def main() -> None:
    series, _ = M.traded_series(M.load(sys.argv[1]), M.load(sys.argv[2]))
    one = K.rth(series)
    one = one.assign(volume=one.get("volume", 0))
    five = resample(one, "5min")
    rows = [run(b, m, lock, fee, slip) for m, b in ((5, five), (1, one)) for lock in (1.0, 0.85, 0.75)
            for fee, slip in ((0.62, 1), (0.95, 2))]
    pd.set_option("display.width", 250)
    print(f"{one.index[0].date()} .. {one.index[-1].date()}")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
