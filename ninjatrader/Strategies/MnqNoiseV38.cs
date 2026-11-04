// MNQ Noise-Area Momentum v3.8 for NinjaTrader 8: the 50K evaluation version (docs/CANDIDATE_E50.md).
//
// The same rules as pine/mnq_noise_momentum.pine v3.8 and mnqbot/noise.py with those settings, in one file:
//   * the noise area: at each half-hour check 10:00-15:00 New York, the day's open (and the previous close) plus or
//     minus the average move from the 09:30 open to that time over the last 14 sessions;
//   * a check that closes above the upper line buys 1 MNQ at market, below the lower line sells, unless a filter says
//     no: no entries after the 15:00 check; after a big day (range over 1.5x the 10-session average) none in its
//     direction; none after a calm stretch (the last 10 sessions' average range under 0.7x the last 40's); the close
//     must sit in the top (bottom) 35% of the day's range so far; no shorts while yesterday's close is above its
//     50-session average; no shorts before 14:00 on Fed days; no trades on holidays and half days;
//   * the stop, sent with the entry: the closer of 0.24 noise units past the line and $260 from the fill (the whole
//     position), then moved with the line at every bar close, never back toward the price; once price has gone
//     0.35 x the max loss in the trade's favour, the stop moves to the entry + 2.5 points;
//   * a take-profit 2 noise units from the fill;
//   * no limit on trades a day, but no new trade may risk more than what is left of $900 lost today: when not even a
//     full trade fits, 1 contract with its stop cut to the room left, if that leaves at least 20 points;
//   * everything closed at market at 16:00.
// Orders follow NinjaTrader's execution as tested (docs/PARITY.md): the bracket goes in with the entry in ticks from
// the fill; a stop the bar's close has already passed is a market exit at the next bar's open ("Stop passed"); the
// 16:00 exit is a market order filled at the next bar's open. ninjatrader/tests/Sim runs this file on bars and
// tests/test_ninjatrader_v38.py holds it to the Python model trade for trade.
//
// Setup: an MNQ chart of 5 or 30 minutes (any length that divides 30), Trading hours "CME US Index Futures ETH" (so a
// bar starts at 16:00 for the 16:00 exit to fill in), Days to load 120 or more (the noise needs 14 full sessions, the
// trend filter 50, the calm filter 40), Calculate On bar close. Written in C# 5 for NinjaTrader 8's compiler.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using System.Windows.Media;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public sealed class V38Settings
    {
        public int Lookback = 14;
        public int Qty = 1;
        public double Tick = 0.25, PointValue = 2.0, CommissionPerSide = 0.62;
        public int SlippageTicks = 1;
        public double StopBuffer = 0.24, MaxLoss = 260.0, TakeProfit = 2.0, LockAt = 0.35, LockPlus = 2.5;
        public double DailyLoss = 900.0, SqueezeMin = 20.0, RangePosMin = 0.65;
        public int LastEntryEnd = 900, BigDayN = 10, CalmShort = 10, CalmLong = 40, TrendN = 50;
        public double BigDayK = 1.5, CalmK = 0.7;
        public bool FedNoShorts = true, TightenOnly = true, RoundPrices = true;
        public string SkipDates = "", FedDates = "";
        // funded growth (pine v3.6's sizing; off in the evaluation): the trade after a loser risks AfterLossMaxLoss;
        // an end-of-day trailing drawdown from TrailFrom that stops at the starting balance; one more contract per
        // ProfitStep of closed profit since then, up to MaxContracts; each trade sized by its own stop
        public double AfterLossMaxLoss = 0.0, TrailDD = 0.0, ProfitStep = 0.0;
        public int MaxContracts = 0;
        public bool SizeByOwnStop = false;
        public string TrailFrom = "";
        // a time stop (G6): a trade not yet locked that is losing at a bar close TimeStop minutes or more after its
        // fill is closed at market, filled at the next bar's open (0 = off)
        public int TimeStop = 0;
        // a gentle start (G30): no contract steps until the trailing floor has stopped at the starting balance
        public bool StepsAfterLock = false;
        // gap and go (G60): when the 09:30 open is at least GapGoK times the last 14 sessions' average gap from the
        // prior close and the 09:30 bar closes beyond its open the gap's way, a market entry that way at the 09:35
        // open, a stop at the 09:30 open, out at the GapGoExit bar's open (595 = 09:55); GapGoMaxQty contracts at most
        public bool GapGo = false;
        public double GapGoK = 0.5;
        public int GapGoMaxQty = 1, GapGoExit = 595;
        // G67: once the trailing floor has stopped at the starting balance, a gap trade may take up to this many
        // contracts in place of GapGoMaxQty (0 = off)
        public int GapGoLockedQty = 0;
        // G72 ("More trading days"): 1-MNQ fill-in trades, only once the trailing floor has stopped at the start and
        // while the account is at least FillMinRoom above it: small gaps (at least FillSmallK x the average gap, the
        // 09:30 bar closing the gap's way), an opening drive (no gap trade, the 09:30 bar's body at least FillDriveK x
        // the last 14 sessions' average body, its way) in the 09:35-09:55 slot, and the shorts the trend filter blocks
        public bool MoreDays = false;
        public double FillSmallK = 0.0, FillDriveK = 0.6, FillMinRoom = 3000;
        // G97: the fill-ins at 2 MNQ while the account is FillQty2Room above the floor (0 = always 1)
        public double FillQty2Room = 0;
        // G99: once the floor has stopped at the start, while the profit is under GivebackBrake x the best end-of-day
        // profit, every trade at 1 MNQ (0 = off)
        public double GivebackBrake = 0;
        // G119: once the floor has stopped at the start, the trade after a loser risks this instead (0 = AfterLossMaxLoss)
        public double AfterLossLockedMaxLoss = 0;
        // G125: no new entry at these checks (the check bar's end, minutes after midnight, e.g. ",780,870,") until the
        // floor has stopped at the start (5-minute bars; "" = off)
        public string EarlySkipChecks = "";
        // G142: above ProfitStepFastFrom of profit, one more contract per ProfitStepFast (5-minute bars; 0 = off)
        public double ProfitStepFast = 0, ProfitStepFastFrom = 10000;
        // G103: a sprint: for the account's first SprintDays sessions, until its profit reaches SprintTarget, every bot and
        // gap trade takes SprintQty contracts (still cut to the day's and the floor's room); then the usual sizing (0 = off)
        public int SprintQty = 0, SprintDays = 5;
        public double SprintTarget = 3000;
        // G76: the bot's sizing counts this many points more slippage at the stop (0 = off)
        public double SizeSlipPts = 0;
        // G87: within ProtectRoom of the trailing floor, no new trade on a session after a shadow (1-contract, paper)
        // record of the bot closed below its average of the last ProtectN sessions (0 = off; set by the wrapper)
        public double ProtectRoom = 0;
        public int ProtectN = 20;

        public V38Settings Clone() { return (V38Settings)MemberwiseClone(); }
    }

    public sealed class V38Trade
    {
        public int Direction, Qty, EntryBar, ExitBar;
        public double Entry, Exit, Pnl;
        public string Reason;
    }

    // The rules, with no NinjaTrader code in them: mnqbot/noise.py with v3.8's settings and nt_execution,
    // round_prices and target_on_fill_bar on. Feed finished bars in order with their START time in New York time.
    public sealed class V38Engine
    {
        public const int NChecks = 12, FirstCheck = 600, LastCheck = 930, Step = 30, RthOpen = 570, RthClose = 960;
        public const int FedCutoff = 840;
        readonly V38Settings s;
        readonly int minutes;
        readonly double slip;
        readonly double[] ring;
        double[] today = NewToday();
        int filled, slot;
        double dayOpen = double.NaN, prevClose = double.NaN, lastRthClose = double.NaN, lastBarClose = double.NaN;
        double dayHi = double.NaN, dayLo = double.NaN;
        readonly List<double> dayRanges = new List<double>(), dayCloses = new List<double>();
        readonly List<int> dayDirs = new List<int>();
        int blockDir, trend;
        bool calm;
        int pendingKind, pendingDir;  // 1: an entry in pendingDir, 3: the 16:00 exit; filled at the next bar's open
        double estPx = double.NaN;
        int qNext, qTrade;
        double mlNext, mlTrade;
        double brStopNext, brTpNext, brStopTrade, brTpTrade;  // the bracket: points from the fill
        string brWhyNext = "", brWhyTrade = "";
        double held = double.NaN, fav = double.NaN;
        string heldWhy = "";
        int consec;                       // losing trades in a row, across days
        double equity;                    // the closed P/L so far
        double trailBase = double.NaN, trailPeak = double.NaN;

        public readonly List<V38Trade> Trades = new List<V38Trade>();
        public int Bar = -1;
        public int Position, EntryBar;
        public double EntryPrice;
        public double Upper = double.NaN, Lower = double.NaN, Sigma = double.NaN;
        public bool Locked, SkipToday, FedToday;
        public double DayPnl;
        // the account's own numbers (the strategy's real fills), set by the wrapper before each bar; every risk limit
        // uses the worse of these and the model's, so a live fill worse than the model's never adds risk (NaN: unset)
        public double ExtDayPnl = double.NaN, ExtEquity = double.NaN;
        // live: the prop account's own room above its trailing floor, from the account's balance (NaN = not used); a new
        // trade never risks more than it
        public double ExtRoom = double.NaN;
        double DayEff { get { return double.IsNaN(ExtDayPnl) ? DayPnl : Math.Min(DayPnl, ExtDayPnl); } }
        double EqEff { get { return double.IsNaN(ExtEquity) ? equity : Math.Min(equity, ExtEquity); } }
        public double Equity { get { return EqEff; } }
        public double TrailBase { get { return trailBase; } }
        public int TimeStopMinutes { get { return s.TimeStop; } }
        public int MinutesInTrade { get { return Position != 0 ? (Bar + 1 - EntryBar) * minutes : 0; } }  // at this close
        // the contract steps may apply: always, or with StepsAfterLock once the floor has stopped at the start
        bool StepsOk { get { return !s.StepsAfterLock || (!double.IsNaN(trailPeak) && trailPeak - s.TrailDD >= trailBase); } }
        public int NextQty
        {
            get
            {
                int q = s.Qty;
                if (s.ProfitStep > 0 && !double.IsNaN(trailBase) && StepsOk)
                {
                    q += NSteps();
                    if (s.MaxContracts > 0) q = Math.Min(q, s.MaxContracts);
                }
                return q;
            }
        }
        public double DayRoom { get { return s.DailyLoss > 0 ? s.DailyLoss + DayEff : double.NaN; } }
        public int NewEntry;          // this bar's signal: +1 / -1 to send now (0: none)
        public int NewQty;
        public double NewStopPts, NewTpPts;
        public bool FlatNow;          // this bar is the 16:00 bar: close at market
        public bool TimeStopNow;      // the time stop: close at market now
        public string Note = "";      // what this bar's check found, for the dashboard
        // gap and go (G60): its own trade, never open at the same time as the main one
        public int GapPos, GapQty, GapBar;
        public double GapEntry, GapStop = double.NaN;
        public int GapNewEntry, GapNewQty;  // this bar's gap signal: send now at market (0: none)
        public double GapNewStop = double.NaN;  // its stop price
        public bool GapExitNow;               // close the gap trade at market now (it fills at the next open)
        bool gapPending, gapExitPending;
        int gapPendingDir, gapPendingQty;
        double gapPendingStop;
        readonly List<double> gapHist = new List<double>();
        readonly List<double> driveHist = new List<double>();  // G72: the 09:30 bars' |close - open|

        // G87: is the shadow gate closed today (set by the wrapper at each session's first bar)?
        public bool ProtectClosed = false;

        // G87: within ProtectRoom of the floor on a day the shadow gate is closed: no new trade
        public bool Protected()
        {
            if (s.ProtectRoom <= 0 || !ProtectClosed || s.TrailDD <= 0 || double.IsNaN(trailPeak)) return false;
            double floor = Math.Min(trailPeak - s.TrailDD, trailBase);
            return EqEff - floor < s.ProtectRoom;
        }

        int sprintSessions;
        bool sprintDone;

        // G103: is the sprint on?
        public bool SprintOn()
        {
            if (s.SprintQty <= 0 || sprintDone || double.IsNaN(trailBase)) return false;
            if (EqEff - trailBase >= s.SprintTarget) { sprintDone = true; return false; }
            return sprintSessions <= s.SprintDays;
        }

        // G99: has the account given back more than (1 - GivebackBrake) of its best profit since the floor stopped?
        public bool Braked()
        {
            if (s.GivebackBrake <= 0 || minutes != 5 || s.TrailDD <= 0 || double.IsNaN(trailPeak)) return false;  // tested on 5-minute bars
            if (trailPeak - s.TrailDD < trailBase) return false;
            return EqEff - trailBase < s.GivebackBrake * (trailPeak - trailBase);
        }

        // G97: the fill-ins' contracts
        int FillQ()
        {
            if (s.FillQty2Room <= 0 || s.TrailDD <= 0 || double.IsNaN(trailPeak) || Braked()) return 1;
            double floor = Math.Min(trailPeak - s.TrailDD, trailBase);
            return EqEff - floor >= s.FillQty2Room ? 2 : 1;
        }

        // G72: may a fill-in trade be taken now? The floor stopped at the start, and FillMinRoom above it
        bool FillOk()
        {
            if (!s.MoreDays || minutes != 5 || s.TrailDD <= 0 || double.IsNaN(trailPeak)) return false;  // tested on 5-minute bars only
            if (trailPeak - s.TrailDD < trailBase) return false;
            double floor = Math.Min(trailPeak - s.TrailDD, trailBase);
            return EqEff - floor >= s.FillMinRoom;
        }
        public int LastEntryMinute { get { return s.LastEntryEnd; } }
        public int ProtectNSessions { get { return s.ProtectN; } }
        // U15: what today's filters allow, for the dashboard (set at the 09:30 bar; the day's loss budget live)
        public string TodayRules
        {
            get
            {
                if (SkipToday) return "no entries (holiday / half day)";
                if (Protected()) return "no entries (within $" + s.ProtectRoom.ToString("0", CultureInfo.InvariantCulture) +
                                        " of the floor, and the shadow record is below its " + s.ProtectN + "-session average)";
                if (calm) return "no entries (calm stretch: the last 10 sessions' ranges are small)" +
                                 (s.GapGo ? "; the 09:35 gap trade still can" : "");
                if (s.DailyLoss > 0 && DayRoom <= 0) return "no entries (today's loss budget is used up)";
                string longs = blockDir == 1 ? "no (after a big up day)" : "yes";
                string shorts = blockDir == -1 ? "no (after a big down day)"
                              : s.TrendN > 0 && trend == 1 ? (FillOk() ? "1 MNQ only (uptrend; More trading days)"
                                                                        : "no (uptrend: above the 50-session average)")
                              : FedToday && s.FedNoShorts ? "after 14:00 (Fed day)" : "yes";
                bool early = !string.IsNullOrEmpty(s.EarlySkipChecks) && minutes == 5
                             && !(s.TrailDD > 0 && !double.IsNaN(trailPeak) && trailPeak - s.TrailDD >= trailBase);
                return "longs " + longs + "; shorts " + shorts + (Braked() ? "; giveback brake on: 1 MNQ a trade" : "")
                       + (early ? "; no entries at " + EarlySkipText() + " until the floor stops" : "");
            }
        }

        public V38Engine(V38Settings settings, int barMinutes)
        {
            if (barMinutes <= 0 || 30 % barMinutes != 0)
                throw new ArgumentException("bar length must divide 30 minutes, not " + barMinutes);
            s = settings;
            minutes = barMinutes;
            slip = s.SlippageTicks * s.Tick;
            ring = new double[s.Lookback * NChecks];
            for (int i = 0; i < ring.Length; i++)
                ring[i] = double.NaN;
        }

        static double[] NewToday()
        {
            double[] t = new double[NChecks];
            for (int i = 0; i < NChecks; i++)
                t[i] = double.NaN;
            return t;
        }

        public bool Ready { get { return filled >= s.Lookback && !double.IsNaN(prevClose); } }
        public int SessionsLoaded { get { return Math.Min(filled, s.Lookback); } }

        double LineStop(int d)
        {
            return d > 0 ? Upper * (1 - s.StopBuffer * Sigma) : Lower * (1 + s.StopBuffer * Sigma);
        }

        // a long's stop and take-profit both round up (the stop toward the price, the take-profit away from it), a
        // short's both down: a loss never goes past the max loss, a target never takes less than tested
        public double OnGrid(int d, double price)
        {
            if (!s.RoundPrices || double.IsNaN(price))
                return price;
            double n = price / s.Tick;
            return (d > 0 ? Math.Ceiling(n - 1e-7) : Math.Floor(n + 1e-7)) * s.Tick;
        }

        double TicksDown(double points)
        {
            return s.RoundPrices ? Math.Max(s.Tick, Math.Floor(points / s.Tick + 1e-7) * s.Tick) : points;
        }

        double TicksUp(double points)
        {
            return s.RoundPrices && !double.IsNaN(points) ? Math.Max(s.Tick, Math.Ceiling(points / s.Tick - 1e-7) * s.Tick) : points;
        }

        static bool InList(string list, DateTime t)
        {
            return !string.IsNullOrEmpty(list) && list.Contains(t.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        }

        // The stop that rests for the next bar, measured from entry (the real fill): the closest of the line stop,
        // the max loss and the lock, on the tick grid, never back toward the price. NaN when flat.
        public double PeekStop(double entry)
        {
            if (Position == 0 || double.IsNaN(Upper))
                return double.NaN;
            int p = Position;
            double line = LineStop(p);
            double cap = entry - p * mlTrade / qTrade / s.PointValue;
            if ((p > 0 && cap > line) || (p < 0 && cap < line)) line = cap;
            if (Locked)
            {
                double lk = entry + p * s.LockPlus;
                if ((p > 0 && lk > line) || (p < 0 && lk < line)) line = lk;
            }
            line = OnGrid(p, line);
            if (s.TightenOnly && !double.IsNaN(held) && ((p > 0 && held > line) || (p < 0 && held < line)))
                line = held;
            return line;
        }

        public double PeekTarget(double entry)
        {
            if (Position == 0 || s.TakeProfit <= 0 || double.IsNaN(Sigma))
                return double.NaN;
            return OnGrid(Position, entry * (1 + Position * s.TakeProfit * Sigma));
        }

        public int TradeQty { get { return qTrade; } }

        void Open(int i, double o, int d)
        {
            Position = d;
            EntryPrice = o + d * slip;
            EntryBar = i;
            qTrade = qNext;
            mlTrade = mlNext;
            brStopTrade = brStopNext;
            brTpTrade = brTpNext;
            brWhyTrade = brWhyNext;
        }

        void Close(int i, double price, string reason)
        {
            double pnl = Position * (price - EntryPrice) * qTrade * s.PointValue - 2 * s.CommissionPerSide * qTrade;
            V38Trade t = new V38Trade();
            t.Direction = Position; t.Qty = qTrade; t.EntryBar = EntryBar; t.Entry = EntryPrice;
            t.ExitBar = i; t.Exit = price; t.Reason = reason; t.Pnl = pnl;
            Trades.Add(t);
            DayPnl += pnl;
            equity += pnl;
            if (pnl < 0 && reason != "Session ended") consec++;
            else if (pnl >= 0) consec = 0;
            Position = 0;
            Locked = false;
            held = double.NaN;
            heldWhy = "";
            fav = double.NaN;
        }

        void GapClose(int i, double price, string reason)
        {
            double pnl = GapPos * (price - GapEntry) * GapQty * s.PointValue - 2 * s.CommissionPerSide * GapQty;
            V38Trade t = new V38Trade();
            t.Direction = GapPos; t.Qty = GapQty; t.EntryBar = GapBar; t.Entry = GapEntry;
            t.ExitBar = i; t.Exit = price; t.Reason = reason; t.Pnl = pnl;
            Trades.Add(t);
            DayPnl += pnl;
            equity += pnl;
            GapPos = 0;
            GapStop = double.NaN;
        }

        // the contract steps for the profit since the start (G142: faster above ProfitStepFastFrom, on 5-minute bars)
        int NSteps()
        {
            double p = Math.Max(0.0, EqEff - trailBase);
            if (s.ProfitStepFast > 0 && minutes == 5 && p > s.ProfitStepFastFrom)
                return (int)Math.Floor(s.ProfitStepFastFrom / s.ProfitStep) + (int)Math.Floor((p - s.ProfitStepFastFrom) / s.ProfitStepFast);
            return (int)Math.Floor(p / s.ProfitStep);
        }

        // the early no-entry checks as clock times ("13:00, 14:30"), for the dashboard
        string EarlySkipText()
        {
            List<string> parts = new List<string>();
            foreach (string m in s.EarlySkipChecks.Split(','))
            {
                int end;
                if (m.Length == 0 || !int.TryParse(m, out end)) continue;
                parts.Add((end / 60).ToString("00", CultureInfo.InvariantCulture) + ":" + (end % 60).ToString("00", CultureInfo.InvariantCulture));
            }
            return string.Join(", ", parts.ToArray());
        }

        // G125: is this check one without entries until the floor has stopped?
        bool EarlySkip(int end)
        {
            if (string.IsNullOrEmpty(s.EarlySkipChecks) || minutes != 5) return false;  // tested on 5-minute bars
            if (s.TrailDD > 0 && !double.IsNaN(trailPeak) && trailPeak - s.TrailDD >= trailBase) return false;
            return s.EarlySkipChecks.Contains("," + end + ",");
        }

        bool StudyOk(int d, int end, double c)
        {
            if (Protected()) { Note = "near the floor, shadow below its average"; return false; }
            if (s.LastEntryEnd > 0 && end > s.LastEntryEnd) { Note = "after the last entry check"; return false; }
            if (EarlySkip(end)) { Note = "no entry at this check until the floor has stopped"; return false; }
            if (blockDir != 0 && d == blockDir) { Note = "after a big day, not its way"; return false; }
            if (s.TrendN > 0 && d < 0 && trend == 1 && !FillOk()) { Note = "no shorts in the uptrend"; return false; }
            if (calm) { Note = "calm stretch"; return false; }
            if (s.RangePosMin > 0 && dayHi > dayLo)
            {
                double rp = d > 0 ? (c - dayLo) / (dayHi - dayLo) : (dayHi - c) / (dayHi - dayLo);
                if (rp < s.RangePosMin) { Note = "not near the day's extreme"; return false; }
            }
            return true;
        }

        public void OnBar(DateTime nyStart, double o, double h, double l, double c)
        {
            int i = ++Bar;
            int tMin = nyStart.Hour * 60 + nyStart.Minute;
            int end = tMin + minutes;
            bool inRth = tMin >= RthOpen && end <= RthClose;
            NewEntry = 0;
            FlatNow = false;
            TimeStopNow = false;
            Note = "";
            GapNewEntry = 0;
            GapExitNow = false;

            if (s.GapGo)  // G60: the gap trade's market orders fill at this open, then its stop
            {
                if (GapPos != 0 && (gapExitPending || tMin >= s.GapGoExit))
                    GapClose(i, o - GapPos * slip, "Gap exit");
                gapExitPending = false;
                if (gapPending)
                {
                    gapPending = false;
                    if (tMin == RthOpen + 5 && Position == 0 && GapPos == 0)
                    {
                        GapPos = gapPendingDir; GapQty = gapPendingQty; GapBar = i;
                        GapEntry = o + GapPos * slip; GapStop = gapPendingStop;
                    }
                }
                if (GapPos != 0 && (GapPos > 0 ? l <= GapStop : h >= GapStop))
                    GapClose(i, (GapPos > 0 ? Math.Min(o, GapStop) : Math.Max(o, GapStop)) - GapPos * slip, "Gap stop");
            }

            if (pendingKind != 0)  // market orders from the last bar fill at this bar's open
            {
                int kind = pendingKind, d = pendingDir;
                pendingKind = 0;
                if (kind == 3 && Position != 0)
                    Close(i, o - Position * slip, "16:00 close");
                else if (kind == 1 && Position == 0)
                    Open(i, o, d);
            }

            if (Position != 0 && !double.IsNaN(Upper))  // the resting stop, then the take-profit
            {
                int p = Position;
                double line = LineStop(p);
                string reason = "Back inside";
                double basePx = EntryBar != i ? EntryPrice : estPx;
                double cap = basePx - p * mlTrade / qTrade / s.PointValue;
                if ((p > 0 && cap > line) || (p < 0 && cap < line)) { line = cap; reason = "Max loss"; }
                if (Locked)
                {
                    double lk = EntryPrice + p * s.LockPlus;
                    if ((p > 0 && lk > line) || (p < 0 && lk < line)) { line = lk; reason = "Lock"; }
                }
                if (EntryBar == i) { line = EntryPrice - p * brStopTrade; reason = brWhyTrade; }  // the bracket
                else line = OnGrid(p, line);
                if (s.TightenOnly)
                {
                    if (EntryBar != i && ((p > 0 && held > line) || (p < 0 && held < line))) { line = held; reason = heldWhy; }
                    held = line;
                    heldWhy = reason;
                }
                bool hit;
                double price;
                if (EntryBar != i && p * (lastBarClose - line) <= 0)
                {
                    hit = true; price = o - p * slip; reason = "Stop passed";  // sent at the last close, filled now
                }
                else if (EntryBar == i)
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = (p > 0 ? Math.Min(o, line) : Math.Max(o, line)) - p * slip;
                }
                else if ((p > 0 && o <= line) || (p < 0 && o >= line))
                {
                    hit = true; price = o - p * slip;
                }
                else
                {
                    hit = p > 0 ? l <= line : h >= line;
                    price = line - p * slip;
                }
                if (s.TimeStop > 0 && !Locked && EntryBar != i && (i - EntryBar) * minutes >= s.TimeStop
                    && p * (lastBarClose - EntryPrice) < 0)
                {
                    hit = true; price = o - p * slip; reason = "Time stop";  // sent at the last close, filled now
                }
                if (hit)
                    Close(i, price, reason);
                else if (s.TakeProfit > 0)
                {
                    double tp = EntryBar == i ? EntryPrice + p * brTpTrade
                                              : OnGrid(p, EntryPrice * (1 + p * s.TakeProfit * Sigma));
                    if ((p > 0 && h >= tp + s.Tick) || (p < 0 && l <= tp - s.Tick))
                        Close(i, tp, "Target");
                }
            }

            if (Position != 0 && !Locked && s.LockAt > 0 && s.MaxLoss > 0)  // the lock arms from the next bar
            {
                double trigger = s.LockAt * mlTrade / qTrade / s.PointValue;
                double x = Position > 0 ? h : l;
                fav = double.IsNaN(fav) ? x : (Position > 0 ? Math.Max(fav, x) : Math.Min(fav, x));
                Locked = Position * (fav - EntryPrice) >= trigger;
            }

            if (Position != 0 && (!inRth || tMin == RthOpen))  // a session that ended early
                Close(i, c - Position * slip, "Session ended");

            if (tMin == RthOpen)
            {
                blockDir = 0;
                DayPnl = 0;
                if (s.TrailDD > 0 && string.CompareOrdinal(nyStart.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), s.TrailFrom ?? "") >= 0)
                {
                    if (double.IsNaN(trailBase)) trailBase = trailPeak = EqEff;  // yesterday's end-of-day equity
                    trailPeak = Math.Max(trailPeak, EqEff);
                    sprintSessions++;  // G103
                }
                if (s.CalmK > 0 && dayRanges.Count >= s.CalmLong)
                    calm = Avg(dayRanges, s.CalmShort) < s.CalmK * Avg(dayRanges, s.CalmLong);
                if (s.TrendN > 0 && dayCloses.Count >= s.TrendN)
                {
                    double ma = Avg(dayCloses, s.TrendN), last = dayCloses[dayCloses.Count - 1];
                    trend = last > ma ? 1 : last < ma ? -1 : 0;
                }
                if (s.BigDayK > 0 && dayRanges.Count >= s.BigDayN &&
                    dayRanges[dayRanges.Count - 1] > s.BigDayK * Avg(dayRanges, s.BigDayN))
                    blockDir = dayDirs[dayDirs.Count - 1];
                dayHi = dayLo = double.NaN;
                prevClose = lastRthClose;
                dayOpen = o;
                Upper = Lower = Sigma = double.NaN;
                today = NewToday();
                SkipToday = InList(s.SkipDates, nyStart);
                FedToday = s.FedNoShorts && InList(s.FedDates, nyStart);
            }
            if (inRth)
            {
                lastRthClose = c;
                dayHi = double.IsNaN(dayHi) ? h : Math.Max(dayHi, h);
                dayLo = double.IsNaN(dayLo) ? l : Math.Min(dayLo, l);
            }

            if (s.GapGo && tMin == RthOpen && minutes == 5 && !double.IsNaN(prevClose) && !double.IsNaN(dayOpen))
                GapSignal(c);
            if (s.GapGo && GapPos != 0 && end == s.GapGoExit)
            {
                GapExitNow = true;  // a market exit at this close, filled at the exit bar's open
                gapExitPending = true;
            }

            if (inRth && !double.IsNaN(dayOpen) && end >= FirstCheck && end <= LastCheck && (end - FirstCheck) % Step == 0)
            {
                int k = (end - FirstCheck) / Step;
                today[k] = Math.Abs(c / dayOpen - 1);
                Note = "not ready";
                if (filled >= s.Lookback && !double.IsNaN(prevClose))
                {
                    double sum = 0.0;
                    for (int d = 0; d < s.Lookback; d++)  // same summation order as the Python and Pine loops
                        sum += ring[d * NChecks + k];
                    Sigma = sum / s.Lookback;
                    Upper = Math.Max(dayOpen, prevClose) * (1 + Sigma);
                    Lower = Math.Min(dayOpen, prevClose) * (1 - Sigma);
                    bool shortOk = !(FedToday && end < FedCutoff);
                    int dir = 0;
                    Note = c > Upper || c < Lower ? "" : "inside the noise area";
                    if (SkipToday) Note = "holiday / half day";
                    else if (Position != 0) Note = "in a trade";
                    else if (c > Upper && StudyOk(1, end, c)) dir = 1;
                    else if (c < Lower && !shortOk) Note = "Fed day: no shorts before 14:00";
                    else if (c < Lower && StudyOk(-1, end, c)) dir = -1;
                    if (dir != 0)
                        Entry(dir, c);
                }
            }

            if (inRth && end == RthClose)
            {
                if (Position != 0)
                {
                    pendingKind = 3;
                    FlatNow = true;
                }
                if (!double.IsNaN(dayOpen) && !double.IsNaN(dayHi))
                {
                    dayRanges.Add((dayHi - dayLo) / dayOpen);
                    dayDirs.Add(c > dayOpen ? 1 : c < dayOpen ? -1 : 0);
                    dayCloses.Add(c);
                }
                bool complete = !double.IsNaN(dayOpen);
                for (int k = 0; k < NChecks && complete; k++)
                    complete = !double.IsNaN(today[k]);
                if (complete)
                {
                    Array.Copy(today, 0, ring, slot * NChecks, NChecks);
                    slot = (slot + 1) % s.Lookback;
                    filled++;
                }
                dayOpen = double.NaN;
            }
            lastBarClose = c;
            TimeStopNow = s.TimeStop > 0 && Position != 0 && !Locked && (i + 1 - EntryBar) * minutes >= s.TimeStop
                          && Position * (c - EntryPrice) < 0 && !FlatNow;
        }

        // What a new trade may risk: the rest of today's loss limit and the room above the trailing floor
        double MoneyRoom()
        {
            double room = double.PositiveInfinity;
            if (s.DailyLoss > 0)
                room = s.DailyLoss + DayEff;
            if (s.TrailDD > 0 && !double.IsNaN(trailPeak))
            {
                double floor = Math.Min(trailPeak - s.TrailDD, trailBase);  // it stops at the starting balance
                room = Math.Min(room, EqEff - floor);
            }
            if (!double.IsNaN(ExtRoom))
                room = Math.Min(room, ExtRoom);
            return room;
        }

        public double TrailFloorRoom { get { return s.TrailDD > 0 && !double.IsNaN(trailPeak) ? EqEff - Math.Min(trailPeak - s.TrailDD, trailBase) : double.NaN; } }

        void Entry(int d, double c)
        {
            int q = s.Qty;
            bool afterLoss = consec > 0;
            double alMl = s.AfterLossMaxLoss;
            if (s.AfterLossLockedMaxLoss > 0 && minutes == 5 && s.TrailDD > 0 && !double.IsNaN(trailPeak)
                && trailPeak - s.TrailDD >= trailBase) alMl = s.AfterLossLockedMaxLoss;  // G119 (tested on 5-minute bars)
            double ml = afterLoss && alMl > 0 ? alMl : s.MaxLoss;
            if (s.ProfitStep > 0 && !double.IsNaN(trailBase) && StepsOk)  // a contract more per step of profit
            {
                int qUp = q + NSteps();
                if (s.MaxContracts > 0) qUp = Math.Min(qUp, s.MaxContracts);
                ml = ml / q * qUp;
                q = qUp;
            }
            if (SprintOn())  // G103: the sprint's size (the day's and the floor's room still cut it below)
            {
                ml = ml / q * s.SprintQty;
                q = s.SprintQty;
            }
            if (s.MoreDays && s.TrendN > 0 && d < 0 && trend == 1)  // G72: a fill-in short in the uptrend at its max loss a contract
            {
                int fq = FillQ();  // G97: 1 MNQ, or 2 well above the floor
                ml = ml / q * fq;
                q = fq;
            }
            if (Braked())  // G99: the giveback brake, 1 MNQ at its max loss a contract
            {
                ml = ml / q;
                q = 1;
            }
            if ((s.DailyLoss > 0 || s.TrailDD > 0) && ml > 0)  // the loss budget
            {
                double costs = 2 * s.CommissionPerSide + 2 * slip * s.PointValue;
                double extra = minutes == 5 ? s.SizeSlipPts * s.PointValue : 0.0;  // G79: tested on 5-minute bars
                double perC = ml / q + costs + extra;
                if (s.SizeByOwnStop)  // a contract's risk is its initial stop: the line's or the max loss
                {
                    double pts = Math.Min(Math.Abs(c + d * slip - LineStop(d)), ml / q / s.PointValue);
                    perC = pts * s.PointValue + costs + extra;
                }
                double room = MoneyRoom();
                int fit = double.IsInfinity(room) ? q : (int)Math.Floor(room / perC + 1e-9);
                if (fit < 1 && s.SqueezeMin > 0 && !double.IsInfinity(room) && room - costs >= s.SqueezeMin * s.PointValue)
                {
                    fit = 1; q = 1; ml = room - costs;  // 1 contract, the stop cut to the room left
                }
                if (fit < 1) { Note = "today's loss budget is used up"; return; }
                if (fit < q) { ml = ml / q * fit; q = fit; }
            }
            Note = d > 0 ? "BUY" : "SELL";
            pendingKind = 1;
            pendingDir = d;
            qNext = q;
            mlNext = ml;
            estPx = c + d * slip;
            double stop = LineStop(d), atLine = stop;
            double cap = estPx - d * ml / q / s.PointValue;
            stop = d > 0 ? Math.Max(stop, cap) : Math.Min(stop, cap);
            double tp = s.TakeProfit > 0 ? estPx * (1 + d * s.TakeProfit * Sigma) : double.NaN;
            brStopNext = TicksDown(d * (estPx - stop));
            brTpNext = TicksUp(d * (tp - estPx));
            brWhyNext = stop != atLine ? "Max loss" : "Back inside";
            NewEntry = d;
            NewQty = q;
            NewStopPts = brStopNext;
            NewTpPts = brTpNext;
        }

        // G60: at the 09:30 bar's close, gap and go's signal for the 09:35 open (5-minute bars only)
        void GapSignal(double c)
        {
            double gap = dayOpen - prevClose;
            if (gapHist.Count >= 10 && gap != 0 && !SkipToday && Position == 0 && GapPos == 0 && !Protected())
            {
                int n = Math.Min(14, gapHist.Count);
                double avg = 0.0;
                for (int k = gapHist.Count - n; k < gapHist.Count; k++)
                    avg += gapHist[k];
                avg /= n;
                int d = gap > 0 ? 1 : -1;
                double body = c - dayOpen;
                bool fire = Math.Abs(gap) >= s.GapGoK * avg && d * body > 0, one = false;
                if (!fire && s.MoreDays && Math.Abs(gap) >= s.FillSmallK * avg && d * body > 0 && FillOk())
                    fire = one = true;  // G72: a small gap
                if (!fire && s.MoreDays && driveHist.Count >= 10 && body != 0 && FillOk())
                {
                    int nb = Math.Min(14, driveHist.Count);
                    double bavg = 0.0;
                    for (int k = driveHist.Count - nb; k < driveHist.Count; k++)
                        bavg += driveHist[k];
                    bavg /= nb;
                    if (Math.Abs(body) >= s.FillDriveK * bavg) { d = body > 0 ? 1 : -1; fire = one = true; }  // a drive
                }
                if (fire)
                {
                    int q = s.Qty;
                    if (s.ProfitStep > 0 && !double.IsNaN(trailBase))
                    {
                        q += NSteps();
                        if (s.MaxContracts > 0) q = Math.Min(q, s.MaxContracts);
                    }
                    double perC = Math.Abs(c + d * slip - dayOpen) * s.PointValue + 2 * s.CommissionPerSide + 2 * slip * s.PointValue;
                    double room = MoneyRoom();
                    int fitQ = double.IsInfinity(room) ? int.MaxValue : (int)Math.Floor(room / perC + 1e-9);
                    q = Math.Min(q, fitQ);
                    bool floorStopped = !double.IsNaN(trailPeak) && trailPeak - s.TrailDD >= trailBase;
                    if (s.GapGoLockedQty > 0 && floorStopped)
                    {
                        q = Math.Min(q, s.GapGoLockedQty);
                        if (Braked()) q = Math.Min(q, 1);  // G99
                    }
                    else if (s.GapGoMaxQty > 0)
                        q = Math.Min(q, s.GapGoMaxQty);
                    if (one)
                        q = Math.Min(q, FillQ());
                    if (SprintOn() && !one)  // G103: the sprint's size, as the room allows
                        q = Math.Min(s.SprintQty, fitQ);
                    if (q >= 1)
                    {
                        gapPending = true; gapPendingDir = d; gapPendingQty = q; gapPendingStop = dayOpen;
                        GapNewEntry = d; GapNewQty = q; GapNewStop = dayOpen;
                    }
                }
            }
            gapHist.Add(Math.Abs(gap));
            driveHist.Add(Math.Abs(c - dayOpen));
        }

        static double Avg(List<double> x, int n)
        {
            double sum = 0.0;
            for (int k = x.Count - n; k < x.Count; k++)
                sum += x[k];
            return sum / n;
        }
    }

    public class MnqNoiseV38 : Strategy
    {
        const string LongName = "Long", ShortName = "Short", GapLongName = "GapLong", GapShortName = "GapShort";
        const string SkipDefault =
            "2025-01-01,2025-01-09,2025-01-20,2025-02-17,2025-04-18,2025-05-26,2025-06-19,2025-07-03,2025-07-04,2025-09-01," +
            "2025-11-27,2025-11-28,2025-12-24,2025-12-25," +
            "2026-01-01,2026-01-19,2026-02-16,2026-04-03,2026-05-25,2026-06-19,2026-07-03,2026-09-07," +
            "2026-11-26,2026-11-27,2026-12-24,2026-12-25,2027-01-01,2027-01-18,2027-02-15,2027-03-26," +
            "2027-05-31,2027-06-18,2027-07-05,2027-09-06,2027-11-25,2027-11-26,2027-12-24";
        const string FedDefault =
            "2025-01-29,2025-03-19,2025-05-07,2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10," +
            "2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29,2026-09-16,2026-10-28,2026-12-09," +
            "2027-01-27,2027-03-17,2027-04-28,2027-06-09,2027-07-28,2027-09-15,2027-10-27,2027-12-08";
        V38Engine engine;
        V38Engine shadow;  // G87: the 1-contract paper record behind the near-floor gate
        double propHigh = double.NaN;  // live: the prop account's highest end-of-day balance, for its trailing floor
        readonly List<double> shadowEod = new List<double>();
        int shadowSessions;
        TimeZoneInfo newYork;
        int minutes;
        bool badChart;
        readonly List<string> setupWarnings = new List<string>();  // the startup check's findings, for the dashboard
        int nTrades;
        string firstBar = "";
        int journaled;                   // the account's closed trades already written to the journal
        double realDayStart;
        int realDayTrades;
        bool guardTripped;  // the loss guard closed out today: no new entries until tomorrow
        // progress, from the account's own fills: this week's and this month's P/L, the closed trades and winners, and
        // the first session the bot could trade (for the pace to the goal)
        string weekKey = "", monthKey = "";
        double weekStart, monthStart;
        int realTrades, realWins;
        int weekTrades, weekWins;  // U14: this week's closed trades and winners
        // U17: the data check: sessions (09:30-16:00, not on the no-trade list) and those with bars missing
        string dqDay = "", dqFirstThin = "";
        int dqBars, dqSessions, dqThin, dqBeforeStart;
        DateTime paceFrom = DateTime.MinValue, lastSession = DateTime.MinValue;
        // fill quality: the price each order was planned at (the close when the entry or a market exit was sent, the
        // resting stop), and the running ticks paid worse than that
        double entryRef = double.NaN, exitRef = double.NaN, stopRef = double.NaN, entryStopPts = double.NaN;
        double entrySlipSum, exitSlipSum;
        int entrySlipN, exitSlipN;
        int realDayWins;          // today's winners, for the day's summary
        string summaryDay = "";   // the session the day's summary was sent for
        bool winWarned;           // U13: the win-rate warning alerted
        bool goalDone;            // U8: the goal alerted or already reached when the strategy went live
        bool slipWarned;          // G158: the fill-quality alert, once
        int milestoneDone;        // U8: the last milestone (multiples of MilestoneStep since the start) alerted or passed
        string realDay = "";
        string journalPath = "", liveJournalPath = "";
        double net, peak, maxDd, worstDay, dayNet;
        DateTime lastDay = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqNoiseV38";
                Description = "MNQ Noise-Area Momentum v3.8, Funded growth: 1 MNQ to start, $187.50 max loss a contract ($250 after a loser), $900 a day, a $2,000 end-of-day trailing floor, a contract more per $1,500 of profit up to 20, the 60-minute time stop; gap and go at 1 MNQ, up to 10 once the trailing floor has stopped at the start; More trading days (fill-in trades once $3,000 above the stopped floor: 1 MNQ, 2 from $6,000); sizing with 4 points more stop slippage.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                Contracts = 1;
                MaxLoss = 187.5;   // U18: the defaults are Funded growth's (the default Mode), so the panel shows what it uses
                DailyLoss = 900;
                TakeProfit = 2.0;
                LockAt = 0.35;
                LockPlus = 2.5;
                StopBuffer = 0.24;
                SqueezeMin = 20;
                LastEntry = "15:00";
                BigDayK = 1.5;
                CalmK = 0.7;
                RangePos = 0.65;
                TrendSessions = 50;
                FedNoShorts = true;
                SkipDates = SkipDefault;
                FedDates = FedDefault;
                PlaceOrders = true;
                Mode = "Funded growth";
                Goal = 50000;
                AfterLossMaxLoss = 187.5;  // G168 (Funded growth sets it by the chart: 187.5 on 5-minute, 250 otherwise)
                TrailDD = 2000;
                TrailFrom = "";
                ProfitStep = 1500;
                MaxContracts = 20;  // G106
                SizeByOwnStop = true;
                TimeStop = 60;
                StepsAfterLock = false;
                LossGuard = 950;
                AlertsOn = true;
                SoundAlerts = true;
                MilestoneStep = 5000;
                GapGo = true;
                GapGoLocked = 10;  // G84 (G67b: 3, G80: 5, G82: 7; G83's 15 broke the daily limit once)
                MoreDays = true;  // G79: on by default (with SizeSlip 2)
                MoreDaysCushion = 3000;
                SizeSlip = 5;  // G170 (G79: 2, G97: 3, G106: 4)
                MoreDaysQty2Room = 6000;  // G97
                GivebackBrake = 0.5;  // G99c
                AfterLossLocked = 187.5;  // G119
                EarlyNoEntryChecks = "13:00,14:30";  // G125
                FastSteps = 750;  // G142
                FastStepsFrom = 10000;
                PropStartBalance = 50000;
                PropHighBalance = 0;
                SizeToAccountRoom = true;
                SprintContracts = 0;  // G103: off
                NearFloorGate = 0;  // G87b: off (it lost more accounts)
                TestedWinRate = 61.2;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                minutes = BarsPeriod.Value;
                badChart = BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || minutes <= 0 || 30 % minutes != 0;
                setupWarnings.Clear();
                // the mode, whatever its case or spaces: a typo would otherwise run Custom's settings unnoticed
                string m = (Mode ?? "").Trim();
                string mc = System.Text.RegularExpressions.Regex.Replace(m, @"\s+", " ");
                if (string.Equals(mc, "Funded growth", StringComparison.OrdinalIgnoreCase)) Mode = "Funded growth";
                else if (string.Equals(mc, "Funded growth 100K", StringComparison.OrdinalIgnoreCase)) Mode = "Funded growth 100K";
                else if (string.Equals(mc, "Funded growth 150K", StringComparison.OrdinalIgnoreCase)) Mode = "Funded growth 150K";
                else if (string.Equals(mc, "Funded growth Apex 100K", StringComparison.OrdinalIgnoreCase)) Mode = "Funded growth Apex 100K";
                else if (string.Equals(mc, "Funded growth Apex 150K", StringComparison.OrdinalIgnoreCase)) Mode = "Funded growth Apex 150K";
                else if (string.Equals(m, "Evaluation", StringComparison.OrdinalIgnoreCase)) Mode = "Evaluation";
                else if (string.Equals(m, "Custom", StringComparison.OrdinalIgnoreCase)) Mode = "Custom";
                else
                {
                    setupWarnings.Add("Mode \"" + Mode + "\" isn't Funded growth (50K, 100K, 150K, Apex 100K or Apex 150K), Evaluation or Custom: running the settings below as Custom");
                    Mode = "Custom";
                }
                if (Mode.StartsWith("Funded growth"))  // the tested growth settings (docs/NINJATRADER_V38.md), whatever is set below
                {
                    Contracts = 1; MaxLoss = 187.5; DailyLoss = 900; TrailDD = 2000;
                    AfterLossMaxLoss = minutes == 5 ? 187.5 : 250;  // G168: as every trade on the 5-minute chart (G167 1.1x, G165 1.2x, 1.33x before)
                    ProfitStep = 1500; SizeByOwnStop = true; TimeStop = 60;
                    MaxContracts = Mode == "Funded growth" && minutes == 5 ? 50 : 15;  // G121: 50 on the 50K's 5-minute chart (G106: 20, G120: 30)
                    // G40: a bigger account trades the 50K's size; its larger limits are cushion (a $2,000 / $3,000
                    // daily loss and a $3,000 / $4,500 trailing drawdown; the bot's budget is 90% of the daily loss)
                    if (Mode == "Funded growth 100K") { DailyLoss = 1800; TrailDD = 3000; LossGuard = 1900; }
                    if (Mode == "Funded growth 150K") { DailyLoss = 2700; TrailDD = 4500; LossGuard = 2850; }
                    // G42: Apex's end-of-day accounts, a tighter day: a $1,500 / $2,000 daily loss, a $3,000 / $4,000 trail
                    if (Mode == "Funded growth Apex 100K") { DailyLoss = 1350; TrailDD = 3000; LossGuard = 1425; }
                    if (Mode == "Funded growth Apex 150K") { DailyLoss = 1800; TrailDD = 4000; LossGuard = 1900; }
                }
                else if (Mode == "Evaluation")  // v3.8: 1 MNQ, $260 a trade, $900 a day
                {
                    Contracts = 1; MaxLoss = 260; AfterLossMaxLoss = 0; DailyLoss = 900; TrailDD = 0;
                    ProfitStep = 0; SizeByOwnStop = false; TimeStop = 0;
                }
                V38Settings st = new V38Settings();
                st.Qty = Contracts; st.MaxLoss = MaxLoss; st.DailyLoss = DailyLoss; st.TakeProfit = TakeProfit;
                st.LockAt = LockAt; st.LockPlus = LockPlus; st.StopBuffer = StopBuffer; st.SqueezeMin = SqueezeMin;
                st.LastEntryEnd = LastEntry == "15:30" ? 930 : 900;
                st.BigDayK = BigDayK; st.CalmK = CalmK; st.RangePosMin = RangePos; st.TrendN = TrendSessions;
                st.FedNoShorts = FedNoShorts; st.SkipDates = SkipDates; st.FedDates = FedDates;
                st.AfterLossMaxLoss = AfterLossMaxLoss; st.TrailDD = TrailDD; st.TrailFrom = TrailFrom ?? "";
                st.ProfitStep = ProfitStep; st.MaxContracts = MaxContracts; st.SizeByOwnStop = SizeByOwnStop;
                st.TimeStop = TimeStop;
                st.StepsAfterLock = StepsAfterLock;
                st.GapGo = GapGo && Mode != "Evaluation";  // G60: on in the Funded growth modes (and Custom, as set)
                st.GapGoLockedQty = GapGoLocked;  // G67
                st.MoreDays = MoreDays && st.GapGo;  // G72: the fill-in trades (5-minute chart, not in Evaluation)
                st.FillMinRoom = MoreDaysCushion;
                st.FillQty2Room = MoreDaysQty2Room;  // G97
                st.GivebackBrake = Mode != "Evaluation" ? GivebackBrake : 0;  // G99
                st.AfterLossLockedMaxLoss = Mode != "Evaluation" ? AfterLossLocked : 0;  // G119
                st.EarlySkipChecks = Mode != "Evaluation" ? CheckEnds(EarlyNoEntryChecks) : "";  // G125
                st.ProfitStepFast = Mode != "Evaluation" ? FastSteps : 0;  // G142
                st.ProfitStepFastFrom = FastStepsFrom;
                st.SprintQty = Mode != "Evaluation" ? SprintContracts : 0;  // G103
                st.SizeSlipPts = Mode != "Evaluation" ? SizeSlip : 0;  // G79: the Funded growth modes and Custom
                st.ProtectRoom = Mode != "Evaluation" ? NearFloorGate : 0;  // G87
                st.Tick = TickSize;
                st.PointValue = Instrument.MasterInstrument.PointValue;
                if (!badChart)
                    engine = new V38Engine(st, minutes);
                if (!badChart && st.ProtectRoom > 0 && st.TrailDD > 0 && minutes == 5)  // G87, tested on 5-minute bars
                {
                    V38Settings sh = st.Clone();
                    sh.ProfitStep = 0; sh.Qty = 1; sh.TrailDD = 0; sh.GapGoLockedQty = 0; sh.GapGoMaxQty = 1;
                    sh.MoreDays = false; sh.ProtectRoom = 0;
                    shadow = new V38Engine(sh, minutes);
                }
                // the journal: every closed trade from the account's own fills, and a line per day. A backtest's goes to
                // MnqNoiseV38_backtest.csv (written anew each run); live trades are also added to
                // MnqNoiseV38_live_<account>.csv, kept across restarts. Both in Documents\NinjaTrader 8.
                try
                {
                    string dir = NinjaTrader.Core.Globals.UserDataDir;
                    journalPath = Path.Combine(dir, "MnqNoiseV38_backtest.csv");
                    liveJournalPath = Path.Combine(dir, "MnqNoiseV38_live_" + Safe(Account == null ? "none" : Account.Name) + ".csv");
                    File.WriteAllText(journalPath, JournalHeader);
                    if (File.Exists(liveJournalPath) && File.ReadAllText(liveJournalPath).Split('\n')[0] + "\n" != JournalHeader)
                        File.Move(liveJournalPath, liveJournalPath.Replace(".csv", "_until_" + DateTime.Now.ToString("yyyyMMdd_HHmmss", CultureInfo.InvariantCulture) + ".csv"));
                    if (!File.Exists(liveJournalPath))
                        File.WriteAllText(liveJournalPath, JournalHeader);
                }
                catch (Exception e)
                {
                    journalPath = liveJournalPath = "";
                    Print("MnqNoiseV38: the journal can't be written (" + e.Message + ")");
                }
                if (badChart)
                    setupWarnings.Add("the chart is " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType + ": use a 5- or 30-minute chart");
                if (!Instrument.FullName.StartsWith("MNQ", StringComparison.OrdinalIgnoreCase))
                    setupWarnings.Add("the instrument is " + Instrument.FullName + ": the bot was built and tested on MNQ");
                if (Bars != null && Bars.TradingHours != null && Bars.TradingHours.ToString().IndexOf("ETH", StringComparison.OrdinalIgnoreCase) < 0)
                    setupWarnings.Add("trading hours are \"" + Bars.TradingHours + "\": use CME US Index Futures ETH so the 16:00 exit fills at 16:00");
                if (LossGuard > 0 && DailyLoss > 0 && LossGuard < DailyLoss)
                    setupWarnings.Add("the loss guard ($" + LossGuard + ") is below the daily budget ($" + DailyLoss + "): it will cut trades the budget allows");
                if (LossGuard <= 0 || (DailyLoss > 0 && LossGuard > DailyLoss / 0.9))
                    setupWarnings.Add("the loss guard is " + (LossGuard <= 0 ? "off" : "$" + LossGuard + ", past the account's daily loss rule") +
                                      ": the daily rule has no live backstop");
                foreach (string w in setupWarnings)
                    Print("MnqNoiseV38 WARNING: " + w);
                Print("MnqNoiseV38 (" + Mode + "): " + Instrument.FullName + ", " + minutes + " " + BarsPeriod.BarsPeriodType + ", " + Contracts +
                      " MNQ, max loss $" + MaxLoss + " a trade, $" + DailyLoss + " a day, take-profit " + TakeProfit +
                      (badChart ? "  -- use a minute chart whose length divides 30 (5 or 30)" : ""));
            }
            else if (State == State.Realtime)
            {
                // U16: live with a trailing drawdown counted from the chart's first bar, the chart's history (the model's
                // backtest there) counts as the account's profit: the steps and the floor's room would start too high
                if (TrailDD > 0 && string.IsNullOrWhiteSpace(TrailFrom))
                {
                    string w = "\"Trailing drawdown and contract steps from date\" is blank: set it to the account's first trading day " +
                               "(yyyy-MM-dd). Blank counts the chart's history as the account's profit, so the first trades would be too big";
                    setupWarnings.Add(w);
                    Print("MnqNoiseV38 WARNING: " + w);
                }
                string dqw = DataWarning();
                if (dqw.Length > 0)
                {
                    setupWarnings.Add(dqw);
                    Print("MnqNoiseV38 WARNING: " + dqw);
                }
                if (PropStartBalance > 0 && TrailDD > 0 && Account != null)  // the prop account's floor from its own balance
                {
                    double bal = Math.Max(0, Account.Get(AccountItem.CashValue, Currency.UsDollar));
                    propHigh = Math.Max(Math.Max(PropStartBalance, PropHighBalance), bal);
                    Print("MnqNoiseV38: live on " + Account.Name + ", balance $" + bal.ToString("0.00", CultureInfo.InvariantCulture) +
                          ", prop floor $" + PropFloor().ToString("0.00", CultureInfo.InvariantCulture));
                }
                foreach (string w in setupWarnings)  // once, as the strategy goes live
                    Say("setup", "SETUP WARNING: " + w);
                milestoneDone = MilestoneStep > 0 ? (int)Math.Floor(Math.Max(0, SinceStart()) / MilestoneStep) : 0;
                goalDone = Goal > 0 && SinceStart() >= Goal;
            }
            else if (State == State.Terminated && engine != null)
            {
                FinishDataDay();
                dqDay = "";
                string dq = DataWarning();
                if (dq.Length > 0)
                    Print("MnqNoiseV38 WARNING: " + dq);
                if (realDay.Length > 0)
                    JournalDay(SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit);
                realDay = "";
                Print("MnqNoiseV38 done: data from " + firstBar + ", " + nTrades + " trades, net $" + net.ToString("0.00", CultureInfo.InvariantCulture) +
                      ", closed drawdown $" + maxDd.ToString("0.00", CultureInfo.InvariantCulture) +
                      ", worst day $" + worstDay.ToString("0.00", CultureInfo.InvariantCulture) +
                      (journalPath.Length > 0 ? ", journal " + journalPath : ""));
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || badChart || engine == null)
                return;
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            DateTime endNy = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified), platform, newYork);
            DateTime start = endNy.AddMinutes(-minutes);
            if (firstBar.Length == 0)
                firstBar = start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            int tMinDq = start.Hour * 60 + start.Minute;
            if (tMinDq >= V38Engine.RthOpen && tMinDq < V38Engine.RthClose)
            {
                string d = start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                if (d != dqDay) { FinishDataDay(); dqDay = d; dqBars = 0; }
                dqBars++;
            }
            // the account's own numbers for the risk limits: its closed P/L, and today's from the 09:30 bar
            double cum = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
            int tMin = start.Hour * 60 + start.Minute;
            // trades closed since the last bar first: at 09:30 they are the day before's (a 16:00 exit filled at this
            // open on a chart without a 16:00 bar), so they go into that day's line
            WriteTrades(platform);
            if (tMin == V38Engine.RthOpen)
            {
                if (realDay.Length > 0)
                    JournalDay(cum);
                realDay = start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                realDayStart = cum;
                realDayTrades = 0;
                realDayWins = 0;
                guardTripped = false;
                string wk = start.Date.AddDays(-(((int)start.DayOfWeek + 6) % 7)).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                string mo = start.ToString("yyyy-MM", CultureInfo.InvariantCulture);
                if (wk != weekKey) { weekKey = wk; weekStart = cum; weekTrades = 0; weekWins = 0; }
                if (mo != monthKey) { monthKey = mo; monthStart = cum; }
                if (paceFrom == DateTime.MinValue && engine.Ready) paceFrom = start.Date;
                lastSession = start.Date;
            }
            engine.ExtEquity = cum;  // before the day's summary: its milestone counts the fills up to this bar
            engine.ExtDayPnl = cum - realDayStart;
            if (tMin >= V38Engine.RthClose)
                DaySummary(cum);
            int before = engine.Trades.Count;
            // live: never more risk than the prop account's own room (only once the account reports a balance; a connection
            // that reports 0 is not used, so it can't block the trades)
            engine.ExtRoom = State == State.Realtime && SizeToAccountRoom && !double.IsNaN(propHigh) && AccountValuesOk()
                             ? PropRoom() : double.NaN;
            if (shadow != null)  // G87: the shadow first; at a session's first bar, the gate from the last session's close
            {
                if (tMin == V38Engine.RthOpen)
                {
                    if (shadowSessions > 0)
                        shadowEod.Add(shadow.Equity);
                    shadowSessions++;
                    int n = engine.ProtectNSessions;
                    bool closed = false;
                    if (shadowEod.Count >= n)
                    {
                        double avg = 0.0;
                        for (int k = shadowEod.Count - n; k < shadowEod.Count; k++)
                            avg += shadowEod[k];
                        closed = shadowEod[shadowEod.Count - 1] < avg / n;
                    }
                    engine.ProtectClosed = closed;
                }
                shadow.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            }
            engine.OnBar(start, Open[0], High[0], Low[0], Close[0]);
            for (int k = before; k < engine.Trades.Count; k++)
                Tally(start, engine.Trades[k].Pnl);
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            CheckLossGuard(Close[0]);
            if (guardTripped && real != 0)
            {
                Flatten(real, "Loss guard");  // again, in case the first exit didn't fill
                Dashboard(endNy);
                return;
            }

            if (real != 0 && engine.FlatNow)
            {
                Flatten(real, "Flat 16:00");
            }
            else if (real != 0 && engine.Position == real && engine.TimeStopNow)
            {
                Flatten(real, "Time stop");  // still losing this long after the fill: out at the next open
                Say("timestop", "Time stop: the trade is still losing " + engine.MinutesInTrade + " min after its fill, closing at market");
            }
            else if (real != 0 && engine.GapPos == real && engine.GapExitNow)
            {
                exitRef = Close[0];
                if (real > 0) ExitLong("Gap exit", GapLongName);
                else ExitShort("Gap exit", GapShortName);
            }
            else if (real == 0 && engine.GapNewEntry != 0 && PlaceOrders && !guardTripped)
            {
                // G60: gap and go, a market entry with its stop at the 09:30 open attached first
                string name = engine.GapNewEntry > 0 ? GapLongName : GapShortName;
                SetStopLoss(name, CalculationMode.Price, engine.GapNewStop, false);
                if (engine.GapNewEntry > 0) EnterLong(engine.GapNewQty, name);
                else EnterShort(engine.GapNewQty, name);
                entryRef = Close[0];
                stopRef = engine.GapNewStop;
                entryStopPts = Math.Abs(Close[0] - engine.GapNewStop);
                Say("entry", (engine.GapNewEntry > 0 ? "BUY " : "SELL ") + engine.GapNewQty + " MNQ at market (gap and go), stop " +
                    engine.GapNewStop.ToString("0.00", CultureInfo.InvariantCulture) + ", out at 09:55");
            }
            else if (real == 0 && engine.NewEntry != 0 && PlaceOrders && !guardTripped)
            {
                // the bracket first, in ticks from the fill, so it is attached the moment the entry fills
                string name = engine.NewEntry > 0 ? LongName : ShortName;
                SetStopLoss(name, CalculationMode.Ticks, Math.Max(1, Math.Round(engine.NewStopPts / TickSize)), false);
                if (!double.IsNaN(engine.NewTpPts))
                    SetProfitTarget(name, CalculationMode.Ticks, Math.Max(1, Math.Round(engine.NewTpPts / TickSize)));
                if (engine.NewEntry > 0) EnterLong(engine.NewQty, name);
                else EnterShort(engine.NewQty, name);
                entryRef = Close[0];
                entryStopPts = Math.Max(1, Math.Round(engine.NewStopPts / TickSize)) * TickSize;
                stopRef = double.NaN;
                Say("entry", (engine.NewEntry > 0 ? "BUY " : "SELL ") + engine.NewQty + " MNQ at market (noise breakout), stop " +
                    engine.NewStopPts.ToString("0.00", CultureInfo.InvariantCulture) + " points" +
                    (double.IsNaN(engine.NewTpPts) ? "" : ", target " + engine.NewTpPts.ToString("0.00", CultureInfo.InvariantCulture) + " points"));
            }
            else if (real != 0 && engine.Position == real)
            {
                // in a trade: the stop and the take-profit for the next bar, from the real fill
                double avg = Position.AveragePrice;
                double stop = engine.PeekStop(avg);
                string name = real > 0 ? LongName : ShortName;
                if (!double.IsNaN(stop))
                {
                    double px = Close[0];
                    if (State == State.Realtime)  // live: where the stop would trigger now, so it is never sent past it
                        px = real > 0 ? Math.Min(px, GetCurrentBid()) : Math.Max(px, GetCurrentAsk());
                    if ((real > 0 && stop >= px) || (real < 0 && stop <= px))
                        Flatten(real, "Stop passed");  // a stop can't rest there: the line moved past the price
                    else
                    {
                        SetStopLoss(name, CalculationMode.Price, stop, false);
                        stopRef = stop;
                        double tp = engine.PeekTarget(avg);
                        if (!double.IsNaN(tp))
                            SetProfitTarget(name, CalculationMode.Price, tp);
                    }
                }
            }
            else if (real != 0 && engine.Position == 0 && engine.GapPos != real)
                Flatten(real, "Model flat");  // the model closed (a fill elsewhere): don't hold an unmanaged position
            WriteTrades(platform);
            Dashboard(endNy);
        }

        const string JournalHeader = "kind,entry time,exit time,side,contracts,trades today,entry,exit,exit kind,P/L,day P/L,total P/L,room today,room above floor,next contracts,entry slip ticks,exit slip ticks\n";

        // a day's line: the same 15 columns as a trade's, with the date, the day's trades, its P/L and the total
        void JournalDay(double cum)
        {
            Journal(string.Join(",", new[] { "DAY", realDay, "", "", "", realDayTrades.ToString(CultureInfo.InvariantCulture),
                                             "", "", "", "", F(cum - realDayStart), F(cum), "", F(engine.TrailFloorRoom),
                                             engine.NextQty.ToString(CultureInfo.InvariantCulture), "", "" }), false);
        }

        // the day's summary, live, once the session's 16:00 exit has filled (the first bar from 16:00 on)
        void DaySummary(double cum)
        {
            if (State != State.Realtime || summaryDay == realDay || realDay.Length == 0)
                return;
            summaryDay = realDay;
            if (!double.IsNaN(propHigh) && Account != null)  // the prop floor trails the end-of-day balance
                propHigh = Math.Max(propHigh, Account.Get(AccountItem.CashValue, Currency.UsDollar));
            double day = cum - realDayStart;
            Say("day", "Day done " + realDay + ": " + (day >= 0 ? "+$" : "-$") + Math.Abs(day).ToString("0.00", CultureInfo.InvariantCulture) +
                " in " + realDayTrades + " trades (" + realDayWins + " winners), total $" + cum.ToString("0.00", CultureInfo.InvariantCulture) +
                (double.IsNaN(engine.TrailFloorRoom) ? "" : ", room above the floor $" + engine.TrailFloorRoom.ToString("0", CultureInfo.InvariantCulture)) +
                ", tomorrow up to " + engine.NextQty + " MNQ");
            CheckMilestone();
            // U14: on Fridays, the week's summary too
            DateTime d = DateTime.ParseExact(realDay, "yyyy-MM-dd", CultureInfo.InvariantCulture);
            if (d.DayOfWeek == DayOfWeek.Friday)
            {
                double week = cum - weekStart, month = cum - monthStart;
                Say("week", "Week done (from " + weekKey + "): " + (week >= 0 ? "+$" : "-$") + Math.Abs(week).ToString("0.00", CultureInfo.InvariantCulture) +
                    " in " + weekTrades + " trades (" + weekWins + " winners); this month " + (month >= 0 ? "+$" : "-$") +
                    Math.Abs(month).ToString("0.00", CultureInfo.InvariantCulture) + ", total $" + cum.ToString("0.00", CultureInfo.InvariantCulture));
            }
        }

        // the account's profit since its start: above the trailing floor's base when there is one, else the real fills'
        double SinceStart()
        {
            double cumReal = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
            // the fills, not the model's equity: at the 16:00 bar the model books its close only after this check
            return double.IsNaN(engine.TrailBase) ? cumReal : cumReal - engine.TrailBase;
        }

        // U8: live, at a day's close, once for each new multiple of MilestoneStep of profit since the start (none for the
        // levels already passed when the strategy went live), and the goal when it is reached
        void CheckMilestone()
        {
            if (MilestoneStep <= 0 || State != State.Realtime)
                return;
            double since = SinceStart();
            int level = (int)Math.Floor(Math.Max(0, since) / MilestoneStep);
            bool goalNow = Goal > 0 && since >= Goal && !goalDone;
            if (level <= milestoneDone && !goalNow)
                return;
            milestoneDone = Math.Max(milestoneDone, level);
            goalDone = goalDone || goalNow;
            string amt = (level * MilestoneStep).ToString("0", CultureInfo.InvariantCulture);
            string room = double.IsNaN(engine.TrailFloorRoom) ? "" : "; room above the floor $" + engine.TrailFloorRoom.ToString("0", CultureInfo.InvariantCulture);
            if (goalNow)
                Say("goal", "GOAL REACHED: +$" + since.ToString("0", CultureInfo.InvariantCulture) + " since the start (goal $" +
                    Goal.ToString("0", CultureInfo.InvariantCulture) + ")" + room + ". Check your firm's payout rules before withdrawing");
            else
                Say("milestone", "Milestone: +$" + amt + " since the start" +
                    (Goal > 0 ? " (" + (100 * level * MilestoneStep / Goal).ToString("0", CultureInfo.InvariantCulture) + "% of the $" +
                     Goal.ToString("0", CultureInfo.InvariantCulture) + " goal)" : "") + room + ", next trade up to " + engine.NextQty + " MNQ");
        }

        static string F(double x) { return double.IsNaN(x) ? "" : x.ToString("0.00", CultureInfo.InvariantCulture); }

        static string Safe(string name)
        {
            foreach (char ch in Path.GetInvalidFileNameChars())
                name = name.Replace(ch, '_');
            return name.Replace(' ', '_');
        }

        void Journal(string line, bool live)
        {
            if (journalPath.Length == 0)
                return;
            try
            {
                File.AppendAllText(journalPath, line + "\n");
                if (live)
                    File.AppendAllText(liveJournalPath, line + "\n");
            }
            catch (Exception e)
            {
                Print("MnqNoiseV38: journal write failed (" + e.Message + ")");
                journalPath = "";
            }
        }

        // every newly closed trade of the account, as NinjaTrader recorded it from the fills
        void WriteTrades(TimeZoneInfo platform)
        {
            double cum = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
            while (journaled < SystemPerformance.AllTrades.Count)
            {
                Trade t = SystemPerformance.AllTrades[journaled++];
                realDayTrades++;
                realTrades++;
                weekTrades++;
                if (t.ProfitCurrency > 0) { realWins++; realDayWins++; weekWins++; }
                DateTime en = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(t.Entry.Time, DateTimeKind.Unspecified), platform, newYork);
                DateTime ex = TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(t.Exit.Time, DateTimeKind.Unspecified), platform, newYork);
                string side = t.Entry.Name == ShortName || t.Entry.Name == GapShortName ? "SHORT" : "LONG";
                int dir = side == "LONG" ? 1 : -1;
                double inSlip = double.IsNaN(entryRef) ? double.NaN : dir * (t.Entry.Price - entryRef) / TickSize;
                double outRef = t.Exit.Name == "Stop loss" ? (double.IsNaN(stopRef) ? t.Entry.Price - dir * entryStopPts : stopRef)
                              : t.Exit.Name == "Profit target" || t.Exit.Name == "Exit on session close" ? double.NaN : exitRef;
                double outSlip = double.IsNaN(outRef) ? double.NaN : dir * (outRef - t.Exit.Price) / TickSize;
                if (!double.IsNaN(inSlip)) { entrySlipSum += inSlip; entrySlipN++; }
                if (!double.IsNaN(outSlip)) { exitSlipSum += outSlip; exitSlipN++; }
                if (!slipWarned && entrySlipN >= 20)  // G158: at 3 ticks a fill the tested bot can lose a fresh account
                {
                    double avgSlip = (entrySlipSum / entrySlipN + (exitSlipN > 0 ? exitSlipSum / exitSlipN : 0.0)) / 2;
                    if (avgSlip > 2.0)
                    {
                        slipWarned = true;
                        Say("fills", "Fills are " + avgSlip.ToString("0.0", CultureInfo.InvariantCulture) + " ticks worse than plan on average (" +
                            entrySlipN + " trades); the backtests assume 1, and at 3 a fresh account can be lost. Check the connection, " +
                            "the data feed and the order type before trading on");
                    }
                }
                entryRef = exitRef = stopRef = double.NaN;
                Journal("TRADE," + en.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + "," +
                        ex.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + "," + side + "," + t.Quantity + "," +
                        realDayTrades + "," + F(t.Entry.Price) + "," + F(t.Exit.Price) + "," + t.Exit.Name + "," + F(t.ProfitCurrency) + "," +
                        F(cum - realDayStart) + "," + F(cum) + "," + F(engine.DayRoom) + "," + F(engine.TrailFloorRoom) + "," +
                        engine.NextQty + "," + F(inSlip) + "," + F(outSlip), State == State.Realtime);
                Say("exit", "Closed " + side + " " + t.Quantity + " MNQ (" + t.Exit.Name + "): " + (t.ProfitCurrency >= 0 ? "+$" : "-$") +
                    Math.Abs(t.ProfitCurrency).ToString("0.00", CultureInfo.InvariantCulture) + ", today " +
                    (cum - realDayStart).ToString("0.00", CultureInfo.InvariantCulture));
            }
        }

        // a live alert (NinjaTrader's Alerts window and, with SoundAlerts, a sound), and the Output window
        void Say(string id, string msg)
        {
            if (State != State.Realtime)
                return;
            Print("MnqNoiseV38: " + msg);
            if (AlertsOn)
                Alert("v38_" + id, Priority.High, msg, SoundAlerts ? NinjaTrader.Core.Globals.InstallDir + @"\sounds\Alert1.wav" : "",
                      0, Brushes.Black, Brushes.White);
        }

        // the loss guard (live only): today's closed P/L plus the open trade's at this price at -LossGuard or worse
        // (a gap or bad fills past the bracket) closes the position at market and stops new entries for the day
        void CheckLossGuard(double price)
        {
            if (LossGuard <= 0 || State != State.Realtime || guardTripped)
                return;
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            double today = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - realDayStart +
                           (real != 0 ? Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, price) : 0.0);
            if (today > -LossGuard)
                return;
            guardTripped = true;
            Print("MnqNoiseV38: loss guard at " + today.ToString("0.00", CultureInfo.InvariantCulture) + " today: flat, no more entries until tomorrow");
            exitRef = price;
            Say("guard", "LOSS GUARD: " + today.ToString("0.00", CultureInfo.InvariantCulture) + " today, flat and done for the day");
            if (real != 0)
                Flatten(real, "Loss guard");
        }

        protected override void OnMarketData(MarketDataEventArgs marketDataUpdate)
        {
            if (marketDataUpdate.MarketDataType == MarketDataType.Last && engine != null)
                CheckLossGuard(marketDataUpdate.Price);
        }

        void Flatten(int real, string why)
        {
            if (double.IsNaN(exitRef)) exitRef = Close[0];  // the price the exit was sent at (the guard sets its tick's)
            if (real > 0) ExitLong(why, "");
            else ExitShort(why, "");
        }

        void Tally(DateTime start, double pnl)  // the model's own results, for the Output window and the dashboard
        {
            DateTime day = start.Date;
            if (day != lastDay) { dayNet = 0; lastDay = day; }
            dayNet += pnl;
            worstDay = Math.Min(worstDay, dayNet);
            nTrades++;
            net += pnl;
            peak = Math.Max(peak, net);
            maxDd = Math.Max(maxDd, peak - net);
        }

        // live: the prop account's trailing floor (its highest end-of-day balance less the trailing drawdown, stopping at
        // the starting balance) and the room above it from the account's net liquidation
        double PropFloor()
        {
            return Math.Min(propHigh - TrailDD, PropStartBalance);
        }

        bool AccountValuesOk()
        {
            return Account != null && Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) > 0;
        }

        double PropRoom()
        {
            return Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) - PropFloor();
        }

        // the dashboard's live-account lines: the real account, the live trades, and the prop floor from the balance
        string LiveAccountLines()
        {
            if (State != State.Realtime || Account == null)
                return "Account: shows the live account once enabled on it (now: the chart's history)\n";
            double bal = Account.Get(AccountItem.CashValue, Currency.UsDollar);
            double nl = Account.Get(AccountItem.NetLiquidation, Currency.UsDollar);
            double rz = Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
            double ur = Account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
            string txt = "LIVE account " + Account.Name + ": balance $" + bal.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", net liq $" + nl.ToString("0.00", CultureInfo.InvariantCulture) + "\n" +
                         "Today on the account: realized $" + rz.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", open $" + ur.ToString("0.00", CultureInfo.InvariantCulture) + "\n" +
                         "Live trades since enabled: " + SystemPerformance.RealTimeTrades.Count + ", $" +
                         SystemPerformance.RealTimeTrades.TradesPerformance.Currency.CumProfit.ToString("0.00", CultureInfo.InvariantCulture) + "\n";
            if (!double.IsNaN(propHigh) && !AccountValuesOk())
                txt += "Prop floor: waiting for the account's balance (the connection reports none yet)\n";
            else if (!double.IsNaN(propHigh))
            {
                double room = PropRoom();
                txt += "Prop floor (from the account): $" + PropFloor().ToString("0.00", CultureInfo.InvariantCulture) +
                       ", room $" + room.ToString("0.00", CultureInfo.InvariantCulture) +
                       ", profit $" + (nl - PropStartBalance).ToString("0.00", CultureInfo.InvariantCulture) + "\n";
                if (!double.IsNaN(engine.TrailFloorRoom) && engine.TrailFloorRoom > room + 100)
                    txt += "CHECK: the strategy counts $" + engine.TrailFloorRoom.ToString("0", CultureInfo.InvariantCulture) +
                           " of room, the account has $" + room.ToString("0", CultureInfo.InvariantCulture) +
                           (SizeToAccountRoom ? " (trades are sized to the account's)" : "") + "\n";
            }
            return txt;
        }

        void Dashboard(DateTime endNy)
        {
            double cumReal = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
            double sinceStart = SinceStart();
            string goal = Goal > 0 ? "Goal $" + Goal.ToString("0", CultureInfo.InvariantCulture) + ": $" +
                          sinceStart.ToString("0", CultureInfo.InvariantCulture) + " so far (" +
                          (100 * sinceStart / Goal).ToString("0.0", CultureInfo.InvariantCulture) + "%)\n" : "";
            string txt = goal + LiveAccountLines() + "Strategy P/L (its fills, history and live): $" + cumReal.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", today $" + (cumReal - realDayStart).ToString("0.00", CultureInfo.InvariantCulture) + "\n" +
                         "Next trade: " + engine.NextQty + " MNQ, room today $" + (double.IsNaN(engine.DayRoom) ? "-" : Math.Max(0, engine.DayRoom).ToString("0", CultureInfo.InvariantCulture)) + "\n" +
                         (setupWarnings.Count > 0 ? "SETUP WARNING (" + setupWarnings.Count + "): " + setupWarnings[0] + "\n" : "Setup: OK\n") +
                         "Trades today: " + realDayTrades + "\n" +
                         TodayLine(endNy) +
                         DataLine() +
                         ProgressLines(cumReal, sinceStart) +
                         WinCheckLine() +
                         FillLine() +
                         (LossGuard > 0 ? "Loss guard: " + (guardTripped ? "TRIPPED, flat and done for today" :
                          "flat at -$" + LossGuard.ToString("0", CultureInfo.InvariantCulture) + " today, closed + open (live)") + "\n" : "") +
                         OpenTradeLine() +
                         "MNQ Noise Momentum v3.8, " + Mode + (engine.TradeQty > 0 && engine.Position != 0 ? ", " + engine.TradeQty + " MNQ" : "") + "\n" +
                         "Data from " + firstBar + " (results need data from 50 sessions before)\n" +
                         "Sessions of history: " + engine.SessionsLoaded + " / 14\n" +
                         (double.IsNaN(engine.TrailFloorRoom) ? "" : "Room above the trailing floor: $" + engine.TrailFloorRoom.ToString("0", CultureInfo.InvariantCulture) + "\n") +
                         (double.IsNaN(engine.Upper) ? "Lines: after the 10:00 check\n" :
                          "Upper / lower: " + engine.Upper.ToString("0.00", CultureInfo.InvariantCulture) + " / " +
                          engine.Lower.ToString("0.00", CultureInfo.InvariantCulture) + "\n") +
                         "Model: trades " + nTrades + ", net $" + net.ToString("0.00", CultureInfo.InvariantCulture) +
                         ", drawdown $" + maxDd.ToString("0.00", CultureInfo.InvariantCulture) + "\n" +
                         (engine.Note.Length > 0 ? "Last check: " + engine.Note : "");
            Draw.TextFixed(this, "v38_dash", txt, TextPosition.TopRight);
        }

        // progress, for the dashboard: this week and month, the real win rate, and the pace to the goal
        string ProgressLines(double cumReal, double sinceStart)
        {
            string s = "This week $" + (cumReal - weekStart).ToString("0.00", CultureInfo.InvariantCulture) +
                       ", this month $" + (cumReal - monthStart).ToString("0.00", CultureInfo.InvariantCulture) +
                       "; real fills: " + realTrades + " trades, " +
                       (realTrades > 0 ? (100.0 * realWins / realTrades).ToString("0.0", CultureInfo.InvariantCulture) : "0.0") + "% winners\n";
            double months = paceFrom == DateTime.MinValue ? 0 : (lastSession - paceFrom).TotalDays / 30.44;
            if (Goal > 0 && months >= 1)
            {
                double pace = sinceStart / months;
                s += "Pace: $" + pace.ToString("0", CultureInfo.InvariantCulture) + " a month since " +
                     paceFrom.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) +
                     (sinceStart >= Goal ? ", goal reached" : pace > 0 ? ", about " + Math.Ceiling((Goal - sinceStart) / pace).ToString("0", CultureInfo.InvariantCulture) +
                      " more months to the goal" : ", no progress yet") + "\n";
            }
            return s;
        }

        // U17: a finished session's bar count: one with under 90% of its bars (outside the no-trade list) is thin data
        void FinishDataDay()
        {
            if (dqDay.Length == 0 || (SkipDates ?? "").Contains(dqDay))
                return;
            dqSessions++;
            if (!string.IsNullOrWhiteSpace(TrailFrom) && string.CompareOrdinal(dqDay, TrailFrom.Trim()) < 0)
                dqBeforeStart++;
            if (dqBars < 0.9 * (V38Engine.RthClose - V38Engine.RthOpen) / minutes)
            {
                dqThin++;
                if (dqFirstThin.Length == 0) dqFirstThin = dqDay;
            }
        }

        // U17: what is wrong with the price data, or "" when it is as the bot was tested on
        string DataWarning()
        {
            string w = "";
            if (dqSessions > 0 && dqThin > Math.Max(2, dqSessions / 20))
                w = "the price data has bars missing in " + dqThin + " of " + dqSessions + " sessions (the first " + dqFirstThin +
                    "): results won't match the tests. Use the instrument MNQ ##-## (or Merge back adjusted) and load the history in Tools > Historical Data";
            if (!string.IsNullOrWhiteSpace(TrailFrom) && dqSessions > dqBeforeStart && dqBeforeStart < 50)
                w += (w.Length > 0 ? "; " : "") + (dqBeforeStart == 0
                     ? "the data starts on " + firstBar + ", after the start date " + TrailFrom.Trim() + ": this instrument has no earlier " +
                       "history here. The filters need 50 sessions before the start, so load the earlier contracts (MNQ 03-26, 06-26, 09-26) " +
                       "in Tools > Historical Data and merge them (Merge back adjusted), or move the start date to about 3 months after " + firstBar
                     : "only " + dqBeforeStart + " sessions of data before the start date " + TrailFrom.Trim() +
                       ": the filters need 50, so start the data about 3 months earlier");
            return w;
        }

        string DataLine()
        {
            if (dqSessions == 0)
                return "";
            string w = DataWarning();
            return w.Length > 0 ? "DATA WARNING: " + w + "\n" : "Data check: " + dqSessions + " sessions, " +
                   (dqThin == 0 ? "all complete" : dqThin + " with bars missing") + "\n";
        }

        // U15: what today's filters allow, and when the next entry check is (checks at the bar closes on :00 and :30)
        string TodayLine(DateTime endNy)
        {
            int m = endNy.Hour * 60 + endNy.Minute;
            int last = engine.LastEntryMinute > 0 ? engine.LastEntryMinute : 930;
            string next;
            if (m < 600 || m >= V38Engine.RthClose)
                next = "next entry check 10:00";
            else if (m >= last)
                next = "no more entry checks today (the last is " + (last / 60) + ":" + (last % 60).ToString("00", CultureInfo.InvariantCulture) + ")";
            else
            {
                int n = (m / 30 + 1) * 30;
                next = "next entry check " + (n / 60) + ":" + (n % 60).ToString("00", CultureInfo.InvariantCulture) + " (in " + (n - m) + " min)";
            }
            return "Today: " + engine.TodayRules + "; " + next + "\n";
        }

        // U13: the real win rate against the tested one. From 30 trades, the chance of this few winners or fewer if the
        // bot still won TestedWinRate% of its trades (binomial); under 5%, a warning (and, live, one alert)
        string WinCheckLine()
        {
            if (TestedWinRate <= 0)
                return "";
            if (realTrades < 30)
                return "Win rate check: from 30 trades (" + realTrades + " so far)\n";
            double chance = BinomialTail(realWins, realTrades, TestedWinRate / 100.0);
            string rate = (100.0 * realWins / realTrades).ToString("0.0", CultureInfo.InvariantCulture) + "% in " + realTrades + " trades";
            string tested = TestedWinRate.ToString("0.0", CultureInfo.InvariantCulture) + "%";
            if (chance >= 0.05)
                return "Win rate in line with the tests: " + rate + " (tested " + tested + ")\n";
            string msg = "WIN RATE WARNING: " + rate + ", below the tested " + tested + " (" +
                         (100 * chance).ToString("0.0", CultureInfo.InvariantCulture) + "% chance): check the fills, the chart and the Mode";
            if (State == State.Realtime && !winWarned)
            {
                winWarned = true;
                Say("winrate", msg);
            }
            return msg + "\n";
        }

        // P(X <= k) for X binomial(n, p)
        static double BinomialTail(int k, int n, double p)
        {
            double logC = 0.0, sum = 0.0;
            for (int i = 0; i <= k; i++)
            {
                if (i > 0)
                    logC += Math.Log(n - i + 1) - Math.Log(i);
                sum += Math.Exp(logC + i * Math.Log(p) + (n - i) * Math.Log(1 - p));
            }
            return Math.Min(1.0, sum);
        }

        // fill quality, for the dashboard: the average ticks paid worse than planned, and a warning past 2 ticks
        string FillLine()
        {
            if (entrySlipN == 0)
                return "";
            double inAvg = entrySlipSum / entrySlipN, outAvg = exitSlipN > 0 ? exitSlipSum / exitSlipN : 0.0;
            string s = "Fills vs plan: entries " + inAvg.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) + " ticks (" + entrySlipN +
                       "), stops and market exits " + outAvg.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) + " ticks (" + exitSlipN + ")";
            if (entrySlipN >= 20 && (inAvg + outAvg) / 2 > 2.0 && !StepsAfterLock)
                s += " -- worse than 2 ticks: consider Gentle start";
            return s + "\n";
        }

        // the open trade, for the dashboard: side and size, entry, the stop and the target for the next bar, the lock, and
        // how long until the time stop can close it
        string OpenTradeLine()
        {
            int real = Position.MarketPosition == MarketPosition.Long ? 1 : Position.MarketPosition == MarketPosition.Short ? -1 : 0;
            if (real == 0)
                return "Open trade: none\n";
            double avg = Position.AveragePrice;
            if (engine.GapPos == real && engine.Position == 0)  // G60: the gap and go trade
                return "Open trade: " + (real > 0 ? "LONG " : "SHORT ") + Position.Quantity + " MNQ @ " + avg.ToString("0.00", CultureInfo.InvariantCulture) +
                       " (gap and go), stop " + engine.GapStop.ToString("0.00", CultureInfo.InvariantCulture) + ", " +
                       (engine.Bar + 1 - engine.GapBar) * BarsPeriod.Value + " min in, out at 09:55\n";
            double stop = engine.PeekStop(avg), tp = engine.PeekTarget(avg);
            string line = "Open trade: " + (real > 0 ? "LONG " : "SHORT ") + Position.Quantity + " MNQ @ " + avg.ToString("0.00", CultureInfo.InvariantCulture) +
                          (double.IsNaN(stop) ? "" : ", stop " + stop.ToString("0.00", CultureInfo.InvariantCulture)) +
                          (double.IsNaN(tp) ? "" : ", target " + tp.ToString("0.00", CultureInfo.InvariantCulture)) +
                          ", " + engine.MinutesInTrade + " min in, " + (engine.Locked ? "locked (can't lose)" : "lock not reached");
            if (engine.TimeStopMinutes > 0 && !engine.Locked)
            {
                int left = engine.TimeStopMinutes - engine.MinutesInTrade;
                line += left > 0 ? ", time stop in " + left + " min if losing" : ", time stop: out at the next bar if losing";
            }
            return line + "\n";
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Mode: Funded growth (50K), Funded growth 100K / 150K (Topstep), Funded growth Apex 100K / Apex 150K, Evaluation, or Custom", Order = 0, GroupName = "1. Size and risk")]
        public string Mode { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Contracts", Order = 1, GroupName = "1. Size and risk")]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Max loss per trade, $ (all contracts)", Order = 2, GroupName = "1. Size and risk")]
        public double MaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Max loss a day, $ (0 = off)", Order = 3, GroupName = "1. Size and risk")]
        public double DailyLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "After a losing trade: max loss per trade, $ (0 = the same)", Order = 5, GroupName = "1. Size and risk")]
        public double AfterLossMaxLoss { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20000)]
        [Display(Name = "Trailing drawdown (end of day, stops at the start), $ (0 = off)", Order = 6, GroupName = "1. Size and risk")]
        public double TrailDD { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Trailing drawdown and contract steps from date, yyyy-MM-dd (blank = the first bar)", Order = 7, GroupName = "1. Size and risk")]
        public string TrailFrom { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Add a contract per $ of profit (0 = off)", Order = 8, GroupName = "1. Size and risk")]
        public double ProfitStep { get; set; }

        [NinjaScriptProperty]
        [Range(0, 60)]
        [Display(Name = "Most contracts (with the contract steps; 0 = no limit)", Order = 9, GroupName = "1. Size and risk")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Size by the trade's own stop", Order = 10, GroupName = "1. Size and risk")]
        public bool SizeByOwnStop { get; set; }

        [NinjaScriptProperty]
        [Range(0, 390)]
        [Display(Name = "Time stop: close a losing trade not yet locked this many minutes after its fill (0 = off)", Order = 11, GroupName = "1. Size and risk")]
        public int TimeStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Gentle start: no contract steps until the trailing floor has stopped (turn on if live fills are 3+ ticks worse)", Order = 12, GroupName = "1. Size and risk")]
        public bool StepsAfterLock { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Loss guard, live: flat and done for the day at this loss today, closed + open, $ (0 = off)", Order = 13, GroupName = "1. Size and risk")]
        public double LossGuard { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Prop account: its starting balance, $ (live: the dashboard's floor and room from the account; 0 = off)", Order = 0, GroupName = "6. Prop account")]
        public double PropStartBalance { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Prop account: its highest end-of-day balance so far, $ (0 = the starting balance; the higher of this and today's is used)", Order = 1, GroupName = "6. Prop account")]
        public double PropHighBalance { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prop account: never risk more than the account's own room above its floor (live)", Order = 2, GroupName = "6. Prop account")]
        public bool SizeToAccountRoom { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Alerts (live): entries, exits, time stop, loss guard, setup warnings", Order = 0, GroupName = "5. Alerts")]
        public bool AlertsOn { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Alerts with a sound", Order = 1, GroupName = "5. Alerts")]
        public bool SoundAlerts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1000000)]
        [Display(Name = "Milestone alerts (live): at each day's close, every this much profit since the start, $ (0 = off)", Order = 2, GroupName = "5. Alerts")]
        public double MilestoneStep { get; set; }

        [NinjaScriptProperty]
        [Range(0, 99)]
        [Display(Name = "Win rate check: the tested win rate, % (warns from 30 trades if well below it; 0 = off)", Order = 3, GroupName = "5. Alerts")]
        public double TestedWinRate { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Gap and go: a trade with a big opening gap, 09:35-09:55 (5-minute chart)", Order = 14, GroupName = "1. Size and risk")]
        public bool GapGo { get; set; }

        [NinjaScriptProperty]
        [Range(0, 15)]
        [Display(Name = "Gap and go once the trailing floor has stopped at the start: up to this many MNQ (0 = 1 MNQ always)", Order = 15, GroupName = "1. Size and risk")]
        public int GapGoLocked { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "More trading days: 1-MNQ fill-in trades once the floor has stopped (about 72-81% of days)", Order = 16, GroupName = "1. Size and risk")]
        public bool MoreDays { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "More trading days: only while the account is at least this far above the trailing floor, $", Order = 17, GroupName = "1. Size and risk")]
        public double MoreDaysCushion { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "More trading days: fill-ins at 2 MNQ while the account is at least this far above the floor, $ (0 = always 1)", Order = 20, GroupName = "1. Size and risk")]
        public double MoreDaysQty2Room { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1)]
        [Display(Name = "Giveback brake: once the floor has stopped, 1 MNQ per trade while the profit is under this share of its best (0 = off)", Order = 21, GroupName = "1. Size and risk")]
        public double GivebackBrake { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "After a losing trade, once the floor has stopped: max loss per trade, $ (0 = as before it stopped)", Order = 25, GroupName = "1. Size and risk")]
        public double AfterLossLocked { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "No entries at these checks until the floor has stopped (HH:mm, comma-separated; blank = off)", Order = 26, GroupName = "1. Size and risk")]
        public string EarlyNoEntryChecks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Faster contract steps: above the profit below, one more MNQ per this much, $ (0 = off)", Order = 27, GroupName = "1. Size and risk")]
        public double FastSteps { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1000000)]
        [Display(Name = "Faster contract steps from this much profit, $", Order = 28, GroupName = "1. Size and risk")]
        public double FastStepsFrom { get; set; }

        // "13:00,14:30" -> ",780,870," (the check bars' ends, minutes after midnight); a bad entry raises a setup warning
        string CheckEnds(string list)
        {
            string outS = ",";
            foreach (string part in (list ?? "").Split(','))
            {
                string t = part.Trim();
                if (t.Length == 0) continue;
                string[] hm = t.Split(':');
                int hh, mm;
                if (hm.Length != 2 || !int.TryParse(hm[0], out hh) || !int.TryParse(hm[1], out mm) || hh < 0 || hh > 23 || mm < 0 || mm > 59)
                {
                    setupWarnings.Add("\"No entries at these checks\": \"" + t + "\" isn't HH:mm; ignored");
                    continue;
                }
                outS += (hh * 60 + mm) + ",";
            }
            return outS == "," ? "" : outS;
        }

        [NinjaScriptProperty]
        [Range(0, 15)]
        [Display(Name = "Sprint: the first 5 sessions from the start date, until +$3,000, every trade this many MNQ (0 = off; see the odds in the docs)", Order = 22, GroupName = "1. Size and risk")]
        public int SprintContracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Sizing: count this many points more slippage at each stop (room kept for a jump past it)", Order = 18, GroupName = "1. Size and risk")]
        public double SizeSlip { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Near-floor gate: within this many $ of the trailing floor, trade only when a 1-MNQ shadow record is at or above its 20-session average (0 = off)", Order = 19, GroupName = "1. Size and risk")]
        public double NearFloorGate { get; set; }

        [NinjaScriptProperty]
        [Range(0, 200)]
        [Display(Name = "When the day's room is short: 1 contract, its stop cut to the room, if at least this many points (0 = no trade)", Order = 4, GroupName = "1. Size and risk")]
        public double SqueezeMin { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Take profit, noise units (0 = off)", Order = 1, GroupName = "2. Exits")]
        public double TakeProfit { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Lock: trigger, in max losses (0 = off)", Order = 2, GroupName = "2. Exits")]
        public double LockAt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Lock: stop to the entry plus, points", Order = 3, GroupName = "2. Exits")]
        public double LockPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2)]
        [Display(Name = "Stop distance past the line, noise units", Order = 4, GroupName = "2. Exits")]
        public double StopBuffer { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Last check for new entries (15:00 or 15:30)", Order = 1, GroupName = "3. Filters")]
        public string LastEntry { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "After a big day: no trades its way if its range > this x the 10-session average (0 = off)", Order = 2, GroupName = "3. Filters")]
        public double BigDayK { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2)]
        [Display(Name = "Calm stretch: no trades if the 10-session average range < this x the 40-session one (0 = off)", Order = 3, GroupName = "3. Filters")]
        public double CalmK { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1)]
        [Display(Name = "Entries near the day's extreme: the close in the top this share of the day's range (0 = off)", Order = 4, GroupName = "3. Filters")]
        public double RangePos { get; set; }

        [NinjaScriptProperty]
        [Range(0, 250)]
        [Display(Name = "No shorts while the last close is above its average of this many sessions (0 = off)", Order = 5, GroupName = "3. Filters")]
        public int TrendSessions { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed days: no shorts before 14:00", Order = 6, GroupName = "3. Filters")]
        public bool FedNoShorts { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "No trades on these dates (holidays, half days)", Order = 7, GroupName = "3. Filters")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fed announcement dates", Order = 8, GroupName = "3. Filters")]
        public string FedDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 1, GroupName = "4. Orders")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Profit goal for the dashboard, $ (0 = hide)", Order = 2, GroupName = "4. Orders")]
        public double Goal { get; set; }
        #endregion
    }
}
