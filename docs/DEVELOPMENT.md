# One development attempt: B + a second lock step (October 18, 2026)

## 0. Pre-registration (written and committed before any candidate result exists)

**Control:**
- Frozen B (`release/MnqMomentumB_v1`): momentum only, 4 MNQ, $200 max loss.
- Lock at 1R (25 points) moves the stop to entry + 2.5 points.
- Take-profit 1.5 noise units, 3 losers a day, flat by 16:00.

**The one change (candidate B2):** once open profit reaches 2R (50 points; R = the $200 cap / 4 / $2), the stop moves
to entry + 1R (25 points). Everything else is unchanged, including the first lock.
- **Why:** the giveback diagnosis (section 1).
- **Its parameters are not tuned:** both are the strategy's own R unit, 2R and 1R.

**Data, decided before running:**
- **Development, used for the diagnosis and the choice:** NQ futures 2015-03 to 2020-12.
- **Validation:**
  - NQ futures 2021-01 to 2025-06;
  - the NSXUSD index 2025-07 to 2026-09.
- **Data treatment:**
  - Both sets are rescaled each month to today's level.
  - NQ is the front-month series with its rolls as in the dataset (mdelcristo/NQ-F_1min; the roll rule is the
    dataset's own and undocumented).
  - Sessions with missing minutes get no new trades.
- **These validation periods were used in earlier rounds for other decisions. They are not genuinely new data:** this
  change has not been seen on them. The only genuinely new data is the forward test (and MNQ bars not yet seen).

**Costs:** $0.95 a side; slippage 1 and 2 ticks on every market and stop fill. The control and the candidate run on
the same data, dates, warm-up and settings, each as a complete rerun on the stand-in.

**Evaluation** (as in docs/EVALUATION.md):
- $50,000, pass at +$3,000, fail at the highest equity (unrealized included) less $2,000, 30 calendar days.
- Each attempt stops at its first pass, breach or expiry. One attempt starts every session (overlapping), and the
  attempts are also run back to back.
- Equity is followed minute by minute; both orders of each bar's high and low are tried.

**Acceptance criteria.** The candidate replaces the control only if, on validation, across the four runs (NQ and the
index, at 1 and 2 ticks), **all** of these hold:
1. **Net after costs:** at least the control's in 3 of 4 runs, and summed over the 4.
2. **Profit factor:** at least the control's in 3 of 4.
3. **Closed-trade drawdown:** no larger than the control's in 3 of 4.
4. **Evaluation:** pass rate higher **and** fail rate lower than the control's in 3 of 4 (overlapping starts).

**It is suitable for the evaluation** (a separate, absolute bar) only if, on validation at 1 and 2 ticks on both
datasets, its evaluations pass more often than they fail.

If any criterion fails, the change is rejected and the control stays as it is. The development-period results are
reported but do not decide.
