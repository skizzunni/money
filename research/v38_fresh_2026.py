"""NinjaTrader's simulator on a fresh 50K started 2026-01-02 (to the data's end): net, traded days, green days and the
worst day for each setting.

    python research/v38_fresh_2026.py <dir with v38_bars_5.csv> "TrailFrom=2026-01-02|Mode=Funded growth plus" ...
"""
import subprocess
import sys

SIM = "ninjatrader/tests/Sim/bin/Release/net8.0/Sim.dll"


def go(d, times, *args):
    out = subprocess.run(["/opt/dotnet/dotnet", SIM, f"{d}/v38_bars_5.csv", "5", "Strategy=V38", "Mode=Funded growth",
                          *args], capture_output=True, text=True).stdout
    rows = [r.split(",") for r in out.splitlines() if r.startswith("T,")]
    sel = [(times[int(r[2])], float(r[7])) for r in rows if times[int(r[2])] >= "2026-01-02"]
    days = {}
    for t, p in sel:
        days[t[:10]] = days.get(t[:10], 0) + p
    net = sum(p for _, p in sel)
    green = sum(v > 0 for v in days.values())
    print(f"{' '.join(args):45s} trades {len(sel):4d} net {net:10.2f} days {len(days)} green {green} "
          f"worst day {min(days.values()):.0f}", flush=True)


if __name__ == "__main__":
    d = sys.argv[1]
    times = [r.split(",")[0] for r in open(f"{d}/v38_bars_5.csv")]
    for a in sys.argv[2:]:
        go(d, times, *a.split("|"))
