"""Rebuild the research data folder that the G-series runs read (docs/DATA_REBUILD.md).

    python tools/rebuild_data.py <data dir> [<MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>]

The folder is not in the repository (data/*.csv and the pickles are too big, and the user's exports are theirs). This
script makes it again in a fresh container:
  nq1m/NQ_1min_<year>.parquet   downloaded from Hugging Face (mdelcristo/NQ-F_1min_OHLCV_Parquet, MIT) when missing
  nq1m_scaled.pkl, nq5m_scaled.pkl   research/nq_rolls.py's month scaling, then 5-minute bars
  histdata_raw/*.zip            HistData NSXUSD 1-minute ASCII zips, put there by hand; unzipped to histdata_raw/<name>/
  bars5_scaled.pkl              the Nasdaq-100 index on 5-minute bars (research/more_trades.py's _bars)
  proxy_5m.pkl, proxy_30m.pkl   research/v24_proxy.py (needs the MNQ exports)
  u48_JS.json                   the U48 base the runs layer U58 / G473 / G511 on, from tests/test_ninjatrader_v38.py
Each step is skipped when its output exists. Check before trusting it: G519's Funded growth rows must come out exactly
as in verification/noise_v2/g519_growth_time_stop.txt.
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "tests"), str(ROOT)]
HF = "https://huggingface.co/datasets/mdelcristo/NQ-F_1min_OHLCV_Parquet/resolve/main/NQ_1min_{}.parquet"


def nq(d: Path) -> None:
    import nq_rolls as N
    import pandas as pd
    (d / "nq1m").mkdir(parents=True, exist_ok=True)
    for y in range(2015, 2026):
        f = d / "nq1m" / f"NQ_1min_{y}.parquet"
        if not f.exists():
            print("downloading", f.name, flush=True)
            urllib.request.urlretrieve(HF.format(y), f)
    if not (d / "nq1m_scaled.pkl").exists():
        N.scaled(N.load_raw(str(d / "nq1m"))).to_pickle(d / "nq1m_scaled.pkl")
    if not (d / "nq5m_scaled.pkl").exists():
        p = pd.read_pickle(d / "nq1m_scaled.pkl")
        p.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().to_pickle(
            d / "nq5m_scaled.pkl")
    print("NQ ready", flush=True)


def index(d: Path) -> bool:
    raw = d / "histdata_raw"
    raw.mkdir(parents=True, exist_ok=True)
    for z in sorted(raw.glob("*.zip")):
        out = raw / z.stem
        if not out.exists():
            if not zipfile.is_zipfile(z):
                print("index: not a zip, skipped:", z.name)
                continue
            with zipfile.ZipFile(z) as f:
                f.extractall(out)
    pattern = str(raw / "*" / "DAT_ASCII_NSXUSD_M1_*.csv")
    if not list(raw.glob("*/DAT_ASCII_NSXUSD_M1_*.csv")):
        print("index: no HistData NSXUSD files in", raw, "(see docs/DATA_REBUILD.md)")
        return False
    if not (d / "bars5_scaled.pkl").exists():
        import more_trades as MT
        MT._bars(pattern).to_pickle(d / "bars5_scaled.pkl")
    print("index ready", flush=True)
    return True


def proxy(d: Path, sep: str, dec: str) -> None:
    if not (d / "proxy_5m.pkl").exists():
        subprocess.run([sys.executable, str(ROOT / "research" / "v24_proxy.py"), str(d), sep, dec], check=True)
    print("stand-in ready", flush=True)


def base(d: Path) -> None:
    import test_ninjatrader_v38 as T

    from mnqbot.noise import NoiseConfig
    # GROW is today's Funded growth; the runs add U58 (G422), G473's brake and G511's fill-ins on top of U48
    g = dataclasses.replace(T.GROW, giveback_brake=0.45, max_losers=3, range_pos_min=0.7, skip_checks="780,870",
                            entry_k_regime=0.0, **T.PRE_G511)
    dflt = NoiseConfig()
    skip = {"nt_execution", "round_prices", "target_on_fill_bar", "tv_path"}  # the runner sets these
    out = {f.name: getattr(g, f.name) for f in dataclasses.fields(g)
           if f.name not in skip and getattr(g, f.name) != getattr(dflt, f.name)}
    (d / "u48_JS.json").write_text(json.dumps(out, indent=1))
    print("u48_JS.json:", len(out), "settings", flush=True)


def main() -> None:
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    nq(d)
    base(d)
    have_index = index(d)
    if len(sys.argv) >= 4 and have_index:
        proxy(d, sys.argv[2], sys.argv[3])
        a = f"{d} {sys.argv[2]} {sys.argv[3]} {d / 'u48_JS.json'}"
        print("\ncheck (must match verification/noise_v2/g519_growth_time_stop.txt):\n"
              f"  cd research && PROCS=4 python g519_growth_time_stop.py {a} fresh && "
              f"PROCS=4 python g519_growth_time_stop.py {a} unseen")
    else:
        print("\nstill needed: the HistData NSXUSD zips in histdata_raw/ and the two MNQ exports")


if __name__ == "__main__":
    main()
