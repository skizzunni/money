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
// Setup: 5-minute MNQ chart, Days to load 30 or more (the noise needs 14 full sessions), Calculate on bar close.
// See docs/NINJATRADER.md. Written in C# 5 for NinjaTrader 8's compiler.
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
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
        const string LongName = "Long", ShortName = "Short";
        NoiseEngine engine;
        NoiseSettings settings;
        TimeZoneInfo newYork;
        int minutes;
        bool badChart;
        bool realLocked;            // the real position reached the lock trigger
        bool closingRejected;       // a rejection already sent the position to market
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
                EntryHandling = EntryHandling.AllEntries;
                StopTargetHandling = StopTargetHandling.ByStrategyPosition;  // one stop and one target for the position
                IsExitOnSessionCloseStrategy = false;  // the strategy closes at 16:00 New York itself
                BarsRequiredToTrade = 0;               // the engine waits for its own 14 sessions
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.IgnoreAllErrors;  // OnOrderUpdate flattens on a rejected stop
                TraceOrders = false;
                IsInstantiatedOnEachOptimizationIteration = true;

                Funded = false;
                EvalQty = 4;           // Apex 50K evaluation, intraday trail (docs/RESULTS.md round 60)
                FundedQty = 10;
                PlaceOrders = true;
                EvalMaxLoss = 200;     // end-of-day plan instead: 6 MNQ, $300, 3 losers
                FundedMaxLoss = 350;
                TakeProfit = 1.5;
                StopBuffer = 0.24;
                LockAt = 1.0;
                LockPlus = 2.5;
                EvalMaxLosers = 3;
                FundedMaxLosers = 4;
                Lookback = 14;
                FedNoShorts = true;
                SkipDates = NoiseEngine.SkipDatesDefault;
                FedDates = NoiseEngine.FedDatesDefault;
                SoundAlerts = true;
                RoundPrices = true;

                AddPlot(Brushes.Teal, "Upper noise line");
                AddPlot(Brushes.Maroon, "Lower noise line");
                AddPlot(Brushes.Orange, "Stop");
                AddPlot(Brushes.LimeGreen, "Take-profit");
            }
            else if (State == State.DataLoaded)
            {
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
                settings.Lookback = Lookback;
                settings.FedNoShorts = FedNoShorts;
                settings.SkipDates = SkipDates ?? "";
                settings.FedDates = FedDates ?? "";
                engine = new NoiseEngine(settings, minutes);
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }  // Windows
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        int Qty { get { return Funded ? FundedQty : EvalQty; } }
        double MaxLoss { get { return Funded ? FundedMaxLoss : EvalMaxLoss; } }
        int MaxLosers { get { return Funded ? FundedMaxLosers : EvalMaxLosers; } }
        string Account { get { return Funded ? "Funded" : "Evaluation"; } }

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
            if (badChart || Calculate != Calculate.OnBarClose)
            {
                Draw.TextFixed(this, "mnq_dash", badChart ?
                    "MNQ Noise Momentum: use a 1, 5, 10, 15 or 30 minute chart (5 is the tested one). Not trading." :
                    "MNQ Noise Momentum: set Calculate to 'On bar close' in the strategy settings. Not trading.",
                    TextPosition.TopRight);
                return;
            }
            // NinjaTrader stamps a bar with its end time in the time zone set under Tools > Options > General
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            DateTime end = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified), platform, newYork);
            DateTime start = end.AddMinutes(-minutes);
            int nTrades = engine.Trades.Count, nOrders = engine.Orders.Count;
            int nHeads = engine.HeadsUps.Count;
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);

            if (PlaceOrders)
                ManageOrders(start, nOrders);
            Tell(nTrades, nOrders, nHeads);
            Draw.TextFixed(this, "mnq_dash", Dashboard(), TextPosition.TopRight);
        }

        // ── Orders on the account
        void ManageOrders(DateTime start, int nOrders)
        {
            int real = RealDir;
            if (real == 0)
            {
                realLocked = false;
                closingRejected = false;
            }

            // 16:00 New York, or a bar outside 09:30-16:00 (a session that ended early): any position is closed at
            // market, whatever the engine's own position is
            int tMin = start.Hour * 60 + start.Minute, endMin = tMin + minutes;
            bool inRth = tMin >= NoiseEngine.RthOpen && endMin <= NoiseEngine.RthClose;
            if (real != 0 && (endMin == NoiseEngine.RthClose || !inRth || tMin == NoiseEngine.RthOpen))
            {
                Flatten(real, "Flat 16:00");
                return;
            }

            // a new entry: the bracket goes in first, so it is attached the moment the entry fills. It is set in ticks
            // from the fill, as a broker's bracket is, so a fill away from the expected price (a fast market) still
            // gets its stop and take-profit on the right side, the same distances away.
            if (engine.Orders.Count > nOrders && real == 0)
            {
                NoiseOrder o = engine.Orders[engine.Orders.Count - 1];
                string name = o.Direction > 0 ? LongName : ShortName;
                SetStopLoss(name, CalculationMode.Ticks, StopTicks(o.Direction * (o.Expected - o.Stop)), false);
                if (!double.IsNaN(o.Target))
                    SetProfitTarget(name, CalculationMode.Ticks, TargetTicks(o.Direction * (o.Target - o.Expected)));
                if (o.Direction > 0)
                    EnterLong(Qty, LongName);
                else
                    EnterShort(Qty, ShortName);
                return;
            }

            if (real == 0)
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
            if (TakeProfit > 0 && !double.IsNaN(engine.Sigma))
                SetProfitTarget(name2, CalculationMode.Price, RoundTarget(real, avg * (1 + real * TakeProfit * engine.Sigma)));
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

        void Flatten(int real, string why)
        {
            if (real > 0)
                ExitLong(why, LongName);
            else if (real < 0)
                ExitShort(why, ShortName);
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
            return RoundStop(-d, price);
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
            if (orderState != OrderState.Rejected)
                return;
            string msg = "ORDER REJECTED: " + order.Name + " (" + comment + ").";
            int real = RealDir;
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

        // ── Alerts and dashboard
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
                Say("entry", side + " " + Qty + " MNQ (" + Account + ") at market. Price " + P(Close[0]) + ". Stop " + P(o.Stop) +
                    (double.IsNaN(o.Target) ? "" : ", take-profit " + P(o.Target)) + be +
                    (PlaceOrders ? ". The strategy placed it." : ". Place it now (orders are off)."));
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
            int real = PlaceOrders ? RealDir : engine.Position;
            double avg = PlaceOrders ? Position.AveragePrice : engine.EntryPrice;
            if (real != 0 && rth)
            {
                double st = PlaceOrders ? RealStop(real, avg) : engine.StopNow(out stopWhy);
                if (!double.IsNaN(st)) Values[2][0] = st;
                if (TakeProfit > 0) Values[3][0] = avg * (1 + real * TakeProfit * engine.Sigma);
            }
        }

        string stopWhy;

        string Dashboard()
        {
            string s = "MNQ Noise Momentum v1.6: " + Account + ", " + Qty + " MNQ, " + Usd(MaxLoss) + " max loss, " + MaxLosers +
                       " losers a day\n";
            s += "Orders: " + (PlaceOrders ? "ON (the strategy trades this account)" : "OFF (alerts only)") + "\n";
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
            int real = RealDir;
            if (PlaceOrders && real != 0)
            {
                double st = RealStop(real, Position.AveragePrice);
                s += "Position: " + (real > 0 ? "LONG " : "SHORT ") + Position.Quantity + " @ " + P(Position.AveragePrice) +
                     (double.IsNaN(st) ? "" : ", stop " + P(RoundStop(real, st))) + (realLocked ? " (locked)" : "") + "\n";
            }
            else if (!PlaceOrders && engine.Position != 0)
                s += "Bot position: " + (engine.Position > 0 ? "LONG" : "SHORT") + " @ " + P(engine.EntryPrice) + "\n";
            else
                s += "Position: flat\n";
            s += "Today: " + engine.DayTrades + " trades, " + Usd(engine.DayPnl) + ", losers " + engine.LosersToday + "/" + MaxLosers +
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
        [Display(Name = "FUNDED ACCOUNT (on: 10 MNQ, $350; off: the 50K evaluation, 4 MNQ, $200)", Order = 1, GroupName = "1. Account")]
        public bool Funded { get; set; }

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
        [Display(Name = "Lock at, max losses of profit (0 = off)", Order = 4, GroupName = "2. Exits")]
        public double LockAt { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Lock: stop to entry + points", Order = 5, GroupName = "2. Exits")]
        public double LockPlus { get; set; }

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

        [Browsable(false)]  // the tests turn it off to compare prices with the Python bot exactly
        public bool RoundPrices { get; set; }
        #endregion
    }
}
