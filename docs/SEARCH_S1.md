# Search S1 — a broad, pre-registered rule search (UNVERIFIED)

Written and committed on 2026-10-30, before `research/s1_search.py` was run.

The user asked for a search that keeps going until the targets are hit. S1 is that search, done in one pass with fixed
rules, so that a "hit" cannot come from trying things until one fits the user's window.

## The rule space (1 MNQ, regular hours, one trade a day)

**Checks:** at the closes of 10:00, 10:30, …, 15:00. The entry is a market order at the next bar's open, plus 1 tick.
Each day takes the first check that signals.

**Entry families (12)**
- MOM k (k = 0.5, 1.0, 1.5): |the move since 09:30| ≥ k × its 14-session average at that time. Trade with the move.
- REV k: the same condition, traded against the move.
- ORB / ORB-R: a check close beyond the 09:30-10:00 range, traded with it (ORB) or against it (ORB-R).
- GAP / GAP-R: at 10:00 only, trade with (or against) the opening gap.
- PREV / PREV-R: at 10:00 only, trade with (or against) the previous session's direction.

**Filters (3)**
- none;
- with-trend: only trades in the direction of the previous close against its 50-session average;
- counter-trend: only trades against it.

**Exits (35)**
- Target T × R, where R is the 14-session average daily range. T ∈ {0.05, 0.1, 0.2, 0.35, 0.5, 1.0, none}.
- Stop S × R. S ∈ {0.1, 0.25, 0.5, 1.0, none}.
- Otherwise out at the 15:55 bar's close.
- A bar that reaches both counts as the stop.
- Target fills are limit fills, with no slippage. Stops and closes get 1 tick of slippage.

That makes 12 × 3 × 35 = **1,260 rules**.

## Data and costs

**Data (raw prices; points scaled to 30,000 on the histories):**
- the Nasdaq-100 index (HistData) 2011 – Sep 2026;
- NQ futures 2015 – Jul 2025 (roll weeks skipped);
- the MNQ stand-in, Jan 2025 – Oct 2026.

**Costs:** $0.62 a side, plus the slippage above.

## Stages, fixed now

1. **Development, all 1,260 rules:** index 2011-2022 and NQ 2015-2022.
   - "Development pass" means, on both sets:
     - net win ≥ 80% (a win is above $0 after costs);
     - PF ≥ 2.0;
     - net > 0;
     - at least 20 trades a year.
   - Also reported: the best PF reached at each win-rate level (the frontier).
2. **Finalists:** the 5 rules with the highest development score.
   - The score is the lower of the two development PFs, among rules with net win ≥ 80% on both sets.
   - If fewer than 5 qualify, the rest are filled from rules with net win ≥ 70%, then by the same score.
3. **Test, one run, finalists only:**
   - 2023-2024: the index, and NQ to Jul 2025;
   - then the user's window (the stand-in).
4. **Size, only for a finalist positive on every test set:**
   - the whole MNQ contracts needed for $75,000 on the user's window;
   - the marked drawdown at that size.

## Acceptance

All four targets on the user's window, at the size from stage 4:
- net at least $75,000;
- net win at least 80%;
- PF at least 2.0;
- marked-equity drawdown under $4,000.

**Multiple testing:** with 1,260 rules, a few will look good on development by chance. That is why a finalist counts
only if it also passes the test years and the user's window, both untouched by selection. Anything that passes will be
reported with that number of rules attached.

**Marked drawdown:**
- In the search, it is computed per trade: closed equity plus the trade's worst excursion before it closed, against
  the closed-equity peak. That understates it slightly, because it leaves out open-trade highs.
- A finalist that passes is recomputed bar by bar before any claim.
