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
