"""G309 (docs/NINJATRADER_V38.md): is U55's gain over U53 real? A check on saved results (G278's and G295's rows,
10 sessions, the same 1,322 Monday starts): paired counts, and a bootstrap of calendar quarters (4,000 draws, seed 309).

    python research/g309_paired.py
"""
import numpy as np
import pandas as pd

a = pd.read_csv("verification/noise_v2/g278_horizon.csv")
b = pd.read_csv("verification/noise_v2/g295_horizon.csv")
m = a[a.sessions == 10].merge(b[b.sessions == 10], on=["set", "start"], suffixes=("_53", "_55"))
print(f"starts {len(m)}: passed U53 {m.passed_53.mean():.3f} U55 {m.passed_55.mean():.3f}; "
      f"failed U53 {m.failed_53.mean():.3f} U55 {m.failed_55.mean():.3f}")
print("passed by U55 only", int((m.passed_55 & ~m.passed_53).sum()), "by U53 only",
    int((~m.passed_55 & m.passed_53).sum()))
print("failed by U55 only", int((m.failed_55 & ~m.failed_53).sum()), "by U53 only",
    int((~m.failed_55 & m.failed_53).sum()))
m["q"] = pd.to_datetime(m.start).dt.to_period("Q").astype(str) + m.set
groups = {q: x for q, x in m.groupby("q")}
qs = list(groups)
rng = np.random.default_rng(309)
dp, df = [], []
for _ in range(4000):
    s = pd.concat([groups[q] for q in rng.choice(qs, len(qs))])
    dp.append(s.passed_55.mean() - s.passed_53.mean())
    df.append(s.failed_55.mean() - s.failed_53.mean())
dp, df = np.array(dp), np.array(df)
print(f"passed U55 - U53: {m.passed_55.mean() - m.passed_53.mean():+.4f}, 95% {np.percentile(dp, 2.5):+.4f} to "
      f"{np.percentile(dp, 97.5):+.4f}, draws at or below 0: {(dp <= 0).mean():.3f}")
print(f"failed U55 - U53: {m.failed_55.mean() - m.failed_53.mean():+.4f}, 95% {np.percentile(df, 2.5):+.4f} to "
      f"{np.percentile(df, 97.5):+.4f}, draws at or above 0: {(df >= 0).mean():.3f}")
