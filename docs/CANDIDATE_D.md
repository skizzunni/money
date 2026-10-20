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

**Data roles:**
- **NQ decides.** The five gates are measured on NQ.
- **MNQ is the execution check**, reported separately: the same trade sequence on the user's MNQ bars, point P/L at
  $2 a point.

**Costs everywhere:** $0.95 a side a contract; 2 ticks of slippage on every market and stop fill.

## 2. The brief's rules (§2.1-2.3a, verbatim)

*To be added from the brief before any code is written:*
- the two sleeves (§2.1-2.2);
- 1R stop placement and sizing (§2.3);
- the runner trail (§2.3a);
- the evaluation state machine and payout mode (§2.3).

Where the brief conflicts with section 1, section 1 wins. Each such conflict will be listed.

## 3. Acceptance gates (all must pass; NQ, non-overlapping evaluation starts, net of $0.95 a side and 2 ticks)

| Gate | Requirement | Measured as |
|---|---|---|
| G1 | Evaluation pass rate **≥ 60%** | Passes ÷ all fully observed non-overlapping starts. A window whose outcome depends on the order of prices inside a bar is never a pass. |
| G2 | Expiry **≤ 15%** | Expired ÷ the same starts |
| G3 | Worst window drawdown **≤ $1,500** | The largest fall of equity from its highest point, open P/L included, within any of those windows (start to outcome), on the replay's worst intrabar path |
| G4 | Measured win rate **≥ 50%** | Positions with net P/L > 0 ÷ all positions, over the continuous NQ run. A position closed in parts counts once, net of all its parts. |
| G5 | Profit factor **≥ 1.35** | Gross net profit of positions ÷ gross net loss, over the continuous NQ run |

**The evaluation:**
- Apex 50K, `research/eval_sim.py` rules:
  - $3,000 target;
  - $2,000 trail of the highest equity including open P/L, persisting across days;
  - 30 calendar days;
  - four intrabar price orders tried.
- **Non-overlapping starts:** from the first eligible session, a new start at the first session at least 30
  calendar days after the previous start, independent of outcomes (as in `research/two_loss.py`).

**NQ data:**
- NQ futures 1-minute, `mdelcristo/NQ-F_1min_OHLCV_Parquet`, 2015-03 to 2025-06.
- Each month rescaled to a 30,661 level, the same file every earlier NQ result used (`nq1m_scaled.pkl`, sha256
  `89c0b157…`). It is priced at MNQ's $2 a point.
- Sessions with missing minutes get no new trades.

**Verdict:**
- D is **accepted only if G1-G5 all pass.** Each gate is reported pass or fail with its value.
- If any gate fails, D is rejected and nothing is retuned on this data.

## 4. Required before any result counts

1. **Parity:** D in NinjaScript and in Python, trade for trade identical on the fixed MNQ sample at 2 ticks
   (`tests/test_parity_mnq.py`'s sample, docs/PARITY.md).
2. **Built from the single source:** D's package comes from `tools/build_release.py`, with sha256 sums.
3. **Unit checks:** $2 a point and $0.50 a tick in sizing, stops, commission and evaluation equity
   (`tests/test_mnq_units.py`). 1R ≤ $125 is checked on every entry.
4. **The MNQ execution check reported separately:** trades, net, intraday drawdown and the 44 MNQ starts. It is
   labelled as not deciding.
