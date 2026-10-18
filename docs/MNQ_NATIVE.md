# The user's native MNQ bars: coverage, a stand-in check, and control B in the evaluation (October 18, 2026)

## Data - executed

**The user's NinjaTrader exports** (Last, 1 minute; time stamps UTC, bar end):

| Contract | Bars | Range (New York) | Sessions 09:30-16:00 | Full sessions | Gaps |
|---|---:|---|---:|---:|---|
| MNQ 09-26 | 75,419 | 6/28 18:00 to 9/11 16:59 | 54 | 52 | 1 minute missing on 8/20; 9/7 Labor Day early close |
| MNQ 12-26 | 36,790 | 9/10 00:00 to 10/16 16:59 | 27 | 25 | 1 minute missing on 9/10 and 9/11 |

**Traded-contract series** (`research/mnq_bars.py`):
- 09-26 through the session of the roll date, 9/10 (eight days before the 9/18 expiry); 12-26 from the 9/11 session.
- 09-26 is back-adjusted by +284.50 points, the 12-26 minus 09-26 difference at the 9/10 16:00 close, so the roll does
  not show as a jump. Point moves are unchanged.
- 7/3 is a holiday.
- **Not provided:** 06-26 and 03-26. No MNQ data before 6/28 is here, so nothing here is untouched validation data.

## Test 1: the stand-in against native NinjaTrader on identical bars - executed

`research/mnq_reconcile.py`:
- **Same:** strategy file, MNQ 12-26 bars, settings, commission and slippage.
- **Compared:** the user's three native B runs started 9/11 (trading 10/1 to 10/16), rebuilt from their fills.

| Slippage | Native | Stand-in | Trades identical |
|---|---|---|---|
| 0 | 20 trades, $4,684.00 | 20 trades, $4,684.00 | 20 of 20: entry, exit price and minute |
| 1 tick | 20, $4,646.00 | 20, $4,646.00 | 19 of 20 |
| 2 ticks | 20, $4,608.00 | 20, $4,608.00 | 19 of 20 |

The one difference (10/16 11:31, short) is a tick at entry and a tick at exit in opposite directions, so the dollars
are the same.

**The stand-in reproduces NinjaTrader on MNQ bars.**

**A correction follows from this.** NinjaTrader's slippage setting slips stop exits too. The earlier statement that it
left most stops unslipped (docs/REFERENCE.md section 4b) misread fills whose stop is set in ticks from an
already-slipped entry. It is corrected there and in `release/REPORT.md`.

## Test 2: control B in the 50K evaluation on the traded contracts - executed

`research/mnq_eval.py`.

**Setup:**
- **Warm-up:** 6/29 to 7/17, the first 14 full sessions.
- **Evaluation starts:** every session from 7/20; 63 resolved before the data ends on 10/16.
- **Rules as in docs/EVALUATION.md:**
  - $3,000 target (the strategy's own close at $3,025);
  - $2,000 trail including unrealized peaks;
  - 30 calendar days;
  - minute equity, both orders of each bar.
- **Costs:** $0.95 a side; slippage 1 and 2 ticks.

| Control B | Trades (7/20-10/16) | Net | Profit factor | Closed DD | Evaluations pass / fail / expired (of 63, overlapping) | Back to back pass / fail / expired | Median days to pass |
|---|---:|---:|---:|---:|---|---|---:|
| 4 MNQ / $200, 1 tick | 97 | $13,218.80 | 2.6 | $2,075.20 | 39 / 10 / 14 | 4 / 1 / 1 | 11 |
| 4 MNQ / $200, 2 ticks | 97 | $13,030.80 | 2.5 | $2,099.20 | 37 / 12 / 14 | 4 / 2 / 1 (1 unresolved) | 9 |
| 2 MNQ / $100, 1 tick | 97 | $6,609.40 | 2.6 | $1,037.60 | 18 / 0 / 30 (48 resolved) | 1 / 0 / 2 (1 unresolved) | 16.5 |
| 2 MNQ / $100, 2 ticks | 97 | $6,515.40 | 2.5 | $1,049.60 | 18 / 0 / 30 (48 resolved) | 1 / 0 / 2 (1 unresolved) | 19.5 |

- No outcome depended on the order of a bar's high and low.
- The window-by-window results for 4 MNQ at 1 tick are in `verification/mnq_native_eval_windows_4mnq_1tick.csv`.

## What it means

**On the user's own MNQ, July to October 2026, control B passed the evaluation more often than it failed.** It
passed 39 times against 10 at 1 tick, and 4 of 6 back to back.

**This is the most direct evidence so far, and also the weakest base for a decision:**
- **It is about 3 independent 30-day windows.** The 63 starts overlap almost completely.
- **It is the period whose results chose B over the combined strategy,** so it is development data, not validation.
- **Over ten years of NQ (substitute, rescaled data), the same strategy and rules fail about twice as often as they
  pass** (docs/EVALUATION.md, docs/DEVELOPMENT.md).

The two disagree. Three good months of MNQ do not overturn ten years of NQ. Nor does the NQ data prove that MNQ in
2026 behaves the same.

**The only evidence that can settle it is new: the frozen practice test** (`release/MnqMomentumB_v1`, preset
B-PRACTICE-v1), judged by the rules defined in docs/NATIVE_RUNS.md section 8.
