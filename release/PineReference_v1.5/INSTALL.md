# Pine v1.5 reference: files and install

The reference as it is. Nothing here is a new strategy.

| File | What it is | sha256 |
|---|---|---|
| `pine/mnq_noise_momentum_v1.5_user.pine` | The user's exact Pine script (v1.5; = repo commit 5e092d0) | `cd44ee68d575e74019cd308f1079838a2b5cb7453d8b7c40473436c59b851975` |
| `bin/Custom/Strategies/MnqNoiseMomentum.cs` | NinjaTrader strategy: frozen B's code, run at the Pine settings | `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35` (B v1.1) |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | Its rules engine, frozen | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` |

**Dependencies:** none beyond NinjaTrader 8, or TradingView for the Pine file. The two .cs files are the same as in
`MnqMomentumB_v1`; installing either package installs the same code.

**Steps:**
1. **TradingView:** Pine Editor → paste the .pine file → Add to chart → set the inputs from `PRESETS.md`.
2. **NinjaTrader:**
   - Copy the two .cs files to `Documents\NinjaTrader 8\bin\Custom\Strategies\` and `...\AddOns\`.
   - Check them with `Get-FileHash`, then press F5 in the NinjaScript Editor.
   - Set up the chart or Strategy Analyzer from `PRESETS.md`.
3. **The trade-by-trade comparison:**
   - Export TradingView's List of Trades and NinjaTrader's Trades for the same dates and preset.
   - `research/pine_reference.py` shows how the two are joined and every mismatch classified.
