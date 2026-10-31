import subprocess, sys
sys.path.insert(0, "research"); sys.path.insert(0, ".")
import numpy as np, pandas as pd
import e50_eval as E
import t1_eval as T, v24_scan as VS
GROW = len(sys.argv) > 1 and sys.argv[1] == "grow"
NTARGS = ["MaxLoss=187.5", "AfterLossMaxLoss=250", "DailyLoss=900", "TrailDD=2000", "TrailFrom=2025-01-02", "ProfitStep=1500", "MaxContracts=15", "SizeByOwnStop=true"] if GROW else []
from mnqbot.noise import NoiseConfig, run
S = "/tmp/claude-0/-home-user-money/b0ea31b5-d9fc-525a-a114-db6430eff3ed/scratchpad"
SIM = "ninjatrader/tests/Sim/bin/Release/net8.0/Sim"
out = []
for m in (30, 5):
    bars = pd.read_pickle(f"{S}/proxy_{m}m.pkl")[["open", "high", "low", "close"]]
    # where a session's data stops at 16:00 with no 16:00 bar after it, add one at the last price: on an ETH chart MNQ
    # keeps trading to 17:00, so NinjaTrader's 16:00 market exit fills there, not at the next morning's open
    t = bars.index.tz_convert("America/New_York")
    mins = t.hour * 60 + t.minute
    last = (mins + m == 960) & ~pd.Series(mins == 960).shift(-1, fill_value=False).to_numpy()
    add = bars[last].copy()
    add.index = add.index + pd.Timedelta(minutes=m)
    add[["open", "high", "low"]] = add[["close"]].to_numpy().repeat(3, axis=1)
    print(m, "min: 16:00 bars added", len(add), "of", int((mins + m == 960).sum()), "sessions", flush=True)
    bars = pd.concat([bars, add]).sort_index()
    t = bars.index.tz_convert("America/New_York")
    csv = f"{S}/v38_bars_{m}.csv"
    with open(csv, "w") as f:
        for ts, r in zip(t, bars.itertuples()):
            f.write(f"{ts.strftime('%Y-%m-%d %H:%M')},{r.open!r},{r.high!r},{r.low!r},{r.close!r}\n")
    res = subprocess.run(["/opt/dotnet/dotnet", SIM + ".dll", csv, str(m), "Strategy=V38", *NTARGS], capture_output=True, text=True, check=True).stdout
    nt = [l.split(",") for l in res.splitlines() if l.startswith("T,")]
    nt = pd.DataFrame([(int(x[1]), int(x[2]), float(x[3]), int(x[4]), float(x[5]), x[6], float(x[7])) for x in nt],
                      columns=["d", "eb", "entry", "xb", "exit", "why", "pnl"])
    base = ({**VS.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0, "trail_from": "2025-01-02"} if GROW
            else {**E.config(1, 2.0, 260.0, 0), "daily_loss_limit": 900.0})
    cfg = NoiseConfig(**{**base, "tv_path": False, "nt_execution": True, "round_prices": True, "target_on_fill_bar": True})
    py = run(bars, cfg, minutes=m).trades_frame()
    same = (len(nt) == len(py) and (nt.d.values == py.direction.values).all() and (nt.eb.values == py.entry_bar.values).all()
            and (nt.xb.values == py.exit_bar.values).all() and np.allclose(nt.entry.values, py.entry.values)
            and np.allclose(nt.exit.values, py.exit.values) and np.allclose(nt.pnl.values, py.pnl.values, atol=0.01))
    k = 0
    if not same:
        n = min(len(nt), len(py))
        bad = [j for j in range(n) if not (nt.eb[j] == py.entry_bar[j] and nt.xb[j] == py.exit_bar[j]
                                            and abs(nt.exit[j] - py.exit[j]) < 1e-6 and nt.d[j] == py.direction[j])]
        k = bad[0] if bad else n
        print("first difference at trade", k, "of", len(nt), len(py))
        print(nt.iloc[max(0, k - 2):k + 3].to_string()); print(py.iloc[max(0, k - 2):k + 3][["direction", "entry_bar", "entry", "exit_bar", "exit", "reason", "pnl"]].to_string())
    first = pd.Timestamp("2025-01-02", tz="America/New_York")
    sel = py.entry_time >= first
    fb = int(np.searchsorted(bars.index, first))
    w = nt[nt.eb >= fb].reset_index(drop=True)
    pw = py[sel].reset_index(drop=True)
    win_same = (len(w) == len(pw) and (w.d.values == pw.direction.values).all() and (w.eb.values == pw.entry_bar.values).all()
                and (w.xb.values == pw.exit_bar.values).all() and np.allclose(w.entry.values, pw.entry.values)
                and np.allclose(w.exit.values, pw.exit.values) and np.allclose(w.pnl.values, pw.pnl.values, atol=0.01))
    w.assign(entry_time=[t[j].strftime("%Y-%m-%d %H:%M") for j in w.eb], exit_time=[t[j].strftime("%Y-%m-%d %H:%M") for j in w.xb]).to_csv(f"{S}/v38{'g' if GROW else ''}_nt_trades_{m}.csv", index=False)
    p = w.pnl.to_numpy()
    e = np.r_[0.0, np.cumsum(p)]
    dayp = py[sel].groupby(py[sel].exit_time.dt.date).pnl.sum()
    q = py[sel].qty.to_numpy() if "qty" in py else None
    out.append({"max qty": int(py[sel].qty.max()), "bars": m, "identical in the window": bool(win_same), "identical overall": bool(same), "trades nt": len(nt), "trades py": len(py),
                "window trades": int(sel.sum()), "net $": round(float(p.sum()), 2),
                "win %": round(100 * float((p > 0).mean()), 1),
                "pf": round(float(p[p > 0].sum() / -p[p <= 0].sum()), 3), "closed dd $": round(float((np.maximum.accumulate(e) - e).max()), 2),
                "largest loss $": round(float(p.min()), 2), "worst day $": round(float(dayp.min()), 2)})
    print(out[-1], flush=True)
pd.DataFrame(out).to_csv(f"{S}/v38{'g' if GROW else ''}_nt.csv", index=False)
