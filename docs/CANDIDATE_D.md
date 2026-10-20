# Candidates D and E: pre-registration (October 20, 2026)

**Committed before any D or E code or result exists.** It supersedes the two partial versions (4601d1d, 89e5c66).

**Sources:**
- The user's instruction of 10/20, "Implement an improvement of the bot using my latest standing decisions".
- The payoff rules the user fixed earlier the same day.
- **The brief (`mnq-bot-rebuild-brief.md`) never reached the session.** Every definition the brief would have supplied
  is fixed here instead and marked **[declared here]**. None of them was chosen after seeing a result: no D or E result
  exists.

**Discipline** (as docs/CANDIDATE_C.md):
- criteria fixed before testing;
- simulator results labelled apart from native NinjaTrader;
- a failed gate is reported as a rejection;
- nothing is retuned on the same data.

**Frozen B** (`release/MnqMomentumB_v1.1`) is the reference and is not changed. The repository and parity work
(docs/VERSIONS.md, docs/PARITY.md) is extended, not redone.

## 1. The shared position manager (every sleeve)

**Size: two MNQ contracts, or no trade.**
- The planned all-in risk of the two contracts must fit **$125**:
  `2 × (R_points × $2 + 2 × $0.95 + allowance_ticks × $0.50) ≤ $125`.
- **The declared slippage allowance:**
  - 4 ticks a contract for a market entry (2 at the entry, 2 at the stop);
  - 2 ticks for a limit entry (at the stop).
- So R may be at most **29.25 points** for a market entry and **29.75** for a limit entry.
- **If it does not fit, the signal is skipped.** The sizing never uses one or three contracts (an exact half needs
  two), never simulates fractions, and never tightens a structural stop to fit.

**R and risk:**
- R_points = |expected entry − initial stop|.
  - The expected entry is the decision bar's close for a market entry, the limit price for a limit entry.
  - The stop is the sleeve's structural stop, rounded to the tick away from the entry (never closer).
- **Price risk** is R_points × $2 × 2. **All-in planned risk** adds the commission and the allowance; it is at most
  $125.
- **$125 is the planned budget, not a guaranteed ceiling on the realized loss.** Gaps and slippage beyond the
  allowance can exceed it. Every completed position whose loss exceeds $125 is logged as an overrun, with its size.

**The initial stop:**
- An absolute price, sent with the entry and attached to both contracts.
- It is never widened, and the strategy never averages down.

**Breakeven at +1R:**
- **Trigger:** a completed bar's high (long) or low (short) reaches the actual average fill ± 1R.
- **From the next bar,** both contracts' stop is at least `fill + d × 1.50 points`.
- The 1.50 points is fee-aware: the round-trip commission (0.95 point a contract) plus 2 ticks of exit slippage
  (0.50), rounded up to the tick. A breakeven exit at the allowance therefore nets about zero, not a loss.
- **If the price is already back past that stop at the bar's close,** the position is closed at market at the next
  open ("Stop passed").

**Half at +2R:**
- One contract has a take-profit limit at `fill + d × 2R`, rounded away from the price to the tick.
- **It fills when price trades a tick through it,** at the limit, without slippage.
- **When it works:**
  - for a market entry, from the fill bar on;
  - for a limit entry, from the bar after the fill (on the fill bar the order of prices is unknown).
- If a bar reaches both a stop and this target, the stop fills first.

**The runner [declared here]:**
- After the half has filled, the remaining contract's stop is at least `best − d × 1R`, and never below the breakeven
  stop. `best` is the highest high (long) or lowest low (short) of the completed bars since the fill.
- It is updated at each bar's close, works from the next bar, is rounded toward the price, and never loosens.
- **There is no profit target.**

**Flat:**
- A market exit is sent at the close of the 15:54 bar and fills at the 15:55 bar's open ± slippage.
- **Earlier closes:**
  - the strategy takes no entries on the skip dates, which include half days;
  - a session that ends early in the data closes the position at the last bar's close ± slippage ("Session ended").

**No strategy-imposed daily profit cap, daily loss cap or loser-count cutoff.**

**At most three entry campaigns a day,** across all sleeves.
- A campaign is an entry that filled, wholly or in part. An entry cancelled with nothing filled is not one.
- One position or pending entry at a time.
- The worst planned day is 3 × $125.

**The account (the firm's limits, kept apart from the strategy's preferences):**
- The Apex 50K evaluation's $2,000 trailing threshold.
- Its highest equity includes open P/L, persists across sessions and restarts, and is never reset.
- At $3,000 of equity the position is closed and trading stops: the pass. At the threshold, trading stops: the breach.
- There is no reserve rule in D or E, so "reserve halts" are 0 by construction.

## 2. The candidates

| Name | Sleeves | Notes |
|---|---|---|
| Reference | Frozen B (B v1.1) | Unchanged: its own exits, 4 MNQ, $200, 3 losers |
| D | Noise momentum + Williams breakout | Both under the position manager |
| D + E1 | D + the sweep/reversal sleeve on higher-timeframe pools | |
| D + E2 | D + the sweep/reversal sleeve on the higher-timeframe pools **and** the session-level pools | The "additional session-level pools"; D + E2 minus D + E1 is the session pools' increment |

**D's entry parameters are B's, frozen:**
- **Noise sleeve:**
  - 14-session lookback; half-hour checks 10:00 to 15:30;
  - a long when a check closes above the upper line, a short below the lower;
  - no shorts before 14:00 on FOMC days; no entries on skip dates.
  - **The structural stop is B's line stop** at the decision: `upper × (1 − 0.24σ)` for a long, `lower × (1 + 0.24σ)`
    for a short. B's 25-point cap was a budget cap, so it is not used.
  - The entry is at market at the next bar's open.
- **Williams sleeve:**
  - levels at today's 09:30 open ± 0.5 × the previous session's 09:30-16:00 range;
  - the first bar starting 09:30-15:00 to reach a level gives the day's one chance;
  - a bar reaching both levels ends the day's chance, as does a level reached while a position or pending entry
    exists, or a signal that does not fit the budget;
  - shorts on.
  - **The structural stop** is 0.25 × the previous range from the expected entry.
  - The entry is at market at the next bar's open.

## 3. The sweep/reversal sleeve E [all of it declared here]

**A causal sequence:** known liquidity level → penetration → reclaim → confirmed five-minute structure break →
completed three-candle FVG → retrace entry.

**Bars:**
- 1-minute bars, New York time, the full electronic session.
- Five-minute bars aggregate the 1-minute bars by clock (:00-:04, :05-:09, …). A five-minute bar is complete when its
  last minute has closed, and only complete bars are used.

**Pools.** Each is known before the session's 09:30 open, so it is fixed for the day:
- **E1, higher timeframe:**
  - the previous session's 09:30-16:00 high and low;
  - the previous calendar week's 09:30-16:00 high and low (Monday to Friday sessions).
- **E2, session level** (from this session's electronic hours, by bar start):
  - overnight 18:00-09:29;
  - Asia 18:00-01:59;
  - London 02:00-08:29.
  - A pool needs at least one bar in its span.
- Each pool can give at most one setup a day.

**Penetration:**
- A 1-minute bar starting 09:35-14:30 trades at least one tick through a pool:
  - low ≤ level − 0.25 for a low pool (it sets up a long);
  - high ≥ level + 0.25 for a high pool (a short).
- Only a pool not yet penetrated today counts. The pool is then used.

**Reclaim:**
- A complete five-minute bar closes back on the other side: above the level for a low pool, below it for a high pool.
- It must come within 6 five-minute bars of the bar containing the penetration (that bar included).
- Otherwise the setup is dead.

**The BOS reference:**
- Fixed at the reclaim bar's close, and never changed afterwards.
- It is the most recent five-minute swing high (for a long; a swing low for a short) that formed before the
  penetration's five-minute bar and was **confirmed by the reclaim bar's close**.
- **A swing high:** a bar whose high is strictly above the highs of the 2 bars before it and the 2 bars after it. It is
  confirmed when the second bar after it completes. A swing low is the mirror image.
- No reference, no setup.

**BOS:**
- A complete five-minute bar closes beyond the reference: above it for a long.
- It must come no later than 12 five-minute bars after the penetration's bar. Otherwise the setup is dead.

**The FVG:**
- **A bullish three-candle FVG** in complete five-minute bars k−2, k−1, k: low[k] > high[k−2]. The gap is
  high[k−2] to low[k]. A bearish one is the mirror image.
- It counts if its first candle (k−2) is at or after the penetration's bar, and it completes at or before the decision.
- **The decision** is at the BOS bar's close if a qualifying FVG exists then. Otherwise it is at the first five-minute
  close, within 3 bars after the BOS, at which one exists. If none appears by then, the setup is dead.
- If several qualify, the most recently completed one is used.

**The retrace entry:**
- A limit order at the gap's proximal edge (low[k] for a long, high[k] for a short), placed at the decision.
- It works from the next 1-minute bar and fills when price trades a tick through it, at the limit, or at the open if a
  bar opens beyond it.
- **It is cancelled** if, before it fills:
  - 6 five-minute bars (30 minutes) pass;
  - price trades through the stop;
  - price reaches entry ± 2R;
  - 15:30 arrives;
  - or another position fills.
- **A fill that arrives while a cancellation is pending is kept and managed.**

**The structural stop:**
- The sweep extreme (the lowest low for a long, from the penetration's bar to the decision bar), minus 0.1 × ATR.
- ATR is the 14-period Wilder ATR of complete five-minute bars (true range with the previous close), as of the
  decision, rounded away to the tick.

**Room:**
- The nearest opposing pool of the candidate's pool set (above the entry for a long), still unpenetrated at the
  decision, must be at least `2R + 1.45 points` away (the +2R partial plus the round-trip cost allowance).
- A pool that is penetrated stays a valid room level.
- **Room only qualifies the entry. It never caps the runner.** There is no opposing-pool runner exit and no daily
  profit lock (both removed, as instructed).

**Session and news restrictions:**
- E decisions from 09:45 to 15:00 only.
- No E on FOMC announcement days, on NFP release days, or on the skip dates.
- These are fixed now and will not be loosened.

**Priority:**
- **Between sleeves:** noise, then Williams, then E. A signal that cannot be taken (a position or pending entry
  exists, the day's three campaigns are used, or it does not fit the budget) is skipped, not queued.
- **Between E setups:** the earliest decision first. On the same bar, an E1 pool before an E2 pool, then the order
  listed above, with lows before highs.

**Price levels on rescaled NQ:**
- Each month of the NQ file is scaled by its own factor. Every level carried across a month boundary is converted by
  the ratio of the two months' factors, from the raw NQ files. This covers prior-day and week levels, pools, swings,
  ATR's previous close, the Williams range and the noise previous close.
- On MNQ the factor is 1.

## 4. Data, dates and costs

**NQ decides the statistical gates** (the user's latest instruction: "NQ decides the statistical gates using
MNQ-equivalent $2-per-point economics"). Actual MNQ is the execution check.

**NQ:**
- NQ futures 1-minute, `mdelcristo/NQ-F_1min_OHLCV_Parquet`, full electronic hours, 2015-03 to 2025-06.
- Each calendar month rescaled to a 30,661 level (`nq1m_scaled.pkl`, sha256 `89c0b157…`). The rolls are the dataset's
  own (front month, undocumented).
- Sessions with missing 09:30-16:00 minutes get no new entries.
- Historical FOMC dates come from `research/fomc_dates.csv`, NFP dates from `research/nfp_dates.csv`. They are the same
  for every candidate, frozen B included.

**MNQ:**
- The user's exports: 09-26 to the 9/10 roll session, back-adjusted +284.50 points, then 12-26, full electronic hours,
  6/28 to 10/16/2026.

**This is development data, all of it.** Both histories were examined in earlier rounds (B's development); neither is
untouched.

**Warm-up and starts:**
- Every candidate starts its evaluation windows on the same sessions: the first session on which every sleeve is ready
  (14 complete sessions for the noise lines, one full previous week for E1), and every session after it.
- **Primary statistics: non-overlapping starts.** From the first common session, a new start at the first session at
  least 30 calendar days after the previous one, independent of outcomes.
- Overlapping starts (every session) are supplementary.
- A window counts as fully observed when no trading session falls between the end of the data and the window's end.

**Costs:**
- $0.95 a side a contract.
- **Slippage:** 2 ticks (the base, which decides) and 3 ticks (the stress, reported), on every market and stop fill.
  Limit fills have none.

## 5. Acceptance gates (NQ, non-overlapping starts, 2 ticks; all must pass)

| Gate | Requirement | Measured as |
|---|---|---|
| G1 | Evaluation pass rate **≥ 60%** | Passes ÷ fully observed non-overlapping starts. A window whose outcome depends on the order of prices inside a bar is never a pass. |
| G2 | Expiry **≤ 15%** | Expired ÷ the same starts |
| G3 | Worst window drawdown **≤ $1,500** | The largest fall of equity from its highest point, open P/L included, within any of those windows (start to outcome), on the replay's worst intrabar path |
| G4 | Measured win rate **≥ 50%** | Completed positions with net P/L > 0 ÷ all completed positions, over the continuous NQ run. A position counts once: its half and its runner combined. |
| G5 | Profit factor **≥ 1.35** | Gross profit ÷ gross loss of completed positions, continuous NQ run |

**The win-rate qualification is kept and reported beside G4.**
- Breakeven and partial exits do not make a strategy majority-winning.
- The share of completed positions that are scratches (|net| < 0.1R) is reported, with the win rate excluding them.

**Verdict:**
- A candidate is adopted only if G1-G5 all pass, and only on top of the parity requirement (section 6).
- Otherwise frozen B is kept and each failed gate is named. Nothing is retuned on this data.
- **The evaluation replay** follows `research/eval_sim.py`'s rules ($3,000, a $2,000 trail of the highest equity
  including open P/L, 30 calendar days, four intrabar price orders), extended to positions closed in two parts.

**Reported beside the gates** (each candidate; NQ, then MNQ separately):
- net expectancy after costs, and the average win and loss in R;
- intraday drawdown; evaluation pass / breach / expiry / reserve-halt;
- trades per eligible session, zero-trade sessions, and the distribution of entries a day;
- monthly (NQ: yearly) results, profit factor, and the dependence on the largest winners;
- **each sleeve's contribution:** its own positions' net, and the profitable trades of the earlier stage it displaces
  (taken in the earlier stage, not in the later one);
- every position's planned and realized risk, and the overruns;
- the 3-tick stress results.

## 6. Required before any result counts

1. **Parity:** the NinjaScript strategy (`MnqCandidateD.cs`) and the Python model agree trade for trade on the user's
   MNQ bars at 2 ticks, for D, D + E1 and D + E2. The simulator gets limit entries and exit executions for this.
2. **Causality tests:**
   - Every decision made up to time t is identical when every bar after t is removed. This is checked on many
     cut-offs.
   - Synthetic sequences check each step of the E chain and the position manager: the sizing and skip, the
     fee-aware breakeven from actual fills, exactly half at +2R, the trail, 15:55, three campaigns, and the pending
     entry kept until its cancellation or completion is confirmed, including a fill arriving during a cancellation.
3. **Units:** $2 a point and $0.50 a tick in sizing, stops, commission and evaluation equity.
4. **The single-source build** (`tools/build_release.py`) with sha256 sums, presets and the trade ledger.
5. **What ran where:**
   - Native NinjaTrader has not run D or E.
   - The results are the Python model's, parity-checked against the strategy's code on the NinjaTrader stand-in.
   - The preset includes the Strategy Analyzer and Playback settings for the user's native check: a granular fill
     resolution and a Playback forward run. Tick Replay alone does not establish fill accuracy.
