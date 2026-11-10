# v2 stops for the Noise-Area Momentum v1.5 rules (plan of 2026-11-10)

The plan: build the v1.5 rules with eval-safe stops (daily loss limit, a lock trigger in noise units, a gap guard,
tighten-only), pre-register gates, test on NQ 2015-2025, and report the $750/day question honestly. This file records
each phase as it is done. Attachments that arrived: the Pine trade log screenshot (Nov 2-9). The Pine v1.5 script used
is the user's archived file `pine/reference/mnq_noise_momentum_v1.5_user.pine`; the C# engine is
`ninjatrader/AddOns/MnqNoiseEngine.cs`. The NinjaTrader trades 229-233 screenshot did not arrive.

## Phase 0: the firm's rules (to confirm)

From Take Profit Trader's help center as read on 2026-11-05 (docs/NINJATRADER_V38.md, "The user's firm"); the user
should confirm these against the current pages:

| Rule | Test (evaluation) | PRO (funded) |
|---|---|---|
| Trailing drawdown | $2,000, **end of day** | $2,000, **intraday, including open profit**, until the floor reaches $50,000 |
| Profit target | $3,000 | none |
| Minimum days | 3 (the plan's gates use 5, stricter) | none |
| Consistency | best day under 50% of the profit | none |
| Daily loss limit | none | none |
| Automation | **not allowed**: "Automated trading systems, bots, or algorithmic execution tools are not permitted" | **not allowed**: "All trades must be manually executed by the trader" |
| Other | positions closed by 16:55; at most 60 micros | flat 1 minute either side of FOMC 14:00, NFP and CPI |

**So on this firm the bot is alert-assisted manual trading only:** NinjaTrader runs on SIM / paper, the strategy
sends the heads-up and the bracket (entry, stop, target) before each check, and the trader places every order
themselves. Bot trades must never be passed off as manual. The NinjaTrader strategies' "Place orders" switch must stay
off on a Take Profit Trader account. Since the funded account trails intraday, every gate below is run under both
end-of-day and intraday trailing.

## Phase 1: reconciliations

**(a) Pine against NinjaTrader on Nov 2-9.** The Pine log in the screenshot is **not v1.5**. It has v3.8's "Why" column
("locked win", "max loss stop", "stop at the line", "16:00 close") and sizes from 5 to 12 contracts, which v3.8's
Funded growth mode sets. In v1.5 the size is a fixed input. Reading the log row by row:
- Nov 5 has **four** Pine trades, not one: 10:30 short 7 (+$4,303.32, target), **11:00 short 10** @ 26974.25 → 11:30
  27069.50 (−$1,917.40, max loss stop), **12:00 short 8 @ 27151.25 → 27149.00 (+$26.08, locked win)**, and 12:00 short 8
  @ 27116.00 → 15:30 26743.25 (+$5,954.08, 16:00 close). The −$1,917.40 trade entered at 11:00. The 12:00 trade at
  27151.25 is exactly NinjaTrader's #229 (short 8 @ 27151.25 → 27149.00, +$26.08). **Pine and NinjaTrader agree on Nov 5
  12:00.** The plan's "divergence" set the 11:00 trade beside the 12:00 one. No data-feed, contract or warmup difference
  shows in that row. (Trades 230-233 can be checked when that screenshot arrives.)
- **The two big losses were not gaps through a stop.** Both filled about 95 points from entry: Nov 5 11:00, 26974.25 →
  27069.50 = 95.25 points on 10 MNQ; Nov 6 10:00, 27346.25 → 27250.50 = 95.75 points on 12 MNQ. Funded growth's max loss
  is **$187.50 a contract = 93.75 points**, measured from the expected fill. Both exits are that stop plus 1.5-2 points of
  slippage and fill difference. The 14.6- and 17.5-point "intended stops" in the plan are $350 ÷ qty ÷ $2, v1.5's
  setting, which this log did not use. **The stop did its job; it was 94 points away on 10-12 contracts.** So the loss
  came from size × per-contract risk, which v1.5 at a fixed 2 MNQ and its own $350 cap would not repeat. A real gap
  (a fill far past a resting stop) is still possible at the open or on news, and the gap guard and G5 measure it.

**(b) Reversals.** v1.5 reverses **only in its "Half-hour check" exit mode**. In its default, "Resting stop at the line",
it does not reverse: `inPosStop = useStop and pos != 0` skips the reverse branch, so an open trade ends only at its
stop, lock, target or 16:00. The C# engine never reverses. The Python reference (`mnqbot/noise.py`) and every
historical backtest in this repository since the resting stop (v1.1) use the resting-stop mode: **no reversals**, the
same as the C# engine. The comparisons below use that mode.

**(c) The $34/day number.** No result in this repository is "$34 a day" exactly. The nearest are the funded measures of
the 50K bot (G372 / G409 / G415 / G421): **per account, total, starting at 1 MNQ and adding a contract per $1,500 of
profit**: U48 $30.4 a session on the 16 recent 12-month starts, G421's variant D $35.1, U58 $49.2. They are not per
contract. The Pine's long-run claim of about $28 a day a contract matches round 32 (`docs/RESULTS.md`, NQ futures
2015-25 at 1 contract and a $117 max loss: $27.94 a day). The plan is right that these are to spec, not something to
"fix".

**(d) The 5-12 sizing.** In v3.8's Funded growth (Pine and NinjaTrader alike): 1 MNQ, plus one contract per $1,500 of
profit since the start date (faster above $9,000), up to 60, each trade's risk at $187.50 a contract, cut to the day's
budget and the room above the trailing floor. **On TradingView the profit is the chart's own backtest** since its start
date, so after a strong simulated history the Pine shows 10-12 contracts that no real account has earned. NinjaTrader
sizes from the smaller of the strategy's equity and the live account's (`EqEff`), so live it cannot size from
simulated profit. The plan's fixed 2 MNQ for the evaluation replaces all of this.
