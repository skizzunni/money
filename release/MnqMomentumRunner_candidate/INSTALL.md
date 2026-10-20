# MNQ Momentum Runner (candidate, rejected): install (NinjaTrader 8)

**Status:** a test candidate. `docs/RUNNER.md` rejects it for the evaluation; it is packaged so the result can be
reproduced and checked natively. It installs next to frozen B without changing B: the AddOn is the same file, byte for
byte.

| File | Goes to | sha256 |
|---|---|---|
| `bin/Custom/Strategies/MnqMomentumRunner.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` | `f5d983b0b17af18cc71602d0f8eb686a38e692ee49ec65c6cc0bf2e4afc24ff9` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` (B's, unchanged) |

1. Copy both files to the folders above. If B is installed, the AddOn file is already there and identical.
2. Check them in PowerShell: `Get-FileHash <file>` must match the table.
3. NinjaTrader → New → NinjaScript Editor → press F5. Expect no errors.
4. Set up the account and chart exactly as in `PRESET_RUNNER-CANDIDATE.md`.

**Measured so far:** stand-in simulator only (`docs/RUNNER.md`). This candidate has not run in NinjaTrader.
