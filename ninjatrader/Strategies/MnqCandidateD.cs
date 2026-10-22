// MNQ candidates D and E (docs/CANDIDATE_D.md): one shared position manager for every sleeve.
//
// The position manager:
//   - two MNQ contracts when their planned all-in risk (2 x (R x $2 + 2 x commission + the declared slippage
//     allowance)) fits the $125 budget, otherwise no trade; never one or three, never a tightened structural stop;
//   - the initial stop is the sleeve's structural stop (an absolute price), never widened, never averaged down;
//   - at +1R (a completed bar's high / low, from the actual average fill) both contracts' stop moves to the fill plus a
//     fee-aware 1.50 points;
//   - exactly half (one contract, "Long half" / "Short half") has a take-profit at +2R from the fill;
//   - the other (the runner) trails 1R behind the best price since the fill once the half has filled; no target;
//   - flat at 15:55 New York; at most three entry campaigns a day across all sleeves; one position or pending entry
//     at a time; no daily profit cap, loss cap or loser count.
// The sleeves: D = B's noise momentum (MnqNoiseEngine's lines) and the Williams breakout (WilliamsBreakout), both with
// B's frozen entry rules; E = a sweep / reversal sequence on five-minute bars (pool, penetration, reclaim, BOS, FVG,
// a limit at the gap's edge) on higher-timeframe pools (E1) and, with UseE2, the session-level pools too.
// mnqbot/candidate_d.py is the same strategy in Python; tests/test_candidate_d.py holds the two to trade-for-trade
// agreement on the NinjaTrader stand-in.
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
using NinjaTrader.NinjaScript.AddOns.MnqBot;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    // The sweep setups' initial stop (docs/CANDIDATE_F.md): E's sweep extreme - 0.1 ATR, or F's FVG far edge - 2 ticks.
    public enum SweepStopReference { SweepExtreme, FvgFarEdge }
    // candidate G (docs/CANDIDATE_G.md): a stop wider than the budget allows is refused (Skip: D, E, F), moved in to the
    // widest affordable distance (Cap), or every stop is that distance (Budget)
    public enum StopFitMode { Skip, Cap, Budget }
    // G amendment 1: a noise campaign's stop also follows frozen B's line stop (tightened only); after the half its runner
    // trails by R (TrailR x R behind the best price: D-G), Line (the line only) or Line2R (the tighter of the line and 2R)
    public enum RunnerTrailMode { R, Line, Line2R }

    // Sleeve E's causal sequence (docs/CANDIDATE_D.md section 3), fed every 1-minute bar.
    public sealed class SweepEngine
    {
        sealed class Setup
        {
            public string Pool; public int D, Pen, Bos = -1; public double Level, Extreme, Ref = double.NaN;
            public string State = "reclaim";
        }

        public sealed class Decision
        {
            public string Pool; public int D, Fvg, Pen, Bos; public double Limit, Far, Extreme, Atr, Ref, Level;
        }

        static readonly string[] E1 = { "PDL", "PDH", "PWL", "PWH" };
        static readonly string[] E2 = { "ONL", "ONH", "ASL", "ASH", "LOL", "LOH" };
        static int DirOf(string pool) { return pool.EndsWith("L") ? 1 : -1; }

        readonly List<string> poolsOn = new List<string>();
        readonly List<double[]> fb = new List<double[]>();  // completed five-minute bars: o, h, l, c
        long curKey = long.MinValue;
        double co, ch, cl, cc;
        bool building;
        readonly List<double[]> swingHi = new List<double[]>(), swingLo = new List<double[]>();  // formation, confirmation, price
        readonly List<double[]> fvgBull = new List<double[]>(), fvgBear = new List<double[]>();  // k, proximal edge, far edge
        double atr = double.NaN, prevC = double.NaN;
        readonly List<double> trSeed = new List<double>();
        string sess;
        double rthHi = double.NaN, rthLo = double.NaN, prevRthHi = double.NaN, prevRthLo = double.NaN;
        string weekKey;
        double weekHi = double.NaN, weekLo = double.NaN, prevWeekHi = double.NaN, prevWeekLo = double.NaN;
        double[] on = Fresh(), asia = Fresh(), lon = Fresh();
        readonly Dictionary<string, double> pools = new Dictionary<string, double>();
        readonly HashSet<string> used = new HashSet<string>();
        readonly List<Setup> setups = new List<Setup>();
        bool activeDay;
        public readonly List<Decision> Decisions = new List<Decision>();

        public const int PenFirst = 575, PenLast = 870, ReclaimBars = 6, BosBars = 12, FvgAfterBos = 3, AtrLen = 14;

        public SweepEngine(bool useE2)
        {
            poolsOn.AddRange(E1);
            if (useE2) poolsOn.AddRange(E2);
        }

        static double[] Fresh() { return new[] { double.NaN, double.NaN }; }

        static string Monday(DateTime day) { return day.AddDays(-(((int)day.DayOfWeek + 6) % 7)).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture); }

        static void Widen(double[] v, double h, double l)
        {
            v[0] = double.IsNaN(v[0]) ? h : Math.Max(v[0], h);
            v[1] = double.IsNaN(v[1]) ? l : Math.Min(v[1], l);
        }

        void Complete()
        {
            building = false;
            double o = co, h = ch, l = cl, c = cc;
            fb.Add(new[] { o, h, l, c });
            int b = fb.Count - 1;
            double tr = double.IsNaN(prevC) ? h - l : Math.Max(h - l, Math.Max(Math.Abs(h - prevC), Math.Abs(l - prevC)));
            prevC = c;
            if (trSeed.Count < AtrLen)
            {
                trSeed.Add(tr);
                if (trSeed.Count == AtrLen)
                {
                    double s = 0.0;
                    foreach (double x in trSeed) s += x;
                    atr = s / AtrLen;
                }
            }
            else
                atr = (atr * (AtrLen - 1) + tr) / AtrLen;
            if (b >= 4)
            {
                int j = b - 2;
                double hj = fb[j][1], lj = fb[j][2];
                if (hj > fb[j - 2][1] && hj > fb[j - 1][1] && hj > fb[j + 1][1] && hj > fb[j + 2][1])
                    swingHi.Add(new double[] { j, b, hj });
                if (lj < fb[j - 2][2] && lj < fb[j - 1][2] && lj < fb[j + 1][2] && lj < fb[j + 2][2])
                    swingLo.Add(new double[] { j, b, lj });
            }
            if (b >= 2)
            {
                if (l > fb[b - 2][1]) fvgBull.Add(new double[] { b, l, fb[b - 2][1] });
                if (h < fb[b - 2][2]) fvgBear.Add(new double[] { b, h, fb[b - 2][2] });
            }
            Advance(b);
        }

        void Advance(int b)
        {
            double c = fb[b][3];
            foreach (Setup s in setups)
            {
                if (s.State == "dead") continue;
                int d = s.D;
                if (s.State == "reclaim")
                {
                    if (d * (c - s.Level) > 0)
                    {
                        List<double[]> sw = d > 0 ? swingHi : swingLo;
                        double[] r = null;
                        foreach (double[] x in sw)
                            if (x[0] < s.Pen && x[1] <= b && (r == null || x[0] > r[0]))
                                r = x;
                        if (r == null) { s.State = "dead"; continue; }
                        s.Ref = r[2];
                        s.State = "bos";
                    }
                    else if (b >= s.Pen + ReclaimBars - 1) { s.State = "dead"; continue; }
                }
                if (s.State == "bos")
                {
                    if (b > s.Pen + BosBars) { s.State = "dead"; continue; }
                    if (d * (c - s.Ref) > 0) { s.Bos = b; s.State = "fvg"; }
                }
                if (s.State == "fvg")
                {
                    List<double[]> gaps = d > 0 ? fvgBull : fvgBear;
                    double[] pick = null;
                    foreach (double[] x in gaps)
                        if (x[0] - 2 >= s.Pen && x[0] <= b && (pick == null || x[0] > pick[0]))
                            pick = x;
                    if (pick != null)
                    {
                        s.State = "dead";
                        Decision dec = new Decision();
                        dec.Pool = s.Pool; dec.D = d; dec.Limit = pick[1]; dec.Far = pick[2]; dec.Fvg = (int)pick[0]; dec.Extreme = s.Extreme;
                        dec.Atr = atr; dec.Pen = s.Pen; dec.Bos = s.Bos; dec.Ref = s.Ref; dec.Level = s.Level;
                        Decisions.Add(dec);
                    }
                    else if (b >= s.Bos + FvgAfterBos)
                        s.State = "dead";
                }
            }
        }

        public void OnBar(DateTime t, int tmin, DateTime day, double o, double h, double l, double c, bool allowedDay)
        {
            Decisions.Clear();
            long key = (t.Ticks / TimeSpan.TicksPerMinute) / 5;
            if (building && key != curKey)
                Complete();
            string sd = day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            if (sd != sess)
            {
                sess = sd;
                on = Fresh(); asia = Fresh(); lon = Fresh();
            }
            if (tmin == NoiseEngine.RthOpen)
                OpenDay(day, allowedDay);
            if (tmin < NoiseEngine.RthOpen || tmin >= 1080)
            {
                Widen(on, h, l);
                if (tmin >= 1080 || tmin < 120) Widen(asia, h, l);
                if (tmin >= 120 && tmin < 510) Widen(lon, h, l);
            }
            if (tmin >= NoiseEngine.RthOpen && tmin < NoiseEngine.RthClose)
            {
                rthHi = double.IsNaN(rthHi) ? h : Math.Max(rthHi, h);
                rthLo = double.IsNaN(rthLo) ? l : Math.Min(rthLo, l);
                weekHi = double.IsNaN(weekHi) ? h : Math.Max(weekHi, h);
                weekLo = double.IsNaN(weekLo) ? l : Math.Min(weekLo, l);
            }
            if (!building)
            {
                curKey = key; co = o; ch = h; cl = l; cc = c; building = true;
            }
            else
            {
                ch = Math.Max(ch, h); cl = Math.Min(cl, l); cc = c;
            }
            foreach (Setup s in setups)
                if (s.State != "dead")
                    s.Extreme = s.D > 0 ? Math.Min(s.Extreme, l) : Math.Max(s.Extreme, h);
            if (activeDay && tmin >= PenFirst && tmin <= PenLast)
                foreach (string name in poolsOn)
                {
                    if (used.Contains(name) || !pools.ContainsKey(name)) continue;
                    double lvl = pools[name];
                    int d = DirOf(name);
                    if ((d > 0 && l <= lvl - 0.25) || (d < 0 && h >= lvl + 0.25))
                    {
                        used.Add(name);
                        Setup s = new Setup();
                        s.Pool = name; s.D = d; s.Level = lvl; s.Pen = fb.Count; s.Extreme = d > 0 ? l : h;
                        setups.Add(s);
                    }
                }
            if (tmin % 5 == 4)
                Complete();
        }

        void OpenDay(DateTime day, bool allowedDay)
        {
            if (!double.IsNaN(rthHi)) { prevRthHi = rthHi; prevRthLo = rthLo; }
            rthHi = rthLo = double.NaN;
            string wk = Monday(day);
            if (wk != weekKey)
            {
                if (weekKey != null) { prevWeekHi = weekHi; prevWeekLo = weekLo; }
                weekKey = wk;
                weekHi = weekLo = double.NaN;
            }
            pools.Clear();
            Put("PDH", prevRthHi); Put("PDL", prevRthLo); Put("PWH", prevWeekHi); Put("PWL", prevWeekLo);
            Put("ONH", on[0]); Put("ONL", on[1]); Put("ASH", asia[0]); Put("ASL", asia[1]); Put("LOH", lon[0]); Put("LOL", lon[1]);
            used.Clear();
            setups.Clear();
            activeDay = allowedDay;
        }

        void Put(string name, double v) { if (!double.IsNaN(v)) pools[name] = v; }

        // the opposing pools of the candidate's set: highs for a long, lows for a short
        public List<double> RoomLevels(int d)
        {
            List<double> r = new List<double>();
            foreach (string n in poolsOn)
                if (DirOf(n) == -d && pools.ContainsKey(n))
                    r.Add(pools[n]);
            return r;
        }
    }

    public class MnqCandidateD : Strategy
    {
        NoiseEngine engine;
        WilliamsBreakout williams;
        SweepEngine sweep;
        TimeZoneInfo newYork;
        double pv;
        bool dayOpenValid;      // the noise engine's day open is set (its 09:30 bar was seen and 16:00 not yet)
        string curDay = "";
        int dayCount;           // entry campaigns today (filled entries)
        // the campaign: its decision, its two orders, its two contracts
        bool inCampaign;
        string campSleeve = "", campKind = "", campDay = "";
        int campDir, campSignalBar, entryBarIdx = -1;
        double campExpected, campStop0, campR, campPlanned;
        Order runnerOrder, halfOrder;
        bool runnerPending, halfPending, runnerOpen, halfOpen, cancelSent;
        double runnerFill = double.NaN, halfFill = double.NaN, runnerExit = double.NaN, halfExit = double.NaN;
        string runnerWhy = "", halfWhy = "";
        int placedBar;
        bool be, halfFilled;
        double best = double.NaN, curStop = double.NaN;
        // the evaluation account (the firm's limits): highest equity, kept across sessions and restarts
        double peak = double.NaN;
        bool accountDone;
        string accountState = "";
        readonly List<string> ledger = new List<string>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqCandidateD";
                Description = "MNQ candidates D / E: noise momentum, Williams breakout and sweep reversals under one position manager.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                // a rejection reaches OnOrderUpdate, which closes the position; any other realtime error stops the
                // strategy, cancels its orders and closes the position (never ignored)
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelCloseIgnoreRejects;
                TraceOrders = false;
                IsInstantiatedOnEachOptimizationIteration = true;

                UseNoise = true;
                UseWilliams = true;
                UseE1 = false;
                UseE2 = false;
                SweepStop = SweepStopReference.SweepExtreme;
                StopFit = StopFitMode.Skip;
                RunnerTrail = RunnerTrailMode.R;
                RiskBudget = 125;
                SizingCommission = 0.95;
                AllowanceMarketTicks = 4;
                AllowanceLimitTicks = 2;
                BreakevenOffset = 1.5;
                PartialR = 2.0;
                TrailR = 1.0;
                MaxCampaigns = 3;
                FlatBar = 954;          // the exit is sent at the 15:54 bar's close and fills at 15:55
                StopBuffer = 0.24;
                SkipDates = NoiseEngine.SkipDatesDefault;
                FedDates = NoiseEngine.FedDatesDefault;
                NfpDates = "";
                EvalTarget = 3000;
                EvalTrail = 2000;
                AccountStart = 50000;
                RememberAccount = true;
                PlaceOrders = true;
                AuditOutput = true;
            }
            else if (State == State.DataLoaded)
            {
                newYork = NewYork();
                pv = Instrument.MasterInstrument.PointValue;
                NoiseSettings ns = new NoiseSettings();  // only its lines are used: B's lookback, buffer and dates
                ns.Qty = 2;
                ns.Tick = TickSize;
                ns.PointValue = pv;
                ns.MaxLoss = 0;
                ns.TakeProfit = 0;
                ns.StopBuffer = StopBuffer;
                ns.LockAt = 0;
                ns.MaxLosers = 0;
                ns.Lookback = 14;
                ns.FedNoShorts = true;
                ns.SkipDates = SkipDates ?? "";
                ns.FedDates = FedDates ?? "";
                engine = new NoiseEngine(ns, 1);
                WilliamsSettings ws = new WilliamsSettings();  // B's breakout; its own sizing is not used
                ws.K = 0.5;
                ws.StopFraction = 0.25;
                ws.Risk = 1e12;
                ws.MaxQty = 2;
                ws.LastEntry = 900;
                ws.PointValue = pv;
                ws.Shorts = true;
                williams = new WilliamsBreakout(ws);
                sweep = UseE1 || UseE2 ? new SweepEngine(UseE2) : null;
                Print("D settings: " + Instrument.FullName + ", " + BarsPeriod.Value + " " + BarsPeriod.BarsPeriodType +
                      ", account " + (Account == null ? "none" : Account.Name) + ", PlaceOrders " + PlaceOrders +
                      ", sleeves " + (UseNoise ? "noise " : "") + (UseWilliams ? "Williams " : "") + (UseE1 ? "E1 " : "") +
                      (UseE2 ? "E2 " : "") + ", sweep stop " + SweepStop + ", stop fit " + StopFit + ", runner trail " + RunnerTrail + ", budget " + RiskBudget + ", commission " + SizingCommission + ", allowance " +
                      AllowanceMarketTicks + "/" + AllowanceLimitTicks + " ticks, breakeven +" + BreakevenOffset + ", half at " +
                      PartialR + "R, trail " + TrailR + "R, campaigns " + MaxCampaigns + ", target " + EvalTarget + ", trail $" + EvalTrail);
                if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                    Print("MnqCandidateD: use a 1-minute chart (CME US Index Futures ETH). Not trading.");
            }
            else if (State == State.Realtime)
                LoadAccount();
            else if (State == State.Terminated)
            {
                foreach (string x in ledger) Print(x);
            }
        }

        static TimeZoneInfo NewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch (TimeZoneNotFoundException) { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        DateTime ToNy(DateTime t)
        {
            TimeZoneInfo platform = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
            return TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), platform, newYork);
        }

        static bool InList(string list, string day) { return !string.IsNullOrEmpty(list) && list.Contains(day); }
        double FloorTick(double x) { return Math.Floor(x / TickSize + 1e-7) * TickSize; }
        double CeilTick(double x) { return Math.Ceiling(x / TickSize - 1e-7) * TickSize; }
        double Away(int d, double price) { return d > 0 ? FloorTick(price) : CeilTick(price); }
        double Toward(int d, double price) { return d > 0 ? CeilTick(price) : FloorTick(price); }

        // the widest R (points, on the grid) whose two-contract planned all-in risk fits the budget
        double MaxR(int allowanceTicks) { return FloorTick((RiskBudget / 2 - 2 * SizingCommission - allowanceTicks * TickSize * pv) / pv); }

        double FitStop(int d, double entry, double stop, int allowanceTicks)
        {
            if (StopFit == StopFitMode.Skip) return stop;
            double rmax = MaxR(allowanceTicks);
            if (StopFit == StopFitMode.Budget || d * (entry - stop) > rmax) return Toward(d, entry - d * rmax);
            return stop;
        }
        string RunnerName { get { return campDir > 0 ? "Long" : "Short"; } }
        string HalfName { get { return campDir > 0 ? "Long half" : "Short half"; } }
        bool Exposed { get { return Position.MarketPosition != MarketPosition.Flat; } }
        bool Pending { get { return runnerPending || halfPending; } }
        static string F(double x) { return double.IsNaN(x) ? "-" : x.ToString("0.00", CultureInfo.InvariantCulture); }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                return;
            DateTime t = ToNy(Time[0]).AddMinutes(-1);
            int tmin = t.Hour * 60 + t.Minute, end = tmin + 1;
            DateTime tday = t.AddHours(6).Date;
            string day = tday.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            double o = Open[0], h = High[0], l = Low[0], c = Close[0];
            if (tmin == NoiseEngine.RthOpen && day != curDay) { curDay = day; dayCount = 0; }
            bool allowed = !Exposed && !Pending && dayCount < MaxCampaigns && !InList(SkipDates, day) && tmin < FlatBar &&
                           !accountDone;
            engine.OnBar(t, o, h, l, c);
            if (tmin == NoiseEngine.RthOpen) dayOpenValid = true;
            bool inRth = tmin >= NoiseEngine.RthOpen && end <= NoiseEngine.RthClose;
            bool isCheck = inRth && dayOpenValid && end >= NoiseEngine.FirstCheck && end <= NoiseEngine.LastCheck &&
                           (end - NoiseEngine.FirstCheck) % NoiseEngine.Step == 0 && engine.Ready;
            if (inRth && end == NoiseEngine.RthClose) dayOpenValid = false;
            williams.OnBar(t, o, h, l, allowed);
            if (sweep != null)
            {
                bool eDay = !InList(SkipDates, day) && !InList(FedDates, day) && !InList(NfpDates, day);
                sweep.OnBar(t, tmin, tday, o, h, l, c, eDay);
            }
            Account_(h, l, c);
            if (Exposed)
                Manage(tmin, day, h, l, c);
            if (Pending && inCampaign && !Exposed)
                ManagePending(tmin, h, l);
            else if (Pending && Exposed && !cancelSent)  // one contract filled, the other still working: cancel it
            {
                Print(Time[0] + "  one contract filled, cancelling the other");
                CancelPending();
            }
            if (allowed && !Exposed && !Pending && !inCampaign && PlaceOrders)
                TryEnter(isCheck, end, tmin, day, c);
            else if (AuditOutput && UseNoise && isCheck && !engine.SkipToday && (c > engine.Upper ||
                     (c < engine.Lower && !(engine.FedToday && end < NoiseEngine.FedCutoff))))
                Refusal("noise", c > engine.Upper ? 1 : -1, Exposed ? "blocked: position" : Pending || inCampaign ?
                        "blocked: pending order" : dayCount >= MaxCampaigns ? "blocked: daily entry budget exhausted" :
                        "blocked: after the entry window");
        }

        // The daily opportunity audit's refusal lines (docs/DAILY_AUDIT.md), comparable with research/daily_audit.py;
        // nothing here changes a decision
        void Refusal(string sleeve, int d, string why)
        {
            if (AuditOutput)
                Print("D refusal," + Time[0].ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + "," + sleeve + "," + d + "," + why);
        }

        void Manage(int tmin, string day, double h, double l, double c)
        {
            int d = campDir;
            double avg = Position.AveragePrice, r = campR;
            if (tmin >= FlatBar || tmin < NoiseEngine.RthOpen || day != campDay)
            {
                string why = tmin == FlatBar ? "Flat 15:55" : "Session ended";
                if (d > 0) ExitLong(why, ""); else ExitShort(why, "");
                return;
            }
            bool freshLimit = campKind == "limit" && CurrentBar == entryBarIdx;
            if (!freshLimit)
            {
                double ext = d > 0 ? h : l;
                best = double.IsNaN(best) ? ext : (d > 0 ? Math.Max(best, ext) : Math.Min(best, ext));
                if (!be && d * (ext - avg) >= r) be = true;
            }
            double nw = curStop;
            if (be)
            {
                double b = avg + d * BreakevenOffset;
                nw = d > 0 ? Math.Max(nw, b) : Math.Min(nw, b);
            }
            bool lineMode = RunnerTrail != RunnerTrailMode.R && campSleeve == "noise";
            if (lineMode && !double.IsNaN(engine.Upper))
            {
                double ln = Toward(d, d > 0 ? engine.Upper * (1 - StopBuffer * engine.Sigma) : engine.Lower * (1 + StopBuffer * engine.Sigma));
                nw = d > 0 ? Math.Max(nw, ln) : Math.Min(nw, ln);
            }
            if (halfFilled && !double.IsNaN(best) && !(lineMode && RunnerTrail == RunnerTrailMode.Line))
            {
                double tr = Toward(d, best - d * (lineMode ? 2.0 : TrailR) * r);
                nw = d > 0 ? Math.Max(nw, tr) : Math.Min(nw, tr);
            }
            if (nw != curStop)
            {
                if (d * (c - nw) <= 0)
                {
                    if (d > 0) ExitLong("Stop passed", ""); else ExitShort("Stop passed", "");
                    return;
                }
                curStop = nw;
                SetStopLoss(RunnerName, CalculationMode.Price, nw, false);
                SetStopLoss(HalfName, CalculationMode.Price, nw, false);
            }
        }

        void ManagePending(int tmin, double h, double l)
        {
            if (campKind != "limit" || cancelSent) return;
            int d = campDir;
            double lim = campExpected, r = campR;
            string why = "";
            if (CurrentBar - placedBar >= 30) why = "expired";
            else if ((d > 0 && l <= campStop0) || (d < 0 && h >= campStop0)) why = "stop traded";
            else if ((d > 0 && h >= lim + PartialR * r) || (d < 0 && l <= lim - PartialR * r)) why = "ran away";
            else if (tmin + 1 >= 930) why = "15:30";
            if (why.Length > 0)
            {
                Print(Time[0] + "  cancelling the " + campSleeve + " limit entry: " + why);
                CancelPending();
            }
        }

        void CancelPending()
        {
            cancelSent = true;
            if (runnerPending && runnerOrder != null) CancelOrder(runnerOrder);
            if (halfPending && halfOrder != null) CancelOrder(halfOrder);
        }

        void TryEnter(bool isCheck, int end, int tmin, string day, double c)
        {
            if (UseNoise && isCheck && !engine.SkipToday)
            {
                int dn = 0;
                double structural = double.NaN;
                if (c > engine.Upper) { dn = 1; structural = engine.Upper * (1 - StopBuffer * engine.Sigma); }
                else if (c < engine.Lower && !(engine.FedToday && end < NoiseEngine.FedCutoff))
                { dn = -1; structural = engine.Lower * (1 + StopBuffer * engine.Sigma); }
                if (dn != 0 && TryMarket("noise", dn, c, structural, day)) return;
            }
            if (UseWilliams && williams.Signal != 0)
            {
                int dw = williams.Signal;
                if (TryMarket("williams", dw, c, c - dw * williams.StopPoints, day)) return;
            }
            if (sweep == null) return;
            foreach (SweepEngine.Decision dec in sweep.Decisions)
            {
                int d = dec.D;
                if (end < 585 || end > 900) { Refusal("sweep", d, "not qualified: decision window"); continue; }
                double lim = d > 0 ? FloorTick(dec.Limit) : CeilTick(dec.Limit);
                double stop = SweepStop == SweepStopReference.FvgFarEdge ? Away(d, dec.Far - d * 2 * TickSize)
                                                                          : Away(d, dec.Extreme - d * 0.1 * dec.Atr);
                stop = FitStop(d, lim, stop, AllowanceLimitTicks);
                double r = d * (lim - stop);
                double planned = 2 * (r * pv + 2 * SizingCommission + AllowanceLimitTicks * TickSize * pv);
                if (r <= 0 || planned > RiskBudget + 1e-9) { Refusal("sweep", d, "unaffordable"); continue; }
                double need = PartialR * r + 1.45, room = double.NaN;
                foreach (double x in sweep.RoomLevels(d))
                {
                    double dist = d * (x - lim);
                    if (dist > 0 && (double.IsNaN(room) || dist < room)) room = dist;
                }
                if (!double.IsNaN(room) && room < need) { Refusal("sweep", d, "not qualified: room"); continue; }
                Submit((SweepStop == SweepStopReference.FvgFarEdge ? "F:" : "E:") + dec.Pool, d, "limit", lim, stop, r, planned, day);
                return;
            }
        }

        bool TryMarket(string sleeve, int d, double c, double structural, string day)
        {
            double stop = FitStop(d, c, Away(d, structural), AllowanceMarketTicks);
            double r = d * (c - stop);
            double planned = 2 * (r * pv + 2 * SizingCommission + AllowanceMarketTicks * TickSize * pv);
            if (r <= 0 || planned > RiskBudget + 1e-9)
            {
                Refusal(sleeve, d, "unaffordable");
                return false;
            }
            Submit(sleeve, d, "market", c, stop, r, planned, day);
            return true;
        }

        void Submit(string sleeve, int d, string kind, double price, double stop, double r, double planned, string day)
        {
            inCampaign = true;
            campSleeve = sleeve; campDir = d; campKind = kind; campDay = day; campSignalBar = CurrentBar;
            campExpected = price; campStop0 = stop; campR = r; campPlanned = planned;
            curStop = stop; be = false; halfFilled = false; best = double.NaN; cancelSent = false;
            runnerFill = halfFill = runnerExit = halfExit = double.NaN; runnerWhy = halfWhy = "";
            placedBar = CurrentBar;
            SetStopLoss(RunnerName, CalculationMode.Price, stop, false);
            SetStopLoss(HalfName, CalculationMode.Price, stop, false);
            SetProfitTarget(HalfName, CalculationMode.Ticks, Math.Round(PartialR * r / TickSize));
            runnerPending = halfPending = true;
            if (kind == "market")
            {
                runnerOrder = d > 0 ? EnterLong(1, RunnerName) : EnterShort(1, RunnerName);
                halfOrder = d > 0 ? EnterLong(1, HalfName) : EnterShort(1, HalfName);
            }
            else
            {
                runnerOrder = d > 0 ? EnterLongLimit(1, price, RunnerName) : EnterShortLimit(1, price, RunnerName);
                halfOrder = d > 0 ? EnterLongLimit(1, price, HalfName) : EnterShortLimit(1, price, HalfName);
            }
            Print(Time[0] + "  D entry " + sleeve + " " + (d > 0 ? "long" : "short") + " " + kind + " at " + F(price) +
                  ", stop " + F(stop) + ", R " + F(r) + " points, price risk $" + F(r * pv * 2) + ", planned risk $" + F(planned));
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                              double averageFillPrice, OrderState orderState, DateTime time,
                                              ErrorCode error, string comment)
        {
            bool runner = order == runnerOrder, half = order == halfOrder;
            if (runner || half)
            {
                // the entry stays pending until its completion or cancellation is confirmed
                if (orderState == OrderState.Filled || orderState == OrderState.Cancelled || orderState == OrderState.Rejected)
                {
                    if (runner) runnerPending = false;
                    if (half) halfPending = false;
                    if (!Pending && !Exposed && !runnerOpen && !halfOpen && inCampaign &&
                        double.IsNaN(runnerFill) && double.IsNaN(halfFill))
                    {
                        inCampaign = false;  // nothing filled: no campaign
                        Print(Time[0] + "  the " + campSleeve + " entry ended unfilled (" + orderState + ")");
                    }
                }
                return;
            }
            if (orderState == OrderState.Rejected && Exposed)
            {
                Print(Time[0] + "  ORDER REJECTED: " + order.Name + " (" + comment + "). Closing the position.");
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("Close: rejected", "");
                else ExitShort("Close: rejected", "");
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || !inCampaign) return;
            string n = execution.Order.Name;
            if (n == RunnerName || n == HalfName)  // an entry fill
            {
                if (!runnerOpen && !halfOpen)
                {
                    entryBarIdx = CurrentBar;
                    dayCount++;
                    be = false; best = double.NaN; halfFilled = false;
                }
                if (n == RunnerName) { runnerOpen = true; runnerFill = price; }
                else { halfOpen = true; halfFill = price; }
                return;
            }
            string from = execution.Order.FromEntrySignal ?? "";
            if (from == RunnerName && runnerOpen) { runnerOpen = false; runnerExit = price; runnerWhy = n; }
            else if (from == HalfName && halfOpen)
            {
                halfOpen = false; halfExit = price; halfWhy = n;
                if (n == "Profit target") halfFilled = true;
            }
            else return;
            if (!runnerOpen && !halfOpen && marketPosition == MarketPosition.Flat)
                Finish();
        }

        void Finish()
        {
            int d = campDir;
            double pnl = 0;
            if (!double.IsNaN(runnerFill)) pnl += d * (runnerExit - runnerFill) * pv - 2 * SizingCommission;
            if (!double.IsNaN(halfFill)) pnl += d * (halfExit - halfFill) * pv - 2 * SizingCommission;
            ledger.Add("D position," + campSleeve + "," + d + "," + campKind + "," + campSignalBar + "," + entryBarIdx + "," +
                       CurrentBar + "," + F(runnerFill) + "," + F(runnerExit) + "," + runnerWhy + "," + F(halfFill) + "," +
                       F(halfExit) + "," + halfWhy + "," + F(campStop0) + "," + F(campR) + "," + F(campPlanned) + "," + F(pnl) +
                       (pnl < -campPlanned - 1e-9 ? ",overrun" : ","));
            inCampaign = false;
            entryBarIdx = -1;
            if (Pending && !cancelSent) CancelPending();
        }

        // The evaluation account (the firm's limits, apart from the strategy's preferences): the highest equity including
        // open P/L, kept across sessions and restarts; at the target the position is closed and trading stops; at the
        // trailing threshold, the same. Off in research runs (EvalTarget 0, EvalTrail 0): research/eval_d.py replays it.
        void Account_(double h, double l, double c)
        {
            if (accountDone || (EvalTarget <= 0 && EvalTrail <= 0)) return;
            double closed = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
            double open = Exposed ? Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, c) : 0;
            double eq = AccountStart + closed + open;
            double hi = eq;
            if (Exposed && entryBarIdx >= 0 && CurrentBar > entryBarIdx)  // exposed for the whole bar: its best price counts
                hi = AccountStart + closed + Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency,
                                                                               Position.MarketPosition == MarketPosition.Long ? h : l);
            if (double.IsNaN(peak) || hi > peak) { peak = hi; SaveAccount(); }
            if (EvalTarget > 0 && eq - AccountStart >= EvalTarget) Stop("passed");
            else if (EvalTrail > 0 && eq <= peak - EvalTrail) Stop("breached");
        }

        void Stop(string why)
        {
            accountDone = true;
            accountState = why;
            Print(Time[0] + "  evaluation " + why + ": equity threshold " + F(peak - EvalTrail) + ", highest equity " + F(peak));
            if (Pending) CancelPending();
            if (Position.MarketPosition == MarketPosition.Long) ExitLong("Evaluation " + why, "");
            else if (Position.MarketPosition == MarketPosition.Short) ExitShort("Evaluation " + why, "");
            SaveAccount();
        }

        string AccountFile
        {
            get
            {
                string name = Account == null ? "none" : Account.Name;
                return Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "MnqCandidateD-" + name + ".txt");
            }
        }

        void LoadAccount()
        {
            if (!RememberAccount || !File.Exists(AccountFile)) return;
            string[] p = File.ReadAllText(AccountFile).Trim().Split(',');
            double v;
            if (p.Length > 0 && double.TryParse(p[0], NumberStyles.Float, CultureInfo.InvariantCulture, out v) &&
                (double.IsNaN(peak) || v > peak))
                peak = v;
            if (p.Length > 1 && p[1].Length > 0) { accountDone = true; accountState = p[1]; }
            Print("D account: highest equity " + F(peak) + (accountState.Length > 0 ? ", " + accountState : "") + " (from " + AccountFile + ")");
        }

        void SaveAccount()
        {
            if (!RememberAccount || State != State.Realtime) return;
            File.WriteAllText(AccountFile, peak.ToString("R", CultureInfo.InvariantCulture) + "," + accountState);
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Sleeve: noise momentum (D)", Order = 1, GroupName = "1. Sleeves")]
        public bool UseNoise { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Sleeve: Williams breakout (D)", Order = 2, GroupName = "1. Sleeves")]
        public bool UseWilliams { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Sleeve: sweep reversal, higher-timeframe pools (E1)", Order = 3, GroupName = "1. Sleeves")]
        public bool UseE1 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Sleeve: sweep reversal, + session pools (E2)", Order = 4, GroupName = "1. Sleeves")]
        public bool UseE2 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Sweep initial stop: sweep extreme (E) or FVG far edge + 2 ticks (F)", Order = 5, GroupName = "1. Sleeves")]
        public SweepStopReference SweepStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Stop wider than the budget: Skip (D, E, F), Cap to the budget (G), Budget always", Order = 6, GroupName = "1. Sleeves")]
        public StopFitMode StopFit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Noise campaigns: runner trail R (D-F), Line (G), Line2R", Order = 7, GroupName = "1. Sleeves")]
        public RunnerTrailMode RunnerTrail { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10000)]
        [Display(Name = "Planned risk budget a position, $ (2 contracts, all-in)", Order = 1, GroupName = "2. Position manager")]
        public double RiskBudget { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Commission a side a contract, $ (for sizing and breakeven)", Order = 2, GroupName = "2. Position manager")]
        public double SizingCommission { get; set; }

        [NinjaScriptProperty]
        [Range(0, 40)]
        [Display(Name = "Slippage allowance, ticks a contract, market entry", Order = 3, GroupName = "2. Position manager")]
        public int AllowanceMarketTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 40)]
        [Display(Name = "Slippage allowance, ticks a contract, limit entry", Order = 4, GroupName = "2. Position manager")]
        public int AllowanceLimitTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Breakeven stop, points past the fill", Order = 5, GroupName = "2. Position manager")]
        public double BreakevenOffset { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 20)]
        [Display(Name = "Half off at this many R", Order = 6, GroupName = "2. Position manager")]
        public double PartialR { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 20)]
        [Display(Name = "Runner trail, R behind the best price", Order = 7, GroupName = "2. Position manager")]
        public double TrailR { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Entry campaigns a day, all sleeves", Order = 8, GroupName = "2. Position manager")]
        public int MaxCampaigns { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Flat: exit sent at this bar's close (minute of day, 954 = 15:54)", Order = 9, GroupName = "2. Position manager")]
        public int FlatBar { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5)]
        [Display(Name = "Noise line stop, noise units past the line", Order = 1, GroupName = "3. Signals")]
        public double StopBuffer { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Skip dates (no entries)", Order = 2, GroupName = "3. Signals")]
        public string SkipDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "FOMC dates (no noise shorts before 14:00; no E)", Order = 3, GroupName = "3. Signals")]
        public string FedDates { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "NFP dates (no E)", Order = 4, GroupName = "3. Signals")]
        public string NfpDates { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Evaluation: target, $ (0 = off)", Order = 1, GroupName = "4. Account")]
        public double EvalTarget { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Evaluation: trailing drawdown, $ (0 = off)", Order = 2, GroupName = "4. Account")]
        public double EvalTrail { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Account starting balance, $", Order = 3, GroupName = "4. Account")]
        public double AccountStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Remember the highest equity across restarts (a file)", Order = 4, GroupName = "4. Account")]
        public bool RememberAccount { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Place orders", Order = 5, GroupName = "4. Account")]
        public bool PlaceOrders { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Print refusals (the daily opportunity audit)", Order = 6, GroupName = "4. Account")]
        public bool AuditOutput { get; set; }
        #endregion
    }
}
