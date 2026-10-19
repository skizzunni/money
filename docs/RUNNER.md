# Candidate: B's entries with risk-budget sizing, account protection and a runner exit (October 19, 2026)

Status: **built and tested on the stand-in simulator; not run in native NinjaTrader.** Frozen B
(`release/MnqMomentumB_v1`, sha256 unchanged) is the comparison and is not modified.

## 1. The rules as implemented (`ninjatrader/Strategies/MnqMomentumRunner.cs`)

**Entries (B's, unchanged):**
- B's own engine (`AddOns/MnqNoiseEngine.cs`, unchanged), with B's settings: noise band, 14-session warm-up,
  half-hour checks 10:00-15:30, both directions, B's skip and Fed dates. The breakout is not part of it.
- One position at a time. Position, quantity and average price come from NinjaTrader's Position, which is built from
  the executions.
- A signal arriving while the candidate still holds a position is not taken.

**Risk before each entry:**
- Stop distance = B's protective stop (the noise-line stop or the 25-point cap, whichever is closer), in whole ticks.
- Risk per contract = stop points × $2 + 2 × $0.95 commission + 4 ticks reserve (2 at the entry, 2 at the stop).
  That is 2 × points + $3.90.
- Budget = the smallest of:
  - $200;
  - half the room above the reserve line;
  - what is left of today's $400 backstop after the day's realized result.
- Contracts = min(4, floor(budget / risk per contract)). If not even one contract fits, there is no trade.
  - Example: a 25-point stop is $53.90 a contract, so 3 contracts ($161.70).
- The stop goes in, in ticks from the fill, before the entry. It never widens, and the strategy never adds to a
  position.
- The reserve is used for sizing only. Results are the fills' P/L less the actual commission; slippage is not charged
  twice.

**Exits:**
- **B's protections:**
  - the protective stop from the fill: the noise line, at most 25 points;
  - the lock: at +25 points the stop moves to entry + 2.5;
  - the stop only ever tightens.
- **Runner (Runner exit on):**
  - no take-profit of its own;
  - R = the fill to the initial stop, fixed for the position;
  - once the best price since the entry (completed bars from the fill on) is 2R past the fill, a trail sits at
    best − 3 × ATR(14) for a long (best + 3 × ATR for a short);
  - ATR(14) is Wilder's, on completed 5-minute bars of 09:30-16:00;
  - the stop is the tighter of the trail and B's stop, rounded to a tick toward the price, and never loosens;
  - a new stop applies from the next bar.
  - The settings 3 × ATR, 2R and 14 bars were chosen before the test; no alternatives were tried.
- **B-protected (Runner exit off):** B's take-profit of 1.5 noise units from the fill.
- **Flat by 15:55 New York**, or 5 minutes before an earlier session end (from NinjaTrader's session iterator). No
  entry after that time.

**Account (evaluation profile: $3,000 target, $2,000 intraday trail, 30 calendar days):**
- Highest equity: closed plus open P/L at each completed bar's best price, from the evaluation start.
  - Live, it is remembered in `Documents\NinjaTrader 8\MnqNoiseMomentum\runner-account-<account>.txt` with the pass
    and today's losers, so a restart keeps them.
  - The threshold Apex shows can be entered as a floor.
- Liquidation line = highest equity − $2,000. Reserve line = liquidation line + $300.
- If an open position's stop would let equity fall below the reserve line, the stop moves up to the reserve line's
  price, or the position is closed at market if the price is already past it.
- No entry after 2 losing positions in a day. Positions are counted once each, however many fills they had.
- Once realized profit reaches the target, everything is closed and the strategy stops for good. The take-profit
  sits at $3,025 realized, a $25 margin.
- **Our own controls, not Apex's.** Apex's current evaluation has no daily loss limit and no minimum days. All these
  limits are planned: a gap or a failed order can exceed them.

**Orders:**
- A rejected order while in a position closes the position at market, sent again at each bar until flat.
- A rejected entry leaves no position.
- Every signal not taken prints its time and reason to the Output.

## 2. Tests (`tests/test_runner.py`, stand-in) - executed

All of these pass:
- With every new limit off, the candidate makes B's trades exactly: the same trades, fills and P/L.
  - Synthetic bars in the tests.
  - The user's MNQ bars at 0, 1 and 2 ticks: 98 / 97 / 97 trades, identical to the cent.
- **Sizing:** the contracts equal the formula's for every entry; a $20 budget skips every signal where one contract
  doesn't fit.
- **The trail**, against an independent ATR computation:
  - the stops are unchanged until 2R;
  - from then on, each stop is the tighter of the untrailed stop and the best trail so far;
  - no stop ever loosens.
- **Flat time:** by 15:55, and by 12:55 on a 13:00 early close.
- **Daily limits:** no entry after 2 losing positions, including positions filled in two parts; each entry's planned
  risk fits within the $400 backstop.
- **Target:** the strategy stops at the evaluation target.
- **Reserve:** stops tighten or the position closes when an outside balance drop threatens the reserve; entries stop
  when the room is gone.
- **Orders and restarts:**
  - a rejected stop closes the position, and a rejected close is sent again;
  - a rejected entry leaves no position;
  - a remembered pass, a remembered peak, and an entered threshold all survive a restart.
- **Entries:** every entry is one of B's.
- **Setup:** anything but a 1-minute chart is refused.

## 3. Comparison - executed (stand-in simulator; not native NinjaTrader)

**Setup:** `research/runner_compare.py`.
- **Configurations:**
  1. **original B** (frozen, 4 MNQ);
  2. **B-protected:** B's exits with the new sizing and account protections;
  3. **runner:** the runner exit with the same sizing and protections.
- **Costs:** $0.95 a side; 1 and 2 ticks of slippage on every market and stop fill.
- **Evaluations:** one per session, from identical start dates for all three, replayed with `research/eval_sim.py`
  (valid price paths, the trail checked after every fill and commission).
  - The candidates' protections depend on the start, so each start is a separate run.
  - Each per-start run uses a 35-day warm-up slice. On MNQ this gives results identical to full-file runs.
- **Trading statistics:** back-to-back attempts (each starts the session after the previous outcome), every trade up
  to its attempt's outcome.
- **"Halted":** an evaluation that expired with its last signal refused because no contract fitted above the reserve.

### MNQ, the contracts traded (7/20 to 10/16/2026; 44 fully observed starts 7/20 to 9/17)

| | 1 original B, 1 t | 1 original B, 2 t | 2 B-protected, 1 t | 2 B-protected, 2 t | 3 runner, 1 t | 3 runner, 2 t |
|---|---|---|---|---|---|---|
| **44 starts: pass / fail / expired** | **24 / 6 / 14** | **24 / 6 / 14** | **18 / 0 / 26** | **18 / 0 / 26** | **18 / 0 / 26** | **18 / 0 / 26** |
| of the expired: halted at the reserve | 0 | 0 | 6 | 6 | 6 | 6 |
| median days to pass | 13.5 | 13.5 | 17.5 | 17.5 | 18.5 | 18.5 |
| intraday drawdown, median / worst | $1,401 / $2,146 | $1,421 / $2,168 | $1,254 / $1,612 | $1,264 / $1,637 | $1,254 / $1,612 | $1,264 / $1,637 |
| 21 late starts: pass / fail / unresolved | 15 / 4 / 2 | 13 / 6 / 2 | 12 / 0 / 9 | 12 / 0 / 9 | 16 / 0 / 5 | 18 / 0 / 3 |
| back to back: pass / fail / expired / unresolved | 4 / 1 / 1 / 0 | 4 / 2 / 1 / 1 | 2 / 0 / 2 / 0 | 2 / 0 / 2 / 0 | 1 / 0 / 2 / 1 | 1 / 0 / 2 / 1 |
| back to back: trades, net | 92, $11,306 | 91, $12,059 | 68, $4,967 | 68, $4,907 | 50, $1,109 | 58, $3,351 |
| profit factor; avg win / loss | 2.5; $327 / −$210 | 2.6; $356 / −$210 | 2.2; $221 / −$151 | 2.2; $220 / −$153 | 1.3; $163 / −$144 | 1.9; $211 / −$144 |
| losing streak; worst day | 6; −$629 | 6; −$635 | 5; −$314 | 5; −$317 | 5; −$314 | 5; −$317 |
| contracts a trade | 4.0 | 4.0 | 3.0 | 3.0 | 2.9 | 2.7 |
| months (Jul / Aug / Sep / Oct) | −324 / +2,126 / +5,859 / +3,645 | −370 / +2,112 / +5,845 / +4,472 | −627 / −420 / +3,487 / +2,527 | −655 / −430 / +3,458 / +2,534 | −627 / −420 / +2,313 / −157 | −655 / −430 / +2,282 / +2,154 |
| exits | stop 71, target 9, 16:00 7, eval target 4, liquidation 1 | stop 70, target 9, 16:00 6, eval target 4, liquidation 2 | stop 54, target 7, 15:55 5, eval target 2 | stop 54, target 7, 15:55 5, eval target 2 | stop 46, 15:55 3, eval target 1 | stop 53, 15:55 4, eval target 1 |

**Notes:**
- "Stop" includes trailed and locked stops; the stand-in names every stop fill alike.
- The 44 starts overlap heavily: they are about three independent 30-day windows.
- The back-to-back figures depend on where attempts start and end:
  - The runner's 2-tick row beats its 1-tick row because, at 1 tick, one trade sized 2 contracts instead of 1. That
    left the account unable to size any further signal. At 2 ticks it kept trading and caught a +$1,784 winner.
  - Small differences can flip a protected account between halted and trading.

### Separate check: NQ 2015-03 to 2025-06, rescaled to today's level (not the user's contract)

| | 1 original B, 1 t / 2 t | 2 B-protected, 1 t / 2 t | 3 runner, 1 t / 2 t |
|---|---|---|---|
| **2,641 starts: pass** | **834 / 794** | **473 / 432** | **500 / 484** |
| fail (certain) | 1,602 / 1,643 | 0 / 0 | 0 / 0 |
| fail on some price paths (gaps) | 2 / 8 | 13 / 13 | 13 / 13 |
| expired; of them halted | 203; 0 / 196; 0 | 2,155; 1,199 / 2,196; 1,268 | 2,128; 1,360 / 2,144; 1,412 |
| 124 non-overlapping starts: pass / fail / expired | 40 / 73 / 11 (1 t) | 26 / 0 / 97 + 1 path-dependent | 27 / 0 / 96 + 1 path-dependent |
| median days to pass | 11 | 17 | 14 |
| intraday drawdown, median / worst | $2,012 / $2,362 | $1,596 / $2,042 | $1,602 / $2,042 |
| back to back: pass / fail / expired | 79 / 162 / 18 | 22 / 1 / 111 | 21 / 0 / 113 |
| back to back: net, profit factor | $101,637, 1.2 / $86,592, 1.2 | $58,856, 1.3 / $40,842, 1.2 | $46,450, 1.2 / $40,419, 1.2 |
| losing streak; worst day | 11; −$629 | 10; −$351 | 10; −$351 |

Yearly results and exits are in `verification/runner_nq/comparison.csv`.

## 4. Verdict

**The runner (3) is rejected.**
- **MNQ:** with the same sizing and protections, it passes exactly the same evaluations as B-protected (18 / 0 / 26
  at both slippages).
  - It is slower: a median 18.5 days against 17.5.
  - It makes less money back to back: $1,109 and $3,351 against $4,967 and $4,907.
  - Its profit factor is lower: 1.3 and 1.9 against 2.2.
  - Drawdown is the same.
- **NQ:** it passes 27 and 52 more of 2,641 overlapping starts, but only 1 more of 124 independent ones. It halts
  more accounts and makes less at 1 tick.
- The results do not support it.

**B-protected (2) is not adopted either.**
- **What it achieves:** it removes the certain liquidations, halves the worst day, and keeps the worst intraday
  drawdown near $1,600 on MNQ.
- **What it costs:** far fewer passes.
  - MNQ: 18 of 44 against B's 24.
  - NQ: 17.9% against 31.6%; 26 of 124 independent starts against 40.
- **Why:**
  - Entries are sized to half the room above the reserve, so trading stops once the drawdown from the peak nears
    about $1,600. The account then sits until it expires: 6 of the 26 MNQ expirations, and about half on NQ.
  - The sizing also cuts 4 contracts to 3 even on a fresh account.
- **The cost to the user:** an expired or halted evaluation costs the same as a failed one. This lowers the chance
  of passing each evaluation bought.

**Frozen B stays the reference, unchanged.** It still does not meet the goal: on NQ about 61% of its evaluations
fail.

**Not done:**
- **Native run:** the candidate has not run in NinjaTrader.
  - Proposed, if wanted for confirmation: compile the package and run the Strategy Analyzer per
    `release/MnqMomentumRunner_candidate/PRESET_RUNNER-CANDIDATE.md`.
  - The stand-in already reproduces B natively on these bars; the candidate shares B's order path.
- **Untouched data:** no untouched MNQ data (03-26, 06-26) was available, so none of this is out-of-sample on the
  user's contract.
