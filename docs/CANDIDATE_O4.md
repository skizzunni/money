# O4 — improving the ONYX Trend Follow replica (pre-registration)

Written and committed on 2026-10-30, before `research/o4_trendpb.py` was run.

**The base:** `trendpb` in `research/patterns.py`, regular hours, mornings, 3R target. It was the one ONYX replica
that held up on data not used to choose it:

| | PF | Average R |
|---|---|---|
| NQ 2015-2019 (development) | 1.42 | +0.25 |
| NQ 2020-2025 | 1.22 | +0.13 |
| Index 2011-2026 | 1.17 | +0.10 |
| Stand-in 2025-2026 | 1.11 | +0.05 |

**The grid**, chosen now, before seeing results:
- L, the regression lookback in 5-minute bars: 12, 24, 36.
- K, the fitted move over L bars that counts as a trend: 2, 3 or 4 ATR.
- S, the stop past the extreme of the last S bars: 3, 7, 12.
- The last entry: 11:00, 12:00, 13:30.
- The target: 2, 3 or 4R.
- The day's-direction filter: off or on.

That makes 486 settings. Everything else is as in `patterns.py`:
- the entry at the next bar's open;
- about $500 of risk, 1-10 MNQ;
- $0.62 a side and a tick on market and stop fills;
- a bar that reaches both the stop and the target counts as the stop;
- flat at 16:00.

**Selection** (NQ 2015-2019 only): the highest PF among settings with at least 50 trades a year.

**Holdout pass** (one run of the selected setting): NQ 2020-2025, the index 2011-2026 and the 2025-2026 stand-in.
- PF ≥ 1.2 on all three; and
- a higher PF than the base on at least 2 of the 3.

If it fails, the base stays as it is.

## Results (2026-10-30; `verification/noise_v2/o4_dev.csv`, `o4_holdout.csv`)

**Development:** 183 of 486 settings had at least 50 trades a year.
- **Selected:** L 12, K 3, S 12, last entry 13:30, 3R, no direction filter.
- On NQ 2015-2019 that is 67 trades a year, 54.6% winners and PF 1.38. The base had 41 a year and PF 1.42; it misses
  the 50-a-year floor.

**Holdout** (one run):

| | Base PF / net a year / DD | Selected PF / net a year / DD |
|---|---|---|
| NQ 2020-2025 | 1.22 / $2,759 / $8,233 | **1.25** / $1,684 / $5,369 |
| Index 2011-2026 | 1.17 / $1,946 / $12,938 | **1.27** / $2,352 / $5,552 |
| Stand-in 2025-2026 | 1.11 / $1,514 / $6,804 | **0.97** / −$311 / $5,448 |

**Fails.** The selected setting needed PF ≥ 1.2 on all three; it lost on the stand-in (PF 0.97).
- It beat the base on 2 of 3 sets, with smaller drawdowns.
- But in the 2025-2026 window it lost money.

**The base stays.** Neither version comes near the user's targets: about $1.5-2.8k a year at about $500 risk a trade.
