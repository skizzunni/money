# Noise-Area Momentum: exact rules

**Script:** [`pine/mnq_noise_momentum.pine`](../pine/mnq_noise_momentum.pine). The Python reference is [`mnqbot/noise.py`](../mnqbot/noise.py), and tests hold the two to the same trades, to the cent.

**Source:** Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)". It uses the paper's settings, minus its VWAP trailing stop, because the test data has no volume.

**In one line:** when price has moved further from the open than it usually does by that time of day, trade in that direction. Check every half hour and be flat by the close.

**It does not "never lose."** Read [What to expect](#6-what-to-expect) before you trade it.

---

## 1. Setup

1. **Chart:** `MNQ1!` (or the front-month MNQ contract) on **5 minutes**. Extended hours can be on or off. 1, 10, 15 and 30 minutes also run, and without the max loss they make the same trades. With it they don't: the max-loss stop needs the entry fill, so it starts on the bar after the fill. On a 30-minute chart that leaves every trade without its $350 cap for the first half hour, and single trades lose well past $350. The dashboard's *Chart* row turns orange when that applies. See round twelve in [RESULTS.md](RESULTS.md).
2. **Load it:** Pine Editor → paste the script → *Add to chart*.
3. **History:** it needs **14 complete sessions** on the chart before its first trade. The dashboard shows *Sessions of history 14 / 14* when it's ready.
4. **Alerts:** set them up as in [section 4](#4-how-it-tells-you-what-to-do).

## 2. Definitions (New York time)

| Item | Rule |
|---|---|
| Day open | Open of the 09:30 bar |
| Previous close | The previous session's 16:00 close (the close of its last bar ending by 16:00) |
| Checks | The closes of the bars ending at 10:00, 10:30, 11:00 … 15:30 (12 a day) |
| Move at a check | \|close ÷ day open − 1\| |
| Noise (σ) for a check | Average of that same check's move over the last **14 complete sessions** |
| Complete session | Reached 16:00 with all 12 checks. Half days and sessions missing a check don't count. |
| **Upper line** | max(day open, previous close) × (1 + σ) |
| **Lower line** | min(day open, previous close) × (1 − σ) |

The lines change at every check, because σ is different for each time of day. It is usually narrow at 10:00 and wider by the afternoon.

## 3. What to do at each check

| You are | The check's close is | Do |
|---|---|---|
| Flat | above the upper line | **BUY** 1 MNQ at market, then put a **stop order just below the upper line** (the alert gives the exact price) and a **take-profit limit 1.5 noise units above your fill** (the alert gives the distance in points) |
| Flat | below the lower line | **SELL** 1 MNQ at market, then put a **stop order just above the lower line** and a **take-profit limit 1.5 noise units below your fill** |
| In a trade | anything | **Move your stop to the new level.** The lines, and the stop with them, move at every half hour. Never let it sit further than your max loss from your fill. |
| Flat, inside the lines | | Nothing. |

- **The stop is the exit, and it sits 0.24 noise units past the line:** for a long at upper × (1 − 0.24 σ), for a short at lower × (1 + 0.24 σ). Why there: a trade-by-trade post-mortem of 2011–2018 found that 77% of losing trades were stop-outs on the line that then went on in our direction, and 0.24 σ is how far they typically overshot the line before resuming ([RESULTS.md](RESULTS.md#tenth-round-why-the-trades-lose)). On 2023–2026, years that analysis never saw, it raised profit per day by 43% and the win rate from 25% to 34%. If the stop level moves past the price when the lines update, the stop fills at once. The setting *Stop distance past the line* = 0 puts the stop on the line itself.
- **A max loss per trade caps it.** The setting *Max loss per trade* (default $350 for the whole position) puts a second stop that many dollars from your fill; whichever stop is closer is the one in force. **Place it with the entry, as a bracket order**: it is live from the moment you're filled. The backtest does the same: on the fill bar it measures the cap from the expected fill (the signal close plus a tick), then from the real fill (round twenty-seven in [RESULTS.md](RESULTS.md)). Over 16 years a cap of $100–$200 per contract raised profit per day in every period and cut the worst losing stretch ([RESULTS.md](RESULTS.md#eleventh-round-the-worst-days-and-a-cap-per-trade)); $35 per contract (a $350 cap over 10 contracts) wrecked it. Fees, slippage and a gap through the stop can add to the loss.
- **A take-profit limit sits 1.5 noise units past your fill:** for a long at fill × (1 + 1.5 σ), for a short at fill × (1 − 1.5 σ), with σ the current check's noise, so it moves a little at each half hour. It works from the bar after the fill and fills once price trades a tick through it; if the stop and the target are both touched in one bar, the backtest counts the stop. The entry alert gives the distance in points and an approximate price. The setting was chosen walk-forward, each year from the years before only: over 2015–2026 it raised profit per day from $24.66 to $25.77 per contract, the t-stat from 4.71 to 5.39, and cut the worst losing stretch from $5,178 to $4,185 ([RESULTS.md](RESULTS.md), round twenty-six). *Take profit* = 0 turns it off. It applies with the resting stop only.
- **After a stop-out you're flat until the next check.** A new signal there can put you back in, including the other way.
- **Orders are market orders** placed right after the check. The backtest fills them at the next bar's open plus 1 tick of slippage. Stops fill at the line, or at the bar's open if price gapped through, minus 1 tick.
- **At 16:00, close everything.**
- **The paper's original rule** (exit only if a half-hour check closes back inside the lines, reverse if it closes through the other side) is still there under *Exit → Half-hour check*. It makes fewer trades and had bigger worst days.
- **Size: the script's default is 10 MNQ with a $350 max loss per trade, $35 per contract.** Every figure in this document and in [RESULTS.md](RESULTS.md) is per contract unless it says otherwise; multiply by the contracts. A $35 stop per contract is tight: it made about $13–16 a day per contract against about $22 for 1–3 contracts under the same $350. **On a $50K evaluation, 10 MNQ failed about 4 attempts in 5; 2 MNQ passed about half** (round thirteen in [RESULTS.md](RESULTS.md)). Set *Contracts* to 2 for the evaluation. No $25K / $1,500 evaluation can hold more than 1 contract of this.
- **No trades on holidays and half days.** On US market holidays (MLK Day, Memorial Day, Labor Day and so on), MNQ still trades but halts at about 13:00 ET. On half days (the day after Thanksgiving, Christmas Eve) the session also ends early. The 16-year test only traded full sessions, so the script sits these out. Its input *Don't trade on these dates* comes pre-filled with every 2026–2027 holiday and half day, and you can add news days to it. In 2028, add that year's dates.
- **On Fed days, no shorts before 14:00.** On the eight scheduled Fed announcement days a year, the bot skips short signals from the 10:00–13:30 checks; longs, and everything from the 14:00 check on, work as usual. Stocks tend to drift up into the 14:00 statement, and the morning shorts on those days lost money in every period tested (round twenty-four in [RESULTS.md](RESULTS.md)). It changes only 1–3 trades a year. The inputs *Fed days: no shorts before 14:00* (on by default) and *Fed announcement days* (pre-filled with 2026–2027 from federalreserve.gov) control it, and the dashboard's *Fed day* row shows when it's in force. In 2028, add that year's dates.
- **If a session ends early anyway**, the script closes any open position at the first bar after the early end, or at the next 09:30 bar. That can be hours later.

## 4. How it tells you what to do

Through a **TradingView alert**. It runs on TradingView's servers, so it keeps working with your browser and the app closed. One alert covers every action.

**Set it up once:**

1. On the chart with the script, click **Alert** (top bar).
2. **Condition:** *Noise-Mom*, then **Order fills and alert() function calls**. The "order fills" part is what tells you when your resting stop has filled.
3. **Notifications:** turn on **Notify in app**, which pushes to the TradingView phone app; log into the app with the same account. Add *Show popup* and *Send email* if you like.
4. **Expiration:** set it as far out as your plan allows, and recreate it when it expires.
5. **Create.**

**Recreate the alert whenever you change the script or its settings.** An alert keeps running the version it was created with.

**What arrives:** each alert is a full instruction, sent right at the half hour, for example *"BUY 3 MNQ at market now. Price 29,980.25 is above the noise area (upper 29,960.00). Bracket: stop 29,921.75 (your $350.00 max loss), take-profit limit 30,070.50, for a fill near 29,980.50. If your fill is different, keep the same distances. At each half hour move the stop with the line (the dashboard shows it); the max loss never moves. Next check 10:30."* **Act on it right away, with a bracket order** (entry, stop and take-profit together; Tradovate calls it a bracket or OSO). Speed matters more than anything else: in the stress tests, filling every entry 5 minutes late cut the profit roughly in half ([RESULTS.md](RESULTS.md), stress tests).

**The lock (v1.2): set it once in Tradovate.** Once a trade has gone as far in your favour as your max loss per contract (17.5 points with $350 on 10 MNQ), its stop moves to the entry plus 2.5 points, so it can't turn into a loser. At your setting it took the winners from about 1 in 7 trades to about 1 in 2 on 16 years of data, for the same money ([RESULTS.md](RESULTS.md), round thirty-seven). It has to act within seconds, so let the broker do it: in Tradovate, make a bracket strategy (ATM) for MNQ with the stop type **Auto Breakeven**, the profit trigger **70 ticks** (17.5 points) and the offset **+10 ticks** (2.5 points), and use it for every entry, with the stop and take-profit from the alert. The chart does the same one bar later, and the entry alert spells it out: *"Auto-breakeven: at 30,002.75 move the stop to 29,987.75."* Set *Lock a small win* to 0 to turn it off. If you change the contracts or the max loss, the trigger in ticks is twice the max loss per contract in dollars (70 ticks for $35).

**Done for the day after 4 losers (v1.3).** After the fourth losing trade of the day the bot takes no new entries until tomorrow (a trade already open runs on as usual). Four losers is about −$1,400 at 10 MNQ and $350. Tested before running on every period of both datasets: more per day, a higher t-stat and a smaller worst losing stretch ([RESULTS.md](RESULTS.md), round thirty-eight). The dashboard's *Trades today* shows the count, and turns orange with *done for today*. *Max losing trades a day* sets it; 0 turns it off.

**On the chart:**

| You see | Meaning |
|---|---|
| Teal line / maroon line | Upper / lower noise line. They appear from 10:00 and step at each half hour. |
| Green **BUY 10 MNQ** label under a candle | That candle's close was above the upper line: buy. |
| Red **SELL 10 MNQ** label over a candle | That candle's close was below the lower line: sell. |
| Grey **EXIT** label | Price touched the line and your stop filled (or, in half-hour check mode, a check closed back inside): the trade is over. |
| Teal **TARGET** label | The take-profit filled: the trade is over, in profit. |
| **REVERSE / SELL 20** or **REVERSE / BUY 20** | Price went through the other line: flip the position. |
| Grey **FLAT** label | 16:00: close the trade. |
| Orange **EXIT NOW** | A session ended early with a trade open: close it. |
| Teal / maroon shading | You're long / short. |
| Dashboard *Last signal* | The most recent instruction, with its time and price. |
| Small arrows with *+10 / −10* | TradingView's own backtest fills, one candle after the label: +10 is 10 contracts bought, −10 is 10 sold. |

The number on a label is the contracts, from the *Contracts* setting (10 by default). **SELL 10 MNQ** means go short 10 contracts.

The label sits on the half-hour candle that just closed, the moment the alert fires. The backtest fills at the next candle's open.

**Trade log.** A table at the bottom right of the chart lists every trade the bot took, newest first. Each row has the time it opened and closed (New York time, month-day hour:minute), the side and contracts, the entry and exit prices, the P/L after fees, and why it closed: *stop at the line*, *max loss stop*, *take profit*, *16:00 close* or *session ended*. While a trade is open it sits on top as **OPEN**, with the price now, the open P/L, and the stop and target to have in. *Trades in the log* sets how many rows it shows (10 by default, up to 30); TradingView's *List of trades* tab has all of them. The dashboard at the top right shows today's P/L, open P/L and trades today. There are no status alerts: nothing to set up to see your trades.

**Where you place the order:** the alert and the labels only tell you. You place every order yourself.

| Account | How to place it |
|---|---|
| TradingView Paper Trading | The **BUY / SELL** buttons on the chart, or the Trading Panel. Use market, 1 contract. |
| Take Profit Trader evaluation or funded account (Tradovate) | In the Tradovate app. Or connect Tradovate in TradingView's Trading Panel and use the chart's BUY / SELL buttons on that account. |

**Speed is worth money.** On 1-minute data, each minute between the alert and your fill cost about 15–25% of the profit, and three minutes late left about half ([RESULTS.md](RESULTS.md), round thirty-five). By hand, have the order ticket open before each half hour with the size and bracket distances set, and send it as soon as the alert lands.

**Automatic orders (webhook mode, v1.1).** First check your prop firm allows automation. **Take Profit Trader does not**: its Universal Trading Policies say *"Automated trading systems, bots, or algorithmic execution tools are not permitted."* Apex bans it too. Lucid Trading, MyFundedFutures, FundedNext Futures and FTMO Futures allow it in writing (September–October 2026; rules change, so read the firm's own page before you buy). Where it is allowed:

1. Get a TradersPost account and connect your Tradovate account (the firm's login). In the TradersPost strategy subscription, turn on **Use signal quantity**, **Use signal stop loss** and **Use signal take profit**, and allow the ticker MNQ.
2. In the script's settings, **Automation → Webhook orders: TradersPost**. Leave the contract blank to use the one behind the chart, or type the exact one (e.g. `MNQZ2026`) and change it at each quarterly roll.
3. Create an alert: **Condition** *Noise-Mom*, **Order fills only**; **Message** exactly `{{strategy.order.alert_message}}`; **Notifications → Webhook URL** your TradersPost URL. Webhooks need a paid TradingView plan.
4. For your phone, create a second alert with **alert() function calls only** and *Notify in app*. It sends the usual instructions, plus a line when a stop or target fills.

What the webhook sends, each time the strategy fills an order on the chart:

| When | Message |
|---|---|
| An entry fills | `{"ticker": "MNQZ2026", "action": "buy", "orderType": "market", "quantity": 10, "price": 25080.25, "stopLoss": {"type": "stop", "stopPrice": 25062.75}, "takeProfit": {"limitPrice": 25190.50}}` (`sell` for a short): a market order with its stop and take-profit attached, the same bracket the text alert names. |
| A stop, the take-profit, 16:00 or a session end closes the trade | `{"ticker": "MNQZ2026", "action": "exit", "cancel": true}`: close at market and cancel the bracket. If the broker's own stop or take-profit already filled, there is nothing left to close. |

In webhook mode the stop **only ever tightens** during a trade, because the broker holds the stop placed with the entry and the script can't move it. When the line moves closer to price, the chart's stop fills first and the exit message closes the trade. Tested both ways: the same money ([RESULTS.md](RESULTS.md), round thirty-five). Watch the first few trades on the TradersPost *Signals* page and in Tradovate, and keep the phone alert on.

| Alert starts with | Do this |
|---|---|
| `BUY 3 MNQ at market now` | Buy at market with a bracket: the stop and take-profit prices the alert names (or the same distances from your fill). |
| `SELL 3 MNQ at market now` | Sell at market with a bracket: the stop and take-profit prices the alert names (or the same distances from your fill). |
| `EXIT LONG: price hit the stop` / `EXIT SHORT: price hit the stop` | Your stop (the max loss, the line or the lock) should have filled. If you had no stop in, exit at market now. Cancel the take-profit order. |
| `TARGET: the long reached the take-profit` / `TARGET: the short …` | Your take-profit limit should have filled. If not, exit at market now. Cancel the stop order. |
| `EXIT LONG` / `EXIT SHORT` (half-hour check mode only) | Close the position at market and stay flat. |
| `REVERSE` | Close the position and open the opposite one, both at market. In Tradovate that means selling 2 to flip a 1-lot long to short, or buying 2 to flip a short to long. |
| `FLAT` | It's 16:00: close the position at market. |
| `EXIT NOW` | A session ended with a position still open: close it at market. |

## 5. Worked example

Say σ at 10:00 is 0.30%, today opened at 25,000.00, and yesterday closed at 24,900.00.

- **10:00 lines:** upper = 25,000 × 1.003 = **25,075.00**, lower = 24,900 × 0.997 = **24,825.30**.
- **10:00:** the check closes at 25,080.00, above the upper line → **BUY** 1 MNQ.
- **10:30:** σ is 0.40%, so upper = 25,000 × 1.004 = **25,100.00** and lower = 24,900 × 0.996 = **24,800.40**.
- **Outcome:** the 10:30 check closes at 25,090.00. That's below the upper line but above the lower → **EXIT**. If it had closed above 25,100.00, you'd hold to the next check.

## 6. What to expect

All numbers are from [RESULTS.md](RESULTS.md#third-round-16-years-2010-2026). They cover 16 years of Nasdaq-100 data, 1 MNQ at today's price level, and today's costs.

- **Average:** about **+$26 per session** (t = 5.0 over 16 years), with daily swings of about **$300**.
- **Trade count:** about 220 trades a year, and only **about a third of them win**. The average win (about $340) is close to three times the average loss (about $125), and a few big trend days carry the results. Losing streaks of ten trades are normal.
- **Worst cases:** the worst single intraday dip over 16 years was **−$1,552**, and the worst losing stretch **$5,666** (with the paper's half-hour exit: −$2,465 and $8,168).
- **By year:** 15 of 16 years were positive, and more than half the gains came from 2018 and 2022. 2026 is **−$1,527 through September.**
- **Why it is losing now:** this is a trend strategy, and 2025–2026 are the two least trending years in the data. In the good years a day moved 1.12–1.25 times its own noise; in 2025 it was 1.01 and in 2026 0.99, so breakouts stop following through. A filter that stands aside after such stretches was tested and didn't help: by the time it switches off, the bad patch is over. 2011 lost, and **2026 is down $3,155 through September**.
- **On a $25K / $1,500-drawdown evaluation**, starting on every historical day:
  - within 125 sessions: **52% pass, 40% fail**
  - within 500 sessions: **62% pass, 38% fail**
  (With the paper's half-hour exit: 38% / 57% and 47% / 53%.)
- **The account size matters most.** The same strategy and the same 1 MNQ, from every start day in 2011–2026, 500 sessions:

| Evaluation account (target / drawdown) | Pass | Fail | Still running | Median days to pass |
|---|---:|---:|---:|---:|
| $25K ($1,500 / $1,500) | 62% | 38% | 0% | 40 |
| $50K ($3,000 / $2,000) | 74% | 26% | 0% | 80 |
| **$100K ($6,000 / $3,000)** | **78%** | **22%** | 1% | 186 |
| $150K ($9,000 / $4,500) | 74% | 3% | 23% | 253 |

  A bigger account gives the same 1-contract swings more room, so far fewer runs die. The price is time: about a year of trading days to reach the $100K target, and the evaluation's monthly fee for each of those months. The tiers are as I understand Take Profit Trader's; check them and the fees on their site before paying.

- **Trading more often doesn't help.** Checking every 15 or 5 minutes, or using narrower bands, adds trades but not edge ([RESULTS.md](RESULTS.md#fourth-round-can-it-trade-more-often)). A version that trades on 83% of days doubled the worst losing stretch and lost about $15,000 over 2025–2026 ([fifth round](RESULTS.md#fifth-round-can-it-trade-on-most-days)). About 4 days in 10 with no trade is normal.

**Bottom line:** the edge is real over 16 years. A $25K evaluation is about 60/40 in your favour; a $100K one about 78/22, over a longer run. Forward-test it on alerts, without money, before paying for one.
