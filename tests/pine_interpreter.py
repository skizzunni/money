"""A small, strict interpreter for the subset of Pine Script v6 used in pine/.

It exists to check the TradingView scripts against the Python reference
engine without TradingView. It executes the real .pine source bar by bar:
var/non-var declarations, := and +=, if/else, for/to, for/in, ternaries,
lazy and/or, history references, user functions, and the built-ins the
scripts call. Drawing and alert calls are recorded, not rendered.

It is deliberately strict where Pine v6 is strict, so mistakes surface:
undefined names, := to an undeclared variable, a function assigning a
global, a non-bool condition, redeclaring a name in the same scope, and
== / != against na all raise.
"""
from __future__ import annotations

import hashlib
import math
import pickle
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from pynescript import ast as A

from mnqbot.data import atr as atr_series

NA = math.nan


class PineError(Exception):
    pass


def is_na(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


class Sym(str):
    """Opaque constant (color.red, shape.circle, ...) that is also a no-op callable."""

    def __call__(self, *args, **kwargs):
        return None

    def __getattr__(self, attr):  # strategy.commission.cash_per_contract
        if attr.startswith("__"):
            raise AttributeError(attr)
        return Sym(f"{self}.{attr}")


_CACHE = Path(__file__).resolve().parent / ".pine_cache"


def load_pine(path: str | Path):
    """Parse a .pine file (pynescript takes ~1 min), caching the tree by content hash."""
    src = Path(path).read_text()
    key = hashlib.sha256(src.encode()).hexdigest()[:16]
    cached = _CACHE / f"{Path(path).stem}-{key}.pkl"
    if cached.exists():
        return pickle.loads(cached.read_bytes())
    tree = A.parse(src)
    _CACHE.mkdir(exist_ok=True)
    cached.write_bytes(pickle.dumps(tree))
    return tree


class Namespace:
    """Built-in namespace (math, str, label, ...). Calling it is a no-op, like plot() or bgcolor()."""

    def __init__(self, name: str, call=None, **members):
        self._name = name
        self._call = call
        self.__dict__.update(members)

    def __getattr__(self, attr):  # only called for members not set explicitly
        if attr.startswith("__"):
            raise AttributeError(attr)
        return Sym(f"{self._name}.{attr}")

    def __call__(self, *args, **kwargs):
        return self._call(*args, **kwargs) if self._call else None


class _Return(Exception):
    pass


class PineRuntime:
    SERIES = ("open", "high", "low", "close", "volume", "time")

    def __init__(self, tree, bars, inputs: dict | None = None, mintick=0.25, pointvalue=2.0,
                 timeframe_seconds=300, timenow_ms: int | None = None, commission=0.62, slippage_ticks=1,
                 limit_fill_ticks=1):
        self.tree = tree
        self.inputs = dict(inputs or {})
        self.used_inputs: set[str] = set()
        self.n = len(bars)
        self.series = {
            "open": bars["open"].to_numpy(float),
            "high": bars["high"].to_numpy(float),
            "low": bars["low"].to_numpy(float),
            "close": bars["close"].to_numpy(float),
            "volume": bars["volume"].to_numpy(float) if "volume" in bars else np.zeros(len(bars)),
            "time": (bars.index.tz_convert("UTC").as_unit("ms").asi8).astype(np.int64),
        }
        self.mintick, self.pointvalue, self.tf_seconds = mintick, pointvalue, timeframe_seconds
        self.timenow = timenow_ms if timenow_ms is not None else int(self.series["time"][-1]) + 1
        self._atr_cache: dict[int, np.ndarray] = {}
        self.funcs: dict[str, A.FunctionDef] = {}
        self.var_done: set[int] = set()
        self.globals: dict = {}
        self.history: list[dict] = []
        self.alerts: list[tuple[int, str]] = []
        self.tables: list = []  # every table.new, in order
        self.labels: list[tuple[int, str]] = []
        self.i = 0
        self.scopes: list[dict] = []
        self.declared: list[set] = []
        self.in_function = 0
        self.strategy = StrategyEmulator(self, commission, slippage_ticks, limit_fill_ticks)
        self._builtins = self._make_builtins()

    # ------------------------------------------------------------------ run
    def run(self, on_bar=None):
        for i in range(self.n):
            self.i = i
            self.scopes, self.declared = [self.globals], [set()]
            self.strategy.process_bar(i)
            for stmt in self.tree.body:
                self.exec(stmt)
            self.history.append(dict(self.globals))
            if on_bar:
                on_bar(i, self.globals)
        unused = set(self.inputs) - self.used_inputs
        if unused:
            raise PineError(f"input overrides matched no input title: {sorted(unused)}")

    # ------------------------------------------------------------ statements
    def exec_block(self, stmts, new_scope=True):
        if new_scope:
            self.scopes.append({})
            self.declared.append(set())
        try:
            value = None
            for s in stmts:
                value = self.exec(s)
            return value
        finally:
            if new_scope:
                self.scopes.pop()
                self.declared.pop()

    def exec(self, node):
        t = type(node)
        if t is A.Assign:
            return self._assign(node)
        if t is A.ReAssign:
            return self._set(node.target.id, self.eval(node.value))
        if t is A.AugAssign:
            cur = self._lookup(node.target.id)
            return self._set(node.target.id, self._binop(node.op, cur, self.eval(node.value)))
        if t is A.FunctionDef:
            self.funcs.setdefault(node.name, node)
            return None
        if t is A.Expr:
            v = node.value
            if type(v) in (A.If, A.ForTo, A.ForIn):
                return self.exec(v)
            return self.eval(v)
        if t is A.If:
            if self._bool(self.eval(node.test), "if condition"):
                return self.exec_block(node.body)
            if node.orelse:
                return self.exec_block(node.orelse)
            return None
        if t is A.ForTo:
            start, end = self.eval(node.start), self.eval(node.end)
            step = self.eval(node.step) if getattr(node, "step", None) is not None else (1 if end >= start else -1)
            k = start
            value = None
            while (k <= end) if step > 0 else (k >= end):
                self.scopes.append({node.target.id: k})
                self.declared.append({node.target.id})
                try:
                    value = self.exec_block(node.body, new_scope=False)
                finally:
                    self.scopes.pop()
                    self.declared.pop()
                k += step
            return value
        if t is A.ForIn:
            value = None
            for item in list(self.eval(node.iter)):
                self.scopes.append({node.target.id: item})
                self.declared.append({node.target.id})
                try:
                    value = self.exec_block(node.body, new_scope=False)
                finally:
                    self.scopes.pop()
                    self.declared.pop()
            return value
        raise PineError(f"unsupported statement {t.__name__}")

    def _assign(self, node):
        name = node.target.id
        is_var = isinstance(getattr(node, "mode", None), A.Var)
        if is_var:
            if self.in_function:
                raise PineError("var inside a function is not used by these scripts")
            if id(node) in self.var_done:
                self._mark_declared(name)
                return self.globals[name] if len(self.scopes) == 1 else self.scopes[-1][name]
            self.var_done.add(id(node))
        self._mark_declared(name)
        value = self.eval(node.value)
        self.scopes[-1][name] = value
        return value

    def _mark_declared(self, name):
        if name in self.declared[-1]:
            raise PineError(f"'{name}' declared twice in the same scope (bar {self.i})")
        self.declared[-1].add(name)

    def _lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise PineError(f"undeclared identifier '{name}' (bar {self.i})")

    def _set(self, name, value):
        for depth in range(len(self.scopes) - 1, -1, -1):
            if name in self.scopes[depth]:
                if self.in_function and depth == 0:
                    raise PineError(f"function assigns global '{name}'")
                self.scopes[depth][name] = value
                return value
        raise PineError(f"':=' to undeclared variable '{name}' (bar {self.i})")

    # ----------------------------------------------------------- expressions
    def eval(self, node):
        t = type(node)
        if t is A.Constant:
            return node.value
        if t is A.Name:
            return self._name(node.id)
        if t is A.Attribute:
            base = self.eval(node.value)
            return getattr(base, node.attr)
        if t is A.Call:
            return self._call(node)
        if t is A.Subscript:
            return self._history(node)
        if t is A.BinOp:
            return self._binop(node.op, self.eval(node.left), self.eval(node.right))
        if t is A.UnaryOp:
            v = self.eval(node.operand)
            if isinstance(node.op, A.Not):
                return not self._bool(v, "not")
            if isinstance(node.op, A.USub):
                return -v
            if isinstance(node.op, A.UAdd):
                return v
        if t is A.BoolOp:
            is_and = isinstance(node.op, A.And)
            for sub in node.values:
                v = self._bool(self.eval(sub), "and/or operand")
                if is_and and not v:
                    return False
                if not is_and and v:
                    return True
            return is_and
        if t is A.Compare:
            if len(node.ops) != 1:
                raise PineError("chained comparison")
            return self._compare(node.ops[0], self.eval(node.left), self.eval(node.comparators[0]))
        if t is A.Conditional:
            if self._bool(self.eval(node.test), "ternary condition"):
                return self.eval(node.body)
            return self.eval(node.orelse)
        if t is A.Specialize:
            return self.eval(node.value)
        if t is A.Tuple:  # [a, b] literals, e.g. input options
            return [self.eval(e) for e in node.elts]
        raise PineError(f"unsupported expression {t.__name__}")

    def _bool(self, v, where):
        if not isinstance(v, (bool, np.bool_)):
            raise PineError(f"{where} is {type(v).__name__}, not bool (bar {self.i})")
        return bool(v)

    def _binop(self, op, a, b):
        if isinstance(op, A.Add):
            if isinstance(a, str) or isinstance(b, str):
                if not (isinstance(a, str) and isinstance(b, str)):
                    raise PineError("string + non-string")
                return a + b
            return a + b
        if isinstance(op, A.Sub):
            return a - b
        if isinstance(op, A.Mult):
            return a * b
        if isinstance(op, A.Div):
            if b == 0:
                return NA
            return a / b
        if isinstance(op, A.Mod):
            return a % b
        raise PineError(f"unsupported operator {type(op).__name__}")

    def _compare(self, op, a, b):
        if isinstance(op, (A.Eq, A.NotEq)):
            if is_na(a) or is_na(b):
                raise PineError(f"== / != against na (bar {self.i})")
            return (a == b) if isinstance(op, A.Eq) else (a != b)
        if is_na(a) or is_na(b):
            return False
        if isinstance(op, A.Lt):
            return a < b
        if isinstance(op, A.LtE):
            return a <= b
        if isinstance(op, A.Gt):
            return a > b
        if isinstance(op, A.GtE):
            return a >= b
        raise PineError(f"unsupported comparison {type(op).__name__}")

    def _name(self, name):
        if name == "na":
            return NA
        if name == "bar_index":
            return self.i
        if name == "timenow":
            return self.timenow
        if name in self.SERIES:
            v = self.series[name][self.i]
            return int(v) if name == "time" else float(v)
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self._builtins:
            return self._builtins[name]
        raise PineError(f"undeclared identifier '{name}' (bar {self.i})")

    def _history(self, node):
        if not isinstance(node.value, A.Name):
            raise PineError("history reference on a non-name")
        name = node.value.id
        off = self.eval(node.slice)
        if not isinstance(off, int) or off < 0:
            raise PineError(f"bad history offset {off!r}")
        j = self.i - off
        if j < 0:
            return NA
        if name in self.SERIES:
            v = self.series[name][j]
            return int(v) if name == "time" else float(v)
        if off == 0:
            return self._name(name)
        if any(name in s for s in self.scopes[1:]):
            raise PineError(f"history of local '{name}' is not supported")
        snap = self.history[j]
        if name not in snap:
            return NA
        return snap[name]

    def _call(self, node):
        args, kwargs = [], {}
        for a in node.args:
            v = self.eval(a.value)
            if getattr(a, "name", None):
                kwargs[a.name] = v
            else:
                args.append(v)
        f = node.func
        if isinstance(f, A.Name) and f.id in self.funcs:
            return self._call_user(self.funcs[f.id], args, kwargs)
        if isinstance(f, A.Name) and f.id == "time":
            return self._session_time(*args)
        if isinstance(f, A.Name) and f.id == "na":
            return is_na(args[0])
        fn = self.eval(f)
        if not callable(fn):
            raise PineError(f"not callable: {A.unparse(f) if hasattr(A, 'unparse') else f}")
        return fn(*args, **kwargs)

    def _call_user(self, fdef, args, kwargs):
        params = [p.name for p in fdef.args]
        local = dict(zip(params, args, strict=False))  # the rest may come as keywords
        local.update(kwargs)
        if set(local) != set(params):
            raise PineError(f"{fdef.name}() called with {sorted(local)} but takes {params}")
        saved = self.scopes, self.declared
        self.scopes, self.declared = [self.globals, local], [set(), set(params)]
        self.in_function += 1
        try:
            return self.exec_block(fdef.body, new_scope=False)
        finally:
            self.in_function -= 1
            self.scopes, self.declared = saved

    # -------------------------------------------------------------- builtins
    def _ny(self, t_ms, tz):
        return datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).astimezone(ZoneInfo(tz))

    def _session_time(self, tf, session, tz):
        start, end = (int(x) for x in session.split("-"))
        d = self._ny(int(self.series["time"][self.i]), tz)
        hhmm = d.hour * 100 + d.minute
        if start > end:
            raise PineError("overnight sessions are not used by these scripts")
        return int(self.series["time"][self.i]) if start <= hhmm < end else NA

    def _input(self, defval, title=None, *args, **kwargs):
        if title in self.inputs:
            self.used_inputs.add(title)
            return self.inputs[title]
        return defval

    def _atr(self, length):
        if length not in self._atr_cache:
            s = self.series
            self._atr_cache[length] = atr_series(s["high"], s["low"], s["close"], length)
        v = self._atr_cache[length][self.i]
        return NA if math.isnan(v) else float(v)

    def _make_builtins(self):
        rt = self

        def nmax(*xs):
            return NA if any(is_na(x) for x in xs) else max(xs)

        def nmin(*xs):
            return NA if any(is_na(x) for x in xs) else min(xs)

        def floor(x):
            return NA if is_na(x) else math.floor(x)

        def tostring(x, fmt=None):
            if fmt == "mintick":
                return f"{x:.2f}"
            if fmt == "#,##0.00":
                return f"{x:,.2f}"
            if fmt == "#":
                return f"{x:.0f}"
            if fmt == "#.##":
                return f"{x:.2f}"
            if isinstance(x, float) and x.is_integer():
                return str(int(x))
            return str(x)

        def alert(msg, freq=None):
            rt.alerts.append((rt.i, msg))

        def label_new(x, y, text="", **kw):
            rt.labels.append((rt.i, text))

        def part(fn):
            return lambda t, tz: getattr(rt._ny(t, tz), fn)

        def array_new(*a):
            return []

        def array_new_float(size=0, initial_value=NA):
            return [initial_value] * int(size)

        def array_index(a, i):
            if not isinstance(i, int) or not 0 <= i < len(a):
                raise PineError(f"array index {i!r} out of bounds for size {len(a)} (bar {rt.i})")
            return i

        def array_get(a, i):
            return a[array_index(a, i)]

        def array_set(a, i, v):
            a[array_index(a, i)] = v

        def to_int(x):
            return NA if is_na(x) else int(x)  # Pine int() truncates toward zero

        def format_time(t_ms, fmt, tz):
            py = fmt
            for java, c in (("yyyy", "%Y"), ("MM", "%m"), ("dd", "%d"), ("HH", "%H"), ("mm", "%M")):
                py = py.replace(java, c)
            if any(ch.isalpha() for ch in py.replace("%Y", "").replace("%m", "").replace("%d", "")
                   .replace("%H", "").replace("%M", "")):
                raise PineError(f"str.format_time format {fmt!r} is not emulated")
            return rt._ny(int(t_ms), tz).strftime(py)

        def table_new(position, columns, rows, **kw):
            t = _Table(int(columns), int(rows))
            rt.tables.append(t)
            return t

        def table_cell(t, column, row, text="", **kw):
            t.cell(int(column), int(row), text)

        def table_clear(t, start_column, start_row, end_column=None, end_row=None):
            t.clear(int(start_column), int(start_row), end_column, end_row)

        return {
            "indicator": Namespace("indicator"),
            "alert": Namespace("alert", call=alert),
            "alertcondition": Namespace("alertcondition"),
            "plot": Namespace("plot"),
            "plotshape": Namespace("plotshape"),
            "bgcolor": Namespace("bgcolor"),
            "hour": part("hour"),
            "minute": part("minute"),
            "year": part("year"),
            "month": part("month"),
            "dayofmonth": part("day"),
            "input": Namespace("input", int=self._input, float=self._input, bool=self._input,
                               string=self._input, session=self._input),
            "math": Namespace("math", max=nmax, min=nmin, floor=floor, abs=abs),
            "str": Namespace("str", tostring=tostring, upper=str.upper, startswith=str.startswith,
                             contains=lambda source, sub: sub in source, format_time=format_time),
            "ta": Namespace("ta", atr=self._atr),
            "array": Namespace("array", new=array_new, push=lambda a, v: a.append(v), size=len,
                               new_float=array_new_float, get=array_get, set=array_set),
            "int": to_int,
            "syminfo": Namespace("syminfo", mintick=self.mintick, pointvalue=self.pointvalue),
            "timeframe": Namespace("timeframe", period=str(self.tf_seconds // 60),
                                   in_seconds=lambda tf=None: rt.tf_seconds),
            "barstate": _Barstate(self),
            "format": Namespace("format", mintick="mintick"),
            "label": Namespace("label", new=label_new),
            "box": Namespace("box"),
            "table": Namespace("table", new=table_new, cell=table_cell, clear=table_clear),
            "color": Namespace("color"),
            "shape": Namespace("shape"),
            "location": Namespace("location"),
            "yloc": Namespace("yloc"),
            "size": Namespace("size"),
            "position": Namespace("position"),
            "strategy": self.strategy,
            "currency": Namespace("currency"),
        }


class _Barstate:
    def __init__(self, rt):
        self._rt = rt

    @property
    def islast(self):
        return self._rt.i == self._rt.n - 1

    @property
    def islastconfirmedhistory(self):  # every bar here is historical, so the last one
        return self._rt.i == self._rt.n - 1

    @property
    def isrealtime(self):
        return False


class StrategyEmulator:
    """Just enough of TradingView's broker emulator for pine/mnq_liquidity_sweep_bot.pine.

    Fills follow mnqbot.engine's worst-case rules (not TradingView's intrabar
    path), so a strategy run here should reproduce the engine trade for trade.
    """

    long = Sym("strategy.long")
    short = Sym("strategy.short")
    fixed = Sym("strategy.fixed")
    commission = Namespace("strategy.commission")

    def __init__(self, rt, commission, slippage_ticks, limit_fill_ticks):
        self.rt = rt
        self.fee = commission
        self.slip_ticks = slippage_ticks
        self.fill_ticks = limit_fill_ticks
        self.entries: dict[str, dict] = {}
        self.market_entries: dict[str, dict] = {}  # strategy.entry without limit: next bar's open
        self.market_close: dict | None = None  # strategy.close: next bar's open
        self.exits: dict[str, dict] = {}
        self.pos: dict | None = None
        self.closed: list[dict] = []
        self.orders: list[dict] = []

    def __call__(self, *args, **kwargs):  # the strategy(...) declaration
        return None

    # ---- read-only state the script uses
    @property
    def position_size(self):
        return 0.0 if self.pos is None else float(self.pos["dir"] * self.pos["qty"])

    @property
    def position_avg_price(self):
        return NA if self.pos is None else self.pos["price"]

    @property
    def netprofit(self):
        return float(sum(t["pnl"] for t in self.closed))

    @property
    def openprofit(self):  # unrealized, at this bar's close, before commission
        if self.pos is None:
            return 0.0
        c = self.rt.series["close"][self.rt.i]
        return float(self.pos["dir"] * (c - self.pos["price"]) * self.pos["qty"] * self.rt.pointvalue)

    @property
    def closedtrades(self):
        return _ClosedTrades(self.closed, self.rt.series["time"])

    @property
    def wintrades(self):
        return sum(t["pnl"] > 0 for t in self.closed)

    @property
    def grossprofit(self):
        return float(sum(t["pnl"] for t in self.closed if t["pnl"] > 0))

    @property
    def grossloss(self):
        return float(-sum(t["pnl"] for t in self.closed if t["pnl"] < 0))

    @property
    def opentrades(self):
        return _OpenTrades(self)

    # ---- order calls
    def entry(self, id, direction, qty=None, limit=None, comment=None, **kw):
        d = 1 if direction == self.long else -1
        order = {"dir": d, "qty": int(qty), "limit": limit, "bar": self.rt.i, "comment": comment}
        if limit is None:
            self.market_entries[id] = order
        else:
            self.entries[id] = order
        self.orders.append({"bar": self.rt.i, "dir": d, "qty": int(qty), "limit": limit})

    def close(self, id, comment=None, immediately=False, **kw):
        if immediately:
            raise PineError("strategy.close with immediately=true is not emulated")
        self.market_close = {"id": id, "bar": self.rt.i, "comment": comment}

    def exit(self, id, from_entry, stop=None, limit=None, comment=None, comment_loss=None, comment_profit=None,
             alert_message=None, **kw):
        self.exits[from_entry] = {"stop": stop, "limit": limit, "loss": comment_loss or comment,
                                  "profit": comment_profit or comment, "alert": alert_message}

    def cancel(self, id):
        self.entries.pop(id, None)

    def close_all(self, comment=None, immediately=False, **kw):
        if not immediately:
            raise PineError("close_all without immediately=true is not emulated")
        if self.pos is not None:
            c = self.rt.series["close"][self.rt.i]
            tick = self.rt.mintick
            self._close(c - self.slip_ticks * tick if self.pos["dir"] > 0 else c + self.slip_ticks * tick, comment)

    # ---- bar processing (before the script runs on the bar)
    def _close(self, price, reason):
        p = self.pos
        gross = p["dir"] * (price - p["price"]) * p["qty"] * self.rt.pointvalue
        fee = 2 * self.fee * p["qty"]
        self.closed.append({"entry_bar": p["bar"], "exit_bar": self.rt.i, "dir": p["dir"], "qty": p["qty"],
                            "entry": p["price"], "exit": price, "pnl": gross - fee, "reason": reason})
        self.pos = None

    def process_bar(self, i):
        s, tick = self.rt.series, self.rt.mintick
        o, h, l = s["open"][i], s["high"][i], s["low"][i]
        thru, slip = self.fill_ticks * tick, self.slip_ticks * tick
        # market orders from earlier bars fill at this bar's open, with slippage against us
        mc, self.market_close = self.market_close, None
        if mc is not None and mc["bar"] < i and self.pos is not None and self.pos["id"] == mc["id"]:
            self._close(o - self.pos["dir"] * slip, mc["comment"])
        for oid, e in list(self.market_entries.items()):
            if e["bar"] >= i:
                continue
            del self.market_entries[oid]
            if self.pos is not None and self.pos["dir"] == -e["dir"]:  # an opposite entry reverses
                self._close(o - self.pos["dir"] * slip, "reversed")
            if self.pos is None:
                self.pos = {"id": oid, "dir": e["dir"], "qty": e["qty"], "price": o + e["dir"] * slip, "bar": i,
                            "market": True}
        if self.pos is None:
            for oid, e in list(self.entries.items()):
                if e["bar"] >= i:
                    continue
                d = e["dir"]
                if (d < 0 and h >= e["limit"] + thru) or (d > 0 and l <= e["limit"] - thru):
                    self.pos = {"id": oid, "dir": d, "qty": e["qty"], "price": e["limit"], "bar": i}
                    del self.entries[oid]
                    break
        if self.pos is None:
            return
        ex = self.exits.get(self.pos["id"])
        if ex is None:
            return
        d, stop, limit = self.pos["dir"], ex["stop"], ex["limit"]

        def stop_fill(px):
            self._close(px + slip if d < 0 else px - slip, ex["loss"])
            if ex.get("alert"):  # an order-fill alert (alert_message on strategy.exit)
                self.rt.alerts.append((i, ex["alert"]))

        if self.pos["bar"] == i:  # fill bar: worst case, stop only
            if stop is not None and ((d < 0 and h >= stop) or (d > 0 and l <= stop)):
                px = stop
                if self.pos.get("market"):  # a market entry can open past its stop; the stop then fills at the open
                    px = min(o, stop) if d > 0 else max(o, stop)
                stop_fill(px)
            return
        if stop is not None and ((d < 0 and o >= stop) or (d > 0 and o <= stop)):
            stop_fill(o)
        elif stop is not None and ((d < 0 and h >= stop) or (d > 0 and l <= stop)):
            stop_fill(stop)
        elif limit is not None and ((d < 0 and l <= limit - thru) or (d > 0 and h >= limit + thru)):
            self._close(limit, ex["profit"])


class _ClosedTrades(int):
    """`strategy.closedtrades` is a count that also has per-trade functions (profit(i), exit_price(i), ...)."""

    def __new__(cls, closed, time=None):
        obj = super().__new__(cls, len(closed))
        obj._closed = closed
        obj._time = time
        return obj

    def _get(self, i, key):
        if not 0 <= i < len(self._closed):
            raise PineError(f"closed trade {i} does not exist")
        return self._closed[i][key]

    def profit(self, i):
        return float(self._get(i, "pnl"))

    def exit_price(self, i):
        return float(self._get(i, "exit"))

    def size(self, i):  # signed contracts: negative for a short
        return float(self._get(i, "dir") * self._get(i, "qty"))

    def exit_comment(self, i):
        return self._get(i, "reason")

    def exit_bar_index(self, i):
        return self._get(i, "exit_bar")

    def entry_price(self, i):
        return float(self._get(i, "entry"))

    def entry_time(self, i):  # the open time of the bar the entry filled on, ms
        return int(self._time[self._get(i, "entry_bar")])

    def exit_time(self, i):
        return int(self._time[self._get(i, "exit_bar")])


class _OpenTrades(int):
    """`strategy.opentrades`: 0 or 1 here (no pyramiding), with per-trade functions for trade 0."""

    def __new__(cls, strategy):
        obj = super().__new__(cls, 0 if strategy.pos is None else 1)
        obj._s = strategy
        return obj

    def _pos(self, i):
        if i != 0 or self._s.pos is None:
            raise PineError(f"open trade {i} does not exist")
        return self._s.pos

    def entry_price(self, i):
        return float(self._pos(i)["price"])

    def entry_time(self, i):
        return int(self._s.rt.series["time"][self._pos(i)["bar"]])

    def size(self, i):
        p = self._pos(i)
        return float(p["dir"] * p["qty"])


class _Table:
    """A table's text, by (column, row), so tests can read what the chart shows."""

    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows
        self.cells: dict[tuple[int, int], str] = {}

    def cell(self, column, row, text):
        if not (0 <= column < self.columns and 0 <= row < self.rows):
            raise PineError(f"table cell ({column}, {row}) is outside a {self.columns}x{self.rows} table")
        self.cells[(column, row)] = text

    def clear(self, c0, r0, c1=None, r1=None):
        c1 = c0 if c1 is None else int(c1)
        r1 = r0 if r1 is None else int(r1)
        self.cells = {k: v for k, v in self.cells.items() if not (c0 <= k[0] <= c1 and r0 <= k[1] <= r1)}

    def grid(self):
        """Rows of text, top to bottom, up to the last row with anything in it."""
        last = max((r for _, r in self.cells), default=-1)
        return [[self.cells.get((c, r), "") for c in range(self.columns)] for r in range(last + 1)]
