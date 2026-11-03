"""G55 (docs/NINJATRADER_V38.md): the share of days traded, and the net, with each day filter turned off.

    python research/g55_filters_off.py <data dir> <MNQ 09-26 file> <MNQ 12-26 file> "<variant>"
"""
import sys, numpy as np, pandas as pd
import t1_eval as T, v24_scan as S
from mnqbot.noise import NoiseConfig, run
S.init({}, *sys.argv[1:4])
VAR = {"current": {}, "no calm filter": {"calm_k": 0.0}, "no range-position filter": {"range_pos_min": 0.0},
       "no big-day rule": {"big_day_k": 0.0}, "shorts in uptrends too": {"trend_n": 0},
       "all four off": {"calm_k": 0.0, "range_pos_min": 0.0, "big_day_k": 0.0, "trend_n": 0}}
v = sys.argv[4]
for name,(bars,first,skip) in S.D.items():
    if name=="win": continue
    cfg=NoiseConfig(**{**S.V23, **T.REFERENCE, "daily_loss_limit":900.0,"trail_dd":2000.0,"time_stop":60, **VAR[v]})
    if isinstance(skip,str): cfg.skip_dates, cfg.fed_dates = skip, ""
    if first: cfg.trail_from=first
    tf=run(bars,cfg,minutes=5).trades_frame()
    if first: tf=tf[tf.entry_time>=pd.Timestamp(first,tz="America/New_York")]
    t=bars.index.tz_convert("America/New_York")
    sess=set(t[(t.hour==9)&(t.minute==30)].date)
    if first: sess={d for d in sess if d>=pd.Timestamp(first).date()}
    days=tf.entry_time.dt.tz_convert("America/New_York").dt.date.nunique()
    p=tf.pnl.to_numpy(); dayp=tf.groupby(tf.exit_time.dt.date).pnl.sum()
    print(f"{v}|{name}|{100*days/len(sess):.0f}%|{len(p)}|{p.sum():.0f}|{dayp.min():.0f}|{S.trail_stats(name, tf)[f'{name} tb0']}", flush=True)
