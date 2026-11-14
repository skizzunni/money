"""Rebuild the research data folder that the G-series runs read (docs/DATA_REBUILD.md).

    [INDEX_MIRROR=1] python tools/rebuild_data.py <data dir> [<MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt>]

Without the MNQ files it writes them from tests/data's committed series. INDEX_MIRROR=1 uses the Hugging Face HistData
mirror when no HistData NSXUSD zips are in histdata_raw/ (close to the original, not identical, ends 2025-03-21).

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
import os
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


def mnq(d: Path) -> tuple[str, str]:
    """The two MNQ exports, rewritten from tests/data's traded series (6/28-10/16/2026, SEP26 back-adjusted): both
    files hold the whole series, so mnq_bars.traded_series (a zero roll difference) gives it back bar for bar."""
    import pandas as pd
    sep, dec = d / "MNQ_09-26.Last.txt", d / "MNQ_12-26.Last.txt"
    if not (sep.exists() and dec.exists()):
        s = pd.read_csv(ROOT / "tests/data/mnq_traded_eth_2026-06-28_2026-10-16.csv.gz", header=None,
                        names=["t", "open", "high", "low", "close"])
        end = (pd.to_datetime(s.t).dt.tz_localize("America/New_York") + pd.Timedelta(minutes=1)).dt.tz_convert("UTC")
        out = pd.DataFrame({"t": end.dt.strftime("%Y%m%d %H%M%S"),
                            **{k: s[k].map("{:.2f}".format) for k in ("open", "high", "low", "close")}, "v": 0})
        for f in (sep, dec):
            out.to_csv(f, sep=";", header=False, index=False)
    return str(sep), str(dec)


def mirror(d: Path) -> None:
    """Fallback for the index: Hugging Face's HistData mirror (elthariel/histdata_fx_1m, NSXUSD to 2025-03-21) as
    HistData CSVs (its UTC back to HistData's EST clock). Not identical to the original files (docs/DATA_REBUILD.md)."""
    import pandas as pd
    out = d / "histdata_raw" / "hf_mirror"
    if out.exists() or list((d / "histdata_raw").glob("*/DAT_ASCII_NSXUSD_M1_*.csv")):
        return
    out.mkdir(parents=True)
    pq = d / "nsxusd_mirror.parquet"
    if not pq.exists():
        urllib.request.urlretrieve(
            "https://huggingface.co/datasets/elthariel/histdata_fx_1m/resolve/main/nsxusd/ticks.parquet", pq)
    x = pd.read_parquet(pq)
    t = x.ts.dt.tz_convert(None) - pd.Timedelta(hours=5)
    x["s"] = t.dt.strftime("%Y%m%d %H%M%S")
    for y, g in x.groupby(t.dt.year):
        g[["s", "open", "high", "low", "close", "volume"]].to_csv(out / f"DAT_ASCII_NSXUSD_M1_{y}.csv", sep=";",
                                                                   header=False, index=False)


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
    sep, dec = (sys.argv[2], sys.argv[3]) if len(sys.argv) >= 4 else mnq(d)
    if os.environ.get("INDEX_MIRROR") == "1":
        mirror(d)
    have_index = index(d)
    if have_index:
        try:
            proxy(d, sep, dec)
        except (IndexError, ValueError, subprocess.CalledProcessError) as e:  # the index must reach 2026-06-30
            print("stand-in not built (the index files stop before 2026-07):", e)
            return
        a = f"{d} {sep} {dec} {d / 'u48_JS.json'}"
        print("\ncheck (must match verification/noise_v2/g519_growth_time_stop.txt):\n"
              f"  cd research && PROCS=4 python g519_growth_time_stop.py {a} fresh && "
              f"PROCS=4 python g519_growth_time_stop.py {a} unseen")
    else:
        print("\nstill needed: the HistData NSXUSD zips in histdata_raw/ and the two MNQ exports")


if __name__ == "__main__":
    main()
