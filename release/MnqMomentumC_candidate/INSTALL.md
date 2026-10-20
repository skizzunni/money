# MNQ Momentum C (candidate): install (NinjaTrader 8)

**Status:** a test candidate, **rejected** by its pre-registered comparison; built and tested on the stand-in
simulator only. `docs/CANDIDATE_C.md` holds its
pre-registered criteria and the result. It installs next to frozen B without changing B: the AddOn is B's file, byte
for byte.

| File | Goes to | sha256 |
|---|---|---|
| `bin/Custom/Strategies/MnqMomentumC.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` | `1a5142c233ae50b56357557f3c584c0f2eb9a71ddc62f0f7a3390bfdcb914fe0` |
| `bin/Custom/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` (B's, unchanged) |

**Dependencies:** none beyond these two files and NinjaTrader 8.

1. Copy both files to the folders above. If B is installed, the AddOn file is already there and identical.
2. Check them in PowerShell: `Get-FileHash <file>` must match the table.
3. NinjaTrader → New → NinjaScript Editor → press F5. Expect no errors.
4. Set up the account and chart exactly as in `PRESET_C-CANDIDATE.md`.
5. After a run, save the NinjaScript Output. `research/output_audit.py <Output.txt>` summarises it.

**Keep exactly one MnqMomentumC.cs.**
- Every version defines `class MnqMomentumC`. Two copies under `bin\Custom` will not compile, or one silently shadows
  the other.
- Search `Documents\NinjaTrader 8\bin\Custom` for `MnqMomentumC*.cs` and delete every copy whose sha256 is not the
  current one.

| MnqMomentumC.cs sha256 | Where it came from | Status |
|---|---|---|
| `0047eb782c70bc81...` | the first candidate zip (commit a2c440b) | Stale: predates the C1 fixes |
| `843e1fda4d65d1eb...`, `8b5d0ef6c0f27fcb...` | C2 and its rejection (e44dbc0, 7b610b6) | Stale |
| `8fdff8ac9ee07004...` | the C1 fixes (2ff619f): partial-fill remainder, order-ID position keys, session audit | Stale: its intrabar peak counted prices after a take-profit fill |
| `0f90ae8836b94383...` | peak accounting ends at each exit, pending guard kept until confirmed (03a5a68) | Stale: ignored realtime errors |
| **`1a5142c233ae50b56357557f3c584c0f2eb9a71ddc62f0f7a3390bfdcb914fe0`** | the same, with realtime errors not ignored (`StopCancelCloseIgnoreRejects`) | **Current** |

**Before a run** (the 0-trade checklist, docs/FIXES_2026-10-20.md):
- 1-minute chart, trading hours CME US Index Futures ETH, Days to load 45;
- MnqMomentumC Enabled on the simulation account;
- EvaluationStart empty, or the evaluation's real first session (never a future date);
- Place orders On;
- the "C settings:" line printed before 09:30 New York.
