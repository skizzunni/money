"""Stand-in against native NinjaTrader on identical MNQ bars (docs/MNQ_NATIVE.md, test 1).

    python research/mnq_reconcile.py <MNQ_12-26.Last.txt> <all-runs NinjaScript Output>

Native: the user's three B runs started 9/11/2026 on MNQ 12-26 (UseBreakout off, commission $0.95 a side, slippage
0 / 1 / 2), rebuilt from their own fills. Stand-in: the same strategy file on the same MNQ 12-26 bars from the 9/11
session (09:30-16:00 and the 16:00 bar), same settings, costs and slippage, the strategy's own skip dates only. Each
native trade is matched by fill time (NinjaTrader stamps a historical fill with its bar's end; the stand-in's fill bar
starts a minute earlier), direction and contracts; prices and exits are compared.
"""
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import controlled as K  # noqa: E402
import mnq_bars as M  # noqa: E402
import nt_reference as R  # noqa: E402

DLL = sys.argv[3] if len(sys.argv) > 3 else "Sim.dll"
dec = M.load(sys.argv[1])
bars = K.rth(dec[dec.index >= pd.Timestamp("2026-09-10 18:00", tz=M.NY)])
csv = Path(tempfile.mkdtemp()) / "b.csv"
K.write_bars(bars, csv)
start = bars.index
lines = Path(sys.argv[2]).read_text().splitlines()
cuts = [i for i, x in enumerate(lines) if x.startswith("MNQ settings: MNQ")] + [len(lines)]
native = []
for a, b in zip(cuts[:-1], cuts[1:], strict=True):
    if "35880 loaded" in lines[a] and "UseBreakout False" in lines[a + 1]:
        native.append(R.trades_from_output(lines[a:b]))
print(f"native B runs started 9/11 found: {len(native)} (slippage 0, 1, 2 in order)")
for slip, nat in zip((0, 1, 2), native, strict=False):
    st = K.run(DLL, csv, UseBreakout=False, SimSlippageTicks=slip, SimCommissionPerSide=0.95)
    st = st.assign(entry_time=(start[st.eb.to_numpy()] + pd.Timedelta(minutes=1)).tz_localize(None),
                   exit_time=(start[st.xb.to_numpy()] + pd.Timedelta(minutes=1)).tz_localize(None))
    nat = nat.assign(net=nat.pnl - 1.9 * nat.qty)
    m = nat.merge(st, left_on=["entry_time", "dir", "qty"], right_on=["entry_time", "d", "q"], how="outer",
                  suffixes=("_nt", "_st"), indicator=True)
    both = m[m._merge == "both"]
    same_entry = (both.entry - both.en).abs() < 1e-9
    same_exit = (both.exit - both.ex).abs() < 1e-9
    same_xt = both.exit_time_nt == both.exit_time_st
    print(f"\nslippage {slip}: native {len(nat)} trades ${nat.net.sum():,.2f}; stand-in {len(st)} trades "
          f"${st.pnl.sum():,.2f}; matched {len(both)}; same entry price {int(same_entry.sum())}; same exit price "
          f"{int(same_exit.sum())}; same exit minute {int(same_xt.sum())}; native only "
          f"{int((m._merge == 'left_only').sum())}; stand-in only {int((m._merge == 'right_only').sum())}")
    diff = both[~(same_entry & same_exit & same_xt)]
    for r in diff.itertuples():
        print(f"   {r.entry_time} dir {r.dir}: native {r.entry} -> {r.exit} {r.exit_time_nt} ({r.exit_name}); "
              f"stand-in {r.en} -> {r.ex} {r.exit_time_st} ({r.why})")
    for r in m[m._merge != "both"].itertuples():
        print(f"   unmatched ({r._merge}): {r.entry_time}")
