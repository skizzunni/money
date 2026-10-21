# Open items (October 21, 2026, after candidate F)

## Not done in this round, and why

**Execution-stream protection in `MnqCandidateD.cs` (the gap found after D/E):**
- At the half's fill, move the runner's stop to breakeven at once, rather than at the bar's close.
- Check the account limits on each execution.
- Include the entry and exit bars in the account's highest equity, as candidate C does.

These would change the file whose hashes F was frozen and judged on. The first also changes a trading rule (a
mid-bar stop move), which the model and the gates do not have. They need their own pre-registration if a sweep or
position-manager candidate is ever accepted. While D, E and F are rejected they protect nothing that trades.

## Needs files from the user

| Item | What would close it |
|---|---|
| Native NinjaTrader run of D / E / F | A Strategy Analyzer run on MNQ DEC26, 9/11-10/16/2026, with PRESET_D / PRESET_F settings: the Trades export and the NinjaScript Output (compared by `research/d_parity.py`) |
| The rebuild brief (`mnq-bot-rebuild-brief.md`) and the F attachment | Never reached the session; definitions were declared in docs/CANDIDATE_D.md and docs/CANDIDATE_F.md instead |
| More MNQ history | Exports before 6/28/2026: a longer execution check than 62 sessions |
| TradingView List of Trades | For the Pine reference reconciliation (docs/PINE_REFERENCE.md) |
| Native DEC26 bars before the 9/10 roll | To replace the back-adjusted 09-26 segment of the MNQ series |
| The zero-trade run's Output | For the zero-trade diagnosis (docs/FIXES_2026-10-20.md) |

## Data caveat now documented

**The NQ file is unadjusted at the contract rolls** (docs/NQ_ROLLS.md).
- D/E/F were judged on it.
- The roll-adjusted sensitivity changes none of their verdicts. It moves frozen B's G4 from 50.00% to 49.99%.
