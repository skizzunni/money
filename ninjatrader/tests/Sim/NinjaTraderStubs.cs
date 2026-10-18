// A stand-in for the parts of NinjaTrader 8's API that Strategies/MnqNoiseMomentum.cs uses, with a simple fill model,
// so the strategy can be compiled and run outside NinjaTrader. The names and signatures follow NinjaTrader's
// documentation; this is not NinjaTrader and proves nothing about it beyond "the strategy's own logic is right".
//
// Fill model (the one mnqbot/noise.py uses): market orders sent at a bar's close fill at the next bar's open plus a
// tick of slippage. The stop and take-profit set before an entry are attached when it fills and work from the fill
// bar (a bracket set in ticks is measured from the fill price): the stop fills at the stop or the open, whichever is worse, minus a tick; from the next bar it fills at the
// open minus a tick when the open is past it, else at the stop minus a tick. The take-profit fills at its price once
// price trades a tick through it, unless the stop filled on that bar. One position at a time: an entry while in a
// position is allowed only with an exit for it sent on the same bar (both fill at the next open, the exit first) or
// in the other direction (a reversal: the position is closed at the next open, "Close position", then the entry).
using System;
using System.Collections.Generic;

namespace System.Windows.Media
{
    public class Brush { }
    public static class Brushes
    {
        public static readonly Brush Teal = new Brush(), Maroon = new Brush(), Orange = new Brush(),
            LimeGreen = new Brush(), Black = new Brush(), White = new Brush();
    }
}

namespace NinjaTrader.Core
{
    public class GeneralOptions { public TimeZoneInfo TimeZoneInfo; }
    public static class Globals
    {
        public static string InstallDir = @"C:\Program Files\NinjaTrader 8";
        // Documents\NinjaTrader 8; here a fresh folder for each run, unless the test gives one (SimUserDataDir)
        public static string UserDataDir = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "nt8-" + Guid.NewGuid().ToString("N"));
        public static GeneralOptions GeneralOptions = new GeneralOptions();
    }
}

namespace NinjaTrader.Cbi
{
    public enum MarketPosition { Flat, Long, Short }
    public enum PerformanceUnit { Currency, Percent, Pips, Points, Ticks }
    public enum AccountItem { CashValue, NetLiquidation, RealizedProfitLoss, UnrealizedProfitLoss }
    public enum Currency { UsDollar }
    // the account the strategy runs on: its net liquidation is $50,000 + the strategy's P/L, or SimNetLiq when set, or
    // SimLiqFile's; its realized / unrealized P/L are the trading day's (from 18:00 New York)
    public class Account
    {
        public string Name = "Sim101";
        internal Func<double> Value, Realized, Unrealized;
        public double Get(AccountItem item, Currency currency)
        {
            if (item == AccountItem.NetLiquidation) return Value();
            if (item == AccountItem.RealizedProfitLoss) return Realized();
            if (item == AccountItem.UnrealizedProfitLoss) return Unrealized();
            throw new NotSupportedException();
        }
    }
    public enum OrderState { Initialized, Submitted, Accepted, Working, Filled, Cancelled, Rejected }
    public enum ErrorCode { NoError, OrderRejected }
    public class Position
    {
        public MarketPosition MarketPosition;
        public double AveragePrice;
        public int Quantity;
        internal double PointValue = 2.0;
        public double GetUnrealizedProfitLoss(PerformanceUnit unit, double price)
        {
            if (unit != PerformanceUnit.Currency) throw new NotSupportedException();
            int d = MarketPosition == MarketPosition.Long ? 1 : MarketPosition == MarketPosition.Short ? -1 : 0;
            return d * (price - AveragePrice) * Quantity * PointValue;
        }
    }
    // SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit: the closed trades' net P/L, fees included
    public class TradesPerformanceValues { public double CumProfit; }
    public class TradesPerformance { public TradesPerformanceValues Currency = new TradesPerformanceValues(); }
    public class TradeCollection { public TradesPerformance TradesPerformance = new TradesPerformance(); }
    public class SystemPerformance { public TradeCollection AllTrades = new TradeCollection(); }
    public class Order { public string Name; }
    public class MasterInstrument
    {
        public double PointValue = 2.0, TickSize = 0.25;
        public double RoundToTickSize(double price) { return Math.Round(price / TickSize) * TickSize; }
    }
    public class Instrument { public MasterInstrument MasterInstrument = new MasterInstrument(); }
}

namespace NinjaTrader.Data
{
    public enum BarsPeriodType { Tick, Second, Minute, Day }
    public class BarsPeriod { public BarsPeriodType BarsPeriodType = BarsPeriodType.Minute; public int Value = 5; }
}

namespace NinjaTrader.NinjaScript
{
    public enum State { SetDefaults, Configure, DataLoaded, Historical, Transition, Realtime, Terminated }
    public enum Calculate { OnBarClose, OnEachTick, OnPriceChange }
    public enum CalculationMode { Currency, Percent, Price, Ticks }
    public enum StartBehavior { AdoptAccountPosition, ImmediatelySubmit, WaitUntilFlat }
    public enum EntryHandling { AllEntries, UniqueEntries }
    public enum StopTargetHandling { PerEntryExecution, ByStrategyPosition }
    public enum RealtimeErrorHandling { IgnoreAllErrors, StopCancelClose, StopCancelCloseIgnoreRejects }
    public enum Priority { High, Low, Medium }

    [AttributeUsage(AttributeTargets.Property)]
    public class NinjaScriptPropertyAttribute : Attribute { }

    public class Series<T>
    {
        readonly List<T> data = new List<T>();
        internal int Current = -1;
        public T this[int barsAgo]
        {
            get { return data[Current - barsAgo]; }
            set { while (data.Count <= Current) data.Add(default(T)); data[Current - barsAgo] = value; }
        }
        internal void Add(T v) { data.Add(v); }
    }

    public abstract class NinjaScriptBase
    {
        public string Name, Description;
        public State State;
        public Calculate Calculate;
        public int BarsInProgress, CurrentBar = -1, BarsRequiredToTrade;
        public NinjaTrader.Data.BarsPeriod BarsPeriod = new NinjaTrader.Data.BarsPeriod();
        public NinjaTrader.Cbi.Instrument Instrument = new NinjaTrader.Cbi.Instrument();
        public double TickSize { get { return Instrument.MasterInstrument.TickSize; } }
        public Series<DateTime> Time = new Series<DateTime>();
        public Series<double> Open = new Series<double>(), High = new Series<double>(), Low = new Series<double>(),
            Close = new Series<double>();
        public Series<double>[] Values = new Series<double>[0];
        public readonly List<string> Printed = new List<string>();
        protected virtual void OnStateChange() { }
        protected virtual void OnBarUpdate() { }
        public void Print(object o) { Printed.Add(o == null ? "" : o.ToString()); }
        public void AddPlot(System.Windows.Media.Brush brush, string name)
        {
            Series<double>[] v = new Series<double>[Values.Length + 1];
            Array.Copy(Values, v, Values.Length);
            v[Values.Length] = new Series<double>();
            Values = v;
        }
        public void Alert(string id, Priority priority, string message, string soundLocation, int rearmSeconds,
                          System.Windows.Media.Brush backBrush, System.Windows.Media.Brush foreBrush) { }
    }
}

namespace NinjaTrader.NinjaScript.DrawingTools
{
    public enum TextPosition { BottomLeft, BottomRight, Center, TopLeft, TopRight }
    public class TextFixed { public string Text; }
    public static class Draw
    {
        public static readonly Dictionary<string, string> Texts = new Dictionary<string, string>();
        public static TextFixed TextFixed(NinjaScriptBase owner, string tag, string text, TextPosition textPosition)
        {
            Texts[tag] = text;
            TextFixed t = new TextFixed();
            t.Text = text;
            return t;
        }
    }
}

namespace NinjaTrader.NinjaScript.Strategies
{
    using NinjaTrader.Cbi;

    public class SimTrade
    {
        public int Direction, EntryBar, ExitBar;
        public double Entry, Exit, Pnl;
        public string ExitName;
    }

    public class Strategy : NinjaScriptBase
    {
        public int EntriesPerDirection;
        public EntryHandling EntryHandling;
        public StopTargetHandling StopTargetHandling;
        public bool IsExitOnSessionCloseStrategy, TraceOrders, IsInstantiatedOnEachOptimizationIteration;
        public StartBehavior StartBehavior;
        public RealtimeErrorHandling RealtimeErrorHandling;
        public Position Position = new Position();
        public SystemPerformance SystemPerformance = new SystemPerformance();
        public Account Account = new Account();
        public double SimNetLiq { get; set; }  // tests: the account's net liquidation, whatever the strategy did
        public string SimLiqFile { get; set; }  // tests: the account's net liquidation at each bar, one per line
        public string SimWithdraw { get; set; }  // tests: "bar:amount": a payout leaves the account at that bar
        public int SimRealtimeFrom { get; set; }  // tests: the strategy goes live at this bar (0: never)
        public string SimAccountName { get { return Account.Name; } set { Account.Name = value; } }
        public string SimUserDataDir
        {
            get { return NinjaTrader.Core.Globals.UserDataDir; }
            set { NinjaTrader.Core.Globals.UserDataDir = value; }
        }

        // the fill model
        public double CommissionPerSide = 0.62;
        public string RejectStopsAt { get; set; }  // "bar,bar,...": the broker rejects a stop change on these bars
        public int SlippageTicks = 1;
        public readonly List<SimTrade> SimTrades = new List<SimTrade>();
        public readonly List<string> OrderLog = new List<string>();
        readonly Dictionary<string, double> stops = new Dictionary<string, double>();
        readonly Dictionary<string, double> targets = new Dictionary<string, double>();
        readonly Dictionary<string, bool> stopInTicks = new Dictionary<string, bool>();
        readonly Dictionary<string, bool> targetInTicks = new Dictionary<string, bool>();
        int pendDir, pendQty;
        string pendName, pendExit;
        string posName;
        int entryBar;
        double stop = double.NaN, target = double.NaN;

        protected virtual void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                             double averageFillPrice, OrderState orderState, DateTime time,
                                             ErrorCode error, string comment) { }

        public double GetCurrentBid() { return Close[0]; }
        public double GetCurrentAsk() { return Close[0]; }

        void Check(string signal)
        {
            if (signal != "Long" && signal != "Short" && signal != "W Long" && signal != "W Short")
                throw new InvalidOperationException("unknown entry " + signal);
        }

        public void SetStopLoss(string fromEntrySignal, CalculationMode mode, double value, bool isSimulatedStop)
        {
            Check(fromEntrySignal);
            if (mode != CalculationMode.Price && mode != CalculationMode.Ticks) throw new NotSupportedException();
            if (mode == CalculationMode.Ticks && value <= 0) throw new ArgumentException("ticks must be positive");
            stops[fromEntrySignal] = value;
            stopInTicks[fromEntrySignal] = mode == CalculationMode.Ticks;
            OrderLog.Add(CurrentBar + ",SetStopLoss," + fromEntrySignal + "," + value.ToString("R") + "," + mode);
            if (Position.MarketPosition != MarketPosition.Flat && posName == fromEntrySignal)
            {
                int d = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
                if (mode == CalculationMode.Ticks) value = Position.AveragePrice - d * value * TickSize;
                if (RejectStopsAt != null && Array.IndexOf(RejectStopsAt.Split(','), CurrentBar.ToString()) >= 0)
                {
                    stop = double.NaN;  // the stop order is gone
                    Order rejected = new Order();
                    rejected.Name = "Stop loss";
                    OnOrderUpdate(rejected, 0, value, Position.Quantity, 0, 0, OrderState.Rejected, Time[0],
                                  ErrorCode.OrderRejected, "stop price is invalid");
                    OnOrderUpdate(rejected, 0, value, Position.Quantity, 0, 0, OrderState.Rejected, Time[0],
                                  ErrorCode.OrderRejected, "stop price is invalid");  // brokers can send it twice
                    return;
                }
                if ((d > 0 && value >= Close[0]) || (d < 0 && value <= Close[0]))
                    throw new InvalidOperationException("bar " + CurrentBar + ": a stop at or past the price would be rejected");
                stop = value;
            }
        }

        public void SetProfitTarget(string fromEntrySignal, CalculationMode mode, double value)
        {
            Check(fromEntrySignal);
            if (mode != CalculationMode.Price && mode != CalculationMode.Ticks) throw new NotSupportedException();
            if (mode == CalculationMode.Ticks && value <= 0) throw new ArgumentException("ticks must be positive");
            targets[fromEntrySignal] = value;
            targetInTicks[fromEntrySignal] = mode == CalculationMode.Ticks;
            OrderLog.Add(CurrentBar + ",SetProfitTarget," + fromEntrySignal + "," + value.ToString("R") + "," + mode);
            if (Position.MarketPosition != MarketPosition.Flat && posName == fromEntrySignal)
            {
                int d = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
                target = mode == CalculationMode.Ticks ? Position.AveragePrice + d * value * TickSize : value;
            }
        }

        void Enter(int d, int qty, string name)
        {
            Check(name);
            OrderLog.Add(CurrentBar + ",Enter," + name + "," + qty);
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (real == d && pendExit == null)
                throw new InvalidOperationException("bar " + CurrentBar + ": entry while in a position");
            if (pendName != null)
                throw new InvalidOperationException("bar " + CurrentBar + ": two entries on one bar");
            if (!stops.ContainsKey(name))
                throw new InvalidOperationException("bar " + CurrentBar + ": entry without a stop");
            pendDir = d; pendQty = qty; pendName = name;
        }

        public void EnterLong(int quantity, string signalName) { Enter(1, quantity, signalName); }
        public void EnterShort(int quantity, string signalName) { Enter(-1, quantity, signalName); }

        void Exit(int d, string signalName, string fromEntrySignal)
        {
            if (fromEntrySignal != "") Check(fromEntrySignal);  // "": every entry
            OrderLog.Add(CurrentBar + ",Exit," + signalName + "," + fromEntrySignal);
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (real == d && (fromEntrySignal == "" || posName == fromEntrySignal))
                pendExit = signalName;
        }

        public void ExitLong(string signalName, string fromEntrySignal) { Exit(1, signalName, fromEntrySignal); }
        public void ExitShort(string signalName, string fromEntrySignal) { Exit(-1, signalName, fromEntrySignal); }

        void Fill(int i, double price, string why)
        {
            int d = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
            SimTrade t = new SimTrade();
            t.Direction = d; t.EntryBar = entryBar; t.Entry = Position.AveragePrice; t.ExitBar = i; t.Exit = price;
            t.ExitName = why;
            t.Pnl = d * (price - t.Entry) * Position.Quantity * Instrument.MasterInstrument.PointValue -
                    2 * CommissionPerSide * Position.Quantity;
            SimTrades.Add(t);
            SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit += t.Pnl;
            Position.MarketPosition = MarketPosition.Flat;
            Position.Quantity = 0;
            Position.AveragePrice = 0;
            stop = target = double.NaN;
        }

        public void Run(IList<DateTime> barEnds, IList<double> o, IList<double> h, IList<double> l, IList<double> c,
                        Action<Strategy> configure)
        {
            State = State.SetDefaults;
            OnStateChange();
            if (configure != null) configure(this);
            State = State.Configure; OnStateChange();
            State = State.DataLoaded; OnStateChange();
            List<double> liqs = new List<double>();
            if (SimLiqFile != null)
                foreach (string line in System.IO.File.ReadAllLines(SimLiqFile))
                    liqs.Add(double.Parse(line, System.Globalization.CultureInfo.InvariantCulture));
            int withdrawBar = int.MaxValue;
            double withdrawAmount = 0;
            if (SimWithdraw != null)
            {
                string[] w = SimWithdraw.Split(':');
                withdrawBar = int.Parse(w[0]);
                withdrawAmount = double.Parse(w[1], System.Globalization.CultureInfo.InvariantCulture);
            }
            int dayFirstBar = 0;
            double dayStartCum = 0;
            Func<double> open = delegate
            {
                return Position.MarketPosition == MarketPosition.Flat ? 0 :
                    Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
            };
            Account.Value = delegate
            {
                double out_ = CurrentBar >= withdrawBar ? withdrawAmount : 0;
                if (SimLiqFile != null) return liqs[CurrentBar] - out_;
                if (SimNetLiq > 0) return SimNetLiq;
                return 50000 + SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit + open() - out_;
            };
            Account.Realized = delegate
            {
                if (SimLiqFile != null) return liqs[CurrentBar] - liqs[dayFirstBar];  // all of it closed
                return SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - dayStartCum;
            };
            Account.Unrealized = delegate { return SimLiqFile != null ? 0 : open(); };
            TimeZoneInfo ny = TimeZoneInfo.FindSystemTimeZoneById("America/New_York");
            DateTime lastDay = DateTime.MinValue;
            State = State.Historical; OnStateChange();
            double slip = SlippageTicks * TickSize;
            for (int i = 0; i < c.Count; i++)
            {
                if (SimRealtimeFrom > 0 && i == SimRealtimeFrom)
                {
                    State = State.Transition; OnStateChange();
                    State = State.Realtime; OnStateChange();
                }
                Time.Add(barEnds[i]); Open.Add(o[i]); High.Add(h[i]); Low.Add(l[i]); Close.Add(c[i]);
                CurrentBar = Time.Current = Open.Current = High.Current = Low.Current = Close.Current = i;
                foreach (Series<double> v in Values) v.Current = i;
                DateTime nyStart = TimeZoneInfo.ConvertTime(barEnds[i], NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo, ny)
                    .AddMinutes(-BarsPeriod.Value);
                bool newDay = nyStart.AddHours(6).Date != lastDay;  // the trading day starts at 18:00 New York
                lastDay = nyStart.AddHours(6).Date;
                // market orders from the last bar
                if (pendExit != null && Position.MarketPosition != MarketPosition.Flat)
                    Fill(i, o[i] - (Position.MarketPosition == MarketPosition.Long ? 1 : -1) * slip, pendExit);
                pendExit = null;
                if (pendName != null && Position.MarketPosition != MarketPosition.Flat)  // a reversal
                    Fill(i, o[i] - (Position.MarketPosition == MarketPosition.Long ? 1 : -1) * slip, "Close position");
                if (pendName != null)
                {
                    Position.MarketPosition = pendDir > 0 ? MarketPosition.Long : MarketPosition.Short;
                    Position.Quantity = pendQty;
                    Position.AveragePrice = o[i] + pendDir * slip;
                    posName = pendName;
                    entryBar = i;
                    stop = stops[pendName];
                    if (stopInTicks[pendName]) stop = Position.AveragePrice - pendDir * stop * TickSize;
                    target = targets.ContainsKey(pendName) ? targets[pendName] : double.NaN;
                    if (targets.ContainsKey(pendName) && targetInTicks[pendName])
                        target = Position.AveragePrice + pendDir * target * TickSize;
                    pendName = null;
                }
                // the attached stop and take-profit
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    int d = Position.MarketPosition == MarketPosition.Long ? 1 : -1;
                    bool hit;
                    double px;
                    if (entryBar == i)
                    {
                        hit = d > 0 ? l[i] <= stop : h[i] >= stop;
                        px = (d > 0 ? Math.Min(o[i], stop) : Math.Max(o[i], stop)) - d * slip;
                    }
                    else if ((d > 0 && o[i] <= stop) || (d < 0 && o[i] >= stop))
                    {
                        hit = true;
                        px = o[i] - d * slip;
                    }
                    else
                    {
                        hit = d > 0 ? l[i] <= stop : h[i] >= stop;
                        px = stop - d * slip;
                    }
                    if (hit)
                        Fill(i, px, "Stop loss");
                    else if (!double.IsNaN(target) && ((d > 0 && h[i] >= target + TickSize) || (d < 0 && l[i] <= target - TickSize)))
                        Fill(i, target, "Profit target");
                }
                if (newDay)  // after the day's first fills: an exit sent at the 16:00 close is the day before's
                {
                    dayFirstBar = i;
                    dayStartCum = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
                }
                OnBarUpdate();
            }
            State = State.Terminated;
            OnStateChange();
        }
    }
}
