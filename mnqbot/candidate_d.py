"""Candidates D and E (docs/CANDIDATE_D.md): the shared position manager and the noise, Williams and sweep sleeves.

A bar-by-bar model of ninjatrader/Strategies/MnqCandidateD.cs on the NinjaTrader stand-in, with the stand-in's fill
model, so the two agree trade for trade (tests/test_candidate_d.py). Bars: 1 minute, New York start times, the full
electronic session. Per bar, in the stand-in's order: a market exit sent at the last close fills at this open; market
entries fill at this open; limit entries fill when price trades a tick through them (at the open if it opens past);
each contract's stop, then its take-profit; then the strategy's decisions at this bar's close.

Prices on rescaled NQ: an optional "scale" column gives each bar's factor (each month of the NQ file is rescaled by its
own); every level carried from one bar to a later one is kept in raw units (price / scale) and converted with the later
bar's factor. On the user's MNQ bars the factor is 1 and the arithmetic is the NinjaScript's.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TICK, PV = 0.25, 2.0
NCHECKS, FIRST_CHECK, LAST_CHECK, STEP, RTH_OPEN, RTH_CLOSE, FED_CUTOFF = 12, 600, 930, 30, 570, 960, 840
NY = "America/New_York"

# the pools, in priority order (E1 before E2, lows before highs); +1: a low pool (a sweep of it sets up a long)
E1_POOLS = (("PDL", 1), ("PDH", -1), ("PWL", 1), ("PWH", -1))
E2_POOLS = (("ONL", 1), ("ONH", -1), ("ASL", 1), ("ASH", -1), ("LOL", 1), ("LOH", -1))


def monday(day: str) -> str:
    """The Monday of the calendar week of a session date ("yyyy-mm-dd"): the week's key."""
    t = pd.Timestamp(day)
    return (t - pd.Timedelta(days=t.weekday())).strftime("%Y-%m-%d")


def floor_tick(x: float) -> float:
    return math.floor(x / TICK + 1e-7) * TICK


def ceil_tick(x: float) -> float:
    return math.ceil(x / TICK - 1e-7) * TICK


def away(d: int, price: float) -> float:
    """A stop on the grid, rounded away from the entry (never closer): a long's down, a short's up."""
    return floor_tick(price) if d > 0 else ceil_tick(price)


def toward(d: int, price: float) -> float:
    """A moving stop on the grid, rounded toward the price: a long's up, a short's down."""
    return ceil_tick(price) if d > 0 else floor_tick(price)


@dataclass
class DConfig:
    noise: bool = True
    williams: bool = True
    e1: bool = False
    e2: bool = False  # the session-level pools, on top of E1's (D + E2 has both)
    slippage_ticks: int = 2
    commission: float = 0.95  # $ a side a contract
    budget: float = 125.0  # planned all-in risk of a position, $
    qty: int = 2  # always two: one runner, one half
    allowance_market: int = 4  # declared slippage allowance, ticks a contract: 2 at the entry and 2 at the stop
    allowance_limit: int = 2  # a limit entry: 2 at the stop
    be_offset: float = 1.50  # points past the fill: the round trip (0.95 point) plus 2 ticks, rounded up to the tick
    be_r: float = 1.0
    partial_r: float = 2.0
    trail_r: float = 1.0
    max_campaigns: int = 3
    flat_bar: int = 954  # the market exit is sent at this bar's close (start 15:54) and fills at 15:55
    lookback: int = 14
    stop_buffer: float = 0.24
    w_k: float = 0.5
    w_stop: float = 0.25
    w_last_entry: int = 900
    skip_dates: frozenset = frozenset()
    fed_dates: frozenset = frozenset()
    nfp_dates: frozenset = frozenset()
    # E
    pen_first: int = 575  # penetrations by 1-minute bars starting 09:35 ..
    pen_last: int = 870  # .. 14:30
    decide_first: int = 585  # decisions at bar ends 09:45 ..
    decide_last: int = 900  # .. 15:00
    reclaim_bars: int = 6  # the reclaim within this many five-minute bars from the penetration's (included)
    bos_bars: int = 12  # the BOS no later than this many five-minute bars after the penetration's
    fvg_after_bos: int = 3
    atr_len: int = 14
    atr_mult: float = 0.1
    limit_minutes: int = 30
    limit_cancel_end: int = 930  # a pending limit is cancelled at the close of the bar ending 15:30
    room_cost: float = 1.45  # points: the round-trip cost allowance for the room test
    # the sweep setups' initial stop (docs/CANDIDATE_F.md): "extreme" (E: the sweep extreme - 0.1 ATR) or "fvg" (F: the
    # selected FVG's far boundary - 2 ticks)
    e_stop: str = "extreme"
    fvg_stop_ticks: int = 2


@dataclass
class Lot:
    name: str  # "runner" / "half"
    qty: int
    fill: float
    fill_bar: int
    stop: float
    target: float  # nan: none
    limit_fill: bool
    exit_bar: int = -1
    exit: float = math.nan
    why: str = ""


@dataclass
class Campaign:
    sleeve: str
    d: int
    signal_bar: int
    expected: float
    stop0: float
    r: float
    planned: float  # $ all-in, both contracts
    kind: str  # "market" / "limit"
    day: str = ""
    lots: list = field(default_factory=list)
    pnl: float = 0.0


class NoiseLines:
    """The noise lines of MnqNoiseEngine (NoiseEngine), without its model position."""

    def __init__(self, cfg: DConfig):
        self.lb = cfg.lookback
        self.skip, self.fed = cfg.skip_dates, cfg.fed_dates
        self.ring = [math.nan] * (self.lb * NCHECKS)
        self.today = [math.nan] * NCHECKS
        self.filled = self.slot = 0
        self.day_open = self.prev_close = self.last_raw = math.nan
        self.upper = self.lower = self.sigma = math.nan
        self.skip_today = self.fed_today = False
        self.check_end = 0  # the check this bar closed (bar end minute), 0 none

    def on_bar(self, tmin: int, o: float, c: float, day: str, scale: float) -> None:
        end = tmin + 1
        in_rth = tmin >= RTH_OPEN and end <= RTH_CLOSE
        self.check_end = 0
        if tmin == RTH_OPEN:
            self.prev_close = self.last_raw * scale
            self.day_open = o
            self.upper = self.lower = self.sigma = math.nan
            self.today = [math.nan] * NCHECKS
            self.skip_today = day in self.skip
            self.fed_today = day in self.fed
        if in_rth:
            self.last_raw = c / scale
        if (in_rth and not math.isnan(self.day_open) and FIRST_CHECK <= end <= LAST_CHECK
                and (end - FIRST_CHECK) % STEP == 0):
            k = (end - FIRST_CHECK) // STEP
            self.today[k] = abs(c / self.day_open - 1)
            if self.filled >= self.lb and not math.isnan(self.prev_close):
                s = 0.0
                for d in range(self.lb):
                    s += self.ring[d * NCHECKS + k]
                self.sigma = s / self.lb
                self.upper = max(self.day_open, self.prev_close) * (1 + self.sigma)
                self.lower = min(self.day_open, self.prev_close) * (1 - self.sigma)
                self.check_end = end
        if in_rth and end == RTH_CLOSE:
            if not math.isnan(self.day_open) and not any(math.isnan(x) for x in self.today):
                self.ring[self.slot * NCHECKS:(self.slot + 1) * NCHECKS] = self.today
                self.slot = (self.slot + 1) % self.lb
                self.filled += 1
            self.day_open = math.nan

    @property
    def ready(self) -> bool:
        return self.filled >= self.lb and not math.isnan(self.prev_close)


class Williams:
    """WilliamsBreakout (MnqNoiseEngine.cs) with its own sizing off: the day's one chance and the stop distance."""

    def __init__(self, cfg: DConfig):
        self.k, self.frac, self.last = cfg.w_k, cfg.w_stop, cfg.w_last_entry
        self.prev_raw = math.nan
        self.hi_raw = self.lo_raw = math.nan
        self.done = True
        self.up = self.down = math.nan
        self.signal = 0
        self.stop_pts = math.nan
        self.raw = 0

    def on_bar(self, tmin: int, o: float, h: float, l: float, allowed: bool, scale: float) -> None:
        self.signal = 0
        self.raw = 0  # this bar's level touch, allowed or not (2: both levels): the daily audit's raw setup
        if tmin == RTH_OPEN:
            if not math.isnan(self.hi_raw):
                self.prev_raw = self.hi_raw - self.lo_raw
            self.hi_raw = self.lo_raw = math.nan
            prev = self.prev_raw * scale
            self.done = math.isnan(prev) or prev <= 0
            self.up = math.nan if self.done else o + self.k * prev
            self.down = math.nan if self.done else o - self.k * prev
        if RTH_OPEN <= tmin < RTH_CLOSE:
            self.hi_raw = h / scale if math.isnan(self.hi_raw) else max(self.hi_raw, h / scale)
            self.lo_raw = l / scale if math.isnan(self.lo_raw) else min(self.lo_raw, l / scale)
        if self.done or tmin < RTH_OPEN:
            return
        if tmin > self.last:
            self.done = True
            return
        hu, hd = h >= self.up, l <= self.down
        if not hu and not hd:
            return
        self.done = True
        self.raw = 2 if (hu and hd) else (1 if hu else -1)
        if hu and hd:
            return
        if not allowed:
            return
        self.signal = 1 if hu else -1
        self.stop_pts = self.frac * self.prev_raw * scale


class Sweep:
    """Sleeve E's causal sequence on five-minute bars: pool, penetration, reclaim, BOS, FVG (docs/CANDIDATE_D.md 3).
    Everything kept in raw units (price / scale); feed every 1-minute bar; .decisions holds this bar's decisions."""

    def __init__(self, cfg: DConfig):
        self.cfg = cfg
        self.pools_on = list(E1_POOLS) + (list(E2_POOLS) if cfg.e2 else [])
        self.fb: list[tuple[float, float, float, float]] = []  # completed five-minute bars (o, h, l, c), raw
        self.cur = None  # the five-minute bar being built: [key, o, h, l, c]
        self.swing_hi: list[tuple[int, int, float]] = []  # (formation, confirmation, price)
        self.swing_lo: list[tuple[int, int, float]] = []
        self.fvg_bull: list[tuple[int, float, float]] = []  # (k, proximal edge low[k], far edge high[k-2])
        self.fvg_bear: list[tuple[int, float, float]] = []  # (k, proximal edge high[k], far edge low[k-2])
        self.atr = math.nan
        self.tr_seed: list[float] = []
        self.prev_c = math.nan
        # sessions: RTH high / low per session, per ISO week; this session's electronic-hours pools
        self.sess = None
        self.rth_hi = self.rth_lo = math.nan
        self.prev_rth = (math.nan, math.nan)
        self.week_key = None
        self.week_hi = self.week_lo = math.nan
        self.prev_week = (math.nan, math.nan)
        self.eth = {"ON": [math.nan, math.nan], "AS": [math.nan, math.nan], "LO": [math.nan, math.nan]}
        self.pools: dict[str, float] = {}  # today's pools, raw
        self.used: set[str] = set()
        self.setups: list[dict] = []
        self.decisions: list[dict] = []
        self.penetrations: list[tuple] = []
        self.active_day = False

    # ---- five-minute bars -------------------------------------------------------------------------------------
    def _complete(self) -> None:
        _, o, h, l, c = self.cur
        self.cur = None
        self.fb.append((o, h, l, c))
        b = len(self.fb) - 1
        tr = h - l if math.isnan(self.prev_c) else max(h - l, abs(h - self.prev_c), abs(l - self.prev_c))
        self.prev_c = c
        n = self.cfg.atr_len
        if len(self.tr_seed) < n:
            self.tr_seed.append(tr)
            if len(self.tr_seed) == n:
                s = 0.0
                for x in self.tr_seed:
                    s += x
                self.atr = s / n
        else:
            self.atr = (self.atr * (n - 1) + tr) / n
        if b >= 4:
            j = b - 2
            hj, lj = self.fb[j][1], self.fb[j][2]
            if all(hj > self.fb[x][1] for x in (j - 2, j - 1, j + 1, j + 2)):
                self.swing_hi.append((j, b, hj))
            if all(lj < self.fb[x][2] for x in (j - 2, j - 1, j + 1, j + 2)):
                self.swing_lo.append((j, b, lj))
        if b >= 2:
            if l > self.fb[b - 2][1]:
                self.fvg_bull.append((b, l, self.fb[b - 2][1]))
            if h < self.fb[b - 2][2]:
                self.fvg_bear.append((b, h, self.fb[b - 2][2]))
        self._advance(b)

    def _advance(self, b: int) -> None:
        cfg = self.cfg
        o, h, l, c = self.fb[b]
        for s in self.setups:
            if s["state"] == "dead":
                continue
            d = s["d"]
            if s["state"] == "reclaim":
                if d * (c - s["level"]) > 0:
                    swings = self.swing_hi if d > 0 else self.swing_lo
                    ref = None
                    for f, conf, px in swings:
                        if f < s["pen"] and conf <= b and (ref is None or f > ref[0]):
                            ref = (f, px)
                    if ref is None:
                        s["state"] = "dead"
                        continue
                    s["ref"] = ref[1]
                    s["state"] = "bos"
                elif b >= s["pen"] + cfg.reclaim_bars - 1:
                    s["state"] = "dead"
                    continue
            if s["state"] == "bos":
                if b > s["pen"] + cfg.bos_bars:
                    s["state"] = "dead"
                    continue
                if d * (c - s["ref"]) > 0:
                    s["bos"] = b
                    s["state"] = "fvg"
            if s["state"] == "fvg":
                gaps = self.fvg_bull if d > 0 else self.fvg_bear
                pick = None
                for k, edge, far in gaps:
                    if k - 2 >= s["pen"] and k <= b and (pick is None or k > pick[0]):
                        pick = (k, edge, far)
                if pick is not None:
                    s["state"] = "dead"
                    self.decisions.append({"pool": s["pool"], "d": d, "limit_raw": pick[1], "far_raw": pick[2],
                                           "fvg": pick[0],
                                           "extreme_raw": s["extreme"], "atr_raw": self.atr, "pen": s["pen"],
                                           "bos": s["bos"], "ref_raw": s["ref"], "level_raw": s["level"]})
                elif b >= s["bos"] + cfg.fvg_after_bos:
                    s["state"] = "dead"

    # ---- per 1-minute bar ----------------------------------------------------------------------------------
    def on_bar(self, t: pd.Timestamp, tmin: int, day: str, o: float, h: float, l: float, c: float,
               scale: float, allowed_day: bool) -> None:
        self.decisions = []
        self.penetrations = []  # (pool, d) penetrated on this bar: the daily audit's raw sweep setups
        ro, rh, rl, rc = o / scale, h / scale, l / scale, c / scale
        # the five-minute bucket: New York wall-clock minutes // 5 (as the NinjaScript computes it)
        wall = t.tz_localize(None) if t.tzinfo is not None else t
        key = (wall.value // 60_000_000_000) // 5
        if self.cur is not None and self.cur[0] != key:
            self._complete()
        # sessions and pools
        sess_day = day
        if sess_day != self.sess:
            self.sess = sess_day
            self.eth = {"ON": [math.nan, math.nan], "AS": [math.nan, math.nan], "LO": [math.nan, math.nan]}
        if tmin == RTH_OPEN:
            self._open_day(day, allowed_day)
        if tmin < RTH_OPEN or tmin >= 1080:  # this session's electronic hours before 09:30 (18:00 on)
            for name, on in (("ON", True), ("AS", tmin >= 1080 or tmin < 120), ("LO", 120 <= tmin < 510)):
                if on:
                    v = self.eth[name]
                    v[0] = rh if math.isnan(v[0]) else max(v[0], rh)
                    v[1] = rl if math.isnan(v[1]) else min(v[1], rl)
        if RTH_OPEN <= tmin < RTH_CLOSE:
            self.rth_hi = rh if math.isnan(self.rth_hi) else max(self.rth_hi, rh)
            self.rth_lo = rl if math.isnan(self.rth_lo) else min(self.rth_lo, rl)
            self.week_hi = rh if math.isnan(self.week_hi) else max(self.week_hi, rh)
            self.week_lo = rl if math.isnan(self.week_lo) else min(self.week_lo, rl)
        # the five-minute bar
        if self.cur is None:
            self.cur = [key, ro, rh, rl, rc]
        else:
            self.cur[2] = max(self.cur[2], rh)
            self.cur[3] = min(self.cur[3], rl)
            self.cur[4] = rc
        # live setups: the sweep extreme
        for s in self.setups:
            if s["state"] != "dead":
                s["extreme"] = min(s["extreme"], rl) if s["d"] > 0 else max(s["extreme"], rh)
        # penetrations
        if self.active_day and self.cfg.pen_first <= tmin <= self.cfg.pen_last:
            for name, d in self.pools_on:
                if name in self.used or name not in self.pools:
                    continue
                lvl = self.pools[name] * scale
                if (d > 0 and l <= lvl - TICK) or (d < 0 and h >= lvl + TICK):
                    self.used.add(name)
                    self.penetrations.append((name, d))
                    self.setups.append({"pool": name, "d": d, "level": self.pools[name], "pen": len(self.fb),
                                        "extreme": rl if d > 0 else rh, "state": "reclaim", "ref": math.nan,
                                        "bos": -1})
        if tmin % 5 == 4:
            self._complete()

    def _open_day(self, day: str, allowed_day: bool) -> None:
        if not math.isnan(self.rth_hi):
            self.prev_rth = (self.rth_hi, self.rth_lo)
        self.rth_hi = self.rth_lo = math.nan
        wk = monday(day)
        if wk != self.week_key:  # a new week: last week's range is complete
            if self.week_key is not None:
                self.prev_week = (self.week_hi, self.week_lo)
            self.week_key = wk
            self.week_hi = self.week_lo = math.nan
        pools = {"PDH": self.prev_rth[0], "PDL": self.prev_rth[1], "PWH": self.prev_week[0], "PWL": self.prev_week[1],
                 "ONH": self.eth["ON"][0], "ONL": self.eth["ON"][1], "ASH": self.eth["AS"][0],
                 "ASL": self.eth["AS"][1], "LOH": self.eth["LO"][0], "LOL": self.eth["LO"][1]}
        self.pools = {k: v for k, v in pools.items() if not math.isnan(v)}
        self.used = set()
        self.setups = []
        self.active_day = allowed_day

    def room_levels(self, d: int) -> list[float]:
        """The opposing pools of the candidate's set (raw): highs for a long, lows for a short."""
        return [self.pools[n] for n, pd_ in self.pools_on if pd_ == -d and n in self.pools]


def sweep_prices(dec: dict, scale: float, cfg: DConfig, mode: str | None = None) -> tuple[float, float, float, float]:
    """A sweep decision's limit, initial stop, R (points) and planned all-in risk ($, both contracts), in the decision
    bar's prices. mode: "extreme" (E) or "fvg" (F); default the configuration's. Both round the stop away from the
    entry, the limit down for a long and up for a short."""
    d = dec["d"]
    lim = (floor_tick if d > 0 else ceil_tick)(dec["limit_raw"] * scale)
    if (mode or cfg.e_stop) == "fvg":
        stop = away(d, dec["far_raw"] * scale - d * cfg.fvg_stop_ticks * TICK)
    else:
        stop = away(d, (dec["extreme_raw"] - d * cfg.atr_mult * dec["atr_raw"]) * scale)
    r = d * (lim - stop)
    planned = cfg.qty * (r * PV + 2 * cfg.commission + cfg.allowance_limit * TICK * PV)
    return lim, stop, r, planned


def room_ok(d: int, lim: float, r: float, levels_raw: list[float], scale: float, cfg: DConfig) -> bool:
    """The room test: the nearest opposing pool beyond the limit at least 2R + 1.45 points away (none: no limit)."""
    rooms = [d * (x * scale - lim) for x in levels_raw]
    rooms = [x for x in rooms if x > 0]
    return not rooms or min(rooms) >= cfg.partial_r * r + cfg.room_cost


class Model:
    """The strategy and the stand-in's fill model, bar by bar."""

    def __init__(self, cfg: DConfig):
        self.cfg = cfg
        self.slip = cfg.slippage_ticks * TICK
        self.noise = NoiseLines(cfg)
        self.wb = Williams(cfg)
        self.sweep = Sweep(cfg) if (cfg.e1 or cfg.e2) else None
        self.lots: list[Lot] = []
        self.pend: list[dict] = []  # entry orders: name, d, kind, limit, placed
        self.pend_exit: str | None = None
        self.entry_bar = -1  # the position's first fill bar
        self.camp: Campaign | None = None
        self.campaigns: list[Campaign] = []
        self.day_count = 0
        self.day = None
        self.be = False
        self.best = math.nan
        self.half_filled = False
        self.stop = math.nan
        self.log: list[tuple] = []  # every decision: (bar, what, detail)
        # the daily opportunity audit (docs/DAILY_AUDIT.md): (bar, sleeve, direction, outcome) for every raw setup;
        # a record only, nothing here changes a decision
        self.audit: list[tuple] = []
        self.sweep_seen: list[tuple] = []  # every sweep decision: (bar, scale, decision, its room levels raw)
        self.prefix = "F:" if cfg.e_stop == "fvg" else "E:"

    # ---- the stand-in's fills ---------------------------------------------------------------------------------
    def _close(self, lot: Lot, i: int, px: float, why: str) -> None:
        lot.exit_bar, lot.exit, lot.why = i, px, why
        self.lots.remove(lot)
        if not self.lots:
            self._finish()

    def _finish(self) -> None:
        c = self.camp
        c.pnl = sum(lt.qty * (c.d * (lt.exit - lt.fill) * PV - 2 * self.cfg.commission) for lt in c.lots)
        self.campaigns.append(c)
        self.camp = None
        self.entry_bar = -1

    def _fill(self, i: int, o: float, h: float, l: float) -> None:
        slip = self.slip
        if self.pend_exit is not None and self.lots:
            for lot in list(self.lots):
                self._close(lot, i, o - self.camp.d * slip, self.pend_exit)
        self.pend_exit = None
        for p in [x for x in self.pend if x["kind"] == "market" and x["placed"] < i]:
            self._open_lot(p, i, o + p["d"] * slip, False)
        for p in [x for x in self.pend if x["kind"] == "limit" and x["placed"] < i]:
            d, lim = p["d"], p["limit"]
            if d * (lim - o) >= 0:  # it opens at or past the limit
                self._open_lot(p, i, o, True)
            elif (d > 0 and l <= lim - TICK) or (d < 0 and h >= lim + TICK):
                self._open_lot(p, i, lim, True)
        if self.lots:
            d = self.camp.d
            for lot in list(self.lots):
                st = lot.stop
                if self.entry_bar == i:
                    hit = l <= st if d > 0 else h >= st
                    px = (min(o, st) if d > 0 else max(o, st)) - d * slip
                elif (d > 0 and o <= st) or (d < 0 and o >= st):
                    hit, px = True, o - d * slip
                else:
                    hit = l <= st if d > 0 else h >= st
                    px = st - d * slip
                if hit:
                    self._close(lot, i, px, "Stop loss")
            for lot in list(self.lots):
                if math.isnan(lot.target) or (lot.limit_fill and lot.fill_bar == i):
                    continue
                if (d > 0 and h >= lot.target + TICK) or (d < 0 and l <= lot.target - TICK):
                    self._close(lot, i, lot.target, "Profit target")
                    self.half_filled = True

    def _open_lot(self, p: dict, i: int, px: float, limit: bool) -> None:
        self.pend.remove(p)
        c = self.camp
        if not self.lots:
            self.entry_bar = i
            self.day_count += 1
            self.be, self.best, self.half_filled, self.stop = False, math.nan, False, c.stop0
        tgt = math.nan
        if p["name"] == "half":
            tgt = px + c.d * self.cfg.partial_r * c.r  # the bracket in ticks from the fill: exact on the grid
        lot = Lot(p["name"], 1, px, i, self.stop, tgt, limit)
        self.lots.append(lot)
        c.lots.append(lot)

    # ---- the strategy at a bar's close ----------------------------------------------------------------------
    def _manage(self, i: int, tmin: int, day: str, h: float, l: float, c: float) -> None:
        cp, cfg = self.camp, self.cfg
        d, avg, r = cp.d, self.lots[0].fill, cp.r
        if tmin >= cfg.flat_bar or tmin < RTH_OPEN or day != cp.day:
            self.pend_exit = "Flat 15:55" if tmin == cfg.flat_bar else "Session ended"
            self.log.append((i, "exit", self.pend_exit))
            return
        fresh_limit = cp.kind == "limit" and i == self.entry_bar
        if not fresh_limit:
            ext = h if d > 0 else l
            self.best = ext if math.isnan(self.best) else (max(self.best, ext) if d > 0 else min(self.best, ext))
            if not self.be and d * (ext - avg) >= cfg.be_r * r:
                self.be = True
        new = self.stop
        if self.be:
            be = avg + d * cfg.be_offset
            new = max(new, be) if d > 0 else min(new, be)
        if self.half_filled and not math.isnan(self.best):
            tr = toward(d, self.best - d * cfg.trail_r * r)
            new = max(new, tr) if d > 0 else min(new, tr)
        if new != self.stop:
            if d * (c - new) <= 0:
                self.pend_exit = "Stop passed"
                self.log.append((i, "exit", "Stop passed"))
                return
            self.stop = new
            for lot in self.lots:
                lot.stop = new
            self.log.append((i, "stop", new))

    def _manage_pending(self, i: int, tmin: int, h: float, l: float) -> None:
        cp, cfg = self.camp, self.cfg
        if cp.kind != "limit":
            return
        lim, d, r = self.pend[0]["limit"], cp.d, cp.r
        why = ""
        if i - self.pend[0]["placed"] >= cfg.limit_minutes:
            why = "expired"
        elif (d > 0 and l <= cp.stop0) or (d < 0 and h >= cp.stop0):
            why = "stop traded"
        elif (d > 0 and h >= lim + cfg.partial_r * r) or (d < 0 and l <= lim - cfg.partial_r * r):
            why = "ran away"
        elif tmin + 1 >= cfg.limit_cancel_end:
            why = "15:30"
        if why:
            self.pend.clear()
            self.log.append((i, "cancel", why))
            if not self.lots:  # nothing filled: no campaign
                self.camp = None

    def _try_enter(self, i: int, tmin: int, day: str, c: float, scale: float) -> None:
        cfg = self.cfg
        cands = []
        if cfg.noise and self.noise.check_end and self.noise.ready and not self.noise.skip_today:
            end = self.noise.check_end
            if c > self.noise.upper:
                cands.append(("noise", 1, self.noise.upper * (1 - cfg.stop_buffer * self.noise.sigma)))
            elif c < self.noise.lower and not (self.noise.fed_today and end < FED_CUTOFF):
                cands.append(("noise", -1, self.noise.lower * (1 + cfg.stop_buffer * self.noise.sigma)))
        if cfg.williams and self.wb.signal != 0:
            d = self.wb.signal
            cands.append(("williams", d, c - d * self.wb.stop_pts))
        for n, (name, d, structural) in enumerate(cands):
            stop = away(d, structural)
            r = d * (c - stop)
            planned = cfg.qty * (r * PV + 2 * cfg.commission + cfg.allowance_market * TICK * PV)
            if r <= 0 or planned > cfg.budget + 1e-9:
                self.log.append((i, "skip", name, r, planned))
                self.audit.append((i, name, d, "unaffordable"))
                continue
            self._submit(i, name, d, "market", c, stop, r, planned, day)
            self.audit.append((i, name, d, "entered"))
            for nm, dd, _ in cands[n + 1:]:
                self.audit.append((i, nm, dd, "same-bar priority"))
            self._displaced(i, self.sweep.decisions if self.sweep is not None else [], "priority")
            return
        if self.sweep is not None:
            end = tmin + 1
            for n, dec in enumerate(self.sweep.decisions):
                d = dec["d"]
                if not (cfg.decide_first <= end <= cfg.decide_last) or day in cfg.skip_dates:
                    self.log.append((i, "skip", dec["pool"], "time"))
                    self.audit.append((i, "sweep", d, "not qualified: decision window"))
                    continue
                lim, stop, r, planned = sweep_prices(dec, scale, cfg)
                if r <= 0 or planned > cfg.budget + 1e-9:
                    self.log.append((i, "skip", dec["pool"], r, planned))
                    self.audit.append((i, "sweep", d, "unaffordable"))
                    continue
                if not room_ok(d, lim, r, self.sweep.room_levels(d), scale, cfg):
                    self.log.append((i, "skip", dec["pool"], "room"))
                    self.audit.append((i, "sweep", d, "not qualified: room"))
                    continue
                self._submit(i, self.prefix + dec["pool"], d, "limit", lim, stop, r, planned, day)
                self.audit.append((i, "sweep", d, "entered (limit placed)"))
                self._displaced(i, self.sweep.decisions[n + 1:], "priority")
                return

    def _displaced(self, i: int, decisions: list, why: str) -> None:
        """Sweep decisions not considered (a log entry only): an entry taken first on this bar ("priority"), or no
        entry allowed ("position", "campaigns", "closed")."""
        for dec in decisions:
            self.log.append((i, "skip", dec["pool"], why))
            self.audit.append((i, "sweep", dec["d"], "same-bar priority" if why == "priority" else self._blocked_why()))

    def _blocked_why(self) -> str:
        """Why a qualified setup could not be taken now (no entry allowed): the audit's refusal reason."""
        if self.lots:
            return "blocked: position"
        if self.pend or self.camp is not None:
            return "blocked: pending order"
        if self.day_count >= self.cfg.max_campaigns:
            return "blocked: daily entry budget exhausted"
        if self.day in self.cfg.skip_dates:
            return "skip day"
        return "blocked: after the entry window"

    def _submit(self, i, sleeve, d, kind, price, stop, r, planned, day) -> None:
        self.camp = Campaign(sleeve, d, i, price, stop, r, planned, kind, day)
        for name in ("runner", "half"):
            self.pend.append({"name": name, "d": d, "kind": kind, "limit": price, "placed": i})
        self.log.append((i, "enter", sleeve, d, kind, price, stop, r))

    def step(self, i: int, t: pd.Timestamp, o: float, h: float, l: float, c: float, scale: float) -> None:
        cfg = self.cfg
        tmin = t.hour * 60 + t.minute
        day = (t + pd.Timedelta(hours=6)).strftime("%Y-%m-%d")  # the trading day starts at 18:00
        self._fill(i, o, h, l)
        if tmin == RTH_OPEN and day != self.day:
            self.day, self.day_count = day, 0
        flat_now = not self.lots and not self.pend
        allowed = flat_now and self.day_count < cfg.max_campaigns and day not in cfg.skip_dates and tmin < cfg.flat_bar
        self.noise.on_bar(tmin, o, c, day, scale)
        self.wb.on_bar(tmin, o, h, l, allowed, scale)
        if self.sweep is not None:
            e_day = day not in cfg.skip_dates and day not in cfg.fed_dates and day not in cfg.nfp_dates
            self.sweep.on_bar(t, tmin, day, o, h, l, c, scale, e_day)
            for dec in self.sweep.decisions:
                self.log.append((i, "E decision", dec["pool"], dec["limit_raw"], dec["extreme_raw"], dec["atr_raw"],
                                 dec["far_raw"]))
                self.sweep_seen.append((i, scale, dec, self.sweep.room_levels(dec["d"])))
        self._audit_raw(i, day, c, allowed)
        if self.lots:
            self._manage(i, tmin, day, h, l, c)
        if self.pend and self.camp is not None and not self.lots:
            self._manage_pending(i, tmin, h, l)
        elif self.pend and self.lots:  # one contract filled, the other still working: cancel it
            self.pend.clear()
            self.log.append((i, "cancel", "partial"))
        can_enter = allowed and not self.lots and not self.pend and self.camp is None
        if can_enter:
            self._try_enter(i, tmin, day, c, scale)
        else:
            self._audit_blocked(i, day, c)
        if not can_enter and self.sweep is not None and self.sweep.decisions:
            busy = self.lots or self.pend or self.camp is not None or not flat_now
            why = "position" if busy else "campaigns" if self.day_count >= cfg.max_campaigns else "closed"
            self._displaced(i, self.sweep.decisions, why)


def _noise_signal(m: "Model", c: float) -> int:
    nz = m.noise
    if not (m.cfg.noise and nz.check_end and nz.ready):
        return 0
    return 1 if c > nz.upper else -1 if c < nz.lower else 0


def _audit_raw(self, i: int, day: str, c: float, allowed: bool) -> None:
    """Raw setups that never reach a decision: noise checks on skip days or FOMC-morning shorts, Williams bars touching
    both levels, sweep penetrations."""
    d = _noise_signal(self, c)
    if d and self.noise.skip_today:
        self.audit.append((i, "noise", d, "skip day"))
    elif d < 0 and self.noise.fed_today and self.noise.check_end < FED_CUTOFF:
        self.audit.append((i, "noise", d, "not qualified: FOMC-morning short"))
    if self.cfg.williams and self.wb.raw == 2:
        self.audit.append((i, "williams", 0, "not qualified: both levels"))
    if self.sweep is not None:
        for _, pd_ in self.sweep.penetrations:
            self.audit.append((i, "sweep", pd_, "raw: penetration"))


def _audit_blocked(self, i: int, day: str, c: float) -> None:
    """Qualified noise / Williams setups on a bar where no entry could be taken."""
    d = _noise_signal(self, c)
    if d and not self.noise.skip_today and not (d < 0 and self.noise.fed_today and self.noise.check_end < FED_CUTOFF):
        self.audit.append((i, "noise", d, self._blocked_why()))
    if self.cfg.williams and self.wb.raw in (1, -1):
        self.audit.append((i, "williams", self.wb.raw, self._blocked_why()))


Model._audit_raw = _audit_raw
Model._audit_blocked = _audit_blocked


def run(bars: pd.DataFrame, cfg: DConfig) -> Model:
    """Every bar through the model; bars: open, high, low, close, optional scale; index: New York start times."""
    m = Model(cfg)
    idx = bars.index.tz_convert(NY) if bars.index.tz is not None else bars.index
    o, h, l, c = (bars[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    sc = bars["scale"].to_numpy(float) if "scale" in bars else np.ones(len(bars))
    for i in range(len(bars)):
        m.step(i, idx[i], o[i], h[i], l[i], c[i], sc[i])
    return m


def ledger(m: Model, idx) -> pd.DataFrame:
    """One row per completed position (its two contracts combined), with each contract's exit."""
    rows = []
    for c in m.campaigns:
        lots = {lt.name: lt for lt in c.lots}
        run_, half = lots.get("runner"), lots.get("half")
        first = min(lt.fill_bar for lt in c.lots)
        last = max(lt.exit_bar for lt in c.lots)
        rows.append({"sleeve": c.sleeve, "d": c.d, "kind": c.kind, "signal_bar": c.signal_bar,
                     "signal_time": idx[c.signal_bar], "entry_bar": first, "entry_time": idx[first],
                     "exit_bar": last, "exit_time": idx[last], "contracts": sum(lt.qty for lt in c.lots),
                     "fill": c.lots[0].fill, "expected": c.expected, "stop0": c.stop0, "r_points": c.r,
                     "price_risk": c.r * PV * m.cfg.qty, "planned_risk": c.planned,
                     "runner_exit": run_.exit if run_ else math.nan, "runner_why": run_.why if run_ else "",
                     "half_exit": half.exit if half else math.nan, "half_why": half.why if half else "",
                     "pnl": c.pnl, "r_multiple": c.pnl / c.planned if c.planned else math.nan,
                     "overrun": c.pnl < -c.planned - 1e-9})
    return pd.DataFrame(rows)
