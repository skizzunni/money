# Code versions and how releases are built

## Single source

**Each NinjaScript and Pine file exists once in the repository:**
- `ninjatrader/Strategies/MnqNoiseMomentum.cs` (B)
- `ninjatrader/Strategies/MnqMomentumC.cs`
- `ninjatrader/Strategies/MnqMomentumRunner.cs`
- `ninjatrader/AddOns/MnqNoiseEngine.cs`
- `pine/reference/mnq_noise_momentum_v1.5_user.pine`

**The simulator compiles these files.** The parity tests run against them, and the packages are built from them.

**Packages** (`release/<package>/`):
- Each holds only its hand-written documents (INSTALL and presets) and a generated SHA256SUMS.txt.
- `python tools/build_release.py` assembles `release/<package>.zip` from the sources and the documents:
  - sorted entries;
  - fixed timestamps (1980-01-01) and permissions;
  - so a rebuild is byte-identical.
- `release/SHA256SUMS.txt` lists each zip's sha256.
- `tests/test_release.py` fails if a committed zip or SHA256SUMS differs from a fresh build. It also fails if a code
  file is copied anywhere outside its source path, or two different versions of a strategy class exist in the
  repository.

## Versions

| File | sha256 | Status | Where to get it |
|---|---|---|---|
| MnqNoiseMomentum.cs, B v1.1 | `d1a4f8633c0d630edabd02ed59b8be0425eda581ab322873db58ecc8cbd26a35` | **Current** (`release/MnqMomentumB_v1.1.zip`) | `ninjatrader/` |
| MnqNoiseMomentum.cs, B v1 | `1fbdcea05fd1f5403bfbc7c798e8bf83f93ccdf1dade3ec0f2724d552c744bd3` | Retired: ignores realtime errors. Reconciled with native NinjaTrader (docs/B_NATIVE.md); v1.1 trades identically | `git show 2ae30ae:ninjatrader/Strategies/MnqNoiseMomentum.cs` |
| MnqNoiseEngine.cs | `e5a1ec0cc18b15509828149ce8aa0e9c7a104a59aff0992190205c42f354deb7` | Current, unchanged since B v1 | `ninjatrader/` |
| MnqMomentumC.cs | `1a5142c233ae50b56357557f3c584c0f2eb9a71ddc62f0f7a3390bfdcb914fe0` | Current; the candidate was not promoted | `ninjatrader/` |
| MnqMomentumC.cs, earlier | `0047eb78…`, `843e1fda…`, `8b5d0ef6…`, `8fdff8ac…`, `0f90ae88…` | Retired (docs/FIXES_2026-10-20.md section 1) | git history |
| MnqMomentumRunner.cs | `f5d983b0b17af18cc71602d0f8eb686a38e692ee49ec65c6cc0bf2e4afc24ff9` | Current; the candidate was rejected | `ninjatrader/` |
| mnq_noise_momentum_v1.5_user.pine | `cd44ee68d575e74019cd308f1079838a2b5cb7453d8b7c40473436c59b851975` | The Pine reference, unchanged | `pine/reference/` |

**The B v1 package (`release/MnqMomentumB_v1.zip`) is removed:** v1.1 replaced it. Only one version of each
strategy class is in circulation.

**In NinjaTrader:** keep exactly one copy of each file under `Documents\NinjaTrader 8\bin\Custom`. Two files defining
the same class will not compile, or one silently shadows the other.
