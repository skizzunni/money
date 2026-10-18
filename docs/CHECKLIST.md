# Master checklist

Every requirement from the conversation, its status and the evidence. Status: **done** (verified), **partly**
(improved, the stated goal not reached), **not met** (with why and what would change it), **open** (being worked on),
**blocked** (needs something only the user can do). Last updated: October 18, 2026 (rounds through 132).

## The account and its rules

| # | Requirement (source) | Status | Evidence |
|---|---|---|---|
| 1 | Trade MNQ only ("keep my market") | done | Every setup is MNQ; other markets were tested only as checks (rounds 72, 97) |
| 2 | Apex only, one 50K account, intraday trail ("i dont have EOD only intraday rn") | done | All defaults and results are for the 50K intraday-trail evaluation and funded account; EOD kept as reference only (rounds 107-108) |
| 3 | At most 10 MNQ ("you can trade 10 contracts of mnq") | done | Bot 4 MNQ, breakout 1-10, bold finish capped at 10 (`ApexMaxQty`); Apex's 50K evaluation allows 6 minis / 60 micros (third-party, Oct 2026) |
| 4 | Stay within Apex's rules, no hedging, no rule-breaking | done (manual mode) | One position at a time (no hedging); flat by 16:00; **Apex bans automation**, so Place orders off is the compliant mode, and its alerts are verified to reproduce the strategy's trades exactly (`test_alerts_only_trader_matches_the_strategy`) |
| 5 | Every order with a stop and a take-profit (2026 rule, third-party, unconfirmed on Apex's site) | done | Bot: both from the fill; breakout: stop + take-profit 8x its stop (round 130); parity tests cover both |
| 6 | Apex's rules verified at the source | blocked | `apextraderfunding.com` is blocked by this environment's network policy; the user can add it under Allowed domains (environment settings). Apex's help center, as quoted by search results (pages themselves blocked here): the intraday evaluation has no daily loss limit; Tradovate's group copier for your own accounts. Third-party sources used meanwhile: 30-day evaluation, $3,000 target, $2,000 intraday trail, no evaluation DLL or consistency rule, funded: threshold locks at +$100, $1,000 DLL tier, 5 x $200 days, $52,600 balance, 50% consistency, caps $1,500-3,000, 6 payouts |

## Performance goals

| # | Requirement | Status | Evidence / what would change it |
|---|---|---|---|
| 7 | More trades a week; no days without trading | done | ~12 trades a week (bot + breakout, round 101) against ~8 for the bot alone |
| 8 | Pass the evaluation more often | done (improved) | Close-at-target: 35-37% passed over 16 years (was 22-26%), 27.9% in the newest 13 months (round 124); bold finish option: about 39% (round 129, off by default) |
| 9 | More money per evaluation (the six payouts) | done (improved) | $1,163-1,835 paid per evaluation (was $690-1,268), round 124 |
| 10 | More likely to win than lose; more winning streaks | partly | 49-50% of trades win; locks raise it to 53-55% and cut red days 5-7 points but cost payouts, re-tested with close-at-target (rounds 103, 112, 131) |
| 11 | $1,500 a week (at one point $500 a day) | not met | Measured as it is lived (round 132): one account slot, a new evaluation after each failed one, pays $29-77 a week before fees (52 weeks; $29 in the newest 13 months). $1,500 a week is 20-64 such accounts copied (Apex allows 20 funded accounts and copying between your own), or one account with four times the strategy's return for its risk (a daily Sharpe of 0.35 against 0.09): the $2,000 drawdown fails about half the accounts already at the strategy's spread. No rule in 131 rounds came near it |
| 12 | First payout within two weeks | partly | 0.2-0.6% of funded accounts pay within 10 sessions (needs ~$1,300 a week). The payout stop (round 128) doubles the first payout within 20 sessions (8.8% against 4.4% in 2019-25); on by default since round 132 (more money a week per account in every period, 26 and 52 weeks); the cycle's state entered once, then kept from the account and remembered in a file across restarts, a payout asked for kept out of the balance until it leaves the account; tested against a replica through five payout cycles and six restart points |
| 13 | Profit uncapped, only losses capped | done | No daily profit cap anywhere; loss caps per trade and per day (losers) |
| 14 | "A little riskier but don't be stupid" | done | Bold finish only adds size when a timeout (= a failed evaluation) is the alternative; off by default |

## The software

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 15 | NinjaTrader 8 files that compile and run | done | C# 5, compiled with no warnings against the stand-in; the user ran earlier versions |
| 16 | Backtested with 0 errors; the strategy trades what was tested | done | 103 NinjaTrader tests: the bot, the breakout (take-profit 8 and 1 stops), the cut / reversal, close-at-target, bold finish, the payout stop and its remembered cycle, rejected stops, alerts only; mutation checks |
| 17 | Alerts complete enough to trade by hand | done | Follow-the-alerts test: the manual trader's trades equal the strategy's, to the cent |
| 18 | Clear setup instructions | done | `docs/NINJATRADER.md`: install, settings, "Trading it by hand on Apex", Playback check |
| 19 | Verified in NinjaTrader itself (not just the stand-in) | open (user) | Needs NinjaTrader: a Playback run as in the guide; the stand-in can't prove NinjaTrader's own fills |

## Open items and next steps

1. Done: the payout stop is an option (round 128), its cycle remembered in a file across restarts, and a payout
   asked for now kept out of the balance until it leaves the account, and its leaving no longer counted as a losing
   day (found while adding the file: before, the balance read too high until the payout left, and once it left, the
   new cycle started with a loss the size of the payout, which held the payout stop back).
2. Re-check the overnight 18:00-02:00 long as more real nights come in (passed 2011-25, lost in 2025-26).
3. Evaluation price: on the newest 13 months a slot's payouts cover an evaluation only up to $65-101 (round 132);
   buy evaluations at promotional prices, not list.
4. Allow `apextraderfunding.com` (user) so the rules above can be read at the source.
5. A Playback run in NinjaTrader with Place orders off: check the alerts arrive and match the chart.

## Failed approaches (and why), so they are not repeated

Sizing up on any signal (busts the trail: 63, 76, 102, 111, 125); safety rules that cut risk (give-back stop, thin
cushion, locks: time runs out instead: 103, 112, 113, 115, 118); new setups that held in history but not in 2025-26
(overnight drift 104-106, 114; overnight-range breakout 120; gap and go 71-72); filters (wick, touch, shorts: 76-77,
117, 118). The method errors found and fixed: passes counted only at a trade's close (124); the same-minute high/low
bias in the give-back test (113); take-profit rounding toward the price (130).
