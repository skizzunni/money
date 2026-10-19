# Trade frequency, reconciled: candidate C's native run, and the reserve lockout (October 19, 2026)

## 1. The native run - NinjaTrader, executed by the user

**Files:**
- Strategy Analyzer summary `3f2ee3fd-...01-49_AM.csv` (sha256 `dd47bf8d...`) and NinjaScript Output
  `0650491d-...1_53_AM.txt` (sha256 `e531314a...`).
- Copies in `verification/c_native_2026-10-19/`.
- MnqMomentumC at its defaults, MNQ DEC26, 1-minute bars, account Backtest.
- Commission $157.70 = 83 contracts at $1.90; slippage 0.
- Requested 1/1 to 10/18/2026.

| Item | Value (from the Output's audit lines) |
|---|---|
| Loaded bars | 129,751: 5/3 18:00 to 10/16 16:58 New York (no MNQ DEC26 data before 5/3) |
| Sessions with 09:30-16:00 data; complete | 94; 91 |
| Warm-up | 5/4 to 5/21 (14 full sessions); engine ready after the 5/21 close |
| Data hole | 5/22 to 6/26: 24 sessions with no bars |
| First entry; last exit | 6/29 13:31; 7/29 14:01 |
| Trades; net | 31; $7.80 (commission included) |
| Qualifying checks; entries | 247; 31 |
| Checks not taken | open position 18, losing positions today 14, account reserve room 184 |

### Every session, 5/4 to 10/16 (120 weekdays; `research/session_audit.py`, table in `sessions.csv`)

| Status | Sessions |
|---|---:|
| Warm-up | 14 |
| Missing data: no bars (5/22 to 6/26) | 24 |
| Holiday / skip date (5/25, 6/19, 7/3, 9/7) | 4 |
| **Eligible** (6/29 to 10/16) | **78** |

| The 78 eligible sessions | Sessions |
|---|---:|
| Active (at least one entry) | 13 |
| No qualifying setup (no check closed past a line) | 42 |
| Every qualifying check refused: account reserve room | 22 |
| Missing data: no 09:30 bar (8/31) | 1 |
| Open position, daily limit, completed evaluation, or order problem as the only reason | 0 |

- **Open position and the 2-loser limit** refused 32 checks, all on days that also had entries.
- **No order was rejected.**
- **The 42 "no qualifying setup" sessions are real:**
  - From 10/1, the stand-in on the user's 12-26 export lists the same 49 qualifying checks as NinjaTrader, minute for
    minute and side for side.
  - Before 10/1 the native DEC26 bars are not available here to repeat the check.

### Frequency over the whole eligible period

**Per eligible session:** 31 entries in 78 sessions is **0.40**. 83% of sessions had no entry; 5% had 1; 4% had 2;
8% had 3 or more.

**NinjaTrader's "Avg. # of trades per day 1.45"** is a different quantity. It matches 31 trades over the 21.4 weekdays
between the first entry (6/29) and the last exit (7/29). It leaves out every session after the lockout began.

### The persistent lockout

**When it began:** **7/29 15:29**, the first refusal for room. From the 7/30 session to the end, 56 eligible sessions
had no entry.
- 22 of them had qualifying checks, all refused for room (184 refused checks in all).
- 33 had no qualifying setup.
- 1 lacked the 09:30 bar.

**The arithmetic at the lock:**
- highest equity $1,647.00; equity $7.80;
- liquidation line −$353.00; reserve line −$53.00; room above the reserve **$60.80**.
- The entry budget was **half** that room, $30.40, less than one contract's planned risk at a 25-point stop ($53.90).

**Why it never released:** without a trade the equity cannot change, so the room cannot grow. The lock lasted to the
end of the data (2.5 months). Nothing in the rules intended that.
- The user's rules: a $300 reserve, planned entry risk reduced as room shrinks, protection when a position threatens
  the reserve.
- Halving the room was the implementation's own choice.
- With the full room, one contract would have fitted.

**Also noted (not a block):** 6/29 is the first session after the 24-session hole. Its lines come from the May
sessions and the 5/21 close. Its 3 entries traded on those stale lines.

## 2. The fix under test: candidate C2 (pre-registration, before any C2 run)

**One change.** The entry budget uses the **full room above the reserve line**, not half of it:
- budget = the smallest of $200, the room above the reserve, and what is left of the day's $400 backstop.
- A planned stop-out can still never take equity below the reserve line. The $300 reserve stays intact for gaps and
  slippage.
- Entry risk still shrinks with the room, from $200 of room down.

**Unchanged:**
- signals and their standards;
- exits;
- the 2-loser limit, the backstop and the 15:55 flat;
- the reserve line and the position protection;
- the evaluation target and the realized-pass rule.

**Added Output (no trading change):** one line per session with its data, checks and outcome, and each refusal for
room with the room and the planned risk. A native run can then be classified without a separate calendar.

**Tests (stand-in simulator; native runs are labelled separately):**
- MNQ traded contracts and NQ 2015-2025, $0.95 a side, 1 and 2 ticks;
- identical evaluation starts; `research/eval_sim.py` rules;
- fully observed starts apart from unfinished ones; expirations counted in the chance of passing.

**Criteria (decided now):**
- **G1:** in the continuous research (no reserve), C2's trades are exactly C1's.
- **G2:** every refusal for room in C2 has room below that signal's planned risk for one contract.
- **H1:** C2's chance of passing is at least C1's on the 44 MNQ starts and on NQ, and higher on NQ, at both slippages.
- **H2:** certain fails stay at most 1 of 44 MNQ starts and at most 1% of NQ starts, at both slippages.
- **H3:** the additional trades are net positive after costs at both slippages, over non-overlapping NQ windows.
  These are C2's trades in each evaluation that C1 does not have.
- **H4:** C2's mean result per evaluation (equity at its outcome) is at least C1's on NQ at both slippages.
- **C2 replaces frozen B only if also:** its chance of passing is at least B's on MNQ (24 of 44) and on NQ, at both
  slippages.

**Frequency** is reported as entries per eligible session over each whole evaluation and the share of zero-entry
sessions, but it is not a criterion. Signal standards stay fixed; nothing enters to reach a count.

**If a criterion fails, C2 is rejected as stated;** nothing is retuned on this data.

---

# 3. Results (after the criteria above were committed in 1373065) - stand-in simulator

**Data and settings:**
- MNQ traded contracts: 44 fully observed evaluation starts, 64 eligible sessions in the continuous research.
- NQ 2015-2025: 2,641 starts, 2,571 eligible sessions.
- $0.95 a side; slippage 1 tick and (second figure) 2 ticks.
- **C1** = candidate C as run natively (half the room). **C2** = the full room.
- Files: `verification/candidate_c2_mnq/`, `verification/candidate_c2_nq/`.

## Frequency over the whole eligible period, every session counted

| | B | C1 | C2 |
|---|---|---|---|
| **Continuous research, MNQ** (no evaluation account): entries per eligible session; sessions with none | 1.52; 58% | 1.27; 58% | 1.27; 58% |
| **Continuous research, NQ** | 1.94; 42% | 1.57; 42% | 1.57; 42% |
| **Within each MNQ evaluation, start to outcome** | 1.40; 58% | 0.99; 63% | 0.99; 63% |
| **Within each NQ evaluation, start to outcome** | 1.77; 42% | 1.23; 53% | 1.20; 55% |
| **The native C run, one evaluation from 6/29** (NinjaTrader) | - | 0.40; 83% | - |

**What sets the frequency:**
- **When the account is not locked:** the signal itself. On MNQ, 58% of eligible sessions have no qualifying setup at
  all; on NQ, 42%.
- **Inside an evaluation:** the protections cut it further.
  - The 2-loser day, with the backstop and the 15:55 flat, removes 16% (MNQ) to 19% (NQ) of B's trades.
  - The reserve lockout produces the sessions with no entry.
- **On days with signals:** B's entries cluster. On MNQ, a third of sessions have 3 or more.

## Before and after: B, C1, C2

| | B, 1 t / 2 t | C1, 1 t / 2 t | C2, 1 t / 2 t |
|---|---|---|---|
| **MNQ, 44 starts:** pass / fail / expired | 24 / 6 / 14 (both) | 18 / 0 / 26 (both) | 18 / 0 / 26 (both) |
| MNQ: expired, halted at the reserve | 0 | 6 | 6 |
| MNQ: mean result per evaluation | $1,525 / $1,507 | $1,028 / $1,012 | $1,021 / $1,006 |
| MNQ: worst intraday drawdown in a window | $2,146 / $2,168 | $1,612 / $1,637 | $1,664 / $1,687 |
| **NQ, 2,641 starts:** pass / certain fail / expired | 834 / 1,602 / 203; 794 / 1,643 / 196 | 472 / 0 / 2,156; 431 / 0 / 2,197 | 471 / 0 / 2,157; 420 / 0 / 2,208 |
| NQ: chance of passing | 31.6% / 30.1% | 17.9% / 16.3% | 17.8% / 15.9% |
| NQ: expired, halted at the reserve | 0 | 1,202 / 1,277 | 1,264 / 1,369 |
| NQ: 124 non-overlapping starts, pass / fail / expired | 40 / 73 / 11; 41 / 72 / 11 | 26 / 0 / 97; 25 / 0 / 98 | 25 / 0 / 98; 23 / 0 / 100 |
| NQ: mean result per evaluation | $479 / $412 | $464 / $369 | $441 / $339 |
| NQ: worst intraday drawdown in a window | $2,362 | $2,042 / $2,057 | $2,092 / $2,109 |
| **Continuous research, MNQ:** net per eligible session; profit factor | $207, 2.58 / $204, 2.54 | $111, 2.39 / $109, 2.35 | same as C1 |

- About 13 path-dependent NQ windows per candidate column are counted apart.
- The continuous research for C1 and C2 is identical: same trades.

## What the full room changed

**MNQ:** no trade added or removed. Only the sizes near the reserve changed.
- Example, the 7/20 start at 1 tick:
  - C2 sized 3 contracts where C1 sized 2. The losses left $42.90 of room, so C2 locked on 8/3 and never traded
    again (180 signals refused).
  - C1 locked on 8/3 with $92.70 of room ($46.35 usable). It resumed weeks later, when a signal with a tight enough
    line stop came.

**NQ:** the additional trades in non-overlapping windows lost money: 13 for −$924 (1 tick) and 5 for −$476 (2 ticks).

**Why it doesn't free the accounts:** B's stops are mostly at the 25-point cap ($53.90 a contract). Near the reserve,
almost no signal fits under either rule. The larger positions C2 allows just bring the lock sooner and lower.

## Against the criteria

| Criterion | Result |
|---|---|
| G1: continuous research identical to C1 | Pass |
| G2: every refusal for room has usable room below one contract's risk | Pass (stand-in tests) |
| H1: chance of passing ≥ C1 on MNQ and NQ, higher on NQ | **Fail** (NQ 17.8% vs 17.9%; 15.9% vs 16.3%) |
| H2: certain fails ≤ 1 of 44 MNQ starts and ≤ 1% of NQ starts | Pass (0) |
| H3: additional trades net positive, non-overlapping NQ windows | **Fail** (−$924; −$476) |
| H4: mean result per evaluation ≥ C1 on NQ | **Fail** ($441 vs $464; $339 vs $369) |

## Verdict

**C2 is rejected.** The code's default goes back to the tested half-room rule (`ReserveRoomShare` 0.5, = C1). The new
Output stays:
- one line per session with its status;
- the room and the one-contract risk on each refusal for room.

**Unintended blocking:** none remains apart from the reserve lockout itself.
- No order was rejected.
- "Open position" and the 2-loser limit worked as specified.
- The native qualifying checks match the stand-in's.

**The lockout is not an implementation slip.** It is the user's reserve rule meeting B's 25-point stops: once equity is
within about one stop of the reserve line, the account cannot trade again, and the evaluation expires.
- It is the main reason the protected candidates pass about half as often as frozen B on NQ: 17.9% against 31.6%.
- It also removes B's certain liquidations: 0 against 1,602.
- Changing that trade-off means changing a protection: the reserve, the sizing, or ending an attempt once it locks.
  That is the user's decision, and nothing is changed until it is made.

**Frozen B stays the benchmark, unchanged.** It averages 1.4-1.9 entries per eligible session within the preferred 1-2.
But its trades cluster: 42-58% of sessions have none, a third have 3 or more. About 61% of its NQ evaluations fail.
