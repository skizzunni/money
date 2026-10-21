# MNQ Momentum BW (candidate): install (NinjaTrader 8)

**BW is frozen B v1.1's file with two settings changed** (PRESET_BW.md). There is no new code.
- If B v1.1 is already installed, nothing needs copying. Check the sha256 below, then change the two settings.
- Otherwise install it as release/MnqMomentumB_v1.1/INSTALL.md describes, with one copy of each file.

| File | Goes to |
|---|---|
| `bin/Custom/Strategies/MnqNoiseMomentum.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` |

The sha256 of both are in `SHA256SUMS.txt`. They are identical to MnqMomentumB_v1.1's.

**Status:** a result of the net-vs-drawdown side study (docs/NET_VS_DRAWDOWN.md). It is **not** the daily MNQ
strategy: it keeps B's 4 MNQ / $200 sizing, not the shared $125 two-contract rules. It is not an evaluation preset.
See docs/NET_VS_DRAWDOWN.md for what was measured and what was not.
