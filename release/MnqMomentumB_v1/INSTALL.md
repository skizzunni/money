# MNQ Momentum B, v1: install (NinjaTrader 8)

This package holds the complete strategy: two source files, no other dependency. It is the code that ran in the
native NinjaTrader tests (commit 2ae30ae; unchanged since).

| File | Goes to | sha256 |
|---|---|---|
| `bin/Custom/Strategies/MnqNoiseMomentum.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` | `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` |

1. Close any chart running MnqNoiseMomentum.
2. Copy both files to the folders above, replacing older copies.
3. Check them in PowerShell: `Get-FileHash <file>` must match the table.
4. NinjaTrader → New → NinjaScript Editor → press F5. Expect no errors.
5. Set up the practice account and chart exactly as in `PRESET_B-PRACTICE-v1.md`.

Do not edit or recompile during the practice test. Any change is a new version and restarts the test.
