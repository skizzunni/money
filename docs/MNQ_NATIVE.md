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

**Scope of this check:** it covers the 20 October trades (10/1 to 10/16). At 0 ticks all 20 match exactly; at 1 and
2 ticks 19 of 20 match exactly and the totals match to the cent. It does not cover July to September: no native
NinjaTrader run on 09-26 bars exists to compare against.

**A correction follows from this.** NinjaTrader's slippage setting slips stop exits too. The earlier statement that it
left most stops unslipped (docs/REFERENCE.md section 4b) misread fills whose stop is set in ticks from an
already-slipped entry. It is corrected there and in `release/REPORT.md`.

## Test 2: control B in the 50K evaluation - executed (the stand-in simulator on the user's MNQ bars)

**This is the stand-in simulator running on the user's MNQ bars, not a NinjaTrader run.** NinjaTrader reproduced it
only for the 20 October trades (test 1). Script: `research/mnq_eval.py`.

**Setup:**
- **Warm-up:** 6/29 to 7/17, the first 14 full sessions.
- **Evaluation starts:** every session from 7/20. The 4- and 2-contract runs use identical start dates.
- **Fully observed starts:** the 44 sessions from 7/20 to 9/17, whose 30 days end by 10/16. **Later starts** (9/18 to
  10/16) are shown separately: they resolve only if the outcome came before the data ends.

**Accounting (corrected, docs/EVALUATION.md):**
- Each position follows a valid price path, with nothing after an exit in its bar.
- Stops crossed at the open fill there.
- The trail is checked at every price point and after every commission.
- Four valid paths are tried.

| Control B | Net (7/20-10/16) | Profit factor | Closed DD | 44 fully observed starts: pass / fail / expired | Later starts (21): pass / fail / unresolved | Back to back pass / fail / expired / unresolved |
|---|---:|---:|---:|---|---|---|
| 4 MNQ / $200, 1 tick | $13,218.80 | 2.6 | $2,075.20 | 24 / 6 / 14 | 15 / 4 / 2 | 4 / 1 / 1 / 0 |
| 4 MNQ / $200, 2 ticks | $13,030.80 | 2.5 | $2,099.20 | 24 / 6 / 14 | 13 / 6 / 2 | 4 / 2 / 1 / 1 |
| 2 MNQ / $100, 1 tick | $6,609.40 | 2.6 | $1,037.60 | 14 / 0 / 30 | 4 / 0 / 17 | 1 / 0 / 2 / 1 |
| 2 MNQ / $100, 2 ticks | $6,515.40 | 2.5 | $1,049.60 | 14 / 0 / 30 | 4 / 0 / 17 | 1 / 0 / 2 / 1 |

- No window's outcome, or its day, depends on the order of prices inside a bar.
- The outcome of every start, all four runs side by side: `verification/mnq_native_eval_by_start.csv`.
- **The fixes changed no MNQ outcome.** The earlier replay's 63 resolved windows (39 pass / 10 fail / 14 expired at
  4 MNQ, 1 tick) are the same 63 here (24 + 15 / 6 + 4 / 14).

## What it means

**On the user's MNQ bars, July to October 2026, the simulator's control B passed more often than it failed.** Of the
44 fully observed starts at 4 MNQ: 24 passed, 6 failed and 14 expired (at both 1 and 2 ticks). Back to back: 4 of 6.

**This is the most direct evidence so far, and also the weakest base for a decision:**
- **It is about 3 independent 30-day windows.** The 44 fully observed starts overlap almost completely.
- **It is the period whose results chose B over the combined strategy,** so it is development data, not validation.
- **Over ten years of NQ (substitute, rescaled data), the same strategy and rules fail about twice as often as they
  pass** (docs/EVALUATION.md, docs/DEVELOPMENT.md).

The two disagree. Three good months of MNQ do not overturn ten years of NQ. Nor does the NQ data prove that MNQ in
2026 behaves the same.

**The only evidence that can settle it is new: the frozen practice test** (`release/MnqMomentumB_v1`, preset
B-PRACTICE-v1), judged by the rules defined in docs/NATIVE_RUNS.md section 8.
