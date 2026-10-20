// MNQ Noise Momentum v1.6 for NinjaTrader 8: the strategy that places the orders.
//
// The rules live in AddOns/MnqNoiseEngine.cs, the same rules as the Pine script and the tested Python bot. This file
// feeds it the chart's bars and turns its decisions into orders on the account the strategy runs on:
//   * entry: a market order at the close of the half-hour check bar, with a stop-loss and a take-profit attached
//     from the moment it fills (the closer of the line stop and the $ max loss, measured from the expected fill);
//   * after the fill, at every bar close: the stop moves with the line, measured from the real fill price, and to
//     entry + 2.5 points once price has reached +1 max loss (the lock); the take-profit sits 1.5 noise units from
//     the fill; if the new stop is already at or past the price, the position is closed at market instead;
//   * 16:00 New York: everything closed at market. A session that ends early: closed at market too.
//   * the breakout (on by default, docs/RESULTS.md round 101): in the bot's gaps, Larry Williams' volatility
//     breakout. The first bar of the day (09:30-15:00) to reach today's open +/- 0.5 x yesterday's 09:30-16:00 range
//     buys (sells) at market, $400 of risk in the evaluation and $200 funded (1-10 MNQ; round 134), the stop a quarter
//     of yesterday's range from the fill, out at 16:00. One a day, only while the bot is flat; the bot always comes
//     first: a bot entry while the breakout trade is open closes it at market (or reverses it) in the same bar.
//   * the evaluation's target (docs/RESULTS.md round 124): in the evaluation, everything is closed the moment the
//     account is $3,000 up (closed + open), which passes it; the take-profit of the trade in progress sits at that
//     price when it is the closer one. No new trades after that. Live only (not in backtests or the history loaded
//     before the strategy goes live); it counts the strategy's own P/L from then, plus "evaluation profit so far".
//   * optional, off by default (round 129): from a chosen day of the evaluation's 30, bigger size (2.5x: the bot at
//     10 MNQ), since an evaluation that runs out of time has failed anyway.
//   * on by default (rounds 128, 132): on the funded account, everything closed and no more trades that day the
//     moment closing makes the day payout-eligible (the payout cycle's state entered once, then kept from the account
//     and remembered in a file across restarts).
// Setup: 1-minute MNQ chart (the lock arms within the minute: more winners than on 5 minutes, docs/RESULTS.md round
// 81), Days to load 30 or more (the noise needs 14 full sessions), Calculate on bar close.
// See docs/NINJATRADER.md. Written in C# 5 for NinjaTrader 8's compiler.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.AddOns.MnqBot;
using NinjaTrader.NinjaScript.DrawingTools;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqNoiseMomentum : Strategy
    {
        const string LongName = "Long", ShortName = "Short", WLongName = "W Long", WShortName = "W Short";
        const string LongHalf = "Long half", ShortHalf = "Short half";  // PartialAtR: the half with its own target
        const int Nobody = 0, Bot = 1, Breakout = 2;
        NoiseEngine engine;
        WilliamsBreakout williams;
        int owner;                  // whose trade the account's position is: Nobody, Bot or Breakout
        NoiseSettings settings;
        TimeZoneInfo newYork;
        int minutes;
        bool badChart;
        bool realLocked;            // the real position reached the lock trigger
        bool closingRejected;       // a rejection already sent the position to market
        bool exitRejected;          // one of the strategy's own exits was rejected: sent again at the next bar
        double lastStop = double.NaN;  // TightenOnly: the bot's stop so far in this trade
        double entryStopPts = double.NaN;  // the bot's bracket stop, points from the fill
        string halfName = "";            // PartialAtR: the entry name of this trade's half ("": not split)
        double halfPts = double.NaN;     // its take-profit, points from the fill (PartialAtR x R)
        bool evalDone;              // the evaluation's target was reached: everything closed, no new trades
        double profitBase;          // the strategy's closed P/L when it went live (the history before doesn't count)
        const double EvalBuffer = 25.0;  // $ past the target, for the closing fees and a tick
        const int ApexMaxQty = 10;       // MNQ on a 50K Apex account
        double boldMult = 1.0;           // today's size multiple (the bold finish), set at each bar
        // alerts-only mode (orders off, the user clicks): what the user's account should hold, so the alerts can say
        // when to move a stop, take a target or close
        double saidStop = double.NaN, saidTarget = double.NaN;   // the bot's stop / take-profit last announced
        int wDir, wQty;                                           // the breakout trade the user was told to take
        double wStop = double.NaN, wTarget = double.NaN;
        bool wPending;                                            // told this bar; it fills at the next bar's open
        double wTargetPts = double.NaN;  // the breakout trade's own take-profit, points from the fill
        // the funded account's payout cycle (round 128): since the last payout, kept from the account day by day
        int cycleQual, payoutsTaken;
        double cycleProfit, cycleBest, dayStartLiq = double.NaN;
        bool payoutToday;                // closing made today payout-eligible: flat, no more trades today
        DateTime cycleDay = DateTime.MinValue;  // the trading day dayStartLiq is the start of
        DateTime lastBarDay = DateTime.MinValue;  // the trading day of the bar before
        double lastLiq = double.NaN;     // the account at the bar before (a payout leaving it shows as a drop)
        double pendingPayout;            // asked for, not yet seen leaving the account: not in the balance
        bool cycleLoaded, cycleFromFile, saveFailed;
        bool botSent, wSent;             // this bar, the entry order really went to the account
        string notSent = "";            // why an entry signal wasn't sent this bar
        int mismatchBars;                // bar closes in a row with the account's position not the strategy's
        static readonly double[] PayoutCaps = { 1500, 1500, 2000, 2500, 2500, 3000 };
        DateTime evalStart = DateTime.MinValue;
        // the diagnostics (docs/NINJATRADER.md, "No trades"): counts at each step from a bar to a trade, and why a signal
        // went no further. Counting only: nothing here places, changes or blocks an order.
        sealed class Tally { public int Step, N; public readonly List<string> Examples = new List<string>(); }
        readonly Dictionary<string, Tally> blockedBy = new Dictionary<string, Tally>();
        readonly List<string> blockedOrder = new List<string>();
        int dBars, dUsed, dReady, dChecks, dNoCross, dBotSignals, dWSignals, dPassed, dSubmitted, dRejected, dCancelled;
        int dExecs, dErrors;
        string dFirst = "", dLast = "", dFirstReady = "", dNow = "";
        readonly HashSet<Order> dAccepted = new HashSet<Order>(), dFilled = new HashSet<Order>();
        string lastSignal = "-";
        string headsUp = "";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqNoiseMomentum";
                Description = "MNQ noise-area momentum v1.6: half-hour checks 10:00-15:30 New York, $350 max loss, lock, 16:00 flat.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                // the bot's entries and the breakout's have their own names, so the bot can enter while the breakout
                // trade is being closed in the same bar
                EntryHandling = EntryHandling.UniqueEntries;
                // NinjaTrader's default: a stop and a target for each fill. With "by strategy position", Playback showed the
                // target for 3 contracts on a 4-contract position (the entry filled in parts)
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                // the strategy closes at 16:00 New York itself; NinjaTrader's own exit 60 s before the session's end (its
                // trading-hours template, holidays and early closes included) is the backstop if no bar comes to do it
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 0;               // the engine waits for its own 14 sessions
                StartBehavior = StartBehavior.WaitUntilFlat;
                // a rejection reaches OnOrderUpdate, which re-sends or flattens; any other realtime error stops the
                // strategy, cancels its orders and closes the position (never ignored)
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                TraceOrders = false;
                IsInstantiatedOnEachOptimizationIteration = true;

                Funded = false;
                AutoAccountType = true;
                EvalQty = 4;           // Apex 50K evaluation, intraday trail (docs/RESULTS.md round 60)
                FundedQty = 4;         // 50K funded (PA): pays the most per evaluation (docs/RESULTS.md round 61)
                PlaceOrders = true;
                EvalMaxLoss = 200;     // end-of-day plan instead: 6 MNQ, $300, 3 losers
                FundedMaxLoss = 200;
                TakeProfit = 1.5;
                StopBuffer = 0.24;
                EvalLockAt = 1.0;
                EvalLockPlus = 2.5;
                FundedLockAt = 0.5;    // funded: arm earlier, stop to entry + 6.25 (docs/RESULTS.md round 83)
                FundedLockPlus = 6.25;
                EvalMaxLosers = 3;
                FundedMaxLosers = 2;
                Lookback = 14;
                FedNoShorts = true;
                SkipDates = NoiseEngine.SkipDatesDefault;
                FedDates = NoiseEngine.FedDatesDefault;
                SoundAlerts = true;
                RoundPrices = true;
                UseBreakout = true;
                BreakoutK = 0.5;
                BreakoutStop = 0.25;
                BreakoutRisk = 200;
                EvalBreakoutRisk = 400;  // money a week per account, all four periods (docs/RESULTS.md round 134)
                BreakoutMaxQty = 10;
                BreakoutShorts = true;
                EvalTarget = 3000;
                EvalProfitSoFar = 0;
                EvalFromAccount = true;
                EvalTargetInHistory = false;
                EvalStartDate = "";
                BoldFromDay = 0;
                BoldSize = 2.5;
                PayoutStop = true;     // pays more a week per account in every period (docs/RESULTS.md round 132)
                FundedPayoutsTaken = 0;
                FundedQualDays = 0;
                FundedCycleProfit = 0;
                FundedBestDay = 0;
                PayoutStopInHistory = false;
                RememberPayoutCycle = true;
                TightenOnly = true;    // the stop never moves back toward the price (docs/RESULTS.md round 139)
                DailyMaxLosers = 0;    // shared daily gate, both setups (docs/VERIFICATION.md): off by default
                DailyLossLimit = 0;
                PartialAtR = 0;        // half off at 1R: frozen for the forward test, off by default
                Diagnostics = false;
                BreakoutTarget = 8;    // 8 x its stop = 2 x yesterday's range: a full bracket (docs/RESULTS.md round 130)
                AccountStart = 50000;

                AddPlot(Brushes.Teal, "Upper noise line");
                AddPlot(Brushes.Maroon, "Lower noise line");
                AddPlot(Brushes.Orange, "Stop");
                AddPlot(Brushes.LimeGreen, "Take-profit");
            }
            else if (State == State.Configure)
            {
                if (Diagnostics)
                    TraceOrders = true;  // NinjaTrader's own line for each order: submitted, ignored and why, rejected
            }
            else if (State == State.DataLoaded)
            {
                DetectAccountType();
                newYork = NewYork();
                badChart = BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value <= 0 ||
                           30 % BarsPeriod.Value != 0;
                minutes = badChart ? 5 : BarsPeriod.Value;
                settings = new NoiseSettings();
                settings.Qty = Qty;
                settings.Tick = TickSize;
                settings.PointValue = Instrument.MasterInstrument.PointValue;
                settings.MaxLoss = MaxLoss;
                settings.TakeProfit = TakeProfit;
                settings.StopBuffer = StopBuffer;
                settings.LockAt = LockAt;
                settings.LockPlus = LockPlus;
                settings.MaxLosers = MaxLosers;
                settings.TightenOnly = TightenOnly;
                settings.Lookback = Lookback;
                settings.FedNoShorts = FedNoShorts;
                settings.SkipDates = SkipDates ?? "";
                settings.FedDates = FedDates ?? "";
                engine = new NoiseEngine(settings, minutes);
                WilliamsSettings ws = new WilliamsSettings();
                ws.K = BreakoutK;
                ws.StopFraction = BreakoutStop;
                ws.Risk = Funded ? BreakoutRisk : EvalBreakoutRisk;
                ws.MaxQty = BreakoutMaxQty;
                ws.Shorts = BreakoutShorts;
                ws.PointValue = settings.PointValue;
                williams = new WilliamsBreakout(ws);
                cycleQual = FundedQualDays;
                cycleProfit = FundedCycleProfit;
                cycleBest = FundedBestDay;
                payoutsTaken = FundedPayoutsTaken;
                DateTime d0;
                if (DateTime.TryParseExact(EvalStartDate ?? "", "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture,
                                           System.Globalization.DateTimeStyles.None, out d0))
                    evalStart = d0;
                PrintSettings();
            }
            else if (State == State.Realtime)
            {
                profitBase = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
                PrintFunnel("the history before going live");
                LoadLiveDay();
            }
            else if (State == State.Terminated && engine != null)
            {
                try { PrintFunnel("end of run"); }
                catch (Exception e) { Print("MNQ funnel: could not be printed (" + e.Message + ")"); }
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }  // Windows
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        int Qty { get { return Funded ? FundedQty : EvalQty; } }
        double MaxLoss { get { return Funded ? FundedMaxLoss : EvalMaxLoss; } }
        double LockAt { get { return Funded ? FundedLockAt : EvalLockAt; } }
        double LockPlus { get { return Funded ? FundedLockPlus : EvalLockPlus; } }
        int MaxLosers { get { return Funded ? FundedMaxLosers : EvalMaxLosers; } }
        string Book { get { return Funded ? "Funded" : "Evaluation"; } }  // not "Account": that is NinjaTrader's
        string accountTypeFrom = "the FUNDED ACCOUNT setting";

        // Evaluation or funded from the account the strategy runs on, so the same settings serve both and nothing is
        // switched by hand when Apex hands over the funded account: Apex names its funded (Performance) accounts
        // PA-APEX-..., its evaluations APEX-... Any other name (a simulation account): the FUNDED ACCOUNT setting.
        void DetectAccountType()
        {
            if (!AutoAccountType || Account == null || string.IsNullOrEmpty(Account.Name))
                return;
            string n = Account.Name.ToUpperInvariant();
            if (n.StartsWith("PA-") || n.StartsWith("PA_") || n.StartsWith("PAAPEX"))
                Funded = true;
            else if (n.StartsWith("APEX"))
                Funded = false;
            else
                return;
            accountTypeFrom = "the account's name, " + Account.Name;
        }

        // The evaluation's target: on in the evaluation, live (or in the tests)
        bool EvalTargetOn { get { return !Funded && EvalTarget > 0 && (State == State.Realtime || EvalTargetInHistory); } }

        // The evaluation's closed profit, $: the account's cash balance less its starting balance (what Apex measures; it
        // survives a restart, or NinjaTrader recalculating the strategy after a lost connection, with nothing to
        // re-enter). EvalFromAccount off, or a connection that reports no balance: the strategy's own closed P/L since
        // it went live, plus "profit already made before this start".
        double EvalClosed
        {
            get
            {
                if (EvalFromAccount && Account != null)
                {
                    double cash = Account.Get(AccountItem.CashValue, Currency.UsDollar);
                    if (cash > 0)
                        return cash - AccountStart;
                }
                return EvalProfitSoFar + SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - profitBase;
            }
        }

        // The evaluation's profit for the dashboard: the strategy's own when it trades, the account's when it only alerts
        double EvalShown
        {
            get
            {
                if (!PlaceOrders && EvalTargetOn)
                    return Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) - AccountStart;
                return EvalClosed;
            }
        }

        // The price at which the position in progress takes the evaluation to its target (NaN: no position)
        double EvalTargetPrice(int d)
        {
            if (d == 0 || Position.Quantity <= 0)
                return double.NaN;
            double need = EvalTarget + EvalBuffer - EvalClosed;
            return Position.AveragePrice + d * need / (Position.Quantity * settings.PointValue);
        }

        bool PayoutStopOn { get { return Funded && PayoutStop && (State == State.Realtime || PayoutStopInHistory); } }

        // Apex's trading day, from a New York time: 18:00 to 17:00 the next day
        static DateTime TradingDay(DateTime ny) { return ny.AddHours(6).Date; }

        // The funded account's payout cycle, from the account's net liquidation: at each trading day's first bar the
        // day before is added to the cycle (and the cycle starts again after a payout day); at each bar, if closing now
        // (with $10 to spare for the fill) would make today payout-eligible, today is a payout day: flat, no more trades.
        // A payout asked for is counted out of the balance until it is seen leaving the account (one bar's drop of 90%
        // of it or more), and that drop is not a trading loss. The state is kept in a file, so a restart goes on from it.
        void PayoutCheck(DateTime nyStart, DateTime prevBarDay)
        {
            if (!PayoutStopOn)
                return;
            if (!cycleLoaded)
                LoadCycle();
            double liq = Account.Get(AccountItem.NetLiquidation, Currency.UsDollar);
            if (pendingPayout > 0 && !double.IsNaN(lastLiq) && lastLiq - liq >= 0.9 * pendingPayout)
            {
                dayStartLiq -= pendingPayout;  // the payout left the account: not part of the day's result
                pendingPayout = 0;
            }
            DateTime day = TradingDay(nyStart);
            if (day != cycleDay)
            {
                // the day's start: now if this is its first bar on the chart; else (started during the day) the
                // balance before today's trades, from the account's P/L for the day
                double start = prevBarDay == day ? liq - Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar) -
                               Account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar) : liq;
                if (!double.IsNaN(dayStartLiq) && cycleDay != DateTime.MinValue)
                {
                    double result = start - dayStartLiq;
                    if (payoutToday)
                    {
                        payoutsTaken++;  // the payout was asked for after the payout day's close: a new cycle
                        cycleQual = 0;
                        cycleProfit = 0;
                        cycleBest = 0;
                    }
                    else
                    {
                        cycleQual += result >= 200 ? 1 : 0;
                        cycleProfit += result;
                        cycleBest = Math.Max(cycleBest, result);
                    }
                    int missed = 0;
                    for (DateTime d = cycleDay.AddDays(1); d < day; d = d.AddDays(1))
                        missed += d.DayOfWeek == DayOfWeek.Saturday || d.DayOfWeek == DayOfWeek.Sunday ? 0 : 1;
                    if (missed > 0)
                        Say("cycle", "PAYOUT CYCLE: the strategy was off on " + missed + " weekday(s) before today; any " +
                            "trading then is counted as part of " + cycleDay.ToString("yyyy-MM-dd") + ". If that is " +
                            "wrong, enter the cycle in the settings (new settings replace the remembered state).");
                }
                cycleDay = day;
                dayStartLiq = start;
                payoutToday = false;
            }
            lastLiq = liq;
            if (payoutToday || double.IsNaN(dayStartLiq) || payoutsTaken >= PayoutCaps.Length)
            {
                SaveCycle();
                return;
            }
            double today = liq - dayStartLiq - 10, bal = liq - AccountStart - pendingPayout - 10;
            double prof = cycleProfit + today, best = Math.Max(cycleBest, today);
            double amount = Math.Min(PayoutCaps[payoutsTaken], bal - 2100);
            if (today >= 200 && cycleQual + 1 >= 5 && bal >= 2600 && prof > 0 && best <= 0.5 * prof && amount >= 500)
            {
                payoutToday = true;
                pendingPayout = amount;
                Say("payout","PAYOUT-ELIGIBLE: closing now makes today your " + (cycleQual + 1) + "th $200 day with the " +
                    "account " + Usd(bal) + " up. " + (PlaceOrders ? "Everything is closed" : "CLOSE EVERYTHING NOW") +
                    "; no more trades today. After the close, request your payout (about " + Usd(amount) + ").");
            }
            SaveCycle();
        }

        // ── The payout cycle's file: Documents\NinjaTrader 8\MnqNoiseMomentum\payout-cycle-<account>.txt
        string CycleFile { get { return DataFile("payout-cycle-"); } }

        string DataFile(string prefix)
        {
            string name = Account == null || string.IsNullOrEmpty(Account.Name) ? "account" : Account.Name;
            foreach (char c in Path.GetInvalidFileNameChars())
                name = name.Replace(c, '_');
            return Path.Combine(Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "MnqNoiseMomentum"), prefix + name + ".txt");
        }

        // the settings the remembered state started from: new settings replace it
        string CycleSettings
        {
            get { return string.Join("|", FundedQualDays, F(FundedCycleProfit), F(FundedBestDay), FundedPayoutsTaken); }
        }

        static string F(double x) { return x.ToString("R", CultureInfo.InvariantCulture); }

        static double D(Dictionary<string, string> kv, string key)
        {
            return kv.ContainsKey(key) ? double.Parse(kv[key], CultureInfo.InvariantCulture) : double.NaN;
        }

        void LoadCycle()
        {
            cycleLoaded = true;
            if (!RememberPayoutCycle)
                return;
            try
            {
                if (!File.Exists(CycleFile))
                    return;
                Dictionary<string, string> kv = new Dictionary<string, string>();
                foreach (string line in File.ReadAllLines(CycleFile))
                {
                    int eq = line.IndexOf('=');
                    if (eq > 0)
                        kv[line.Substring(0, eq)] = line.Substring(eq + 1);
                }
                if (!kv.ContainsKey("settings") || kv["settings"] != CycleSettings)
                {
                    Print("Payout cycle: the settings changed since " + CycleFile + " was written; starting from the settings.");
                    return;
                }
                cycleQual = int.Parse(kv["qual"], CultureInfo.InvariantCulture);
                payoutsTaken = int.Parse(kv["taken"], CultureInfo.InvariantCulture);
                cycleProfit = D(kv, "profit");
                cycleBest = D(kv, "best");
                dayStartLiq = D(kv, "start");
                lastLiq = D(kv, "last");
                pendingPayout = D(kv, "pending");
                payoutToday = kv["payoutToday"] == "1";
                cycleDay = DateTime.ParseExact(kv["day"], "yyyy-MM-dd", CultureInfo.InvariantCulture);
                cycleFromFile = true;
                Print("Payout cycle: continuing from " + CycleFile);
            }
            catch (Exception e)
            {
                Print("Payout cycle: could not read " + CycleFile + " (" + e.Message + "); starting from the settings.");
                cycleQual = FundedQualDays;
                cycleProfit = FundedCycleProfit;
                cycleBest = FundedBestDay;
                payoutsTaken = FundedPayoutsTaken;
                dayStartLiq = lastLiq = double.NaN;
                pendingPayout = 0;
                payoutToday = false;
                cycleDay = DateTime.MinValue;
            }
        }

        void SaveCycle()
        {
            if (!RememberPayoutCycle || cycleDay == DateTime.MinValue)
                return;
            try
            {
                string file = CycleFile, tmp = file + ".tmp";
                Directory.CreateDirectory(Path.GetDirectoryName(file));
                File.WriteAllText(tmp, "settings=" + CycleSettings + "\nqual=" + cycleQual + "\ntaken=" + payoutsTaken +
                    "\nprofit=" + F(cycleProfit) + "\nbest=" + F(cycleBest) + "\nday=" + cycleDay.ToString("yyyy-MM-dd") +
                    "\nstart=" + F(dayStartLiq) + "\nlast=" + F(lastLiq) + "\npending=" + F(pendingPayout) +
                    "\npayoutToday=" + (payoutToday ? "1" : "0") + "\n");
                if (File.Exists(file))
                    File.Replace(tmp, file, null);
                else
                    File.Move(tmp, file);
                saveFailed = false;
            }
            catch (Exception e)
            {
                if (!saveFailed)  // said once; it tries again at the next bar, and the payout stop goes on meanwhile
                    Print("Payout cycle: could not write " + CycleFile + " (" + e.Message + "); trying again each bar.");
                saveFailed = true;
            }
        }

        // The bold finish: on in the evaluation from day BoldFromDay of its 30 (counted from EvalStartDate), until passed
        bool BoldDay(DateTime nyStart)
        {
            return !Funded && BoldFromDay > 0 && BoldSize > 1 && !evalDone && evalStart != DateTime.MinValue &&
                   (nyStart.Date - evalStart.Date).Days >= BoldFromDay;
        }

        // Contracts for a new entry: as set, or the bold finish's multiple of them, within Apex's 10 MNQ
        int BotQty { get { return boldMult > 1 ? Math.Min(ApexMaxQty, Math.Max(1, (int)Math.Round(Qty * boldMult))) : Qty; } }

        int BreakoutQty
        {
            get
            {
                if (boldMult <= 1) return williams.Qty;
                return Math.Min(Math.Min(BreakoutMaxQty, ApexMaxQty), Math.Max(1, (int)Math.Floor(williams.Qty * boldMult)));
            }
        }

        int RealDir
        {
            get
            {
                if (Position.MarketPosition == MarketPosition.Long) return 1;
                if (Position.MarketPosition == MarketPosition.Short) return -1;
                return 0;
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0)
                return;
            try
            {
                BarUpdate();
            }
            catch (Exception e)
            {
                // said in the Output window with the bar, then passed on: NinjaTrader stops the strategy and logs it
                dErrors++;
                Block(0, "runtime error", e.GetType().Name + ": " + e.Message);
                Print("MNQ RUNTIME ERROR at the bar ending " + dNow + " (New York): " + e);
                throw;
            }
        }

        void BarUpdate()
        {
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            DateTime end = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified), platform, newYork);
            dNow = end.ToString("yyyy-MM-dd HH:mm");
            dBars++;
            if (dFirst.Length == 0)
                dFirst = dNow;
            dLast = dNow;
            if (badChart || Calculate != Calculate.OnBarClose)
            {
                Block(1, badChart ? "the chart's bars aren't 1-30 minutes dividing 30" : "Calculate isn't On bar close", "");
                Draw.TextFixed(this, "mnq_dash", badChart ?
                    "MNQ Noise Momentum: use a 1, 5, 10, 15 or 30 minute chart (1 minute is best). Not trading." :
                    "MNQ Noise Momentum: set Calculate to 'On bar close' in the strategy settings. Not trading.",
                    TextPosition.TopRight);
                return;
            }
            dUsed++;
            // NinjaTrader stamps a bar with its end time in the time zone set under Tools > Options > General (above)
            DateTime start = end.AddMinutes(-minutes);
            int nTrades = engine.Trades.Count, nOrders = engine.Orders.Count;
            int nHeads = engine.HeadsUps.Count;
            if (PlaceOrders)  // the bot's loser limit from the day's fills (simulated in history, the account's live)
            {
                int bn, bl;
                double br;
                Ledger(DayRecords(start), true, out bn, out bl, out br);
                engine.ExternalLosers = bl;
            }
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            // the breakout only while the bot is flat with no entry coming, and the account is flat
            bool free = engine.Position == 0 && engine.PendingEntry == 0 && !engine.SkipToday && engine.Ready &&
                        (!PlaceOrders || RealDir == 0) && engine.Orders.Count == nOrders;
            if (UseBreakout)
                williams.OnBar(start, Open[0], High[0], Low[0], free);
            CountSignals(nOrders);
            if (start.Hour * 60 + start.Minute == NoiseEngine.RthOpen)  // once a day in the Output window, chart or not
                Print(start.ToString("yyyy-MM-dd") + " MNQ Noise Momentum (" + Book + ", " + Qty + " MNQ, orders " +
                      (PlaceOrders ? "ON" : "OFF") + "): " + (engine.Ready ? "ready, trading today" + (engine.SkipToday ?
                      " (no: skip date)" : "") : "loading history, " + engine.SessionsLoaded + "/" + Lookback +
                      " full sessions; no trades until " + Lookback + ". Load more days."));

            boldMult = BoldDay(start) ? BoldSize : 1.0;
            PayoutCheck(start, lastBarDay);
            lastBarDay = TradingDay(start);
            if (PlaceOrders)
                ManageOrders(start, nOrders);
            if (PlaceOrders && LiveBook)
                SaveLiveDay(start);
            CountSent(nOrders);
            Tell(nTrades, nOrders, nHeads);
            Draw.TextFixed(this, "mnq_dash", Dashboard(), TextPosition.TopRight);
        }

        // ── Orders on the account

        // ── The day's closed trades, from executions. Two sources, never mixed: in a backtest and in the history a
        // strategy runs through before going live, its simulated fills (SystemPerformance.AllTrades); live, only the
        // account's real fills since the strategy went live (SystemPerformance.RealTimeTrades), with those of earlier
        // runs today from the live-day file (a restart), never the simulated trades of today's history.
        sealed class Closed { public long EntryTicks, ExitTicks; public string EntryName, ExitName; public int Qty; public double Pnl; }
        readonly List<Closed> liveFromFile = new List<Closed>();
        DateTime liveFileDay = DateTime.MinValue;
        int liveSaved = -1;

        bool LiveBook { get { return State == State.Realtime; } }

        static string Key(Closed c)
        {
            return c.EntryTicks + "|" + c.EntryName + "|" + c.ExitTicks + "|" + c.Qty + "|" + F(c.Pnl);
        }

        List<Closed> DayRecords(DateTime nyNow)
        {
            DateTime day = TradingDay(nyNow);
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            TradeCollection src = LiveBook ? SystemPerformance.RealTimeTrades : SystemPerformance.AllTrades;
            List<Closed> list = new List<Closed>();
            Dictionary<string, bool> seen = new Dictionary<string, bool>();
            for (int k = src.Count - 1; k >= 0; k--)
            {
                Trade tr = src[k];
                DateTime exitNy = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(tr.Exit.Time, DateTimeKind.Unspecified),
                                                           platform, newYork);
                if (TradingDay(exitNy) != day)
                    break;
                Closed c = new Closed();
                c.EntryTicks = tr.Entry.Time.Ticks; c.ExitTicks = tr.Exit.Time.Ticks; c.EntryName = tr.Entry.Name;
                c.ExitName = tr.Exit.Name; c.Qty = tr.Quantity; c.Pnl = tr.ProfitCurrency;
                list.Add(c);
                seen[Key(c)] = true;
            }
            if (LiveBook && liveFileDay == day)
                foreach (Closed c in liveFromFile)
                    if (!seen.ContainsKey(Key(c)))
                        list.Add(c);
            return list;
        }

        // the bot's two lots of one trade (PartialAtR) are one position
        static string Family(string entryName)
        {
            if (entryName == LongHalf) return LongName;
            if (entryName == ShortHalf) return ShortName;
            return entryName;
        }

        static bool IsBotEntry(string name)
        {
            return name == LongName || name == ShortName || name == LongHalf || name == ShortHalf;
        }

        // The trading day's closed positions (from 18:00 New York): one position filled in parts, or the bot's two lots,
        // is several records with the same entry, counted here as one trade. botOnly: the bot's own, for its loser
        // limit, without the positions closed at the session's end (as the model, which doesn't count those).
        void TodayLedger(DateTime nyNow, out int trades, out int losers, out double realized)
        {
            Ledger(DayRecords(nyNow), false, out trades, out losers, out realized);
        }

        static void Ledger(List<Closed> records, bool botOnly, out int trades, out int losers, out double realized)
        {
            trades = losers = 0;
            realized = 0.0;
            Dictionary<string, double> byPosition = new Dictionary<string, double>();
            Dictionary<string, bool> sessionEnd = new Dictionary<string, bool>();
            foreach (Closed c in records)
            {
                if (botOnly && !IsBotEntry(c.EntryName))
                    continue;
                string key = c.EntryTicks + "|" + Family(c.EntryName);
                double v;
                byPosition[key] = (byPosition.TryGetValue(key, out v) ? v : 0.0) + c.Pnl;
                if (c.ExitName == "Flat 16:00" || c.ExitName == "Exit on session close")
                    sessionEnd[key] = true;
                realized += c.Pnl;
            }
            foreach (KeyValuePair<string, double> kv in byPosition)
            {
                trades++;
                if (kv.Value < 0 && !(botOnly && sessionEnd.ContainsKey(kv.Key)))
                    losers++;
            }
        }

        // ── The live-day file: Documents\NinjaTrader 8\MnqNoiseMomentum\live-day-<account>.txt, the day's live closed
        // trades, so a restart during the day still counts them (the loser limits, the daily gate, the dashboard)
        string LiveFile { get { return DataFile("live-day-"); } }

        void LoadLiveDay()
        {
            liveFromFile.Clear();
            liveFileDay = DateTime.MinValue;
            try
            {
                if (!File.Exists(LiveFile))
                    return;
                foreach (string line in File.ReadAllLines(LiveFile))
                {
                    if (line.StartsWith("day="))
                        liveFileDay = DateTime.ParseExact(line.Substring(4), "yyyy-MM-dd", CultureInfo.InvariantCulture);
                    else if (line.StartsWith("trade="))
                    {
                        string[] f = line.Substring(6).Split('|');
                        Closed c = new Closed();
                        c.EntryTicks = long.Parse(f[0], CultureInfo.InvariantCulture); c.EntryName = f[1];
                        c.ExitTicks = long.Parse(f[2], CultureInfo.InvariantCulture); c.ExitName = f[3];
                        c.Qty = int.Parse(f[4], CultureInfo.InvariantCulture); c.Pnl = double.Parse(f[5], CultureInfo.InvariantCulture);
                        liveFromFile.Add(c);
                    }
                }
                if (liveFromFile.Count > 0)
                    Print("Live day: " + liveFromFile.Count + " live trade record(s) of " + liveFileDay.ToString("yyyy-MM-dd") +
                          " from " + LiveFile);
            }
            catch (Exception e)
            {
                Print("Live day: could not read " + LiveFile + " (" + e.Message + "); today's earlier live trades are not counted.");
                liveFromFile.Clear();
            }
        }

        void SaveLiveDay(DateTime nyNow)
        {
            List<Closed> today = DayRecords(nyNow);
            if (today.Count == liveSaved && liveFileDay == TradingDay(nyNow))
                return;
            try
            {
                string file = LiveFile, tmp = file + ".tmp";
                Directory.CreateDirectory(Path.GetDirectoryName(file));
                System.Text.StringBuilder b = new System.Text.StringBuilder("day=" + TradingDay(nyNow).ToString("yyyy-MM-dd") + "\n");
                foreach (Closed c in today)
                    b.Append("trade=" + c.EntryTicks + "|" + c.EntryName + "|" + c.ExitTicks + "|" + c.ExitName + "|" + c.Qty + "|" +
                             F(c.Pnl) + "\n");
                File.WriteAllText(tmp, b.ToString());
                if (File.Exists(file))
                    File.Replace(tmp, file, null);
                else
                    File.Move(tmp, file);
                liveFileDay = TradingDay(nyNow);  // the file holds today's only
                liveFromFile.Clear();
                liveFromFile.AddRange(today);
                liveSaved = today.Count;
            }
            catch (Exception e)
            {
                if (liveSaved != -2)
                    Print("Live day: could not write " + LiveFile + " (" + e.Message + "); trying again each bar.");
                liveSaved = -2;
            }
        }

        // The shared daily gate in front of both entry paths (bot and breakout): "" to go, else why not. No entry once
        // the day has DailyMaxLosers losing trades (both setups); none whose planned risk (stop distance x contracts x
        // $2, plus a tick a side) could take the day's realized loss past DailyLossLimit. Live, the realized loss is
        // the worse of the strategy's and the account's own for the day.
        string RiskGate(DateTime nyNow, double plannedRisk)
        {
            if (DailyMaxLosers <= 0 && DailyLossLimit <= 0)
                return "";
            int n, losers;
            double realized;
            TodayLedger(nyNow, out n, out losers, out realized);
            if (State == State.Realtime && Account != null)
                realized = Math.Min(realized, Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar));
            if (DailyMaxLosers > 0 && losers >= DailyMaxLosers)
                return "today's " + losers + " losing trades reach the daily limit (both setups)";
            if (DailyLossLimit > 0 && realized - plannedRisk < -DailyLossLimit)
                return "its risk (" + Usd(plannedRisk) + ") could take today past the " + Usd(DailyLossLimit) + " loss limit";
            return "";
        }

        double PlannedRisk(double stopPoints, int qty)
        {
            return (stopPoints + 2 * TickSize) * qty * settings.PointValue;
        }

        // Live: the account's own position in MNQ against the strategy's. They differ after a restart with a position
        // left open (NinjaTrader cancels a disabled strategy's stop and target), a trade placed by hand, or a fill the
        // strategy missed. Apart at a bar close: no new entries (no doubling up) until they agree again; apart at two
        // in a row: a loud alert. The strategy's own position, if any, is still managed.
        bool EntriesBlocked()
        {
            if (State != State.Realtime || PositionAccount == null)
                return false;
            int acct = Signed(PositionAccount), mine = Signed(Position);
            if (acct == mine)
            {
                if (mismatchBars >= 2)
                    Say("account", "ACCOUNT AND STRATEGY AGREE AGAIN (" + mine + " MNQ): new entries allowed.");
                mismatchBars = 0;
                return false;
            }
            mismatchBars++;  // entries are blocked from the first bar apart; the alert waits for the second
            if (mismatchBars == 2)
                Say("account", "ACCOUNT POSITION MISMATCH: the account holds " + acct + " MNQ, the strategy " + mine +
                    ". No new entries until they agree. If the account's position has no stop, close it or protect it NOW.");
            return true;
        }

        static int Signed(Position p)
        {
            return p.MarketPosition == MarketPosition.Long ? p.Quantity : p.MarketPosition == MarketPosition.Short ? -p.Quantity : 0;
        }
        void ManageOrders(DateTime start, int nOrders)
        {
            int real = RealDir;
            bool blocked = EntriesBlocked();
            botSent = wSent = false;
            notSent = blocked ? "the account's position isn't the strategy's" : "";
            if (real == 0)
            {
                realLocked = false;
                closingRejected = false;
                exitRejected = false;
                owner = Nobody;
                lastStop = double.NaN;
                halfName = "";
            }
            else if (exitRejected)
            {
                // an exit was rejected: never left there, the position is sent to market again at every bar until flat
                exitRejected = false;
                Say("retry", "EXIT REJECTED, SENT AGAIN: closing the " + (real > 0 ? "long" : "short") + " at market. " +
                    "If this repeats, close it by hand.");
                Flatten(real, "Close: retry");
                notSent = "a rejected exit is being sent again";
                return;
            }

            // 16:00 New York, or a bar outside 09:30-16:00 (a session that ended early): any position is closed at
            // market, whatever the engine's own position is
            int tMin = start.Hour * 60 + start.Minute, endMin = tMin + minutes;
            bool inRth = tMin >= NoiseEngine.RthOpen && endMin <= NoiseEngine.RthClose;
            if (real != 0 && (endMin == NoiseEngine.RthClose || !inRth || tMin == NoiseEngine.RthOpen))
            {
                Flatten(real, "Flat 16:00");
                notSent = "the position is being closed (16:00 or the session's end)";
                return;
            }

            // the funded account's payout day (round 128): flat, no more trades today
            if (payoutToday)
            {
                notSent = "today is a payout day";
                if (real != 0)
                    Flatten(real, "Payout-eligible");
                return;
            }

            // the evaluation's target: passed once the closed profit is there (the take-profit below aims $25 past it,
            // for the closing fees); a position already past target + $25 at this close is closed at market
            if (EvalTargetOn)
            {
                if (!evalDone && EvalClosed >= EvalTarget)
                {
                    evalDone = true;
                    Say("evaltarget", "EVALUATION TARGET REACHED: " + Usd(EvalClosed) + " up. Everything is closed and " +
                        "the strategy takes no new trades. Run it on the funded account (PA-APEX-...) when Apex gives it to you.");
                }
                double open = real != 0 ? Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) : 0.0;
                if (real != 0 && (evalDone || EvalClosed + open >= EvalTarget + EvalBuffer))
                {
                    Flatten(real, "Evaluation target");
                    return;
                }
                if (evalDone)
                {
                    notSent = "the evaluation's target is reached";
                    return;
                }
            }

            // a new entry: the bracket goes in first, so it is attached the moment the entry fills. It is set in ticks
            // from the fill, as a broker's bracket is, so a fill away from the expected price (a fast market) still
            // gets its stop and take-profit on the right side, the same distances away.
            // The bot comes first: an open breakout trade is closed in the same direction's case, reversed by the entry
            // itself in the other.
            string gate = "";
            if (!blocked && engine.Orders.Count > nOrders && (real == 0 || owner == Breakout))
            {
                NoiseOrder go = engine.Orders[engine.Orders.Count - 1];
                gate = RiskGate(start, PlannedRisk(go.Direction * (go.Expected - go.Stop), BotQty));
                if (gate.Length > 0)
                    notSent = gate;
            }
            if (!blocked && gate.Length == 0 && engine.Orders.Count > nOrders && (real == 0 || owner == Breakout))
            {
                NoiseOrder o = engine.Orders[engine.Orders.Count - 1];
                string name = o.Direction > 0 ? LongName : ShortName;
                if (real == o.Direction)
                {
                    if (real > 0) ExitLong("Breakout: bot first", WLongName);
                    else ExitShort("Breakout: bot first", WShortName);
                }
                double stopTicks = StopTicks(o.Direction * (o.Expected - o.Stop));
                SetStopLoss(name, CalculationMode.Ticks, stopTicks, false);
                entryStopPts = stopTicks * TickSize;  // R: the initial risk, points from the fill
                lastStop = double.NaN;
                double tpPts = double.IsNaN(o.Target) ? double.NaN : o.Direction * (o.Target - o.Expected);
                double evalPts = EvalPoints(BotQty);
                if (!double.IsNaN(evalPts) && (double.IsNaN(tpPts) || evalPts < tpPts))
                    tpPts = evalPts;
                if (!double.IsNaN(tpPts))
                    SetProfitTarget(name, CalculationMode.Ticks, TargetTicks(tpPts));
                // the partial exit (off by default; docs/VERIFICATION.md): half the contracts are their own entry, with
                // the same stop and their own take-profit PartialAtR x R from the fill, both sent with it (Set orders,
                // per entry: no separate exit order to conflict with them). Not on a reversal of a breakout trade.
                int half = PartialAtR > 0 && BotQty >= 2 && real != -o.Direction ? BotQty / 2 : 0;
                halfName = half > 0 ? (o.Direction > 0 ? LongHalf : ShortHalf) : "";
                halfPts = half > 0 ? PartialAtR * entryStopPts : double.NaN;
                if (half > 0)
                {
                    SetStopLoss(halfName, CalculationMode.Ticks, stopTicks, false);
                    double hp = !double.IsNaN(evalPts) && evalPts < halfPts ? evalPts : halfPts;
                    SetProfitTarget(halfName, CalculationMode.Ticks, TargetTicks(hp));
                }
                Submitted(o.Direction > 0 ? EnterLong(BotQty - half, LongName) : EnterShort(BotQty - half, ShortName), "bot");
                if (half > 0)
                    Submitted(o.Direction > 0 ? EnterLong(half, LongHalf) : EnterShort(half, ShortHalf), "bot half");
                botSent = true;
                owner = Bot;
                realLocked = false;
                closingRejected = false;
                return;
            }

            // the breakout: its stop in ticks from the fill, out at 16:00 (above); nothing else to manage
            string wgate = !blocked && williams.Signal != 0 && real == 0 ?
                RiskGate(start, PlannedRisk(williams.StopPoints, BreakoutQty)) : "";
            if (wgate.Length > 0)
                notSent = wgate;
            if (!blocked && wgate.Length == 0 && williams.Signal != 0 && real == 0)
            {
                string wname = williams.Signal > 0 ? WLongName : WShortName;
                int wq = BreakoutQty;
                SetStopLoss(wname, CalculationMode.Ticks, StopTicks(williams.StopPoints), false);
                double wPts = BreakoutTarget > 0 ? BreakoutTarget * williams.StopPoints : double.NaN;
                double wEval = EvalPoints(wq);
                if (!double.IsNaN(wEval) && (double.IsNaN(wPts) || wEval < wPts))
                    wPts = wEval;
                if (!double.IsNaN(wPts))
                    SetProfitTarget(wname, CalculationMode.Ticks, TargetTicks(wPts));
                wTargetPts = BreakoutTarget > 0 ? BreakoutTarget * williams.StopPoints : double.NaN;
                Submitted(williams.Signal > 0 ? EnterLong(wq, wname) : EnterShort(wq, wname), "breakout");
                wSent = true;
                owner = Breakout;
                return;
            }

            if (real != 0 && owner == Breakout && EvalTargetOn)  // the breakout's target: the nearer of its own and the evaluation's
            {
                double wt = EvalTargetPrice(real);
                double pxw = Close[0];
                if ((real > 0 && wt <= pxw) || (real < 0 && wt >= pxw))
                {
                    Flatten(real, "Evaluation target");
                    return;
                }
                if (!double.IsNaN(wTargetPts))
                {
                    double own = Position.AveragePrice + real * wTargetPts;
                    if ((real > 0 && own < wt) || (real < 0 && own > wt))
                        wt = own;
                }
                SetProfitTarget(real > 0 ? WLongName : WShortName, CalculationMode.Price, RoundTarget(real, wt));
                return;
            }
            if (real == 0 || owner != Bot)
                return;
            // in a trade: the stop and the take-profit for the next bar, measured from the real fill
            double avg = Position.AveragePrice;
            double lockPts = engine.LockPoints;
            if (!realLocked && !double.IsNaN(lockPts))
                realLocked = real * ((real > 0 ? High[0] : Low[0]) - avg) >= lockPts;
            double stop = RealStop(real, avg);
            if (double.IsNaN(stop))
                return;
            stop = RoundStop(real, stop);
            if (TightenOnly)  // never back toward the price: the tighter of this and the stop it already had
            {
                if (double.IsNaN(lastStop) && !double.IsNaN(entryStopPts))
                    lastStop = avg - real * entryStopPts;  // the bracket sent with the entry
                if (!double.IsNaN(lastStop) && ((real > 0 && lastStop > stop) || (real < 0 && lastStop < stop)))
                    stop = lastStop;
                lastStop = stop;
            }
            double px = Close[0];
            if (State == State.Realtime)
                px = real > 0 ? Math.Min(px, GetCurrentBid()) : Math.Max(px, GetCurrentAsk());
            string name2 = real > 0 ? LongName : ShortName;
            if ((real > 0 && stop >= px) || (real < 0 && stop <= px))
            {
                Flatten(real, "Stop passed");  // a stop can't rest there: the line moved past the price
                return;
            }
            SetStopLoss(name2, CalculationMode.Price, stop, false);
            if (halfName.Length > 0)  // the half's stop moves with the rest (kept for the next entry if it is closed)
                SetStopLoss(halfName, CalculationMode.Price, stop, false);
            double tp = TakeProfit > 0 && !double.IsNaN(engine.Sigma) ? avg * (1 + real * TakeProfit * engine.Sigma) : double.NaN;
            if (EvalTargetOn)
            {
                double et = EvalTargetPrice(real);
                if ((real > 0 && et <= px) || (real < 0 && et >= px))
                {
                    Flatten(real, "Evaluation target");
                    return;
                }
                if (double.IsNaN(tp) || (real > 0 && et < tp) || (real < 0 && et > tp))
                    tp = et;
                if (halfName.Length > 0)  // the half's take-profit: its own, or the evaluation's when nearer
                {
                    double hp = avg + real * halfPts;
                    if ((real > 0 && et < hp) || (real < 0 && et > hp))
                        hp = et;
                    SetProfitTarget(halfName, CalculationMode.Price, RoundTarget(real, hp));
                }
            }
            if (!double.IsNaN(tp))
                SetProfitTarget(name2, CalculationMode.Price, RoundTarget(real, tp));
        }

        // Points from the fill at which `qty` contracts take the evaluation to its target (NaN: off)
        double EvalPoints(int qty)
        {
            if (!EvalTargetOn || qty <= 0)
                return double.NaN;
            return Math.Max(TickSize, (EvalTarget + EvalBuffer - EvalClosed) / (qty * settings.PointValue));
        }

        // The closest of the line stop, the max loss from the real fill and the lock (as NoiseEngine.StopNow)
        double RealStop(int d, double avg)
        {
            if (double.IsNaN(engine.Upper))
                return double.NaN;
            double line = d > 0 ? engine.Upper * (1 - StopBuffer * engine.Sigma) : engine.Lower * (1 + StopBuffer * engine.Sigma);
            if (MaxLoss > 0)
            {
                double cap = avg - d * MaxLoss / Qty / settings.PointValue;
                if ((d > 0 && cap > line) || (d < 0 && cap < line)) line = cap;
            }
            if (realLocked)
            {
                double lk = avg + d * LockPlus;
                if ((d > 0 && lk > line) || (d < 0 && lk < line)) line = lk;
            }
            return line;
        }

        void Flatten(int real, string why)  // the whole position, whichever setup's it is
        {
            if (real > 0)
                ExitLong(why, "");
            else if (real < 0)
                ExitShort(why, "");
        }

        // Orders go in on the tick grid. A stop is rounded toward the price, so a loss never goes past the max loss; a
        // take-profit away from it, so it never takes less than the tested target.
        double RoundStop(int d, double price)
        {
            if (!RoundPrices) return price;
            double n = price / TickSize;
            return (d > 0 ? Math.Ceiling(n - 1e-7) : Math.Floor(n + 1e-7)) * TickSize;
        }

        double RoundTarget(int d, double price)
        {
            return RoundStop(d, price);  // away from the price: up for a long's take-profit, down for a short's
        }

        double StopTicks(double points)  // whole ticks, rounded down: never past the max loss
        {
            double n = points / TickSize;
            return Math.Max(1, RoundPrices ? Math.Floor(n + 1e-7) : n);
        }

        double TargetTicks(double points)  // whole ticks, rounded up: never short of the target
        {
            double n = points / TickSize;
            return Math.Max(1, RoundPrices ? Math.Ceiling(n - 1e-7) : n);
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time,
                                              ErrorCode error, string comment)
        {
            CountOrder(order, orderState, quantity, filled, averageFillPrice, error, comment);
            if (orderState != OrderState.Rejected)
                return;
            string msg = "ORDER REJECTED: " + order.Name + " (" + comment + ").";
            int real = RealDir;
            if (real != 0 && IsOwnExit(order.Name))
            {
                exitRejected = true;  // ManageOrders sends it again at the next bar
                Say("rejected", msg + " The exit is sent again at the next bar.");
                return;
            }
            if (real != 0 && !closingRejected && order.Name != "Flat 16:00" && order.Name != "Stop passed" &&
                order.Name != "Close: rejected")
            {
                msg += " The position is being closed at market so it is never left without a stop.";
                closingRejected = true;  // once per position: OnOrderUpdate can run inside the exit call itself
                Flatten(real, "Close: rejected");
            }
            else if (real != 0 && closingRejected)
                msg += " The position is already being closed at market.";
            else
                msg += " Check the position by hand.";
            Say("rejected", msg);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            Order o = execution == null ? null : execution.Order;
            if (o != null && IsEntry(o.Name))
            {
                dExecs++;
                dFilled.Add(o);
            }
            if (Diagnostics)
                Print("MNQ execution: " + (o == null ? "?" : o.Name) + " " + quantity + " @ " + P(price) + " " + marketPosition +
                      " " + time);
        }

        static bool IsEntry(string name)
        {
            return name == LongName || name == ShortName || name == WLongName || name == WShortName || name == LongHalf ||
                   name == ShortHalf;
        }

        static bool IsOwnExit(string name)
        {
            return name == "Close: rejected" || name == "Close: retry" || name == "Flat 16:00" || name == "Stop passed" ||
                   name == "Evaluation target" || name == "Payout-eligible" || name == "Breakout: bot first";
        }

        // ── Diagnostics: counting only (docs/NINJATRADER.md, "No trades")

        // A step a signal (or a bar) didn't get past, and why; the first three examples are kept (and, with Diagnostics
        // on, printed as they happen). Step: 0 error, 1 bar not used, 2 engine not ready, 4 signal not sent,
        // 6 entry not accepted, 7 entry not filled.
        void Block(int step, string why, string detail)
        {
            string key = step + "|" + why;
            Tally t;
            if (!blockedBy.TryGetValue(key, out t))
            {
                t = new Tally();
                t.Step = step;
                blockedBy[key] = t;
                blockedOrder.Add(key);
            }
            t.N++;
            if (t.Examples.Count < 3)
            {
                string ex = dNow + (detail.Length > 0 ? " " + detail : "");
                t.Examples.Add(ex);
                if (Diagnostics)
                    Print("MNQ blocked (step " + step + "): " + why + " - " + ex);
            }
        }

        static string EngineWhy(string note)
        {
            if (note == "skip date") return "today is on the skip list";
            if (note == "in a trade") return "the bot's model is already in a trade";
            if (note == "loser limit") return "the day's losing-trade limit (the bot's own)";
            if (note == "Fed day") return "Fed day: no shorts before 14:00";
            return note;
        }

        // the signals of this bar: the bot's half-hour check (a close past a line) and the breakout's level
        void CountSignals(int nOrders)
        {
            if (engine.Ready)
            {
                dReady++;
                if (dFirstReady.Length == 0)
                    dFirstReady = dNow;
            }
            string note = engine.CheckNote;
            if (note == "not ready")
                Block(2, "a half-hour check before the engine has " + Lookback + " full sessions",
                      "(" + engine.SessionsLoaded + "/" + Lookback + ")");
            else if (note.Length > 0)
            {
                dChecks++;
                if (note == "no cross")
                    dNoCross++;
                else
                {
                    dBotSignals++;
                    if (note != "signal")
                        Block(4, "bot: " + EngineWhy(note), "");
                }
            }
            if (!UseBreakout || williams.Note.Length == 0)
                return;
            dWSignals++;
            if (williams.Note == "both levels")
                Block(4, "breakout: both levels in one bar (no trade by rule)", "");
            else if (williams.Note == "stop too wide")
                Block(4, "breakout: stop too wide for the risk", "");
            else if (williams.Note == "shorts off")
                Block(4, "breakout: the short level first, breakout shorts off", "");
            else if (williams.Note == "not allowed")
                Block(4, "breakout: level reached while a trade isn't allowed",
                      "(" + (!engine.Ready ? "engine not ready" : engine.SkipToday ? "skip date" :
                       engine.Position != 0 ? "bot in a trade" : engine.PendingEntry != 0 ? "bot entry pending" :
                       engine.Orders.Count != nOrders ? "bot signal this bar" : "the account holds a position") + ")");
        }

        // whether this bar's signals were sent to the account
        void CountSent(int nOrders)
        {
            bool bot = engine.Orders.Count > nOrders, brk = UseBreakout && williams.Signal != 0;
            if (!bot && !brk)
                return;
            string why = !PlaceOrders ? "orders are off (alerts only)" :
                         notSent.Length > 0 ? notSent : "the strategy already holds a position", detail = "";
            if (why.StartsWith("its risk"))  // one reason, whatever the amounts
            {
                detail = "(" + why + ")";
                why = "daily gate: the trade's risk could take today past the loss limit";
            }
            else if (why.StartsWith("today's "))
            {
                detail = "(" + why + ")";
                why = "daily gate: the day's losing trades reach the limit";
            }
            if (bot && PlaceOrders && botSent) dPassed++;
            else if (bot) Block(4, "bot: " + why, detail);
            if (brk && PlaceOrders && wSent) dPassed++;
            else if (brk) Block(4, "breakout: " + why, detail);
        }

        void Submitted(Order o, string setup)
        {
            dSubmitted++;
            if (o == null)
                Block(6, "the entry call gave no order back (NinjaTrader ignored it: the TraceOrders line says why)", setup);
        }

        void CountOrder(Order order, OrderState state, int quantity, int filled, double avgFill, ErrorCode error,
                        string comment)
        {
            if (Diagnostics)
                Print("MNQ order: " + order.Name + " " + state + ", " + quantity + " MNQ, " + filled + " filled" +
                      (filled > 0 ? " @ " + P(avgFill) : "") + (error != ErrorCode.NoError ? ", error " + error : "") +
                      (string.IsNullOrEmpty(comment) ? "" : " (" + comment + ")"));
            if (error != ErrorCode.NoError)
                Block(0, "order error " + error, order.Name + (string.IsNullOrEmpty(comment) ? "" : " (" + comment + ")"));
            if (!IsEntry(order.Name))
                return;
            if (state == OrderState.Accepted || state == OrderState.Working || state == OrderState.Filled ||
                state == OrderState.PartFilled)
                dAccepted.Add(order);
            if (state == OrderState.Rejected)
            {
                dRejected++;
                Block(6, "entry rejected", order.Name + (string.IsNullOrEmpty(comment) ? "" : " (" + comment + ")"));
            }
            if (state == OrderState.Cancelled && !dFilled.Contains(order))
            {
                dCancelled++;
                Block(7, "entry cancelled before it filled", order.Name);
            }
        }

        void PrintSettings()
        {
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            Print("MNQ settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType + " bars (" +
                  Bars.Count + " loaded, trading hours " + Bars.TradingHours + "), Calculate " + Calculate +
                  (badChart ? " - THE CHART'S BARS DON'T WORK: not trading" : "") +
                  (Calculate != Calculate.OnBarClose ? " - NOT ON BAR CLOSE: not trading" : "") + ", platform time zone " +
                  platform.Id);
            Print("MNQ settings: account " + (Account == null ? "none" : Account.Name) + ", " + Book + " (from " +
                  accountTypeFrom + "), PlaceOrders " + PlaceOrders + ", " + Qty + " MNQ, max loss " + Usd(MaxLoss) +
                  ", losers " + MaxLosers + ", Lookback " + Lookback + ", DailyLossLimit " + DailyLossLimit +
                  ", DailyMaxLosers " + DailyMaxLosers + ", PartialAtR " + PartialAtR + ", TightenOnly " + TightenOnly +
                  ", UseBreakout " + UseBreakout + " (risk " + Usd(Funded ? BreakoutRisk : EvalBreakoutRisk) + ", shorts " +
                  BreakoutShorts + ")");
            Print("MNQ settings: history controls: EvalTarget " + EvalTarget + " in history " + EvalTargetInHistory +
                  ", PayoutStop " + PayoutStop + " in history " + PayoutStopInHistory + ", EvalFromAccount " + EvalFromAccount +
                  ", RememberPayoutCycle " + RememberPayoutCycle + ", StartBehavior " + StartBehavior +
                  ", exit on session close " + IsExitOnSessionCloseStrategy + " (" + ExitOnSessionCloseSeconds + " s)" +
                  ", BarsRequiredToTrade " + BarsRequiredToTrade + ", TraceOrders " + TraceOrders + ", Diagnostics " +
                  Diagnostics);
        }

        void PrintFunnel(string when)
        {
            Dictionary<string, bool> positions = new Dictionary<string, bool>();
            for (int k = 0; k < SystemPerformance.AllTrades.Count; k++)
            {
                Trade tr = SystemPerformance.AllTrades[k];
                positions[tr.Entry.Time.Ticks + "|" + tr.Entry.Name] = true;
            }
            int[] n = { dBars, dUsed, dReady, dBotSignals + dWSignals, dPassed, dSubmitted, dAccepted.Count, dFilled.Count,
                        positions.Count };
            string[] step = { "bars loaded", "bars used", "engine ready", "signals", "signals passing the gates",
                              "entry orders submitted", "entry orders accepted", "entry orders filled", "completed trades" };
            Print("MNQ funnel, " + when + ":");
            Print("  1 bars loaded: " + dBars + (dBars > 0 ? " (" + dFirst + " to " + dLast + " New York)" : "") +
                  "; used: " + dUsed);
            Print("  2 engine ready: " + dReady + " bars" + (dFirstReady.Length > 0 ? " (from " + dFirstReady + ")" : "") +
                  "; full sessions " + engine.SessionsLoaded + "/" + Lookback);
            Print("  3 signals: " + n[3] + " (bot " + dBotSignals + " of " + dChecks + " half-hour checks, " + dNoCross +
                  " with no close past a line; breakout " + dWSignals + ")");
            Print("  4 passing the gates: " + dPassed);
            Print("  5 entry orders submitted: " + dSubmitted);
            Print("  6 accepted: " + dAccepted.Count + " (rejected " + dRejected + ")");
            Print("  7 filled: " + dFilled.Count + " (" + dExecs + " executions; cancelled unfilled " + dCancelled + ")");
            Print("  8 completed trades: " + positions.Count + " (NinjaTrader trade records " + SystemPerformance.AllTrades.Count +
                  ")" + "; runtime errors " + dErrors);
            List<string> keys = new List<string>(blockedOrder);  // by step, then as they first happened
            keys.Sort(delegate (string a, string b)
            {
                int c = blockedBy[a].Step.CompareTo(blockedBy[b].Step);
                return c != 0 ? c : blockedOrder.IndexOf(a).CompareTo(blockedOrder.IndexOf(b));
            });
            foreach (string key in keys)
            {
                Tally t = blockedBy[key];
                Print("  blocked " + (t.Step == 0 ? "(error)" : "before step " + t.Step) + ": " + key.Substring(key.IndexOf('|') + 1) +
                      ": " + t.N + " (e.g. " + string.Join("; ", t.Examples) + ")");
            }
            int stop = -1;
            for (int k = 0; k < n.Length && stop < 0; k++)
                if (n[k] == 0)
                    stop = k;
            if (stop < 0)
                Print("  every step has entries");
            else
            {
                string why = "";
                foreach (string key in keys)
                    if (blockedBy[key].Step == stop || (blockedBy[key].Step == 0 && dErrors + dRejected > 0))
                        why += (why.Length > 0 ? "; " : "") + key.Substring(key.IndexOf('|') + 1) + " x" + blockedBy[key].N;
                if (stop == 3 && why.Length == 0 && dChecks > 0)
                    why = "no close past a line at any of the " + dChecks + " half-hour checks";
                Print("  FUNNEL STOPS AT step " + (stop == 0 ? 1 : stop) + ", " + step[stop] + ": 0" +
                      (why.Length > 0 ? ". Recorded there: " + why : ". Nothing recorded there: see the Log tab and the lines above"));
            }
        }

        // ── Alerts and dashboard

        // what happened to an entry signal with orders on: sent to the account (the fill shows in the Orders and
        // Executions tabs), or not sent and why
        string Sent(bool sent)
        {
            if (sent)
                return ". The strategy sent the order.";
            return ". NOT sent by the strategy: " + (notSent.Length > 0 ? notSent : "it already holds a position") + ".";
        }
        void Tell(int nTrades, int nOrders, int nHeads)
        {
            for (int k = nOrders; k < engine.Orders.Count; k++)
            {
                NoiseOrder o = engine.Orders[k];
                string side = o.Direction > 0 ? "BUY" : "SELL";
                lastSignal = side + " " + NoiseEngine.Hhmm(engine.BarTime.Hour * 60 + engine.BarTime.Minute + minutes) + " @ " + P(Close[0]);
                string be = double.IsNaN(engine.LockPoints) ? "" :
                    ", breakeven: at " + P(o.Expected + o.Direction * engine.LockPoints) + " the stop moves to " +
                    P(o.Expected + o.Direction * LockPlus);
                if (!PlaceOrders && (evalDone || payoutToday))
                    continue;  // the evaluation is passed, or today is a payout day: no new trades
                string first = "";
                if (!PlaceOrders && wDir != 0)
                {
                    first = "First CLOSE the breakout " + (wDir > 0 ? "long" : "short") + " at market (the bot comes first). ";
                    wDir = 0;
                    wPending = false;
                }
                Say("entry", first + side + " " + BotQty + " MNQ (" + Book + ") at market. Price " + P(Close[0]) + ". Stop " +
                    P(RoundStop(o.Direction, o.Stop)) + (double.IsNaN(o.Target) ? "" : ", take-profit " +
                    P(RoundTarget(o.Direction, o.Target))) + be +
                    (PlaceOrders ? Sent(botSent) : ". Place it now (orders are off) with that stop and take-profit."));
                saidStop = RoundStop(o.Direction, o.Stop);
                saidTarget = double.IsNaN(o.Target) ? double.NaN : RoundTarget(o.Direction, o.Target);
            }
            for (int k = nTrades; k < engine.Trades.Count; k++)
            {
                NoiseTrade t = engine.Trades[k];
                string side = t.Direction > 0 ? "long" : "short";
                lastSignal = t.Reason + " @ " + P(t.Exit);
                if (t.Reason == "16:00 close" || t.Reason == "Session ended")
                    Say("flat", "FLAT: the " + side + " is closed at market (" + t.Reason + ")." + (PlaceOrders ? "" : " Close it now."));
                else
                    Say("exit", (t.Reason == "Target" ? "TARGET: " : "EXIT: ") + "the " + side + " closed at " + P(t.Exit) +
                        " (" + Why(t.Reason) + "), " + Usd(t.Pnl) + ".");
            }
            if (!PlaceOrders)
                TellManual();
            if (UseBreakout && williams.Signal != 0 && !payoutToday && !(PlaceOrders ? evalDone : evalDone || wDir != 0))
            {
                int d = williams.Signal;
                string side = d > 0 ? "BUY" : "SELL";
                double fill = Close[0] + d * TickSize;  // the expected fill: the next bar's open, a tick of slippage
                double st = RoundStop(d, fill - d * williams.StopPoints);
                double tp = BreakoutTarget > 0 ? RoundTarget(d, fill + d * BreakoutTarget * williams.StopPoints) : double.NaN;
                lastSignal = "Breakout " + side + " " + NoiseEngine.Hhmm(engine.BarTime.Hour * 60 + engine.BarTime.Minute + minutes) +
                             " @ " + P(Close[0]);
                Say("breakout", "BREAKOUT " + side + " " + BreakoutQty + " MNQ (" + Book + ") at market. Price " + P(Close[0]) +
                    " is past " + P(d > 0 ? williams.Up : williams.Down) + ". Stop " + P(st) + " (" + P(williams.StopPoints) +
                    " points from the fill)" + (double.IsNaN(tp) ? "" : ", take-profit " + P(tp)) + ", out at 16:00" +
                    (PlaceOrders ? Sent(wSent) :
                     ". Place it now (orders are off) with that stop and take-profit; close it if the bot signals."));
                if (!PlaceOrders)
                {
                    wDir = d;
                    wQty = BreakoutQty;
                    wStop = st;
                    wTarget = tp;
                    wPending = true;
                }
            }
            int endMin = engine.BarTime.Hour * 60 + engine.BarTime.Minute + minutes;
            if (endMin >= NoiseEngine.FirstCheck && (endMin - NoiseEngine.FirstCheck) % NoiseEngine.Step == 0)
                headsUp = "";  // the check it announced has happened
            for (int k = nHeads; k < engine.HeadsUps.Count; k++)
            {
                NoiseHeadsUp h = engine.HeadsUps[k];
                headsUp = NoiseEngine.Hhmm(h.CheckMinute) + (h.Direction > 0 ? " BUY likely" : " SELL likely");
                Say("headsup", "HEADS-UP: " + headsUp + ". Price " + P(Close[0]) + " is already " + (h.Direction > 0 ? "above" : "below") +
                    " the " + NoiseEngine.Hhmm(h.CheckMinute) + " line (" + P(h.Line) + ").");
            }

            bool rth = endMin > NoiseEngine.RthOpen && endMin <= NoiseEngine.RthClose && !double.IsNaN(engine.Upper);
            if (rth)
            {
                Values[0][0] = engine.Upper;
                Values[1][0] = engine.Lower;
            }
            int real = PlaceOrders ? (owner == Bot ? RealDir : 0) : engine.Position;
            double avg = PlaceOrders ? Position.AveragePrice : engine.EntryPrice;
            if (real != 0 && rth)
            {
                double st = PlaceOrders ? RealStop(real, avg) : engine.StopNow(out stopWhy);
                if (!double.IsNaN(st)) Values[2][0] = st;
                if (TakeProfit > 0) Values[3][0] = avg * (1 + real * TakeProfit * engine.Sigma);
            }
        }

        string stopWhy;

        // Alerts-only mode, the evaluation's target: the price at which `qty` contracts held in direction d take the account
        // (its net liquidation, open P/L included) to the target + $25 (NaN: off)
        double ManualEvalPrice(int d, int qty)
        {
            if (!EvalTargetOn || evalDone || qty <= 0)
                return double.NaN;
            double profit = Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) - AccountStart;
            return Close[0] + d * (EvalTarget + EvalBuffer - profit) / (qty * settings.PointValue);
        }

        static double Nearer(int d, double a, double b)  // the take-profit nearer the price (NaN: the other one)
        {
            if (double.IsNaN(a)) return b;
            if (double.IsNaN(b)) return a;
            return d > 0 ? Math.Min(a, b) : Math.Max(a, b);
        }

        // Alerts-only mode: tell the user each change the tested strategy would make to what they hold
        void TellManual()
        {
            int endMin = engine.BarTime.Hour * 60 + engine.BarTime.Minute + minutes;
            // the bot's stop and take-profit, as the tested strategy moves them (the line at the checks, the lock)
            if (engine.Position != 0)
            {
                int d = engine.Position;
                string why;
                double st = engine.StopNow(out why);
                if (!double.IsNaN(st))
                {
                    st = RoundStop(d, st);
                    if (double.IsNaN(saidStop) || Math.Abs(st - saidStop) >= TickSize / 2)
                    {
                        Say("move", "MOVE STOP: the " + (d > 0 ? "long" : "short") + "'s stop to " + P(st) + " (" + Why(why) + ").");
                        saidStop = st;
                    }
                }
                double tp = Nearer(d, engine.TargetNow(), ManualEvalPrice(d, BotQty));
                if (!double.IsNaN(tp))
                {
                    tp = RoundTarget(d, tp);
                    if (double.IsNaN(saidTarget) || Math.Abs(tp - saidTarget) >= TickSize / 2)
                    {
                        Say("move", "MOVE TAKE-PROFIT: the " + (d > 0 ? "long" : "short") + "'s take-profit to " + P(tp) + ".");
                        saidTarget = tp;
                    }
                }
            }
            else if (engine.PendingEntry == 0)
                saidStop = saidTarget = double.NaN;

            // the breakout trade the user was told to take: its stop, its take-profit, 16:00
            if (wDir != 0 && !wPending)
            {
                double near = Nearer(wDir, wTarget, ManualEvalPrice(wDir, wQty));
                if (!double.IsNaN(near) && (double.IsNaN(wTarget) || Math.Abs(near - wTarget) >= TickSize / 2))
                {
                    near = RoundTarget(wDir, near);
                    Say("move", "MOVE TAKE-PROFIT: the breakout " + (wDir > 0 ? "long" : "short") + "'s take-profit to " +
                        P(near) + " (it takes the evaluation to its target).");
                    wTarget = near;
                }
            }
            if (wDir != 0)
            {
                if (wPending)
                    wPending = false;  // it filled at this bar's open
                else if ((wDir > 0 && Low[0] <= wStop) || (wDir < 0 && High[0] >= wStop))
                {
                    Say("bexit", "BREAKOUT EXIT: the breakout " + (wDir > 0 ? "long" : "short") + "'s stop " + P(wStop) +
                        " was reached. If it didn't fill, close it now.");
                    wDir = 0;
                }
                else if (!double.IsNaN(wTarget) && ((wDir > 0 && High[0] >= wTarget + TickSize) ||
                                                   (wDir < 0 && Low[0] <= wTarget - TickSize)))
                {
                    Say("bexit", "BREAKOUT TARGET: the breakout " + (wDir > 0 ? "long" : "short") + "'s take-profit " +
                        P(wTarget) + " was reached.");
                    wDir = 0;
                }
                if (wDir != 0 && endMin >= NoiseEngine.RthClose)
                {
                    Say("flat", "FLAT: close the breakout " + (wDir > 0 ? "long" : "short") + " at market (16:00 close).");
                    wDir = 0;
                }
            }

            // the evaluation's target, from the account itself (live): close everything, no new trades
            if (EvalTargetOn && !evalDone)
            {
                double profit = Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) - AccountStart;
                if (profit >= EvalTarget)
                {
                    evalDone = true;
                    wDir = 0;
                    Say("evaltarget", "EVALUATION TARGET REACHED: the account is " + Usd(profit) + " up. CLOSE EVERYTHING NOW " +
                        "at market and take no more trades: the evaluation is passed.");
                }
            }
        }

        string Dashboard()
        {
            string s = "MNQ Noise Momentum v1.6: " + Book + ", " + Qty + " MNQ, " + Usd(MaxLoss) + " max loss, " + MaxLosers +
                       " losers a day\n";
            s += "Account: " + Book + " (from " + accountTypeFrom + ")\n";
            if (PlaceOrders && engine.BarTime != DateTime.MinValue)
            {
                int ln, ll;
                double lr;
                TodayLedger(engine.BarTime, out ln, out ll, out lr);
                s += "Today (" + (LiveBook ? "live fills" : "simulated fills") + ", both setups): " + ln + " trades, " + Usd(lr) + ", " + ll + " losers" +
                     (DailyMaxLosers > 0 || DailyLossLimit > 0 ? " - daily gate: " + (DailyMaxLosers > 0 ? DailyMaxLosers + " losers" : "") +
                      (DailyMaxLosers > 0 && DailyLossLimit > 0 ? ", " : "") + (DailyLossLimit > 0 ? Usd(DailyLossLimit) : "") : "") + "\n";
            }
            s += "Orders: " + (PlaceOrders ? "ON (the strategy trades this account)" : "OFF (alerts only)") + "\n";
            if (PlaceOrders && mismatchBars >= 2)
                s += "ACCOUNT POSITION MISMATCH: the account holds " + Signed(PositionAccount) + " MNQ, the strategy " +
                     Signed(Position) + " - no new entries until they agree\n";
            if (minutes != 1)
                s += "Use a 1-minute chart: the lock arms within the minute (about 6 points more winning trades).\n";
            if (!engine.Ready)
                s += "History: " + engine.SessionsLoaded + "/" + Lookback + " full sessions. No trades yet: set Days to load to 30+.\n";
            if (!double.IsNaN(engine.Upper))
                s += "Upper / lower now: " + P(engine.Upper) + " / " + P(engine.Lower) + "\n";
            int nm;
            double nu, nl;
            if (engine.NextCheckLines(out nm, out nu, out nl))
                s += "Next check " + NoiseEngine.Hhmm(nm) + ": " + P(nu) + " / " + P(nl) + (headsUp == "" ? "" : "   " + headsUp) + "\n";
            if (engine.SkipToday) s += "Today is on the skip list: no new trades.\n";
            if (engine.FedToday) s += "Fed day: no shorts before 14:00.\n";
            if (!Funded && EvalTarget > 0)
                s += "Evaluation: " + Usd(EvalShown) + " of " + Usd(EvalTarget) + (evalDone ? " - TARGET REACHED, no new trades" :
                     EvalTargetOn ? " (everything closes at the target)" : " (target close works live)") + "\n";
            if (Funded && PayoutStop)
                s += "Payout cycle: " + cycleQual + "/5 days of $200, " + Usd(cycleProfit) + " since the last payout, best day " +
                     Usd(cycleBest) + ", payouts taken " + payoutsTaken + (payoutToday ? " - PAYOUT DAY: request it after the close" :
                     PayoutStopOn ? "" : " (works live)") + (pendingPayout > 0 ? ", " + Usd(pendingPayout) +
                     " asked for, not yet out of the account" : "") + (cycleFromFile ? " (remembered)" : "") + "\n";
            if (!Funded && BoldFromDay > 0)
                s += "Bold finish: " + (evalStart == DateTime.MinValue ? "set the evaluation's start date" :
                     "from " + evalStart.AddDays(BoldFromDay).ToString("yyyy-MM-dd") + ", " + BoldSize.ToString("0.#") + "x size" +
                     (boldMult > 1 ? " - ON TODAY (" + BotQty + " MNQ)" : "")) + "\n";
            if (UseBreakout)
                s += "Breakout: " + (double.IsNaN(williams.Up) ? "" : P(williams.Up) + " / " + P(williams.Down) + ", ") +
                     williams.Status + "\n";
            int real = RealDir;
            if (PlaceOrders && real != 0)
            {
                double st = RealStop(real, Position.AveragePrice);
                if (owner == Breakout)
                    s += "Position: breakout " + (real > 0 ? "LONG " : "SHORT ") + Position.Quantity + " @ " +
                         P(Position.AveragePrice) + ", out at 16:00\n";
                else
                    s += "Position: " + (real > 0 ? "LONG " : "SHORT ") + Position.Quantity + " @ " + P(Position.AveragePrice) +
                         (double.IsNaN(st) ? "" : ", stop " + P(RoundStop(real, st))) + (realLocked ? " (locked)" : "") + "\n";
            }
            else if (!PlaceOrders && engine.Position != 0)
                s += "Bot position: " + (engine.Position > 0 ? "LONG" : "SHORT") + " @ " + P(engine.EntryPrice) + "\n";
            else
                s += "Position: flat\n";
            s += "Bot today" + (PlaceOrders ? "" : " (model)") + ": " + engine.DayTrades + " trades, " + Usd(engine.DayPnl) +
                 ", losers " + engine.LosersCounted + "/" + MaxLosers + (PlaceOrders ? " (from fills)" : "") +
                 (engine.FreshOk ? "" : " (limit reached: no new entries today)") + "\n";
            s += "Last: " + lastSignal;
            return s;
        }

        void Say(string id, string msg)
        {
            Print(Time[0] + "  " + msg);
            if (State == State.Realtime)
                Alert("mnq_" + id, Priority.High, msg, SoundAlerts ? NinjaTrader.Core.Globals.InstallDir + @"\sounds\Alert1.wav" : "",
                      0, Brushes.Black, Brushes.White);
        }

        static string Why(string reason)
        {
            if (reason == "Max loss") return "max loss stop";
            if (reason == "Lock") return "locked win";
            if (reason == "Back inside") return "stop at the line";
            return reason.ToLower();
        }

        static string P(double x) { return x.ToString("0.00"); }

        static string Usd(double x) { return (x < 0 ? "-$" : "$") + Math.Abs(x).ToString("0"); }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "FUNDED ACCOUNT (on: 4 MNQ, $200, 2 losers; off: the 50K evaluation, 4 MNQ, $200, 3 losers)", Order = 1, GroupName = "1. Account")]
        public bool Funded { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Evaluation or funded from the account's name (APEX-... / PA-APEX-...); other names: the setting above", Order = 0, GroupName = "1. Account")]
        public bool AutoAccountType { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts in an evaluation", Order = 2, GroupName = "1. Account")]
        public int EvalQty { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts on a funded account", Order = 3, GroupName = "1. Account")]
        public int FundedQty { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Evaluation: max loss per trade, $ (0 = off)", Order = 4, GroupName = "1. Account")]
        public double EvalMaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Funded: max loss per trade, $ (0 = off)", Order = 5, GroupName = "1. Account")]
        public double FundedMaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Evaluation: no new entries after this many losers today (0 = no limit)", Order = 6, GroupName = "1. Account")]
        public int EvalMaxLosers { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Funded: no new entries after this many losers today (0 = no limit)", Order = 7, GroupName = "1. Account")]
        public int FundedMaxLosers { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders (off: alerts only, you click)", Order = 8, GroupName = "1. Account")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "Take-profit, noise units (0 = off)", Order = 2, GroupName = "2. Exits")]
        public double TakeProfit { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Line stop, noise units past the line", Order = 3, GroupName = "2. Exits")]
        public double StopBuffer { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "Evaluation: lock at, max losses of profit (0 = off)", Order = 4, GroupName = "2. Exits")]
        public double EvalLockAt { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Evaluation: lock moves the stop to entry + points", Order = 5, GroupName = "2. Exits")]
        public double EvalLockPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "Funded: lock at, max losses of profit (0 = off)", Order = 6, GroupName = "2. Exits")]
        public double FundedLockAt { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Funded: lock moves the stop to entry + points", Order = 7, GroupName = "2. Exits")]
        public double FundedLockPlus { get; set; }

        [NinjaScriptProperty]
        [Range(2, 60)]
        [Display(Name = "Noise lookback, sessions", Order = 2, GroupName = "3. Entries")]
        public int Lookback { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed days: no shorts before 14:00", Order = 3, GroupName = "3. Entries")]
        public bool FedNoShorts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Skip dates (yyyy-MM-dd,...)", Order = 4, GroupName = "3. Entries")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed dates (yyyy-MM-dd,...)", Order = 5, GroupName = "3. Entries")]
        public string FedDates { get; set; }

        [Display(Name = "Sound alerts", Order = 1, GroupName = "4. Alerts")]
        public bool SoundAlerts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Breakout in the bot's gaps (docs/RESULTS.md round 101)", Order = 1, GroupName = "5. Breakout")]
        public bool UseBreakout { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 5.0)]
        [Display(Name = "Levels: today's open +/- this x yesterday's range", Order = 2, GroupName = "5. Breakout")]
        public double BreakoutK { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 5.0)]
        [Display(Name = "Stop: this x yesterday's range from the fill", Order = 3, GroupName = "5. Breakout")]
        public double BreakoutStop { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 100000.0)]
        [Display(Name = "Risk a trade on the funded account, $ (sets the contracts)", Order = 4, GroupName = "5. Breakout")]
        public double BreakoutRisk { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 100000.0)]
        [Display(Name = "Risk a trade in the evaluation, $ (sets the contracts; round 134)", Order = 4, GroupName = "5. Breakout")]
        public double EvalBreakoutRisk { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Most contracts", Order = 5, GroupName = "5. Breakout")]
        public int BreakoutMaxQty { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Breakout shorts (off: a day whose short level is reached first has no breakout trade)", Order = 7, GroupName = "5. Breakout")]
        public bool BreakoutShorts { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Evaluation: close everything at this profit, $ (0 = off)", Order = 9, GroupName = "1. Account")]
        public double EvalTarget { get; set; }

        [NinjaScriptProperty]
        [Range(-100000.0, 100000.0)]
        [Display(Name = "Evaluation: profit already made before this start, $ (only with the next setting off)", Order = 10, GroupName = "1. Account")]
        public double EvalProfitSoFar { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Evaluation: read its profit from the account (balance - starting balance; survives restarts)", Order = 11, GroupName = "1. Account")]
        public bool EvalFromAccount { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Evaluation: the day it was bought (yyyy-MM-dd), for the bold finish", Order = 11, GroupName = "1. Account")]
        public string EvalStartDate { get; set; }

        [NinjaScriptProperty]
        [Range(0, 30)]
        [Display(Name = "Evaluation: bold finish from this day of the 30 (0 = off; 20 tested)", Order = 12, GroupName = "1. Account")]
        public int BoldFromDay { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name = "Evaluation: bold finish size, x (2.5: the bot at 10 MNQ)", Order = 13, GroupName = "1. Account")]
        public double BoldSize { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Funded: stop for the day once closing makes it payout-eligible (rounds 128, 132)", Order = 15, GroupName = "1. Account")]
        public bool PayoutStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 6)]
        [Display(Name = "Funded: payouts taken so far", Order = 16, GroupName = "1. Account")]
        public int FundedPayoutsTaken { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Funded: $200 days since the last payout", Order = 17, GroupName = "1. Account")]
        public int FundedQualDays { get; set; }

        [NinjaScriptProperty]
        [Range(-100000.0, 100000.0)]
        [Display(Name = "Funded: profit since the last payout, $", Order = 18, GroupName = "1. Account")]
        public double FundedCycleProfit { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Funded: best day since the last payout, $", Order = 19, GroupName = "1. Account")]
        public double FundedBestDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Stop only ever tightens (never moves back toward the price; round 139)", Order = 21, GroupName = "1. Account")]
        public bool TightenOnly { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "Bot: close half at this many R from the fill (R = the initial risk; 0 = off)", Order = 24, GroupName = "1. Account")]
        public double PartialAtR { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Daily gate, both setups: no entry after this many losing trades today (0 = off)", Order = 22, GroupName = "1. Account")]
        public int DailyMaxLosers { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100000.0)]
        [Display(Name = "Daily gate, both setups: no entry whose risk could take today's loss past this, $ (0 = off)", Order = 23, GroupName = "1. Account")]
        public double DailyLossLimit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Funded: remember the payout cycle in a file (a restart goes on from it; new settings above replace it)", Order = 20, GroupName = "1. Account")]
        public bool RememberPayoutCycle { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Diagnostics: NinjaTrader's order trace and a line for each order, fill and blocked signal (no trading change)", Order = 1, GroupName = "6. Diagnostics")]
        public bool Diagnostics { get; set; }

        [Browsable(false)]  // the tests turn it on: the payout stop in a historical run
        public bool PayoutStopInHistory { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 50.0)]
        [Display(Name = "Breakout: take-profit, x its stop distance (0 = none)", Order = 6, GroupName = "5. Breakout")]
        public double BreakoutTarget { get; set; }

        [NinjaScriptProperty]
        [Range(1000.0, 1000000.0)]
        [Display(Name = "Evaluation: account's starting balance, $ (alerts-only mode reads the account against it)", Order = 14, GroupName = "1. Account")]
        public double AccountStart { get; set; }

        [Browsable(false)]  // the tests turn it on: the evaluation's target in a historical run
        public bool EvalTargetInHistory { get; set; }

        [Browsable(false)]  // the tests turn it off to compare prices with the Python bot exactly
        public bool RoundPrices { get; set; }
        #endregion
    }
}
