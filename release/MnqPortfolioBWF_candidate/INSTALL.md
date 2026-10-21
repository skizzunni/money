# MNQ portfolio BWF (candidate): install (NinjaTrader 8)

**Contents:**

| File | Goes to |
|---|---|
| `bin/Custom/Strategies/MnqNoiseMomentum.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\`: frozen B v1.1's file, unchanged |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\`: unchanged |
| `bin/Custom/Strategies/MnqFomcDrift.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\`: new |

**Steps:**
1. Keep one copy of each file under `bin\Custom` (see release/MnqMomentumB_v1.1/INSTALL.md). Check the sha256 against
   `SHA256SUMS.txt`.
2. NinjaScript Editor → F5: expect no errors.
3. Set up the two strategies as PRESET_BWF.md.

**Status:**
- A research candidate for continuous trading on a simulation account.
- Native NinjaTrader has not run the breakout settings or MnqFomcDrift.
- Run it beside frozen B (PRESET_B-PRACTICE-v1.1) so that both are measured on the same sessions.
