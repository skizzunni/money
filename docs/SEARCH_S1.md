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

## Results (2026-10-30; one run; `verification/noise_v2/s1_dev.csv`, `s1_test.csv`)

**Development** (index 2011-2022, NQ 2015-2022; all 1,260 rules had at least 20 trades a year on both sets)
- **No rule passed.** None had net win ≥ 80% and PF ≥ 2.0 on both sets.
- **The frontier**, taking each rule's worse development set:

| Requirement | Rules meeting it | Best achieved alongside |
|---|---|---|
| Net win ≥ 60% / 70% / 80% / 90% | 443 / 313 / 208 / 53 | the best PF is 1.277 at every level |
| PF ≥ 1.2 | 77 | the best net win is 93.1% |
| PF ≥ 1.5 | **0** | — |
| PF ≥ 2.0 | **0** | — |

The highest PF of any rule was 1.487.
- **High win rates are easy:** a target of 0.05 × the daily range wins 90%+ of trades.
- But the few losers are large, so PF stays near 1.

**The finalists' test** (one run). Net per trade at 1 MNQ:

| Finalist (target 0.05 R for all) | 2023-24 index | 2023 – mid-2025 NQ | User's window | Net win, user's window |
|---|---|---|---|---|
| MOM 1.0, with-trend, no stop | −$4.73 | +$5.59 | **−$2.43** (PF 0.93) | 92.8% |
| MOM 1.0, with-trend, stop 0.5 | −$0.26 | +$10.37 | **−$0.96** (PF 0.97) | 91.0% |
| MOM 1.0, with-trend, stop 1.0 | −$3.12 | +$5.07 | **−$4.72** (PF 0.87) | 92.8% |
| MOM 1.5, counter-trend, stop 0.5 | +$11.33 | +$0.64 | **−$0.56** (PF 0.98) | 90.6% |
| PREV-R, counter-trend, stop 1.0 | −$2.28 | −$6.41 | +$4.95 (PF 1.19) | 91.0% |

None is positive on every test set, so the size stage is not reached.
- The user's window: −$783 to +$1,045 at 1 MNQ. PF 0.87-1.19. Marked DD $1,072-$3,200.
- The 90%+ net win rates hold on new data, but the money does not: each is about breakeven after costs.

**Decision:** S1 found no rule that meets the targets.
- 80% net winners with PF ≥ 2.0 did not occur together anywhere in 1,260 rules, even on the data used to pick them.
- Raising the size multiplies the drawdown as fast as the profit, so it cannot turn a breakeven rule into $75,000.
