# The NQ file's contract rolls (gap found October 21, 2026)

**The gap:**
- The NQ 1-minute file that decides the D/E (and now F) gates, `mdelcristo/NQ-F_1min_OHLCV_Parquet`, is the front
  month, **unadjusted**.
- At each quarterly roll its price jumps by the carry between the expiring and the next contract:
  - about **+1.0% to +1.4%** a roll in 2023-2025;
  - a few tenths of a percent either way in 2015-2021.
- The monthly rescaling (each New York month × 30,661 / its first close) removes the jump only at month boundaries.
  Rolls fall in the expiry week, mid-month, so the rescaled series (`nq1m_scaled.pkl`, sha256 `89c0b157…`) keeps them.

**What it touches:**
- **The session the roll happens on:**
  - the noise lines' previous close;
  - the Williams range is not touched (it is a range);
  - the sweep pools carried into it: the previous day's range, the previous week's range for the rest of that week,
    and swings and gaps formed before it.
- About 4 sessions a year of 252, plus the weekly pools for the rest of the roll week.
- It is a correctness gap, not a large one. It was not known when D/E ran.

## Detection

**Method:** `research/nq_rolls.py`. The file has no contract column, so the roll session is found against the NSX
1-minute series.
- NSX is a Nasdaq-100 CFD. It rolls itself on the expiry Friday, so that day is not a candidate.
- **Candidates:** the third Friday minus 8 days to the Thursday before it.

**Three detectors.** Each picks the candidate with the largest change of log(NQ/NSX):
- **minute:** the session's first open against the previous session's last close, with NSX at the same two minutes;
- **median:** the median over 18:00-03:59 against 15:00-16:59 of the previous session;
- **rth:** 10:00-15:29 medians, session against session.

**The roll** is the session at least two detectors agree on.
- With no agreement, the minute detector's pick is used if its jump is at least twice the next candidate's.
- Otherwise the quarter is undetermined and not adjusted.

**Result** (`verification/nq_rolls/nq_rolls.csv`): 42 quarters, 2015-03 to 2025-06.
- All three detectors agree on 29 and two on 9.
- **4 are undetermined:** 2016-12, 2021-03, 2021-12 and 2022-03. Their largest minute jumps are 0.05%, 0.14%, 0.13% and
  0.21%, at or near the noise of the basis.
- **The roll days follow the volume roll:**
  - Monday of the expiry week in 2015-2019;
  - Tuesday or Wednesday from 2020.

**Mean jump a roll, by year:**

| Year | Mean jump |
|---|---:|
| 2015 | −0.16% |
| 2016 | −0.31% |
| 2017 | +0.24% |
| 2018 | +0.35% |
| 2019 | +0.29% |
| 2020 | −0.38% (2020-03 is −1.1%, in the Covid crash; uncertain) |
| 2021 | −0.05% |
| 2022 | +0.58% |
| 2023 | +1.19% |
| 2024 | +1.27% |
| 2025 | +1.12% |

**Limits:**
- The estimate carries the basis noise of an hour's break, about 0.05%.
- In March the NSX timestamps appear misaligned by an hour between the US and European clock changes. The March basis
  is the noisiest (2019-03, 2021-03, 2022-03, 2023-03).

## The adjusted series

**How it is built:**
- Every bar before a roll session is multiplied by exp(jump) of that roll. This is a ratio back-adjustment.
- The months are then rescaled exactly as before.
- The unadjusted series rebuilt this way from the raw files is identical to `nq1m_scaled.pkl`, to the tick.
- The adjusted file is `nq1m_scaled_roll_adjusted.pkl` (sha256 `0a61966c…`). It is not in the repository, being
  derived from the public raw files.
- Its `scale` column is the month's factor on the adjusted prices. Levels carried across a roll or a month boundary
  are therefore converted in continuous units.

**Effect at the roll sessions:**
- In 2022-12 to 2025-03 the session's opening gap falls from +1.0-1.4% to within ±0.25%.
- The remaining gaps are the market's own moves over the break (e.g. 2019-09-16, 2020-03-17, 2025-06-17).

## Use

**Candidate F's pre-registration (docs/CANDIDATE_F.md) fixes how it is used:**
- The deciding series stays the one D/E were judged on, so that F is compared with E on the same data and the same
  evaluation starts.
- The adjusted series is a declared sensitivity run (frozen B, D, D + F1, D + F2), reported beside it.

**D, D + E1 and D + E2 are not re-judged.** Their verdict stands, and the sensitivity run reports them only as a
reference.
