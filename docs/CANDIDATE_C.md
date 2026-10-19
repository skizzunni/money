# Candidate C: B's signals and exits with correct execution-state handling (pre-registration, October 19, 2026)

Written and committed **before any test of candidate C was run.** Frozen B (`release/MnqMomentumB_v1`, sha256
`1fbdcea0...` strategy, `e5a1ec0c...` engine) is the benchmark and is not changed. The runner candidate is rejected
(docs/RUNNER.md).

**A correction to the premise.** The drop from 24 to 18 passes on the 44 MNQ starts did not come from the runner exit:
B-protected (B's exits with the same sizing and protections) also passed 18. It came from the sizing and account
protections, mostly accounts halted at the reserve. Candidate C keeps those protections, so it starts from 18 (C0
below), not from 24.

## The trading requirements (fixed for the whole session)

- **Signal (objective, known before entry):**
  - B's half-hour checks 10:00 to 15:30 New York: a completed check bar closing above the upper noise line (long) or
    below the lower one (short).
  - The engine needs its 14 full sessions.
  - No signal on skip dates; no short before 14:00 on Fed days.
  - The entry is at the next bar's open.
- **One position at a time.** A re-entry needs a fresh qualifying check after the previous position has closed. No
  entry is ever made to reach a trade count; 0 and 1 trade days are normal.
- **Before each entry:**
  - the trigger is the check close;
  - the invalidation is B's line stop: back inside the line, past a 0.24 noise-unit buffer;
  - the protective stop is the closer of that line and 25 points, sent with the entry in ticks from the fill;
  - the size is min(4, floor(budget / (2 × stop points + 2 × $0.95 + 4 ticks))).
  - The budget is the smallest of $200, half the room above the account reserve, and what is left of the day's $400
    backstop.
  - The stop is never widened. The strategy never averages down and never sizes up to recover.
- **Exits:** B's, unchanged:
  - line stop / 25-point cap;
  - lock at +25 points to entry + 2.5;
  - stop only tightens;
  - take-profit 1.5 noise units.
  - Plus: flat by 15:55 (earlier on short sessions); the account reserve; close at the evaluation target.
- **Account:**
  - $3,000 target, $2,000 intraday trail of the highest equity including open P/L, persisting across days, 30
    calendar days;
  - $300 reserve;
  - no entry after 2 losing positions in a day.

## The corrections under test

1. **Signals separated from the hypothetical portfolio (C1a).**
   - **Before (C0, = B-protected):** an entry was sent only when B's engine model, which keeps its own hypothetical
     position, signalled. A refused entry left the model "in a trade", and later checks were suppressed while the
     actual strategy was flat.
   - **After:** each check is qualified from the market data alone (the lines, the close, the dates). The actual
     order is gated only by the actual position, pending entry orders, executions and the risk limits.
2. **The evaluation counts as passed only when executions confirm it (C1 = C1a + this).**
   - **Before:** an open profit past the target closed the position and stopped the strategy for good, even when
     the exit fill left realized profit below $3,000.
   - **After:** only realized net profit of at least the target (account cash or closed trades) marks the pass.
     Otherwise trading continues on fresh signals.
3. **Execution state (no effect in a backtest; tested with the stand-in's failure modes):**
   - pending entry orders block a new entry;
   - partial fills are managed at the filled quantity;
   - a rejected entry leaves no position and no hypothetical one;
   - a rejected order in a position closes it, retried each bar;
   - restarts keep the highest equity, the pass and the day's losers.

## Tests (all on the stand-in simulator; NinjaTrader results will be labelled separately)

**Data:**
- the user's MNQ traded-contract bars: 09-26 to the 9/10 roll session, then 12-26, 09-26 back-adjusted;
- $0.95 a side; slippage 1 and 2 ticks.
- A separate check on NQ 2015-03 to 2025-06, rescaled.

**Continuous research:**
- One run per configuration over the whole history.
- The per-trade sizing, the daily limits and the 15:55 flat are on. The evaluation-account limits (target, trail,
  reserve) are off, because they depend on where an evaluation starts.
- **Eligible sessions:** every session from the first possible trade (7/20 on MNQ) with a 09:30 bar, skip dates
  excluded.
- **Reported:**
  - trades per eligible session and the share of sessions with 0 / 1 / 2 / 3+ trades;
  - net and net per eligible session, monthly;
  - profit factor, and the five largest winners' share of net;
  - intraday drawdown (open P/L included), losing streak, worst day;
  - the trades C1 has that C0 has not ("recovered"), and the reverse, each with their own results.

**Evaluation replay:**
- For B, C0, C1a and C1, from every session (identical starts) until the first pass, breach or expiry.
- `research/eval_sim.py` rules; the candidate's protections run from each start.
- Fully observed starts are reported apart from unfinished ones.
- The chance of passing counts expirations (pass / fully observed starts).
- Windows whose outcome depends on the intrabar price path are reported separately and never counted as passes.

## Acceptance criteria (decided now)

**The state correction (C1 against C0) is accepted into the candidate only if all hold:**
- **K1:** with every new limit off, C1 trades exactly like B (stand-in, MNQ bars at 0 / 1 / 2 ticks), and every
  stand-in test passes.
- **K2:** the recovered trades' net after costs is positive at 1 and 2 ticks in the continuous research on NQ.
  - On MNQ it must also be positive if there are at least 20 recovered trades. With fewer, the MNQ figure is
    reported as too few to judge.
- **K3:** on the 44 fully observed MNQ starts, at each slippage, C1 passes at least as many as C0 and has no more
  certain fails.

**C1 replaces B for the practice account only if K1-K3 hold and also:**
- **A1:** on the 44 MNQ starts, at each slippage, C1 passes at least as many as B (24) with no more certain fails than
  B (6).
- **A2:** on NQ, C1's pass rate is at least B's on all starts and on the 124 non-overlapping starts, at each
  slippage.
- **A3:** in the continuous research, net per eligible session is positive and the net without the five largest
  winners is positive, at each slippage, on MNQ and NQ.
- **A4:** in the replay, C1's worst intraday drawdown over fully observed windows is no larger than B's.

**Trade frequency** is reported against the preferred 2-3 a day but is not a criterion. Additional trades count only
through K2.

**If a criterion fails, the result is stated as a rejection;** nothing is retuned on this data to rescue it.
