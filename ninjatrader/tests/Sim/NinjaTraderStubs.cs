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
// A position can be two entries sent on the same bar in the same direction (two names, not on a reversal): they fill
// together, each with its own stop and take-profit (a lot each), and each lot's close is its own trade record.
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
            if (item == AccountItem.CashValue) return Value() - Unrealized();  // the balance: net liquidation less open P/L
            if (item == AccountItem.RealizedProfitLoss) return Realized();
            if (item == AccountItem.UnrealizedProfitLoss) return Unrealized();
            throw new NotSupportedException();
        }
    }
    public enum OrderState { Initialized, Submitted, Accepted, Working, PartFilled, Filled, Cancelled, Rejected }
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
    // the closed trades, as NinjaTrader records them from executions: a position filled in parts is several trades
    public class Execution
    {
        public DateTime Time;
        public string Name;
        public Order Order;
        public double Price;
        public int Quantity;
    }
    public class Trade { public double ProfitCurrency; public Execution Entry, Exit; public int Quantity; }
    public class TradeCollection
    {
        public TradesPerformance TradesPerformance = new TradesPerformance();
        internal readonly List<Trade> List = new List<Trade>();
        public int Count { get { return List.Count; } }
        public Trade this[int i] { get { return List[i]; } }
    }
    public class SystemPerformance
    {
        public TradeCollection AllTrades = new TradeCollection();
        public TradeCollection RealTimeTrades = new TradeCollection();  // the trades closed live
    }
    public class Order { public string Name; public OrderState OrderState; public int Quantity; }
    public class MasterInstrument
    {
        public double PointValue = 2.0, TickSize = 0.25;
        public double RoundToTickSize(double price) { return Math.Round(price / TickSize) * TickSize; }
    }
    public class Instrument
    {
        public MasterInstrument MasterInstrument = new MasterInstrument();
        public string FullName = "MNQ 12-26";
    }
}

namespace NinjaTrader.Data
{
    public enum BarsPeriodType { Tick, Second, Minute, Day }
    public class BarsPeriod { public BarsPeriodType BarsPeriodType = BarsPeriodType.Minute; public int Value = 5; }
    public class TradingHours
    {
        public string Name = "CME US Index Futures ETH";
        public override string ToString() { return Name; }
    }
    public class Bars
    {
        public TradingHours TradingHours = new TradingHours();
        internal int N;
        public int Count { get { return N; } }
    }
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
        public NinjaTrader.Data.Bars Bars = new NinjaTrader.Data.Bars();
        public NinjaTrader.Cbi.Instrument Instrument = new NinjaTrader.Cbi.Instrument();
        public double TickSize { get { return Instrument.MasterInstrument.TickSize; } }
        public Series<DateTime> Time = new Series<DateTime>();
        public Series<double> Open = new Series<double>(), High = new Series<double>(), Low = new Series<double>(),
            Close = new Series<double>();
        public Series<double>[] Values = new Series<double>[0];
        public readonly List<string> Printed = new List<string>();
        internal int ThrowAt = -1;  // tests: the dashboard call throws on this bar (a runtime error inside OnBarUpdate)
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
            if (owner.CurrentBar == owner.ThrowAt)
                throw new InvalidOperationException("test error on bar " + owner.CurrentBar);
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
        public string ExitName, EntryName;
        public int Qty;
    }

    public class Strategy : NinjaScriptBase
    {
        public int EntriesPerDirection;
        public EntryHandling EntryHandling;
        public StopTargetHandling StopTargetHandling;
        public bool IsExitOnSessionCloseStrategy, TraceOrders, IsInstantiatedOnEachOptimizationIteration;
        public int ExitOnSessionCloseSeconds;  // not modelled: the stand-in has no trading-hours template
        public StartBehavior StartBehavior;
        public RealtimeErrorHandling RealtimeErrorHandling;
        public Position Position = new Position();
        public SystemPerformance SystemPerformance = new SystemPerformance();
        public Account Account = new Account();
        // the account's own position in the instrument: the strategy's, plus SimForeignPosition's ("from:to:qty", signed
        // MNQ held on the account from bar from to bar to, outside the strategy: a restart's leftover, a manual trade)
        public string SimForeignPosition { get; set; }
        public Position PositionAccount
        {
            get
            {
                int d = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
                int q = d * Position.Quantity;
                if (SimForeignPosition != null)
                {
                    string[] f = SimForeignPosition.Split(':');
                    if (CurrentBar >= int.Parse(f[0]) && CurrentBar < int.Parse(f[1])) q += int.Parse(f[2]);
                }
                Position p = new Position();
                p.MarketPosition = q > 0 ? MarketPosition.Long : q < 0 ? MarketPosition.Short : MarketPosition.Flat;
                p.Quantity = Math.Abs(q);
                p.AveragePrice = Position.AveragePrice;
                return p;
            }
        }
        public double SimNetLiq { get; set; }  // tests: the account's net liquidation, whatever the strategy did
        public bool SimSplitFills { get; set; }  // tests: each entry fills in two executions (two trade records)
        public string SimLiqFile { get; set; }  // tests: the account's net liquidation at each bar, one per line
        public string SimWithdraw { get; set; }  // tests: "bar:amount": a payout leaves the account at that bar
        public int SimRealtimeFrom { get; set; }  // tests: the strategy goes live at this bar (0: never)
        public int SimThrowAtBar { get { return ThrowAt; } set { ThrowAt = value; } }
        public string SimAccountName { get { return Account.Name; } set { Account.Name = value; } }
        public string SimUserDataDir
        {
            get { return NinjaTrader.Core.Globals.UserDataDir; }
            set { NinjaTrader.Core.Globals.UserDataDir = value; }
        }

        // the fill model
        public double CommissionPerSide = 0.62;
        public string RejectStopsAt { get; set; }  // "bar,bar,...": the broker rejects a stop change on these bars
        public string RejectExitsAt { get; set; }  // "bar,bar,...": the broker rejects a market exit sent on these bars
        public int SlippageTicks = 1;
        public int SimSlippageTicks { get { return SlippageTicks; } set { SlippageTicks = value; } }  // ticks a market fill
        public double SimCommissionPerSide { get { return CommissionPerSide; } set { CommissionPerSide = value; } }
        public readonly List<SimTrade> SimTrades = new List<SimTrade>();
        public readonly List<string> OrderLog = new List<string>();
        readonly Dictionary<string, double> stops = new Dictionary<string, double>();
        readonly Dictionary<string, double> targets = new Dictionary<string, double>();
        readonly Dictionary<string, bool> stopInTicks = new Dictionary<string, bool>();
        readonly Dictionary<string, bool> targetInTicks = new Dictionary<string, bool>();

        // the position: one lot per entry name (an entry and its own stop and take-profit, as NinjaTrader's
        // per-entry Set orders); all the lots of a position fill together, at the same price
        sealed class Lot { public string Name; public int Qty; public double Stop = double.NaN, Target = double.NaN; }
        sealed class Pending { public int Dir, Qty; public string Name; public Order Order; }
        readonly List<Lot> lots = new List<Lot>();
        readonly List<Pending> pend = new List<Pending>();
        string pendExit;
        int entryBar;

        protected virtual void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                             double averageFillPrice, OrderState orderState, DateTime time,
                                             ErrorCode error, string comment) { }
        protected virtual void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                 MarketPosition marketPosition, string orderId, DateTime time) { }

        // the entry order's life, as NinjaTrader reports it: Submitted, Accepted, Working at the call; Filled (and an
        // execution) at the next bar's open. SimIgnoreEntriesAt: on these bars an entry is ignored (no order comes
        // back, nothing is sent: NinjaTrader's managed-order rules); SimRejectEntriesAt: the broker rejects it.
        public string SimIgnoreEntriesAt { get; set; }
        public string SimRejectEntriesAt { get; set; }
        int execs;
        static bool At(string bars, int bar) { return bars != null && Array.IndexOf(bars.Split(','), bar.ToString()) >= 0; }
        void Report(Order o, OrderState st, string comment)
        {
            o.OrderState = st;
            OnOrderUpdate(o, 0, 0, o.Quantity, st == OrderState.Filled ? o.Quantity : 0, 0, st, Time[0],
                          st == OrderState.Rejected ? ErrorCode.OrderRejected : ErrorCode.NoError, comment);
        }

        public double GetCurrentBid() { return Close[0]; }
        public double GetCurrentAsk() { return Close[0]; }

        static readonly string[] Entries = { "Long", "Short", "W Long", "W Short", "Long half", "Short half" };
        void Check(string signal)
        {
            if (Array.IndexOf(Entries, signal) < 0)
                throw new InvalidOperationException("unknown entry " + signal);
        }

        int Dir { get { return Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0; } }

        Lot LotOf(string name)
        {
            foreach (Lot x in lots)
                if (x.Name == name) return x;
            return null;
        }

        public void SetStopLoss(string fromEntrySignal, CalculationMode mode, double value, bool isSimulatedStop)
        {
            Check(fromEntrySignal);
            if (mode != CalculationMode.Price && mode != CalculationMode.Ticks) throw new NotSupportedException();
            if (mode == CalculationMode.Ticks && value <= 0) throw new ArgumentException("ticks must be positive");
            stops[fromEntrySignal] = value;
            stopInTicks[fromEntrySignal] = mode == CalculationMode.Ticks;
            OrderLog.Add(CurrentBar + ",SetStopLoss," + fromEntrySignal + "," + value.ToString("R") + "," + mode);
            Lot lot = LotOf(fromEntrySignal);
            if (lot != null)
            {
                int d = Dir;
                if (mode == CalculationMode.Ticks) value = Position.AveragePrice - d * value * TickSize;
                if (RejectStopsAt != null && Array.IndexOf(RejectStopsAt.Split(','), CurrentBar.ToString()) >= 0)
                {
                    lot.Stop = double.NaN;  // the stop order is gone
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
                lot.Stop = value;
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
            Lot lot = LotOf(fromEntrySignal);
            if (lot != null)
                lot.Target = mode == CalculationMode.Ticks ? Position.AveragePrice + Dir * value * TickSize : value;
        }

        Order Enter(int d, int qty, string name)
        {
            Check(name);
            OrderLog.Add(CurrentBar + ",Enter," + name + "," + qty);
            if (At(SimIgnoreEntriesAt, CurrentBar))
                return null;
            int real = Dir;
            if (real == d && pendExit == null)
                throw new InvalidOperationException("bar " + CurrentBar + ": entry while in a position");
            foreach (Pending x in pend)
                if (x.Name == name || x.Dir != d)
                    throw new InvalidOperationException("bar " + CurrentBar + ": two entries on one bar");
            if (pend.Count > 0 && real == -d)
                throw new InvalidOperationException("bar " + CurrentBar + ": two entries reversing a position");
            if (!stops.ContainsKey(name))
                throw new InvalidOperationException("bar " + CurrentBar + ": entry without a stop");
            Order o = new Order();
            o.Name = name;
            o.Quantity = qty;
            Report(o, OrderState.Submitted, "");
            if (At(SimRejectEntriesAt, CurrentBar))
            {
                Report(o, OrderState.Rejected, "the broker refused the entry");
                return o;
            }
            Report(o, OrderState.Accepted, "");
            Report(o, OrderState.Working, "");
            Pending p = new Pending();
            p.Dir = d; p.Qty = qty; p.Name = name; p.Order = o;
            pend.Add(p);
            return o;
        }

        public Order EnterLong(int quantity, string signalName) { return Enter(1, quantity, signalName); }
        public Order EnterShort(int quantity, string signalName) { return Enter(-1, quantity, signalName); }

        void Exit(int d, string signalName, string fromEntrySignal)
        {
            if (fromEntrySignal != "") Check(fromEntrySignal);  // "": every entry
            OrderLog.Add(CurrentBar + ",Exit," + signalName + "," + fromEntrySignal);
            int real = Dir;
            if (real == d && RejectExitsAt != null && Array.IndexOf(RejectExitsAt.Split(','), CurrentBar.ToString()) >= 0)
            {
                Order rejected = new Order();
                rejected.Name = signalName;
                OnOrderUpdate(rejected, 0, 0, Position.Quantity, 0, 0, OrderState.Rejected, Time[0],
                              ErrorCode.OrderRejected, "the broker refused the exit");
                return;  // the position stays open
            }
            if (real == d && (fromEntrySignal == "" || (lots.Count == 1 && lots[0].Name == fromEntrySignal)))
                pendExit = signalName;
        }

        public void ExitLong(string signalName, string fromEntrySignal) { Exit(1, signalName, fromEntrySignal); }
        public void ExitShort(string signalName, string fromEntrySignal) { Exit(-1, signalName, fromEntrySignal); }

        // the strategy's closed trades, as NinjaTrader keeps them: all of them, and those closed live (RealTimeTrades)
        void Record(Lot lot, int i, double price, string why, int parts)
        {
            int d = Dir;
            SimTrade t = new SimTrade();
            t.Direction = d; t.EntryBar = entryBar; t.Entry = Position.AveragePrice; t.ExitBar = i; t.Exit = price;
            t.ExitName = why; t.EntryName = lot.Name; t.Qty = lot.Qty;
            t.Pnl = d * (price - t.Entry) * lot.Qty * Instrument.MasterInstrument.PointValue - 2 * CommissionPerSide * lot.Qty;
            SimTrades.Add(t);
            SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit += t.Pnl;
            if (State == State.Realtime)
                SystemPerformance.RealTimeTrades.TradesPerformance.Currency.CumProfit += t.Pnl;
            // NinjaTrader's trade records: one per entry execution; SimSplitFills fills each entry in two parts
            parts = parts == 2 && lot.Qty > 1 ? 2 : 1;
            for (int k = 0; k < parts; k++)
            {
                Trade rec = new Trade();
                rec.Quantity = parts == 1 ? lot.Qty : (k == 0 ? lot.Qty / 2 : lot.Qty - lot.Qty / 2);
                rec.ProfitCurrency = t.Pnl * rec.Quantity / lot.Qty;
                // Time[] counts bars ago, as NinjaTrader's does
                rec.Entry = new Execution(); rec.Entry.Time = Time[CurrentBar - entryBar]; rec.Entry.Name = lot.Name;
                rec.Exit = new Execution(); rec.Exit.Time = Time[CurrentBar - i]; rec.Exit.Name = why;
                SystemPerformance.AllTrades.List.Add(rec);
                if (State == State.Realtime)
                    SystemPerformance.RealTimeTrades.List.Add(rec);
            }
        }

        void CloseLot(Lot lot, int i, double price, string why)
        {
            Record(lot, i, price, why, SimSplitFills ? 2 : 1);
            lots.Remove(lot);
            Position.Quantity -= lot.Qty;
            if (lots.Count == 0)
            {
                Position.MarketPosition = MarketPosition.Flat;
                Position.Quantity = 0;
                Position.AveragePrice = 0;
            }
        }

        void Fill(int i, double price, string why)  // the whole position at market
        {
            foreach (Lot lot in new List<Lot>(lots))
                CloseLot(lot, i, price, why);
        }

        public void Run(IList<DateTime> barEnds, IList<double> o, IList<double> h, IList<double> l, IList<double> c,
                        Action<Strategy> configure)
        {
            State = State.SetDefaults;
            OnStateChange();
            if (configure != null) configure(this);
            State = State.Configure; OnStateChange();
            Bars.N = c.Count;  // all the bars loaded, as NinjaTrader's Bars.Count
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
                    Fill(i, o[i] - Dir * slip, pendExit);
                pendExit = null;
                if (pend.Count > 0 && Position.MarketPosition != MarketPosition.Flat && Dir == -pend[0].Dir)  // a reversal
                    Fill(i, o[i] - Dir * slip, "Close position");
                if (pend.Count > 0)
                {
                    int pd = pend[0].Dir;
                    Position.MarketPosition = pd > 0 ? MarketPosition.Long : MarketPosition.Short;
                    Position.AveragePrice = o[i] + pd * slip;
                    entryBar = i;
                    foreach (Pending x in pend)
                    {
                        Lot lot = new Lot();
                        lot.Name = x.Name; lot.Qty = x.Qty;
                        lot.Stop = stops[x.Name];
                        if (stopInTicks[x.Name]) lot.Stop = Position.AveragePrice - pd * lot.Stop * TickSize;
                        if (targets.ContainsKey(x.Name))
                            lot.Target = targetInTicks[x.Name] ? Position.AveragePrice + pd * targets[x.Name] * TickSize : targets[x.Name];
                        lots.Add(lot);
                        Position.Quantity += x.Qty;
                    }
                    foreach (Pending x in pend)
                    {
                        Report(x.Order, OrderState.Filled, "");
                        Execution ex = new Execution();
                        ex.Time = barEnds[i]; ex.Name = x.Name; ex.Order = x.Order; ex.Price = Position.AveragePrice;
                        ex.Quantity = x.Qty;
                        execs++;
                        OnExecutionUpdate(ex, "x" + execs, ex.Price, ex.Quantity, Position.MarketPosition, "o" + execs, barEnds[i]);
                    }
                    pend.Clear();
                }
                // each lot's attached stop, then its take-profit
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    int d = Dir;
                    foreach (Lot lot in new List<Lot>(lots))
                    {
                        double st = lot.Stop;
                        bool hit;
                        double px;
                        if (entryBar == i)
                        {
                            hit = d > 0 ? l[i] <= st : h[i] >= st;
                            px = (d > 0 ? Math.Min(o[i], st) : Math.Max(o[i], st)) - d * slip;
                        }
                        else if ((d > 0 && o[i] <= st) || (d < 0 && o[i] >= st))
                        {
                            hit = true;
                            px = o[i] - d * slip;
                        }
                        else
                        {
                            hit = d > 0 ? l[i] <= st : h[i] >= st;
                            px = st - d * slip;
                        }
                        if (hit)
                            CloseLot(lot, i, px, "Stop loss");
                    }
                    foreach (Lot lot in new List<Lot>(lots))
                        if (!double.IsNaN(lot.Target) &&
                            ((d > 0 && h[i] >= lot.Target + TickSize) || (d < 0 && l[i] <= lot.Target - TickSize)))
                            CloseLot(lot, i, lot.Target, "Profit target");
                }
                if (newDay)  // after the day's first fills: an exit sent at the 16:00 close is the day before's
                {
                    dayFirstBar = i;
                    dayStartCum = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
                }
                try
                {
                    OnBarUpdate();
                }
                catch (Exception e)  // as NinjaTrader: logged, and the strategy is stopped
                {
                    Printed.Add("LOG: Error on calling 'OnBarUpdate' method on bar " + i + ": " + e.Message);
                    break;
                }
            }
            State = State.Terminated;
            OnStateChange();
        }
    }
}
