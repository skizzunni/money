# Noise-Area Momentum: exact rules

**Script:** [`pine/mnq_noise_momentum.pine`](../pine/mnq_noise_momentum.pine). The Python reference is [`mnqbot/noise.py`](../mnqbot/noise.py), and tests hold the two to the same trades, to the cent.

**Source:** Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)". It uses the paper's settings, minus its VWAP trailing stop, because the test data has no volume.

**In one line:** when price has moved further from the open than it usually does by that time of day, trade in that direction. Check every half hour and be flat by the close.

**It does not "never lose."** Read [What to expect](#6-what-to-expect) before you trade it.

---

## 1. Setup

1. **Chart:** `MNQ1!` (or the front-month MNQ contract) on **30 minutes** or 5 minutes. 1, 10 and 15 minutes also work. Extended hours can be on or off. Every one of these makes the same trades, because the script only acts at the half hours; a 30-minute chart just loads the most history.
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
| Flat | above the upper line | **BUY** 1 MNQ at market, then put a **stop order just below the upper line** (the alert gives the exact price) |
| Flat | below the lower line | **SELL** 1 MNQ at market, then put a **stop order just above the lower line** (the alert gives the exact price) |
| In a trade | anything | **Move your stop to the new level.** The lines, and the stop with them, move at every half hour. |
| Flat, inside the lines | | Nothing. |

- **The stop is the exit, and it sits 0.24 noise units past the line:** for a long at upper × (1 − 0.24 σ), for a short at lower × (1 + 0.24 σ). Why there: a trade-by-trade post-mortem of 2011–2018 found that 77% of losing trades were stop-outs on the line that then went on in our direction, and 0.24 σ is how far they typically overshot the line before resuming ([RESULTS.md](RESULTS.md#tenth-round-why-the-trades-lose)). On 2023–2026, years that analysis never saw, it raised profit per day by 43% and the win rate from 25% to 34%. If the stop level moves past the price when the lines update, the stop fills at once. The setting *Stop distance past the line* = 0 puts the stop on the line itself.
- **After a stop-out you're flat until the next check.** A new signal there can put you back in, including the other way.
- **Orders are market orders** placed right after the check. The backtest fills them at the next bar's open plus 1 tick of slippage. Stops fill at the line, or at the bar's open if price gapped through, minus 1 tick.
- **At 16:00, close everything.**
- **The paper's original rule** (exit only if a half-hour check closes back inside the lines, reverse if it closes through the other side) is still there under *Exit → Half-hour check*. It makes fewer trades and had bigger worst days.
- **Size: 1 MNQ.** On a $1,500 drawdown even that is large for this strategy; [What to expect](#6-what-to-expect) shows the account size that fits it.
- **No trades on holidays and half days.** On US market holidays (MLK Day, Memorial Day, Labor Day and so on), MNQ still trades but halts at about 13:00 ET. On half days (the day after Thanksgiving, Christmas Eve) the session also ends early. The 16-year test only traded full sessions, so the script sits these out. Its input *Don't trade on these dates* comes pre-filled with every 2026–2027 holiday and half day, and you can add news days to it. In 2028, add that year's dates.
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

**What arrives:** each alert is a full instruction, sent right at the half hour, for example *"BUY 1 MNQ at market now. Price 29,980.25 is above the noise area (upper 29,960.00). Hold until a half-hour check closes back below the upper line, or the 16:00 close. Next check 10:30."* Act on it right away: the backtest assumes you fill at about that price.

**On the chart:**

| You see | Meaning |
|---|---|
| Teal line / maroon line | Upper / lower noise line. They appear from 10:00 and step at each half hour. |
| Green **BUY 1** label under a candle | That candle's close was above the upper line: buy. |
| Red **SELL 1** label over a candle | That candle's close was below the lower line: sell. |
| Grey **EXIT** label | Price touched the line and your stop filled (or, in half-hour check mode, a check closed back inside): the trade is over. |
| **REVERSE / SELL 2** or **REVERSE / BUY 2** | Price went through the other line: flip the position. |
| Grey **FLAT** label | 16:00: close the trade. |
| Orange **EXIT NOW** | A session ended early with a trade open: close it. |
| Teal / maroon shading | You're long / short. |
| Dashboard *Last signal* | The most recent instruction, with its time and price. |
| Small arrows with *+1 / −1* | TradingView's own backtest fills, one candle after the label. |

The label sits on the half-hour candle that just closed, the moment the alert fires. The backtest fills at the next candle's open.

**Where you place the order:** the alert and the labels only tell you. You place every order yourself.

| Account | How to place it |
|---|---|
| TradingView Paper Trading | The **BUY / SELL** buttons on the chart, or the Trading Panel. Use market, 1 contract. |
| Take Profit Trader evaluation or funded account (Tradovate) | In the Tradovate app. Or connect Tradovate in TradingView's Trading Panel and use the chart's BUY / SELL buttons on that account. |

**Automatic orders** are possible: a webhook from the alert to a service such as TradersPost, which places the order on Tradovate. Webhooks need a paid TradingView plan, and prop firms set their own rules on automated trading, so check Take Profit Trader's rules before you try it. Doing it by hand is the safe default.

| Alert starts with | Do this |
|---|---|
| `BUY 1 MNQ at market now` | Buy 1 MNQ at market, then place a stop at the price the alert names (just below the upper line). |
| `SELL 1 MNQ at market now` | Sell 1 MNQ at market, then place a stop at the price the alert names (just above the lower line). |
| `EXIT LONG: price hit the stop` / `EXIT SHORT: price hit the stop` | Your stop should have filled. If you had no stop in, exit at market now. |
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
