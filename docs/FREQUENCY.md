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
