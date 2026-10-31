# E50 — v3.6 for a 50K evaluation: at most $300 lost per trade, profit uncapped (pre-registration)

Written and committed on 2026-10-31, before `research/e50_eval.py` was run.

## The user's request

- **$300 loss per trade at most**, with the profit on a trade uncapped.
- **As many trades a day as the signal gives.**
- **A 50K evaluation, and then the funded account, must not be lost.**

**The firm's rules are not known yet.** Assumed, from the user's earlier limits:
- a $2,000 end-of-day trailing drawdown that stops rising at the starting balance;
- a $1,000 daily loss limit;
- a $3,000 profit target.

## Rules (v3.6's entries, filters and lock, unchanged)

**What changes**
- **The loss cap is for the whole position:** `max_loss_per_trade` = $300.
  - The trade after a loser keeps the same cap (`after_loss_ml_mult` 1).
  - The line stop is used when it is closer.
- **No take-profit** (`take_profit` 0). A trade ends at its stop, at the breakeven lock, back inside the noise area, or
  at 16:00.
- **No limit on trades a day** (`max_losers` 0), apart from the $1,000 daily limit, which the engine enforces.
- **No size growth** (`profit_step` off), so the $300 cap always holds.

**Variants**
- Contracts: 1, 2 or 3 MNQ. At $300 for the position, the cap sits 150, 75 or 50 points away.
- Each also with v3.6's 2-noise-unit take-profit, for comparison.

That makes 6 variants.

## Evaluation replay

The trades do not depend on the account, so one run per data set is sliced by start date.
- An evaluation starts at the first trade on or after each start day: every 5th session of the history.
- **Pass:** the closed equity reaches +$3,000.
- **Fail:** the closed equity after any trade falls below the floor. The floor is the highest end-of-day equity so
  far (at least the start) less $2,000, and it stops rising at the start.
- Reported: pass %, fail %, still running at the data's end, and median trading days to pass.

## Selection and report

- **Selection:** the variant with the highest pass rate on NQ 2015-2025 and the index 2011-2026 (the average of the
  two), on 5-minute bars.
- The user's Jan 2025 – Oct 2026 window is not used to choose. It is reported once, on 5- and 30-minute bars:
  - net, winners, PF;
  - the largest single loss (to check the $300 cap);
  - the closed and end-of-day drawdown;
  - the evaluation pass rate.

## Results (2026-10-31; `verification/noise_v2/e50_5.csv`, `e50_30.csv`)

**Evaluation pass rate on the histories** (5-minute bars; the selection data):

| Contracts | Take-profit | NQ pass / fail | Index pass / fail | Average pass |
|---|---|---|---|---|
| 1 | 2.0 | 91.1% / 6.8% | 96.3% / 1.7% | **93.7% (selected)** |
| 1 | none (uncapped) | 87.6% / 10.4% | 93.3% / 4.6% | 90.5% |
| 2 | 2.0 | 69.3% / 28.7% | 70.2% / 28.5% | 69.8% |
| 2 | none | 56.9% / 41.0% | 68.6% / 30.0% | 62.8% |
| 3 | 2.0 | 58.0% / 39.7% | 61.7% / 37.4% | 59.9% |
| 3 | none | 47.9% / 49.9% | 56.6% / 42.4% | 52.3% |

**The user's window, Jan 2025 – Oct 2026 stand-in, 30-minute bars** (reported once):

| Contracts, take-profit | Net | Winners | PF | Largest loss | Largest win | EOD DD | Pass / fail | Median days to pass |
|---|---|---|---|---|---|---|---|---|
| 1, 2.0 (selected) | $8,357 | 55.4% | 1.79 | −$310 | $1,123 | $1,513 | 81.7% / 0% | 180 |
| 1, none | $8,852 | 55.6% | 1.87 | −$302 | $3,493 | $1,597 | 77.4% / 0% | 159 |
| 2, 2.0 | $13,451 | 57.3% | 1.61 | −$320 | $2,246 | $3,242 | 61.3% / 34.4% | 85 |
| 3, 2.0 | $17,397 | 53.7% | 1.54 | −$331 | $2,943 | $4,162 | 51.6% / 44.1% | 45 |

**Findings**
- **One contract never failed an evaluation** in the user's window, and it failed in 2-10% of starts in the histories.
  But it is slow: a median of 6-8 months to make the $3,000.
- **More contracts pass sooner but fail far more often**: about 1 start in 3 with 2 MNQ, and in 2-3 with 3 MNQ.
- **Uncapped profit vs the 2-unit take-profit:** about the same.
  - Uncapped keeps the big days (the largest win is $3,493 against $1,123), but passes slightly fewer evaluations
    on the histories.
- **The $300 cap is the stop, not a guarantee.** Slippage and gaps through the stop made the largest losses $302-439.
  A stop set at about $260 keeps the realized loss under $300.
- **$50,000 is not reachable under a $300 per-trade cap.** Profit scales with contracts, and 3 MNQ (the most that fits
  a $300 stop of reasonable width) made about $17k in the window, while failing nearly half the evaluations.

## E50b: limiting losing streaks (registered 2026-10-31, before its run)

**The user's request:** no consecutive losing trades.
- No rule can guarantee that, since any trade can lose.
- What a rule can do is stop trading for the day after a loss: `max_losers` 1. Then two losses never fall on the same
  day.

**Variants:**
- 1 MNQ, a $260 cap for the whole position;
- take-profit off or 2.0;
- `max_losers` 0 (no limit) or 1 (stop for the day after a loss).

That makes 4 variants. Everything else is as in E50.

**Reported:**
- the longest run of losing trades;
- how often a loss is followed by another loss (as a share of losses);
- the 50K evaluation pass and fail rates;
- net, winners and PF.

**Selection:** the highest average evaluation pass rate on NQ and the index, on 5-minute bars, as before.
- The user's window is reported once, on 30-minute bars.
- The selected variant becomes the Pine script's defaults (v3.8).

## E50b results (`verification/noise_v2/e50b_5.csv`, `e50b_30.csv`)

1 MNQ at a $260 cap.

| Take-profit, stop after a loss | NQ pass / fail (5-min) | Index pass / fail | Loss after a loss (NQ) | Longest losing run (NQ) |
|---|---|---|---|---|
| 2.0, no (selected) | 89.1% / 8.9% | 93.5% / 4.4% | 39.3% of losses | 8 |
| none, no | 88.9% / 9.1% | 93.0% / 4.9% | 40.1% | 8 |
| 2.0, yes | 76.3% / 20.3% | 82.1% / 5.2% | 40.2% | 7 |
| none, yes | 76.0% / 21.3% | 72.1% / 18.2% | 40.3% | 7 |

**Stopping for the day after a loss did not cut back-to-back losers.** The next loss simply came the next day: about
40% of losses were followed by another loss either way. It also passed fewer evaluations, so it is off.

- The largest realized loss at the $260 cap was $262-291, under $300.
- **The user's window, 30-minute bars, selected variant:**
  - net $8,215, 55.9% winners, PF 1.78, worst day −$417;
  - longest losing run 6;
  - 84% of evaluations passed and none failed.

## The daily limit at $900 instead of $1,000 (`e50c_daily900_*.csv`)

**The user's request:** never touch the firm's $1,000 daily limit, without stopping trading.
- At a $900 internal limit, each new trade's stop is cut to the room left (at least 20 points), so trading continues
  on smaller risk.
- **Worst day:** −$898 to −$902 on every set and bar length. There was no day at −$1,000 or worse; at $1,000 there was
  one −$1,012 day on 30-minute NQ.
- **The cost:** 30-minute NQ evaluations passed 74.7% instead of 82.1%. The index and the user's window were unchanged.

## Pine v3.8

`pine/mnq_noise_momentum.pine`'s defaults are now the selected variant:
- 1 MNQ, max loss $260 (also after a loser), take-profit 2.0, no loser limit;
- max loss a day $900;
- no trailing-drawdown sizing and no extra contracts;
- the evaluation tracker at a $3,000 target and a $2,000 end-of-day trailing drawdown.

The 155 Pine-against-Python parity tests pass.

## E50R: size each trade to its own stop at a fixed $260 risk (registered 2026-10-31, before its run)

**The user's request:** one account, the same rules ($300 a trade at most, under $1,000 a day, a small drawdown),
more profit.

**The lever:** v3.8 always trades 1 MNQ. Its $260 is a ceiling, and the line stop is often much closer.
- New option `risk_per_trade` R: contracts = floor(R / (the initial stop's distance × $2 + $2.24 costs)), from 1 up
  to `risk_max_qty`.
- The whole position's max loss is R, so the cap per contract is R / contracts.
- Everything else is v3.8, including the $900 daily budget with its squeeze. The lock trigger is 0.35 × the cap per
  contract, so it scales with the size.

**Variants:** R = $260; most contracts 3, 5 or 10. Each also with no take-profit. That makes 6 variants.

**Selection** (NQ 2015-2025 and the index 2011-2026, 5-minute bars):
- Among variants whose average evaluation fail rate is at most 10% (v3.8: 6.65%) and whose largest loss is under
  $300, the highest average net per year.
- If none qualifies, v3.8 stays.
- The user's window is reported once, on 30-minute bars.

## E50R results (`verification/noise_v2/e50r_5.csv`, `e50r_30.csv`): rejected, v3.8 stays

Sizing each trade to its own stop at $260 put on 1.4-1.8 contracts on average.

| 5-minute bars | v3.8 | Up to 3 MNQ | Up to 5 | Up to 10 |
|---|---|---|---|---|
| Net a year, NQ / index | $5,490 / $5,365 | $6,764 / $5,970 | $6,789 / $6,000 | $6,778 / $5,962 |
| Evaluations failed, NQ / index | **8.9% / 4.4%** | 18.9% / 19.1% | 20.3% / 20.0% | 20.0% / 20.1% |
| Largest loss | −$274.74 | −$306.95 | −$306.95 | −$306.95 |
| User's window: net (5 / 30-min) | $7,853 / $8,215 | $8,318 / $9,292 | $8,439 / $9,414 | $9,054 / $10,029 |

These rows are with the 2.0 take-profit; the no-take-profit rows are alike.

- **About 10-25% more profit a year, and about twice the failed evaluations.**
  - More trades risk close to the full $260, so losing runs reach the $2,000 floor sooner.
  - Gaps through stops pushed the largest loss past $300.
- **No variant meets the frozen rule** (fail rate at most 10%, largest loss under $300), so E50R is rejected.
- Even the best variant adds about $2,000 over the user's 21-month window, not the ~$40,000 more needed for $50,000.
