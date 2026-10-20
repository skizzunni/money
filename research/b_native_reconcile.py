"""Frozen B: the user's native NinjaTrader runs against the stand-in, trade by trade, 6/29 to 10/16 (docs/B_NATIVE.md).

    python research/b_native_reconcile.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> [<out folder>]

Native: B_L0 / B_L1 / B_L2 (verification/native_long/*_trades_from_output.csv, rebuilt from the runs' own fills):
MNQ DEC26 only, Start 1/1/2026, data from 5/3, engine ready 5/21, the 5/22-6/26 hole, so trading from 6/29.
Stand-in: the same two files on the traded-contract series (research/mnq_bars.traded_series: 09-26 to the 9/10
session, back-adjusted, then 12-26), warm-up 6/29-7/17, as in every MNQ evaluation result. The two do not run on the
same bars before 10/1, so each trade is put in one period:
- 6/29-7/17: native trades, the stand-in still warming up (its first 14 full sessions);
- 7/20-9/10: different contracts (native DEC26, the deferred contract; stand-in 09-26, the one an account trades);
- 9/11-9/30: the same 12-26 bars, but the 14-session noise average still holds 09-26 sessions in the stand-in;
- 10/1-10/16: the same bars and the same noise history (the identical-bars check, docs/MNQ_NATIVE.md test 1).
Matched by entry minute (NinjaTrader stamps a fill with its bar's end), direction and contracts.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PERIODS = [("6/29-7/17 stand-in warming up", "2026-06-29", "2026-07-17"),
           ("7/20-9/10 different contracts", "2026-07-20", "2026-09-10"),
           ("9/11-9/30 same bars, mixed noise history", "2026-09-11", "2026-09-30"),
           ("10/1-10/16 identical bars and history", "2026-10-01", "2026-10-16")]


def period(t):
    d = t.normalize()
    for name, a, b in PERIODS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b):
            return name
    return "other"


def stand_in(sep, dec, dll, slip):
    series, _ = M.traded_series(sep, dec)
    bars = K.rth(series)
    csv = Path(tempfile.mkdtemp()) / "b.csv"
    K.write_bars(bars, csv)
    st = K.run(dll, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=0.95)
    start = bars.index
    return st.assign(entry_time=(start[st.eb.to_numpy()] + pd.Timedelta(minutes=1)).tz_localize(None),
                     exit_time=(start[st.xb.to_numpy()] + pd.Timedelta(minutes=1)).tz_localize(None))


def main():
    sep, dec, dll = M.load(sys.argv[1]), M.load(sys.argv[2]), sys.argv[3]
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    rows = []
    for slip in (0, 1, 2):
        nat = pd.read_csv(ROOT / f"verification/native_long/B_L{slip}_trades_from_output.csv",
                          parse_dates=["entry_time", "exit_time"])
        st = stand_in(sep, dec, dll, slip)
        m = nat.merge(st, left_on=["entry_time", "dir", "qty"], right_on=["entry_time", "d", "q"], how="outer",
                      suffixes=("_nt", "_st"), indicator=True)
        m["period"] = m.entry_time.map(period)
        m["slippage"] = slip
        both = m._merge == "both"
        m["same entry"] = both & ((m.entry - m.en).abs() < 1e-9)
        m["same exit"] = both & ((m.exit - m.ex).abs() < 1e-9) & (m.exit_time_nt == m.exit_time_st)
        # on different contracts the price levels differ by the spread between them; the trade is the same when its
        # points (exit - entry) and its exit minute are
        m["same points"] = both & ((m.exit - m.entry) - (m.ex - m.en)).abs().lt(1e-9) & (
            m.exit_time_nt == m.exit_time_st)
        m["found in"] = m._merge.astype(str).replace({"left_only": "native only", "right_only": "stand-in only"})
        m["native net"] = m.net
        m["stand-in net"] = m.pnl_st
        tested = st[st.entry_time >= "2026-06-29"]
        print(f"\nslippage {slip}: native {len(nat)} trades ${nat.net.sum():,.2f}; stand-in (from 6/29) "
              f"{len(tested)} trades ${tested.pnl.sum():,.2f}")
        for name, _, _ in PERIODS:
            p = m[m.period == name]
            r = {"slippage": slip, "period": name, "native trades": int(p.net.notna().sum()),
                 "stand-in trades": int(p.pnl_st.notna().sum()), "same entry minute": int((p._merge == "both").sum()),
                 "identical (entry and exit price, exit minute)": int((p["same entry"] & p["same exit"]).sum()),
                 "same points and exit minute": int(p["same points"].sum()),
                 "native net $": round(p.net.sum(), 2), "stand-in net $": round(p.pnl_st.sum(), 2)}
            rows.append(r)
            print("   " + "; ".join(f"{k} {v}" for k, v in r.items() if k != "slippage"))
        if out:
            cols = ["slippage", "period", "entry_time", "dir", "qty", "entry", "en", "exit", "ex", "exit_time_nt",
                    "exit_time_st", "exit_name", "why", "native net", "stand-in net", "same points", "found in"]
            m.sort_values("entry_time")[cols].rename(columns={
                "en": "stand-in entry", "ex": "stand-in exit", "entry": "native entry", "exit": "native exit",
                "exit_name": "native exit name", "why": "stand-in exit name"}).to_csv(
                out / f"B_L{slip}_native_vs_standin.csv", index=False)
    if out:
        pd.DataFrame(rows).to_csv(out / "by_period.csv", index=False)


if __name__ == "__main__":
    main()
