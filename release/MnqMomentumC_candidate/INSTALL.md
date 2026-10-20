# MNQ Momentum C (candidate): install (NinjaTrader 8)

**Status:** a test candidate, **rejected** by its pre-registered comparison; built and tested on the stand-in
simulator only. `docs/CANDIDATE_C.md` holds its
pre-registered criteria and the result. It installs next to frozen B without changing B: the AddOn is B's file, byte
for byte.

| File | Goes to | sha256 |
|---|---|---|
| `bin/Custom/Strategies/MnqMomentumC.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` | `0f90ae8836b94383c0d545468d732ecaab8504297d328a1551bef394716dad19` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` (B's, unchanged) |

**Dependencies:** none beyond these two files and NinjaTrader 8.

1. Copy both files to the folders above. If B is installed, the AddOn file is already there and identical.
2. Check them in PowerShell: `Get-FileHash <file>` must match the table.
3. NinjaTrader → New → NinjaScript Editor → press F5. Expect no errors.
4. Set up the account and chart exactly as in `PRESET_C-CANDIDATE.md`.
5. After a run, save the NinjaScript Output. `research/output_audit.py <Output.txt>` summarises it.
