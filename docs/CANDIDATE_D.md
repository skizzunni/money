# Candidate D: pre-registration (October 20, 2026)

**Status:**
- **Part 1** (this commit): the rules and gates the user fixed. It is committed **before any Candidate D code or
  result exists.**
- **Part 2:** the brief's entry and trade-management rules (`mnq-bot-rebuild-brief.md` §2.1-2.3a), copied verbatim
  and committed before the build. The brief has not reached the session yet.
- **Discipline** (as docs/CANDIDATE_C.md):
  - criteria fixed before testing;
  - simulator results labelled apart from native NinjaTrader;
  - a failed gate is reported as a rejection;
  - nothing is retuned on the same data.

## 1. Rules fixed by the user (they override the brief and `mnq-bot-fixes.pdf` where they differ)

**Risk:**
- Every trade risks at most **1R = $125**.
- That is a hard cap. A stop is never widened, and the strategy never averages down.

**Trade management:**
- **Breakeven at +1R:** the stop moves to the entry once the position is 1R in profit.
- **Half banked at +2R.**
- **The runner trails with no target:** profit is uncapped. The trail is the brief's (§2.3a).

**Daily governor:**
- The only daily governor is **at most 3 entries a day.** It also sets the participation: 1 to 3 trades a day, never
  forced.
- **No daily profit cap, no daily loss cap, no loser-count cutoff.** The PDF's −$300 daily stop and +$450 profit lock
  are not part of D.
- The worst possible day is structural: 3 × 1R, plus any gap through a stop.

**Data roles** (corrected by the user the same day, before any code: "we doing MNQ not NQ"):
- **MNQ decides.** The five gates are measured on the user's MNQ bars, which is the instrument traded.
- **NQ is a supplementary robustness check only:** reported separately, labelled, never deciding, and never quoted as
  MNQ results.

**Costs everywhere:** $0.95 a side a contract; 2 ticks of slippage on every market and stop fill.

## 2. The brief's rules (§2.1-2.3a, verbatim)

*To be added from the brief before any code is written:*
- the two sleeves (§2.1-2.2);
- 1R stop placement and sizing (§2.3);
- the runner trail (§2.3a);
- the evaluation state machine and payout mode (§2.3).

Where the brief conflicts with section 1, section 1 wins. Each such conflict will be listed.

## 3. Acceptance gates (all must pass; MNQ, non-overlapping evaluation starts, net of $0.95 a side and 2 ticks)

| Gate | Requirement | Measured as |
|---|---|---|
| G1 | Evaluation pass rate **≥ 60%** | Passes ÷ all fully observed non-overlapping starts. A window whose outcome depends on the order of prices inside a bar is never a pass. |
| G2 | Expiry **≤ 15%** | Expired ÷ the same starts |
| G3 | Worst window drawdown **≤ $1,500** | The largest fall of equity from its highest point, open P/L included, within any of those windows (start to outcome), on the replay's worst intrabar path |
| G4 | Measured win rate **≥ 50%** | Positions with net P/L > 0 ÷ all positions, over the continuous MNQ run. A position closed in parts counts once, net of all its parts. |
| G5 | Profit factor **≥ 1.35** | Gross net profit of positions ÷ gross net loss, over the continuous MNQ run |

**The evaluation:**
- Apex 50K, `research/eval_sim.py` rules:
  - $3,000 target;
  - $2,000 trail of the highest equity including open P/L, persisting across days;
  - 30 calendar days;
  - four intrabar price orders tried.
- **Non-overlapping starts:** from the first eligible session, a new start at the first session at least 30
  calendar days after the previous start, independent of outcomes (as in `research/two_loss.py`).

**MNQ data and its exact coverage:**
- **The bars:** the user's NinjaTrader exports, traded contracts.
  - 09-26 to the 9/10 roll session, back-adjusted +284.50; 12-26 from 9/11.
  - 09:30-16:00 plus the 16:00 bar.
  - 6/29 to 10/16/2026: 80 sessions. This is the fixed parity sample, `tests/data/`, sha256 `ad73d17a…`.
- **Warm-up:** the first 14 full sessions (to 7/17), or longer if the brief's rules need more. Tested from 7/20:
  64 sessions.
- **Non-overlapping starts: 7/20, 8/19 and 9/18. Only three windows.**
  - The 9/18 window ends on 10/18, a Sunday, so its last possible session, 10/16, is in the data.
  - Rule, fixed now: a window counts as fully observed when no trading session falls between the end of the data and
    the window's end.
  - **What that means for the gates:**
    - G1 needs at least 2 of 3 passes;
    - G2 allows no expiry (1 of 3 is 33%);
    - G3 rests on three windows.
- **The limitation, stated before any result:**
  - Three windows cannot establish a 60% pass rate. A pass on them is consistent with the gate, not proof of it.
  - This is also development data: it chose frozen B.
  - The 44 overlapping starts (7/20 to 9/17) are reported too, labelled as overlapping and not deciding.
- **More MNQ history would make the gates meaningful.** Earlier contracts (MNQ 06-26, 03-26 and before) exported from
  NinjaTrader would be added as untouched data, if the user provides them before D is run on them.

**NQ, supplementary:**
- 2015-03 to 2025-06, rescaled monthly to 30,661 (`nq1m_scaled.pkl`, sha256 `89c0b157…`), priced at $2 a point.
- The same five measurements on non-overlapping starts, reported in their own table, labelled. Not deciding.

**Verdict:**
- D is **accepted only if G1-G5 all pass.** Each gate is reported pass or fail with its value.
- If any gate fails, D is rejected and nothing is retuned on this data.

## 4. Required before any result counts

1. **Parity:** D in NinjaScript and in Python, trade for trade identical on the fixed MNQ sample at 2 ticks
   (`tests/test_parity_mnq.py`'s sample, docs/PARITY.md).
2. **Built from the single source:** D's package comes from `tools/build_release.py`, with sha256 sums.
3. **Unit checks:** $2 a point and $0.50 a tick in sizing, stops, commission and evaluation equity
   (`tests/test_mnq_units.py`). 1R ≤ $125 is checked on every entry.
4. **NQ reported separately as the supplementary check,** labelled as not deciding.
