"""The Pine v1.5 reference three ways on identical 5-minute MNQ bars, joined trade by trade (docs/PINE_REFERENCE.md).

    python research/pine_reference.py <MNQ_09-26.Last.txt> <MNQ_12-26.Last.txt> <sim.dll> <out folder>

(a) the user's Pine v1.5 source in tests/pine_interpreter.py; (b) the NinjaTrader strategy MnqNoiseMomentum (frozen B's
code) at the reference's settings, in the stand-in; (c) mnqbot/noise.py. R4: 2 MNQ, $70 max loss (17.5 points), 4
losing trades a day; R2: 2. Commission $0.95 a side, slippage 1 and 2 ticks. Bars: the traded contracts
(research/mnq_bars.py), 1-minute 09:30-16:00 aggregated to 5 minutes (bar start, New York).
"""
import subprocess
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

from mnqbot.data import resample  # noqa: E402
from mnqbot.noise import NoiseConfig  # noqa: E402
from mnqbot.noise import run as noise_run  # noqa: E402

PINE = ROOT / "pine" / "reference" / "mnq_noise_momentum_v1.5_user.pine"
FEE = 0.95
SETTINGS = {"R4": 4, "R2": 2}
# the same exit, by platform: Pine's comment, the Python reference's reason, the NinjaTrader order name
EXIT = {"Back inside": "stop", "Max loss": "stop", "Lock": "stop", "Stop loss": "stop", "Target": "target",
        "Profit target": "target", "16:00 close": "16:00", "Flat 16:00": "16:00", "Session ended": "session end",
        "Exit on session close": "16:00"}


def bars_5min(sep_path, dec_path):
    series, _ = M.traded_series(M.load(sep_path), M.load(dec_path))
    one = K.rth(series)
    five = resample(one.assign(volume=one.get("volume", 0)), "5min")
    return five


def run_pine(bars, losers, slip):
    from pine_interpreter import PineRuntime, load_pine
    src = Path(tempfile.mkdtemp()) / "v15.pine"
    src.write_text(PINE.read_text(newline=""), newline="\n")  # the same text, LF line endings for the parser
    inputs = {"Contracts": 2, "Max loss per trade, $ (all contracts, 0 = off)": 70,
              "Max losing trades a day (0 = no limit)": losers}
    rt = PineRuntime(load_pine(src), bars, inputs, timeframe_seconds=300, commission=FEE, slippage_ticks=slip)
    rt.run()
    return pd.DataFrame([{"eb": t["entry_bar"], "xb": t["exit_bar"], "d": t["dir"], "en": t["entry"], "ex": t["exit"],
                          "pnl": t["pnl"], "why": t["reason"]} for t in rt.strategy.closed])


def run_python(bars, losers, slip):
    cfg = NoiseConfig(qty=2, max_loss_per_trade=70, max_losers=losers, commission_per_side=FEE, slippage_ticks=slip)
    res = noise_run(bars, cfg, minutes=5)
    return pd.DataFrame([{"eb": t.entry_bar, "xb": t.exit_bar, "d": t.direction, "en": t.entry, "ex": t.exit,
                          "pnl": t.pnl, "why": t.reason} for t in res.trades])


def run_nt(dll, csv, losers, slip):
    props = {"UseBreakout": False, "Funded": False, "AutoAccountType": False, "EvalQty": 2, "EvalMaxLoss": 70,
             "EvalMaxLosers": losers, "EvalLockAt": 1.0, "EvalLockPlus": 2.5, "TakeProfit": 1.5, "StopBuffer": 0.24,
             "TightenOnly": False, "SimSlippageTicks": slip, "SimCommissionPerSide": FEE}
    r = subprocess.run([K.DOTNET, str(dll), str(csv), "5", *[f"{k}={v}" for k, v in props.items()]],
                       capture_output=True, text=True, env=K.ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    t = [x.split(",")[1:] for x in r.stdout.splitlines() if x.startswith("T,")]
    return pd.DataFrame([{"d": int(a[0]), "eb": int(a[1]), "en": float(a[2]), "xb": int(a[3]), "ex": float(a[4]),
                          "why": a[5], "pnl": float(a[6])} for a in t])


def join(a, b, la, lb, bars):
    """Trades matched by entry bar and side; each pair's differences, each unmatched trade."""
    t = bars.index.tz_convert(K.NY)
    m = a.merge(b, on=["eb", "d"], how="outer", suffixes=(f"_{la}", f"_{lb}"), indicator=True)
    m["entry time"] = [t[int(e)].strftime("%Y-%m-%d %H:%M") for e in m.eb]
    rows = []
    for r in m.to_dict("records"):
        if r["_merge"] != "both":
            note = f"only in {la if r['_merge'] == 'left_only' else lb}"
        else:
            diffs = []
            if r[f"xb_{la}"] != r[f"xb_{lb}"]:
                diffs.append("exit bar")
            if abs(r[f"en_{la}"] - r[f"en_{lb}"]) > 1e-6:
                diffs.append("entry price")
            if abs(r[f"ex_{la}"] - r[f"ex_{lb}"]) > 1e-6:
                diffs.append("exit price")
            if EXIT.get(r[f"why_{la}"], r[f"why_{la}"]) != EXIT.get(r[f"why_{lb}"], r[f"why_{lb}"]):
                diffs.append("exit kind")
            note = "match" if not diffs else "differs: " + ", ".join(diffs)
        rows.append({**r, "result": note})
    return pd.DataFrame(rows).drop(columns="_merge")


CAP = 17.5  # points: $70 over 2 MNQ


def classify(j, la, lb, slip, tick=0.25):
    """Why each joined pair differs (la = Pine, lb = NinjaTrader): every row gets a category."""
    cats = []
    bad_days = set()
    for r in j.to_dict("records"):
        day = r["entry time"][:10]
        if r["result"] == "match":
            cats.append("match")
            continue
        if r["result"].startswith("only in"):
            cats.append("knock-on: an earlier exit that day differs" if day in bad_days else "unexplained")
            continue
        bad_days.add(day)
        d, ka, kb = r["d"], EXIT.get(r[f"why_{la}"], r[f"why_{la}"]), EXIT.get(r[f"why_{lb}"], r[f"why_{lb}"])
        xa, xb = r[f"ex_{la}"], r[f"ex_{lb}"]
        fill_cap = r[f"en_{lb}"] - d * CAP - d * slip * tick
        if ka == kb == "16:00" and r[f"xb_{lb}"] == r[f"xb_{la}"] + 1:
            cats.append("A: 16:00 exit, Pine at the 15:55 close, NinjaTrader at the next bar's open")
        elif abs(xa - xb) < 1e-6:
            cats.append("B: same exit price, named differently (Pine 'Lock', NinjaTrader 'Stop passed')")
        elif abs(xb - fill_cap) < 1e-6:
            cats.append("C: fill-bar max-loss stop, Pine from the expected fill, NinjaTrader from the actual")
        elif abs(xb - xa) <= 2 * tick and ka == kb:
            cats.append("D: the same stop or target rounded to a tick in NinjaTrader")
        else:
            cats.append("unexplained")
    j = j.copy()
    j["category"] = cats
    return j


def main():
    sep, dec, dll, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    bars = bars_5min(sep, dec)
    csv = out / "mnq_5min_bars.csv"
    K.write_bars(bars, csv)
    summary = []
    for name, losers in SETTINGS.items():
        for slip in (1, 2):
            p, py, nt = run_pine(bars, losers, slip), run_python(bars, losers, slip), run_nt(dll, csv, losers, slip)
            for label, df in (("pine", p), ("python", py), ("nt", nt)):
                df.to_csv(out / f"trades_{name}_{slip}t_{label}.csv", index=False)
            jp = join(p, py, "pine", "python", bars)
            jn = classify(join(p, nt, "pine", "nt", bars), "pine", "nt", slip)
            jn.to_csv(out / f"joined_{name}_{slip}t_pine_vs_nt.csv", index=False)
            summary.append({"settings": name, "slippage": slip, "pine trades": len(p), "python trades": len(py),
                            "nt trades": len(nt), "pine net": round(p.pnl.sum(), 2),
                            "python net": round(py.pnl.sum(), 2), "nt net": round(nt.pnl.sum(), 2),
                            "pine vs python": jp.result.value_counts().to_dict(),
                            "pine vs nt": jn.category.value_counts().to_dict()})
            print(summary[-1], flush=True)
    pd.DataFrame(summary).to_csv(out / "summary.csv", index=False)


if __name__ == "__main__":
    main()
