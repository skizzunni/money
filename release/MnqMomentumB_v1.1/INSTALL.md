# MNQ Momentum B, v1.1: install (NinjaTrader 8)

**v1.1 is frozen B with one live-safety fix and no trading change.**
- `RealtimeErrorHandling` changes from `IgnoreAllErrors` to `StopCancelCloseIgnoreRejects`.
- A rejected order still reaches the strategy's own handling: a rejected exit is sent again at the next bar, and a
  rejected stop closes the position.
- Any other realtime error now stops the strategy, cancels its orders and closes the position. Before, it was ignored.
- Backtests are unaffected. On the simulator every MNQ trade is v1's (97 of 97, 7/20 to 10/16). So the native
  reconciliation of v1 (docs/B_NATIVE.md) carries over.

| File | Goes to | sha256 |
|---|---|---|
| `bin/Custom/Strategies/MnqNoiseMomentum.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` | `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` (v1's, unchanged) |

**Keep exactly one copy of each file.**
- v1 and v1.1 both define `class MnqNoiseMomentum`. Two copies anywhere under `bin\Custom` will not compile, or one
  silently shadows the other.
- Before copying, search `Documents\NinjaTrader 8\bin\Custom` for `MnqNoiseMomentum*.cs` and delete every other
  copy, including backups such as `MnqNoiseMomentum - Copy.cs`.

1. Close any chart running MnqNoiseMomentum.
2. Copy both files to the folders above, replacing the old ones.
3. Check them in PowerShell: `Get-FileHash <file>` must match the table.
4. NinjaTrader → New → NinjaScript Editor → press F5. Expect no errors.
5. Set up the practice account and chart exactly as in `PRESET_B-PRACTICE-v1.1.md`. For the Strategy Analyzer, use
   `PRESET_B-NATIVE-v1.1.md`.
6. **Before the first session, open the NinjaScript Output.** The "MNQ settings:" lines must show the account,
   orders ON and the settings. The daily line must say "ready, trading today" from the 15th full session.

Do not edit or recompile during the practice test. Any change is a new version and restarts the test.

**Versions:**

| Version | MnqNoiseMomentum.cs sha256 | Status |
|---|---|---|
| v1 | `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3` | Reconciled with native NinjaTrader. Ignores realtime errors: do not use on an account |
| **v1.1** | `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35` | **Current.** v1's trading logic, realtime errors not ignored |
