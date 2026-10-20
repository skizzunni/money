# MNQ candidates D / E (MnqCandidateD): install (NinjaTrader 8)

**Status: rejected by its pre-registered gates** (docs/CANDIDATE_D.md, Results).
- 0 of 123 NQ evaluations passed: every window expired.
- Profit factor 1.07-1.09.
- 0.10 trades a session.
- **Frozen B v1.1 stays the reference.** This package exists so the tested code can be inspected, compiled, and checked
  in the Strategy Analyzer or Playback. It is not for an account.

| File | Goes to |
|---|---|
| `bin/Custom/Strategies/MnqCandidateD.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` (B's, unchanged; it supplies the noise lines and the Williams levels) |

- The sha256 of each file is in `SHA256SUMS.txt`. Check with `Get-FileHash <file>` in PowerShell.
- `MnqCandidateD` is its own class and installs beside B. **Keep exactly one copy of each file.**
- **Dependencies:** NinjaTrader 8 only.

1. Copy both files, then press F5 in the NinjaScript Editor. Expect no errors.
2. Set it up as in `PRESET_D-CANDIDATE.md`.
3. The NinjaScript Output lists every completed position at the end of a run as a `D position` line: both contracts,
   their exits, R, the planned risk and the P/L. An `overrun` flag marks a loss beyond the planned $125.
