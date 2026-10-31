import sys
sys.path.insert(0, "research"); sys.path.insert(0, ".")
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
import t1_eval as T, v24_scan as S
from mnqbot.noise import NoiseConfig, run
NY = "America/New_York"
CFG = {**S.V23, **T.REFERENCE, "daily_loss_limit": 900.0, "trail_dd": 2000.0}
def one(job):
    name, start = job
    bars, _f, skip = S.D[name]
    s = pd.Timestamp(start, tz=NY)
    b = bars[bars.index >= s - pd.Timedelta(days=150)]
    cfg = NoiseConfig(**CFG); cfg.skip_dates, cfg.fed_dates = skip, ""; cfg.trail_from = start
    tf = run(b, cfg, minutes=S.MIN[0]).trades_frame()
    tf = tf[tf.entry_time >= s].sort_values("exit_time")
    eq = tf.pnl.cumsum()
    hit = tf.exit_time[eq >= 50000]
    months = (hit.iloc[0] - s).days / 30.44 if len(hit) else np.nan
    end = (bars.index[-1] - s).days / 30.44
    return {"set": name, "start": start, "months to $50k": round(months, 1), "months of data": round(end, 1)}
if __name__ == "__main__":
    S.init({}, *sys.argv[1:4])
    jobs = []
    for name in ("nq", "index"):
        first = S.D[name][0].index[0].tz_convert(NY) + pd.Timedelta(days=200)
        last = S.D[name][0].index[-1].tz_convert(NY) - pd.Timedelta(days=365 * 3)
        jobs += [(name, q.strftime("%Y-%m-%d")) for q in pd.date_range(first.strftime("%Y-%m-01"), last.strftime("%Y-%m-%d"), freq="QS")]
    with ProcessPoolExecutor(4, initializer=S.init, initargs=({}, *sys.argv[1:4])) as ex:
        d = pd.DataFrame(list(ex.map(one, jobs)))
    d.to_csv(sys.argv[4], index=False)
    for n, g in d.groupby("set"):
        m = g["months to $50k"]
        print(n, "starts", len(g), "reached $50k:", int(m.notna().sum()), "| months: 25th", round(m.quantile(.25), 1), "median", round(m.median(), 1), "75th", round(m.quantile(.75), 1), "| within 21 months:", int((m <= 21).sum()), "within 36:", int((m <= 36).sum()))
