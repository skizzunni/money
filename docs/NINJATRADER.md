# MNQ Noise Momentum in NinjaTrader 8

The same bot as `pine/mnq_noise_momentum.pine` v1.6, as a NinjaTrader 8 strategy that places its own orders on one
account. Copy that account to others with a trade copier (Tradesyncer, or NinjaTrader's own).

| File | Goes in (Windows) |
|---|---|
| `ninjatrader/AddOns/MnqNoiseEngine.cs` | `Documents\NinjaTrader 8\bin\Custom\AddOns\` |
| `ninjatrader/Strategies/MnqNoiseMomentum.cs` | `Documents\NinjaTrader 8\bin\Custom\Strategies\` |

`ninjatrader/tests/` is only for the tests here. Don't copy it into NinjaTrader.

> **Apex and automation.** Apex's rules (4.0, March 2026) say no automation or algorithms on any account,
> evaluations included, and that orders must be placed by hand. With **Place orders** on, this strategy is an
> automated system. Apex can close the accounts and keep the fees. With **Place orders** off it only alerts, and you
> click. That's your decision; read Apex's current rules before you switch it on there.

## Install

1. Close any NinjaScript Editor windows. Copy the two `.cs` files into the folders above.
2. In NinjaTrader: **New → NinjaScript Editor**, then press **F5** (compile). The bottom of the editor must show no
   errors. If it shows an error, send me the exact message.
3. A chart: **New → Chart**, instrument **MNQ** front month (e.g. `MNQ 12-26`), **1 Minute**, **Days to load: 30**
   or more. The noise needs 14 full sessions before the first trade. **Use 1 minute, not 5:** the strategy works on
   bar closes, so on a 1-minute chart the breakeven lock arms within the minute price reaches it instead of at the
   end of a 5-minute bar. Over 16 years that made 5-7 points more winning trades, more money a week, smaller losing
   stretches and more passed evaluations (round eighty-one). Any trading-hours template that contains
   09:30–16:00 New York works (`CME US Index Futures ETH` is the default). Any platform time zone works too: the
   strategy converts bar times to New York itself.
4. Right-click the chart → **Strategies… → MnqNoiseMomentum → Add**, and set:
   - **Account:** the one account the bot trades (Tradesyncer's leader).
   - **Calculate: On bar close.** Any other setting and the strategy won't trade; the chart says so.
   - **Start behavior: Wait until flat** (the default).
   - **FUNDED ACCOUNT:** off = the Apex **50K Intraday Trail evaluation: 4 MNQ, $200 max loss a trade, no new
     entries after 3 losers a day**, lock at +25 points to entry + 2.5. On = funded: **4 MNQ, $200, 2 losers**, and the
     lock arms earlier, at +12.5 points, moving the stop to entry + 6.25 (rounds sixty-one and eighty-three: on a
     funded account this won 58-63% of trades and paid more per evaluation in every period; 10 MNQ at $350 busts the
     $2,000 drawdown before it pays much). Each side has its own contracts, max
     loss and loser limit in the settings. For a **50K EOD Trail** evaluation set the evaluation side to **6 MNQ,
     $300, 3 losers** instead (3 x $300 stays under that plan's $1,000 daily loss limit).
     (Rounds 107-108 in [RESULTS.md](RESULTS.md) compare the two plans.)
   - **Place orders:** on = the strategy trades; off = alerts only.
   - **Breakout in the bot's gaps:** on (the default) adds the breakout above: about $40-45 more a week, more
     payouts per evaluation and a first payout about twice as often within 20 sessions, at the cost of more red
     days (about half the days instead of a third). Off = the bot alone.
   - Leave the rest at the tested defaults: take-profit 1.5, line stop 0.24, the two locks above, 14 sessions,
     Fed days on.
   - Tick **Enabled**, then **OK**.

The dashboard at the top right of the chart shows: Evaluation or Funded and the contracts; orders ON/OFF; how many
sessions of history are loaded (until 14, it says so and doesn't trade); the noise lines now and at the next check;
the heads-up; the breakout's two levels for today and its status ("watching", "BUY 2 triggered", "no trigger
today"…); the position with its live stop (and "locked" once the stop is at entry + 2.5); and today's trades,
P/L and losers. The orange and green lines on the chart are the stop and take-profit.

Add it **from the chart** (step 4), not from the Control Center's Strategies tab: started there it runs without a
chart, so there's no dashboard and no lines. Either way, every morning at 09:30 it writes one line to the Output
window (**New → NinjaScript Output**): "ready, trading today", or "loading history, 7/14 full sessions" when it
needs more days loaded.

## What it does

- **10:00, 10:30 … 15:30 New York**, at the close of each check bar: if flat, price outside the noise area, the day
  not on the skip list, fewer than 3 losers today (4 funded), and not a short before 14:00 on a Fed day, it sends a **market
  order**. The stop-loss and take-profit go in with it, in ticks from the fill. NinjaTrader sends them the moment
  the entry fills, as an OCO pair (one pair per fill if the entry fills in parts). The stop is the closer of the line stop and the max loss. The max loss is rounded
  toward the price, so a trade never risks more than the max loss (fees and slippage aside).
- **Every bar close in a trade:** the stop moves with the line (it's measured from your real fill), and to
  **entry + 2.5 points** once a bar has reached +1 max loss (the lock: +17.5 points at 10 MNQ and $350, +25 at
  4 MNQ and $200). The take-profit stays 1.5 noise units from the fill. If the line has moved past the price, the position is closed at
  market, because a stop can't rest there.
- **16:00 New York:** any position is closed at market, whatever happened before. A session that ends early (a half
  day) is closed at its first bar outside 09:30–16:00.
- **The breakout, in the bot's gaps** (on by default; round 101, [RESULTS.md](RESULTS.md)): Larry Williams'
  volatility breakout. Its levels are today's 09:30 open ± half of yesterday's 09:30–16:00 range. The first 1-minute
  bar from 09:30 to 15:00 that reaches one buys (or sells) at market at the next minute's open, with a stop a quarter
  of yesterday's range from the fill, sized to $200 of risk (1 to 10 MNQ), out at 16:00. One a day at most. It's taken
  only while the bot is flat, and the bot always comes first: if the bot signals while the breakout trade is open,
  the breakout trade is closed at market and the bot's entry goes in on the same bar (opposite directions: the bot's
  entry reverses the position). No breakout trade on the skip dates, or until the bot's 14 sessions are loaded.
- **A rejected order:** if the broker rejects the stop while you're in a trade, the strategy closes the position at
  market at once, so it's never left without a stop, and the Alerts window says so.
- **Alerts** (Alerts window, with sound; also in the Output window): heads-up five minutes before a likely signal,
  BUY/SELL with stop, take-profit and breakeven prices, exits with the reason and P/L, and the 16:00 flat.

## Before real money: run it in Playback

The tests here prove the rules and the order handling match the tested Python bot trade for trade, but they run on a
stand-in for NinjaTrader, not on NinjaTrader. Watch it trade once in NinjaTrader before an evaluation:

1. Connect to your data feed first (Connections → your Apex connection; NinjaTrader only downloads while connected).
   **Tools → Historical Data → Download:** MNQ front month, Minute, Last, from about **two months back** to
   yesterday. Then disconnect.
2. **Connections → Playback Connection.** In the Playback window pick **Historical**, and set **Start** at least
   **four weeks after** the first downloaded day (the bot needs 14 full sessions before its first trade), End
   yesterday. Open a 1-minute chart, **Days to load 45**, add the strategy **from the chart** on the **Playback101**
   account with Place orders on, drag the speed slider toward **Max** and press play. It trades only between 10:00
   and 16:00 New York; if the dashboard says "History: x/14", start the playback later.
3. Check, on at least one day with a trade: the entry fills right after a check bar closes; a stop and a take-profit
   appear at once (Orders tab); the stop moves at the half hours and to entry + 2.5 after the lock; everything is
   flat after 16:00; the dashboard's P/L matches the Positions/Executions tabs. On a day with a breakout trade: the
   entry the minute after a bar reaches a level, a stop at once, and, if the bot signals while it's open, the
   breakout closed ("Breakout: bot first") or reversed in the same minute as the bot's entry.
4. Then run a day on **Sim101** live (real-time data, simulated money) with Tradesyncer copying to a simulated
   follower, and check the follower gets the same entry, **the same stop moves**, and the 16:00 exit.

**Strategy Analyzer** backtests it too (Slippage 1, Commission template on). Expect close to the Python numbers,
not identical: NinjaTrader's historical fills differ from the worst-case fills the research uses.

## How it differs from the backtest (and the Pine script)

- **Take-profit from the fill**, as a broker bracket is. The Pine script can only place it from the next bar. On
  16 years of index data and 10½ years of NQ futures this made slightly more per day, with a slightly smaller worst
  losing stretch (index: $12.09 vs $11.60 a day per contract-unit; NQ: $10.18 vs $9.74).
- **Prices on the 0.25 tick:** stops rounded toward the price, take-profits away from it.
- **The lock arms at a bar's close** (if the bar's high reached the trigger), as in the backtest, not on the tick.
- The skip and Fed date lists run to the end of 2027. Add next year's in the strategy settings.

## How it was checked

`tests/test_ninjatrader.py` (needs the .NET SDK; skipped without it):

- The C# rules (`AddOns/MnqNoiseEngine.cs`) compiled as **C# 5**, the oldest NinjaTrader 8 accepts, against the
  Python bot on hand-built sessions, random sessions at 9 settings (3 and 10 MNQ, no max loss, early lock, no
  take-profit…), gaps, Fed and skip dates, 1-minute bars: **every trade, price, P/L, alert, bracket and heads-up the
  same.**
- The strategy compiled (no warnings) against `tests/Sim/NinjaTraderStubs.cs`, a stand-in for the parts of
  NinjaTrader's API it uses, with the backtest's fill model. **The trades it places are the Python bot's trades,
  to the cent.** Also: a stop goes in before every entry, every order price is on the tick, the first stop never
  risks more than the max loss, every position is flat by 16:00 even when the real fills drift from the bot's, a rejected
  stop closes the position, alerts-only mode places nothing, and the switch puts on 3 or 10 contracts with each
  side's own max loss and loser limit.
- With the breakout on, on random 1-minute sessions (evaluation and funded, three seeds): **the account's trades
  are `research/combo_priority.py`'s, trade for trade**: the bot's trades all kept, the breakout's only in its
  gaps, cut or reversed at the bot's next entry, stopped, or flat at 16:00, with the same prices, sizes and P/L.
- Every NinjaTrader call (SetStopLoss, SetProfitTarget, ExitLong, OnOrderUpdate, Alert, Draw.TextFixed,
  GetCurrentBid, StartBehavior, RealtimeErrorHandling) was checked against NinjaTrader's help guide.
- Mutation check: breaking the rules or the order handling on purpose (a stop in the wrong place, no 16:00 exit, the
  lock on the close, the switch swapped, rounding the wrong way…) makes a test fail every time, except one change
  that can't alter a trade.

What can't be checked here is NinjaTrader itself: its compiler, its fills and the broker connection. That's what
the Playback run above is for.
