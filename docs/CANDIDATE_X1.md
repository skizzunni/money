# X1 — does the noise-momentum edge exist on the Dow and the Russell? (pre-registration)

Written and committed on 2026-10-30, before `research/x1_markets.py` was run.

**Why:** every account so far traded the Nasdaq, so all accounts win and lose together. A second market with the same
edge would make a multi-account plan steadier.
- The Dow (MYM) and the Russell 2000 (M2K) are prop-tradable micro futures that this repository has never tested.
- Gold, silver, crude oil and the euro failed in round 68.

**Data:** Yahoo Finance hourly futures bars, Jun 2024 – Oct 2026: YM=F, RTY=F, NQ=F (the reference) and ES=F.
- The bars start on the hour, so v3.6's 09:30 open and half-hour checks cannot be copied.
- So the same simplified hourly rules run on all four markets, and NQ calibrates what "working" looks like here.

**Rules (identical for every market, 1 micro contract):**
- **Day open O:** the 10:00 bar's open.
- **Previous close C:** the 15:00 bar's close of the previous session.
- **σ at hour h:** the 14-session average of |close at h ÷ O − 1|.
- **Band:** upper = max(O, C) × (1 + σ); lower = min(O, C) × (1 − σ).
- **Checks** at the closes of the 10:00, 11:00, 12:00, 13:00 and 14:00 bars:
  - above the upper band → long;
  - below the lower band → short;
  - back inside the band → flat.
- Every change fills at the next bar's open. Any position is closed at the 15:00 bar's close.
- **Costs:** $0.62 a side, plus 1 tick a fill:
  - MNQ 0.25 point × $2;
  - MES 0.25 × $5;
  - MYM 1 × $0.50;
  - M2K 0.1 × $5.

**Qualifies as a second market:**
- profit factor ≥ 1.2 and t ≥ 1.5 on the whole period;
- and the correlation of its daily P&L with NQ's below 0.5.

**One run. No settings are changed afterwards.** If a market qualifies, the next step is real 5-minute data for it
(v3.6's own rules), not more tuning on these hourly bars.
