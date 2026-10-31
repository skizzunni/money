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
