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

## Results (2026-10-30; one run; `verification/noise_v2/x1_markets.csv`)

| Market | Trades | Net $ | Net $/trade | t | Win % | PF | Closed DD | Correlation with NQ |
|---|---|---|---|---|---|---|---|---|
| NQ (reference) | 309 | −$2,454 | −$7.94 | −0.51 | 42.1 | 0.920 | $6,212 | 1.00 |
| ES | 322 | −$808 | −$2.51 | −0.36 | 40.7 | 0.944 | $2,063 | 0.76 |
| YM | 334 | −$2,144 | −$6.42 | −1.53 | 35.0 | 0.794 | $2,553 | 0.45 |
| RTY | 315 | −$878 | −$2.79 | −0.77 | 41.3 | 0.890 | $1,288 | 0.37 |

**No market qualifies.**

**The test is inconclusive for the Dow and the Russell.** The reference itself failed: the simplified hourly rules lose
money on NQ over the same months in which v3.6 (half-hour checks from the 09:30 open, its stops and its filters) made
money on NQ.
- So the hourly simplification removed the edge.
- It cannot say whether v3.6 itself works on MYM or M2K. That needs regular-hours 1- or 5-minute bars for those
  markets.
- Yahoo serves those for the last 60 days only.

What it does show:
- Daily P&L on the Dow and the Russell is much less tied to the Nasdaq (correlation 0.45 and 0.37) than the S&P's is
  (0.76).
- So if v3.6's edge held on them, they would be real diversifiers.
