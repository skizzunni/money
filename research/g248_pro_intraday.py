"""G248 (docs/NINJATRADER_V38.md): the 526 fresh starts under Take Profit Trader's PRO drawdown: $2,000 trailing
INTRADAY from the highest balance including open profit, stopping at the starting balance. A measurement.

The bot as it is (it sizes from the end-of-day floor). Per bar, the open trades' best and worst marks come from the
bar's high and low; "worst order" counts the bar's best mark before its worst (the floor rises first), "best order" the
worst mark first. An account is lost when its marked balance reaches the floor.

    START_FREQ=MS|MID VARIANT_TAG=<tag> VARIANT_JSON='{...}' python research/g248_pro_intraday.py <data dir> <MNQ 09-26>
    <MNQ 12-26>
"""
import sys

sys.argv = sys.argv[:4] + ["json"]
import g35_start_dates as G  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import t1_eval as T  # noqa: E402
import v24_scan as S  # noqa: E402

from mnqbot.noise import NoiseConfig, run  # noqa: E402

DD = 2000.0
PV = 2.0


def pro_lost(b: pd.DataFrame, trades, s0) -> tuple[bool, bool, float]:
    hi, lo = b.high.to_numpy(), b.low.to_numpy()
    n = len(b)
    fav, adv = np.zeros(n), np.zeros(n)
    closed_at = np.zeros(n)  # realized P/L booked at each bar (on the exit bar)
    for t in trades:
        if t.entry_time < s0:
            continue
        sl = slice(t.entry_bar + 1, t.exit_bar + 1)
        if t.direction > 0:
            fav[sl] += t.qty * (hi[sl] - t.entry) * PV
            adv[sl] += t.qty * (lo[sl] - t.entry) * PV
        else:
            fav[sl] += t.qty * (t.entry - lo[sl]) * PV
            adv[sl] += t.qty * (t.entry - hi[sl]) * PV
        closed_at[t.exit_bar] += t.pnl
    # the open marks on a trade's exit bar belong to before its exit; the realized P/L counts from the next bar
    closed_before = np.r_[0.0, np.cumsum(closed_at)[:-1]]
    start = int(np.searchsorted(b.index.values, np.datetime64(s0.tz_convert("UTC").tz_localize(None)), side="left"))
    lost_w = lost_b = False
    pk_w = pk_b = 0.0
    low_room = np.inf
    for i in range(start, n):
        c = closed_before[i]
        best, worst = c + fav[i], c + adv[i]
        # worst order: the best mark first, then the worst
        pk_w = max(pk_w, best, c)
        if worst <= min(pk_w - DD, 0.0):
            lost_w = True
        # best order: the worst mark first against yesterday's peak, then the best
        if worst <= min(pk_b - DD, 0.0):
            lost_b = True
        pk_b = max(pk_b, best, c)
        low_room = min(low_room, worst - min(pk_w - DD, 0.0))
        if lost_w and lost_b:
            break
    end = closed_before[-1] + closed_at[-1]
    if end <= min(max(pk_w, end) - DD, 0.0):
        lost_w = True
    return lost_w, lost_b, low_room


def one(job):
    name, start = job
    bars, _, skip = S.D[name]
    s0 = pd.Timestamp(start, tz=G.NY)
    s1 = s0 + pd.DateOffset(months=G.MONTHS)
    b = bars[(bars.index >= s0 - pd.Timedelta(days=150)) & (bars.index < s1)]
    cfg = NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": DD, "time_stop": 60,
                         **G.EXTRA})
    cfg.tv_path, cfg.nt_execution, cfg.round_prices, cfg.target_on_fill_bar = False, True, True, True
    if isinstance(skip, str):
        cfg.skip_dates, cfg.fed_dates = skip, ""
    cfg.trail_from = start
    res = run(b, cfg, minutes=S.MIN[0])
    lw, lb, room = pro_lost(b, res.trades, s0)
    net = sum(t.pnl for t in res.trades if t.entry_time >= s0)
    return {"set": name, "start": start, "net $": round(net), "pro lost (worst order)": lw,
            "pro lost (best order)": lb, "lowest room $": round(room)}


def main() -> None:
    import os
    from concurrent.futures import ProcessPoolExecutor
    S.init({}, *sys.argv[1:4])
    S.D = {k: (G.with_1600(b, S.MIN[0]), first, skip) for k, (b, first, skip) in S.D.items() if k != "win"}
    fq = os.environ.get("START_FREQ", "MS")
    off = pd.Timedelta(days=14) if fq == "MID" else pd.Timedelta(0)
    jobs = [("nq", (d + off).strftime("%Y-%m-%d")) for d in pd.date_range("2015-04-01", "2023-10-01", freq="MS")]
    jobs += [("index", (d + off).strftime("%Y-%m-%d")) for d in pd.date_range("2011-04-01", "2024-07-01", freq="MS")]
    with ProcessPoolExecutor(int(os.environ.get("PROCS", "4"))) as ex:
        d = pd.DataFrame(list(ex.map(one, jobs)))
    d.to_csv(f"verification/noise_v2/g248_pro_{G.VARIANT}_{fq}.csv", index=False)
    for name, g in d.groupby("set"):
        print(name, G.VARIANT, fq, "starts", len(g), "PRO lost (worst order)", int(g["pro lost (worst order)"].sum()),
              "(best order)", int(g["pro lost (best order)"].sum()), "median net", int(g["net $"].median()),
              flush=True)


if __name__ == "__main__":
    main()
