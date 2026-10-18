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

## 1. Diagnosis of B - executed (development data only: NQ 2015-03 to 2020-12, stand-in, $0.95 a side, 1 tick)

Full output: `verification/diagnose_b_development.txt`. 2,704 trades.

| Suspect | Evidence | Verdict |
|---|---|---|
| Trading costs | ≈ $11.6 of each trade's ≈ $35 edge before costs (33%) | Large, but not the failure |
| Repeated entries | 1st / 2nd / 3rd+ trade of the day: $15.6 / $30.9 / $25.0 average | Not a weakness |
| Sideways markets | The most sideways half of days lose $77k, the directional half make $141k | Real, but known only at the close; no real-time filter without a search |
| Stop placement | Nearly every loser exits at the 25-point cap; 70% later go 25+ points their way | A wider stop raises the risk per trade, against the account's trail |
| **Profit giveback** | 855 trades (32%) reached +25 to +60 points and kept 0.4-2.5 | **Chosen.** On an intraday trail it also eats the cushion: the peak raises the threshold, the giveback lowers equity |

## 2. Result - executed (stand-in, complete reruns; not native NinjaTrader)

Files: `verification/b2_compare.csv` and `.txt`. Candidate code: `verification/candidate_b2_rejected.patch`.

| | Control B, 1 tick | Candidate B2, 1 tick | Control B, 2 ticks | Candidate B2, 2 ticks |
|---|---:|---:|---:|---:|
| **Validation: NQ 2021-01 to 2025-06** | | | | |
| Net after costs | $48,719 | $32,814 | $40,662 | $24,486 |
| Profit factor | 1.21 | 1.13 | 1.18 | 1.10 |
| Closed-trade drawdown | $10,410 | $9,185 | $11,115 | $9,478 |
| Longest losing streak | 9 | 9 | 9 | 9 |
| Evaluation pass / fail / expired (1,157 overlapping starts) | 32.8% / 63.5% / 3.6% | 24.5% / 65.1% / 10.4% | 31.8% / 64.4% / 3.8% | 24.6% / 66.0% / 9.4% |
| Back to back, pass / fail / expired | 39 / 82 / 4 | 24 / 67 / 8 | 37 / 83 / 4 | 24 / 70 / 8 |
| **Validation: index 2025-07 to 2026-09** | | | | |
| Net after costs | $3,279 | $5,712 | $2,293 | $4,124 |
| Profit factor | 1.07 | 1.11 | 1.05 | 1.08 |
| Closed-trade drawdown | $9,912 | $8,908 | $10,349 | $9,619 |
| Longest losing streak | 7 | 7 | 7 | 7 |
| Evaluation pass / fail / expired (323 starts) | 21.5% / 63.4% / 15.1% | 17.0% / 53.9% / 29.1% | 17.7% / 68.1% / 14.2% | 17.0% / 55.2% / 27.8% |
| **Development: NQ 2015-03 to 2020-12** (reported, not deciding) | | | | |
| Net / evaluation pass-fail | $62,455 / 30.9%-58.9% | $58,570 / 30.2%-54.6% | $51,095 / 29.2%-61.1% | $49,109 / 27.7%-59.1% |

**Minute-bar sequencing:** no evaluation outcome depended on the order of a bar's high and low. The stand-in fills a
trade's stop before its take-profit when one bar reaches both.

**Against the pre-registered criteria (validation, 4 runs):**
1. Net at least the control's in 3 of 4 and summed: **2 of 4; $67,136 against $94,953. Failed.**
2. Profit factor at least the control's in 3 of 4: **2 of 4. Failed.**
3. Closed drawdown no larger in 3 of 4: **4 of 4. Met.**
4. Pass rate higher and fail rate lower in 3 of 4: **0 of 4. Failed.**
5. Suitability, passes more often than fails: **0 of 4** (the control: also 0 of 4). **Failed.**

**B2 is rejected. The control is unchanged:** the repository's strategy files are again the frozen release
(`release/MnqMomentumB_v1`, same sha256).
- The second lock did reduce drawdown.
- It cut the large winners that carry the edge: on NQ validation the net fell by a third and passes fell from 33% to
  25%.

## 3. Where the control stands

**Positive expectancy after costs: yes on NQ, weak on the index.**
- On NQ validation (2021-2025), B makes $48,719 at 1 tick and $40,662 at 2: profit factor 1.21 and 1.18, about $43 a
  session at 4 MNQ.
- On the index's 15 months it makes $3,279 and $2,293: profit factor 1.07 and 1.05, barely above costs.
- Both are substitute data, rescaled. Natively (MNQ, 6/29 to 10/16) it made $12,889 at 1 tick over 77 sessions.

**Suitable for this evaluation: no.** On every dataset and slippage it fails about twice as often as it passes.

The reason is structural:
- The expected gain over a 30-day window (about 21 sessions × $43 ≈ $900 at 4 MNQ) is a third of the $3,000 target.
  A pass therefore needs a lucky run.
- The $2,000 trail, which follows unrealized peaks, is reached first about two times in three.
- More size raises both the gain and the swings, pushing toward a coin flip that hits the trail first.
- Less size mostly runs out of time (docs/EVALUATION.md).

Passing reliably needs a much larger edge for the same risk. Neither the control nor this change has it.

## 4. What needs the user's MNQ bars, and the exact export

**Two tests need them; nothing else here does:**
1. The control's evaluation replay on native MNQ prices, with unrealized peaks.
2. Checking the stand-in against NinjaTrader on identical bars.

**Export from NinjaTrader** (Tools → Historical Data → Export; Data type Last; Interval Minute):
- **MNQ 09-26: 6/1/2026 to 9/11/2026.** The contract actually traded until the September roll.
- **MNQ 12-26: 9/1/2026 to 10/16/2026.** The overlap shows the roll.
- **MNQ 06-26 and MNQ 03-26, for whatever dates NinjaTrader has** (January to June 2026). That is the only MNQ data
  not yet used for any choice here.

**Rollover method:** each contract is used from the session after the previous one's roll date (8 days before
expiry), and the roll is documented in the result.
