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

---

# Results (October 19, 2026, after the criteria above were committed in e1f9b35)

All figures are the **stand-in simulator's**. No NinjaTrader run of candidate C exists yet.
- **MNQ:** the traded contracts, 7/20 to 10/16/2026: 64 eligible sessions, 44 fully observed evaluation starts.
- **NQ:** 2015-03 to 2025-06: 2,571 eligible sessions, 2,641 fully observed starts.
- **Files:** `verification/candidate_c_mnq/`, `verification/candidate_c_nq/`. The script is `research/candidate_c.py`.

## The 40-trade native run (1/1 to 10/17, summary `2d625b0f-...11-09_PM.csv`)

**Only its summary was provided, so this is inferred, not confirmed from its Output.**
- **Which strategy:** almost certainly the rejected runner.
  - Commission is $199.50 for 40 trades: 105 contracts at $1.90, about 2.6 a trade. B always trades 4.
  - The largest winner, $1,788.20, matches the runner's +$1,784 winner on the stand-in, plus slippage.
- **Loaded data** (from the earlier native Outputs on the same DEC26 data): bars from 5/3. The warm-up completed
  5/21 16:00. 5/22 to 6/26 has no bars, so trading was possible only from 6/29: 77 sessions, not January to October.
- **When trading stopped:** "Longest flat period 74.77 days" and "Max. time to recover 107.78 days" (never
  recovered) put the last trade at about **8/3**. The net is $2,328.50, below the target, so the account was not
  passed.
- **The stand-in matches this:**
  - The runner on the user's MNQ bars at 0 ticks, evaluation from the first bar, also made its last entry on 8/3.
  - Every qualifying signal after that was refused for lack of room above the reserve. Candidate C's audit counts
    171; the runner's own Output lists only 90.
  - The other 81 checks were suppressed silently by the engine's hypothetical position. That is the defect C
    corrects in its Output.
- **Needed to confirm:** that run's NinjaScript Output and its Trades export.

## Before and after: B against candidate C1, MNQ (stand-in)

C0 (the earlier coupling) is identical to C1 in every figure here: no trade was recovered or displaced.

| | B, 1 tick | B, 2 ticks | C1, 1 tick | C1, 2 ticks |
|---|---:|---:|---:|---:|
| **Continuous research** (64 sessions) | | | | |
| trades; per session | 97; 1.52 | 97; 1.52 | 81; 1.27 | 81; 1.27 |
| sessions with 0 / 1 / 2 / 3+ trades | 58 / 5 / 5 / 33 % | 58 / 5 / 5 / 33 % | 58 / 5 / 11 / 27 % | 58 / 5 / 11 / 27 % |
| net; per eligible session | $13,219; $207 | $13,031; $204 | $7,112; $111 | $6,990; $109 |
| months (Jul / Aug / Sep / Oct) | −328 / +3,320 / +5,580 / +4,646 | −374 / +3,280 / +5,516 / +4,608 | −782 / +699 / +4,455 / +2,740 | −812 / +674 / +4,413 / +2,715 |
| profit factor | 2.58 | 2.54 | 2.39 | 2.35 |
| 5 largest winners' share of net; net without them | 72%; $3,643 | 73%; $3,455 | 82%; $1,313 | 83%; $1,191 |
| intraday drawdown (open P/L included) | $2,613 | $2,653 | $2,030 | $2,061 |
| losing streak; worst day | 6; −$629 | 6; −$635 | 5; −$314 | 5; −$317 |
| contracts a trade | 4.0 | 4.0 | 3.0 | 3.0 |
| **Evaluation replay** (44 fully observed starts) | | | | |
| pass / fail / expired | 24 / 6 / 14 | 24 / 6 / 14 | 18 / 0 / 26 | 18 / 0 / 26 |
| chance of passing (expirations counted) | 54.5% | 54.5% | 40.9% | 40.9% |
| expired, halted at the reserve | 0 | 0 | 6 | 6 |
| median days to pass | 13.5 | 13.5 | 17.5 | 17.5 |
| intraday drawdown in a window, median / worst | $1,401 / $2,146 | $1,421 / $2,168 | $1,254 / $1,612 | $1,264 / $1,637 |
| 21 unfinished starts: pass / fail / unresolved | 15 / 4 / 2 | 13 / 6 / 2 | 12 / 0 / 9 | 12 / 0 / 9 |

The 44 starts overlap: they are about 3 independent 30-day windows (2 non-overlapping starts fit in the period).

**NQ 2015-2025 (separate check, rescaled):**

| | B, 1 t | B, 2 t | C1, 1 t | C1, 2 t |
|---|---:|---:|---:|---:|
| trades per session; sessions with 0 / 1 / 2 / 3+ | 1.94; 42 / 14 / 10 / 35 % | 1.93; 42 / 14 / 10 / 35 % | 1.57; 42 / 14 / 18 / 27 % | 1.57; 42 / 14 / 18 / 26 % |
| net per eligible session; profit factor | $43.24; 1.22 | $35.69; 1.18 | $30.65; 1.26 | $23.40; 1.19 |
| 5 largest winners' share; intraday drawdown | 17%; $13,444 | 21%; $15,146 | 18%; $9,338 | 23%; $9,571 |
| losing streak; worst day | 11; −$629 | 11; −$635 | 11; −$351 | 11; −$354 |
| 2,641 starts: pass / fail / expired; chance of passing | 834 / 1,602 / 203; 31.6% | 794 / 1,643 / 196; 30.1% | 472 / 0 / 2,156; 17.9% | 431 / 0 / 2,197; 16.3% |
| fail on some price paths only | 2 | 8 | 13 | 13 |
| 124 non-overlapping starts: pass / fail / expired | 40 / 73 / 11 | 41 / 72 / 11 | 26 / 0 / 97 (+1 path-dependent) | 25 / 0 / 98 (+1) |

## What each correction changed

**1. Signals kept apart from the model's position (C0 → C1a):**
- **MNQ:** no trade changed.
  - C0's refusals included 26 checks blocked by the model's hypothetical position (73 in an evaluation from 7/20).
  - Each of those checks was still refused in C1, now for its real reason: the day's 2 losing positions, or no room
    above the reserve. Both refusals last the rest of the day or longer.
- **NQ:** 6 trades recovered and 1 displaced at 1 tick; 25 and 6 at 2 ticks.
  - The recovered trades lost money: −$631.60 and −$1,185.90.
  - Mechanism: the candidate rounds its stop to a whole tick toward the price, so its actual position is
    occasionally stopped a tick before the model's hypothetical one. C0 then stayed blocked by the model; C1 took the
    next qualifying check.
  - Evaluation passes changed by one start in each direction: C1 472 / 431 against C0 (B-protected's identical code
    path) 473 / 432.
- **Participation:** the correction does not raise it. Trade frequency is set by B's 12 half-hour checks, one
  position at a time, the 2-loser day, and the reserve.

**2. The pass counted only on realized profit (C1a → C1):** no outcome changed on MNQ or NQ.
- The take-profit set at the target fills at the target in a backtest, so the open-profit close rarely falls short.
- The rule matters live: partial fills, slippage on the closing order, a restart.

**3. Pending entries, partial fills, rejections, restarts:** no effect in a backtest; verified with the stand-in's
failure modes (`tests/test_candidate_c.py`, 21 tests).

## Against the pre-registered criteria

| Criterion | Result |
|---|---|
| K1: C1 equals B with the limits off; tests pass | **Pass.** Identical trades at 0 / 1 / 2 ticks on MNQ and on synthetic bars, in both signal modes |
| K2: recovered trades net positive (NQ at both slippages; MNQ only if 20 or more) | **Fail.** NQ −$631.60 (6 trades) and −$1,185.90 (25); MNQ 0 trades |
| K3: C1 passes ≥ C0 with no more certain fails, 44 MNQ starts | **Pass.** 18 = 18, 0 = 0 |
| A1: C1 passes ≥ B (24) with fails ≤ 6, 44 MNQ starts | **Fail.** 18 |
| A2: C1's NQ pass rate ≥ B's, all and non-overlapping starts | **Fail.** 17.9% vs 31.6%; 26 vs 40 of 124 |
| A3: net per session and net without the 5 largest winners positive | Pass |
| A4: worst intraday drawdown in the replay ≤ B's | Pass ($1,612 vs $2,146 MNQ; $2,042 vs $2,362 NQ) |

## Verdict

**Candidate C is rejected.**
- **The state correction (K2):** it recovers no trades on MNQ, and the few it recovers on NQ lose money.
- **C against B (A1, A2):** C passes far fewer evaluations than frozen B on both data sets.
  - It never certainly liquidates, and its worst day and drawdown are smaller.
  - But most of its non-passes are accounts that stop trading at the reserve and expire. An expired evaluation costs
    as much as a failed one.

**Frozen B stays the benchmark, unchanged.**
- B still does not meet the goal: about 61% of its NQ evaluations fail.
- Its trades arrive in bursts, not as 2-3 a day: on MNQ, 58% of sessions have no trade and 33% have 3 or more.

**What C's code still provides:** a correct execution-state implementation and an Output that accounts for every
qualifying check. Whatever candidate comes next can build on it; it does not make C a better strategy.

**Not done:**
- **Native runs:** no NinjaTrader run of C exists.
- **The 40-trade run:** explained only from its summary.
- **Untouched data:** no untouched MNQ data was available (03-26, 06-26).
