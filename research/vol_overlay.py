"""Volatility-scaled contracts on a trade list from research/ratio_study.py (Zarattini, Aziz & Barbon 2024 size their
position by target volatility over the last 14 days' volatility; this is the same idea in contracts).

    python research/vol_overlay.py <ratio_study out folder> <bars pkl kind=path ...>

Rule, fixed before any result: q_t = clip(round(4 x median(sigma over the previous 252 sessions) / sigma_t), 1, 8),
sigma_t = the mean |16:00 close / 09:30 open - 1| over the previous 14 sessions (today excluded; open to close, so no
overnight, roll or month-rescaling jump enters it). Every rule of the strategy in points is unchanged (the 25-point
max loss stays 25 points, $50 a contract), so a trade of q contracts makes q / 4 of the 4-contract trade, costs
included: the scaled P/L is exact, not an approximation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import eval_d as ED  # noqa: E402
import ratio_study as R  # noqa: E402


def sizes(rth: pd.DataFrame) -> pd.Series:
    day = rth.index.tz_localize(None).normalize()
    g = rth.groupby(day)
    oc = (g.close.last() / g.open.first() - 1).abs()
    sig = oc.rolling(14).mean().shift(1)
    ref = sig.rolling(252, min_periods=60).median()
    return (4 * ref / sig).round().clip(1, 8)


def main() -> None:
    folder = Path(sys.argv[1])
    paths = dict(a.split("=", 1) for a in sys.argv[2:])
    rows = []
    for kind, path in paths.items():
        bars = ED.mnq_series(*path.split(",")) if kind == "mnq" else ED.nq_bars(path, paths.get("raw", ""))
        if kind == "raw":
            continue
        rth = K.rth(bars[["open", "high", "low", "close"]])
        q = sizes(rth)
        for f in sorted(folder.glob(f"trades_{kind}_*_[23]t.csv")):
            tr = pd.read_csv(f, parse_dates=["day"])
            k = q.reindex(tr.day).fillna(4).to_numpy() / 4.0
            scaled = tr.assign(pnl=tr.pnl * k, q=(tr.q * k).round().astype(int))
            tag = f.stem.replace("trades_", "")
            for label, t in (("fixed 4", tr), ("vol-scaled", scaled)):
                rows.append({"run": tag, "sizing": label, "period": "all", **R.summary(t, rth)})
                for name, a, b in R.HALVES[kind]:
                    part = t[(t.day >= pd.Timestamp(a)) & (t.day < pd.Timestamp(b))]
                    rows.append({"run": tag, "sizing": label, "period": name, **R.summary(part, rth)})
            print(tag, "mean contracts", round(float(4 * k.mean()), 2))
    res = pd.DataFrame(rows)
    res.to_csv(folder / "vol_overlay.csv", index=False)
    pd.set_option("display.width", 250)
    print(res[["run", "sizing", "period", "trades", "net $", "gross profit $", "intraday DD $", "net / intraday DD",
               "gross profit / intraday DD", "profit factor"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
