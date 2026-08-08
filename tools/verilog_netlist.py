"""Structural (gate-level) Verilog reader/writer for this repo's tools.

This is the shared parse layer under ``tools/compare`` and ``tools/rename``.  It
handles the subset of Verilog that gate-level netlists actually use — the shape
that Yosys ``write_verilog`` and OpenROAD emit, and the shape an extractor
should emit:

    module <top> (<ports>);
     input a; output [7:0] b; wire \\escaped/name ;
     assign x = y;
     <cell_type> <instance_name> (.PIN(net), .PIN(net[3]), .PIN(1'b0));
    endmodule

Deliberately *not* supported (each raises ``ParseError`` naming the line, rather
than silently mis-parsing): behavioural statements, generate blocks, parameters,
positional port connections, concatenations, and multiple modules per file.

The canonical intermediate form is the JSON document described by
``SCHEMA`` — the form ``tools/extract`` is expected to emit, so that the
comparator is symmetric and can compare any two netlists rather than only
"ours against theirs":

    {
      "schema": "sky130-asic-puzzle/netlist@1",
      "top": "adder_demo",
      "ports": [{"name": "A", "direction": "input"}, ...],
      "nets": ["A", "B", "sum[0]", ...],
      "instances": [
        {"name": "u0", "cell": "sky130_fd_sc_hd__nand2_2",
         "connections": {"A": "x", "B": "y", "Y": "z"}}
      ]
    }
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SCHEMA = "sky130-asic-puzzle/netlist@1"

# Supply pins/nets of the sky130 standard cells.  Extracted netlists usually
# carry these; the published warm-up `01_netlist.v` does not.  Comparing the two
# is only possible if they can be dropped, so tools default to ignoring them.
POWER_PINS = frozenset(
    {"VPWR", "VGND", "VPB", "VNB", "VDD", "VSS", "VDDA", "VSSA", "VDDIO", "KAPWR", "LOWHVPWR"}
)
POWER_NETS = frozenset({"VPWR", "VGND", "VPB", "VNB", "VDD", "VSS", "vpwr", "vgnd", "vdd", "vss"})

# Fill/tap cells carry no signal connectivity.  Requiring a 1:1 correspondence
# on them would fail a comparison for reasons that say nothing about extraction
# quality, so they are matched by count as a separate class.
FILL_PREFIXES = ("tapvpwrvgnd", "tapvgnd", "tap", "decap", "fill", "diode")

CONSTANT_NETS = frozenset({"1'b0", "1'b1"})


class ParseError(Exception):
    """Raised with a line number when a netlist cannot be parsed."""


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------


@dataclass
class Port:
    name: str
    direction: str  # input | output | inout

    def to_json(self) -> dict:
        return {"name": self.name, "direction": self.direction}


@dataclass
class Instance:
    name: str
    cell: str
    connections: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"name": self.name, "cell": self.cell, "connections": dict(self.connections)}


@dataclass
class Netlist:
    top: str
    ports: list[Port] = field(default_factory=list)
    nets: list[str] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)
    source: str = "<memory>"

    # -- convenience ------------------------------------------------------
    def port_names(self) -> list[str]:
        return [p.name for p in self.ports]

    def instance(self, name: str) -> Instance:
        for inst in self.instances:
            if inst.name == name:
                return inst
        raise KeyError(name)

    def to_json(self) -> dict:
        return {
            "schema": SCHEMA,
            "top": self.top,
            "ports": [p.to_json() for p in self.ports],
            "nets": list(self.nets),
            "instances": [i.to_json() for i in self.instances],
        }

    def to_json_text(self) -> str:
        return json.dumps(self.to_json(), indent=2, sort_keys=False) + "\n"


def from_json(obj: dict, source: str = "<json>") -> Netlist:
    schema = obj.get("schema")
    if schema is not None and schema != SCHEMA:
        raise ParseError(f"{source}: unknown netlist schema {schema!r} (expected {SCHEMA!r})")
    nl = Netlist(top=obj.get("top", "top"), source=source)
    for p in obj.get("ports", []):
        nl.ports.append(Port(name=p["name"], direction=p.get("direction", "input")))
    nl.nets = list(obj.get("nets", []))
    for i in obj.get("instances", []):
        nl.instances.append(
            Instance(name=i["name"], cell=i["cell"], connections=dict(i.get("connections", {})))
        )
    return nl


# --------------------------------------------------------------------------
# tokenizer
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<lcomment>//[^\n]*)
    | (?P<bcomment>/\*.*?\*/)
    | (?P<attr>\(\*.*?\*\))
    | (?P<escaped>\\\S+)
    | (?P<number>[0-9]*'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_?]+|[0-9][0-9_]*)
    | (?P<ident>[a-zA-Z_][a-zA-Z0-9_$]*)
    | (?P<sym>[(),;.\[\]:={}@#])
    | (?P<other>\S)
    """,
    re.VERBOSE | re.DOTALL,
)


@dataclass
class Token:
    kind: str  # 'escaped' | 'number' | 'ident' | 'sym'
    text: str
    line: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    pos = 0
    end = len(text)
    while pos < end:
        m = _TOKEN_RE.match(text, pos)
        if not m:  # pragma: no cover - the 'other' branch matches anything
            raise ParseError(f"line {line}: cannot tokenize {text[pos:pos + 20]!r}")
        kind = m.lastgroup
        raw = m.group()
        if kind in ("ws", "lcomment", "bcomment", "attr"):
            line += raw.count("\n")
            pos = m.end()
            continue
        if kind == "other":
            raise ParseError(f"line {line}: unexpected character {raw!r}")
        if kind == "escaped":
            tokens.append(Token("escaped", raw[1:], line))
        else:
            tokens.append(Token(kind, raw, line))
        line += raw.count("\n")
        pos = m.end()
    return tokens


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------

_DECL_KEYWORDS = {"input", "output", "inout"}
_NET_KEYWORDS = {"wire", "reg", "tri", "logic", "supply0", "supply1"}
_IGNORED_TYPE_KEYWORDS = {"wire", "reg", "signed", "logic", "tri"}


class _Parser:
    def __init__(self, tokens: list[Token], source: str):
        self.toks = tokens
        self.i = 0
        self.source = source
        # union-find over net names, used to fold `assign` aliases away
        self.parent: dict[str, str] = {}

    # -- token helpers ----------------------------------------------------
    def peek(self, offset: int = 0) -> Token | None:
        j = self.i + offset
        return self.toks[j] if j < len(self.toks) else None

    def next(self) -> Token:
        if self.i >= len(self.toks):
            raise ParseError(f"{self.source}: unexpected end of file")
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect_sym(self, sym: str) -> Token:
        tok = self.next()
        if tok.kind != "sym" or tok.text != sym:
            raise ParseError(f"{self.source}:{tok.line}: expected {sym!r}, got {tok.text!r}")
        return tok

    def at_sym(self, sym: str) -> bool:
        tok = self.peek()
        return tok is not None and tok.kind == "sym" and tok.text == sym

    def at_keyword(self, word: str) -> bool:
        tok = self.peek()
        return tok is not None and tok.kind == "ident" and tok.text == word

    def name_token(self) -> Token:
        tok = self.next()
        if tok.kind not in ("ident", "escaped"):
            raise ParseError(f"{self.source}:{tok.line}: expected an identifier, got {tok.text!r}")
        return tok

    # -- union-find -------------------------------------------------------
    def find(self, name: str) -> str:
        self.parent.setdefault(name, name)
        root = name
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[name] != root:
            self.parent[name], name = root, self.parent[name]
        return root

    def union(self, a: str, b: str, ports: set[str]) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return

        def rank(n: str) -> tuple[int, int, str]:
            # constants win, then ports, then shorter names, for a stable
            # representative that reads well in reports
            return (0 if n in CONSTANT_NETS else 1, 0 if n in ports else 1, n)

        keep, drop = sorted([ra, rb], key=rank)[0], sorted([ra, rb], key=rank)[1]
        self.parent[drop] = keep

    # -- grammar ----------------------------------------------------------
    def parse(self) -> Netlist:
        while self.peek() is not None and not self.at_keyword("module"):
            self.next()
        if self.peek() is None:
            raise ParseError(f"{self.source}: no `module` declaration found")
        self.next()  # 'module'
        top = self.name_token().text
        nl = Netlist(top=top, source=self.source)

        declared_ports: list[str] = []
        if self.at_sym("("):
            self.next()
            depth = 1
            while depth:
                tok = self.next()
                if tok.kind == "sym":
                    if tok.text == "(":
                        depth += 1
                    elif tok.text == ")":
                        depth -= 1
                    continue
                if tok.kind == "ident" and tok.text in _DECL_KEYWORDS | _IGNORED_TYPE_KEYWORDS:
                    continue
                if tok.kind in ("ident", "escaped"):
                    declared_ports.append(tok.text)
        if self.at_sym(";"):
            self.next()

        directions: dict[str, str] = {}
        nets: list[str] = []
        raw_instances: list[Instance] = []
        assigns: list[tuple[str, str, int]] = []

        while True:
            tok = self.peek()
            if tok is None:
                raise ParseError(f"{self.source}: missing `endmodule`")
            if tok.kind == "ident" and tok.text == "endmodule":
                self.next()
                break
            if tok.kind == "sym" and tok.text == ";":
                self.next()
                continue
            if tok.kind == "ident" and tok.text in _DECL_KEYWORDS:
                self.next()
                names = self._parse_decl_names()
                for n in names:
                    directions[n] = tok.text
                    nets.append(n)
                continue
            if tok.kind == "ident" and tok.text in _NET_KEYWORDS:
                self.next()
                nets.extend(self._parse_decl_names())
                continue
            if tok.kind == "ident" and tok.text == "assign":
                self.next()
                lhs = self._parse_signal_ref()
                self.expect_sym("=")
                rhs = self._parse_signal_ref()
                self.expect_sym(";")
                assigns.append((lhs, rhs, tok.line))
                continue
            if tok.kind == "ident" and tok.text in ("parameter", "localparam", "defparam"):
                raise ParseError(
                    f"{self.source}:{tok.line}: parameters are not supported in gate-level netlists"
                )
            if tok.kind in ("ident", "escaped"):
                raw_instances.append(self._parse_instance())
                continue
            raise ParseError(f"{self.source}:{tok.line}: unexpected token {tok.text!r}")

        port_set = set(declared_ports) | set(directions)
        for name in nets:
            self.find(name)
        for lhs, rhs, _line in assigns:
            self.union(lhs, rhs, port_set)

        # ports, in declaration order, deduplicated
        seen: set[str] = set()
        ordered_ports = declared_ports + [n for n in directions if n not in declared_ports]
        for name in ordered_ports:
            if name in seen:
                continue
            seen.add(name)
            nl.ports.append(Port(name=name, direction=directions.get(name, "input")))

        net_set: set[str] = set()
        for inst in raw_instances:
            resolved = {pin: self.find(net) for pin, net in inst.connections.items()}
            nl.instances.append(Instance(name=inst.name, cell=inst.cell, connections=resolved))
            net_set.update(resolved.values())
        for name in nets:
            net_set.add(self.find(name))
        nl.nets = sorted(net_set)
        return nl

    def _parse_decl_names(self) -> list[str]:
        """Parse the tail of a declaration: `[7:0] a, b;` -> ['a[7]', ..., 'b[0]']."""
        while True:
            tok = self.peek()
            if tok is not None and tok.kind == "ident" and tok.text in _IGNORED_TYPE_KEYWORDS:
                self.next()
                continue
            break
        bits: list[int] | None = None
        if self.at_sym("["):
            hi, lo = self._parse_range()
            step = -1 if hi >= lo else 1
            bits = list(range(hi, lo + step, step))
        names: list[str] = []
        while True:
            name = self.name_token().text
            if self.at_sym("["):  # `wire a[3];` (rare, but legal)
                hi, lo = self._parse_range()
                step = -1 if hi >= lo else 1
                names.extend(f"{name}[{b}]" for b in range(hi, lo + step, step))
            elif bits is None:
                names.append(name)
            else:
                names.extend(f"{name}[{b}]" for b in bits)
            if self.at_sym(","):
                self.next()
                continue
            if self.at_sym(";"):
                self.next()
            return names

    def _parse_range(self) -> tuple[int, int]:
        self.expect_sym("[")
        hi_tok = self.next()
        if hi_tok.kind != "number":
            raise ParseError(f"{self.source}:{hi_tok.line}: expected a bit index, got {hi_tok.text!r}")
        hi = int(hi_tok.text)
        lo = hi
        if self.at_sym(":"):
            self.next()
            lo_tok = self.next()
            if lo_tok.kind != "number":
                raise ParseError(
                    f"{self.source}:{lo_tok.line}: expected a bit index, got {lo_tok.text!r}"
                )
            lo = int(lo_tok.text)
        self.expect_sym("]")
        return hi, lo

    def _parse_signal_ref(self) -> str:
        tok = self.next()
        if tok.kind == "number":
            return normalize_constant(tok.text, tok.line, self.source)
        if tok.kind == "sym" and tok.text == "{":
            raise ParseError(
                f"{self.source}:{tok.line}: concatenations are not supported in gate-level netlists"
            )
        if tok.kind not in ("ident", "escaped"):
            raise ParseError(f"{self.source}:{tok.line}: expected a signal, got {tok.text!r}")
        name = tok.text
        if self.at_sym("["):
            hi, lo = self._parse_range()
            if hi != lo:
                raise ParseError(
                    f"{self.source}:{tok.line}: multi-bit reference {name}[{hi}:{lo}] is not supported"
                )
            name = f"{name}[{hi}]"
        return name

    def _parse_instance(self) -> Instance:
        cell_tok = self.name_token()
        name_tok = self.name_token()
        if self.at_sym("["):  # instance arrays
            raise ParseError(f"{self.source}:{name_tok.line}: instance arrays are not supported")
        self.expect_sym("(")
        conns: dict[str, str] = {}
        if not self.at_sym(")"):
            while True:
                if not self.at_sym("."):
                    tok = self.peek()
                    raise ParseError(
                        f"{self.source}:{tok.line if tok else 0}: positional port connections are "
                        "not supported — use .PIN(net) form"
                    )
                self.next()  # '.'
                pin = self.name_token().text
                self.expect_sym("(")
                if self.at_sym(")"):
                    self.next()  # unconnected pin: `.A()`
                else:
                    net = self._parse_signal_ref()
                    self.expect_sym(")")
                    if pin in conns:
                        raise ParseError(
                            f"{self.source}:{name_tok.line}: pin {pin} connected twice on "
                            f"instance {name_tok.text}"
                        )
                    conns[pin] = net
                if self.at_sym(","):
                    self.next()
                    continue
                break
        self.expect_sym(")")
        self.expect_sym(";")
        return Instance(name=name_tok.text, cell=cell_tok.text, connections=conns)


def normalize_constant(text: str, line: int, source: str) -> str:
    """Normalise `1'b0`/`1'h0`/`1'd1` to the canonical `1'b0` / `1'b1` net names."""
    m = re.fullmatch(r"(\d*)'[sS]?([bBoOdDhH])([0-9a-fA-FxXzZ_]+)", text)
    if not m:
        raise ParseError(f"{source}:{line}: unsupported literal {text!r}")
    width, base, digits = m.groups()
    digits = digits.replace("_", "")
    if width not in ("", "1"):
        raise ParseError(f"{source}:{line}: multi-bit literal {text!r} is not supported")
    value = digits.lower()
    if value in ("0", "1"):
        return f"1'b{value}"
    raise ParseError(f"{source}:{line}: unsupported literal value {text!r}")


def parse_verilog(text: str, source: str = "<memory>") -> Netlist:
    return _Parser(tokenize(text), source).parse()


def load(path: str) -> Netlist:
    """Load a netlist from a `.v` (structural Verilog) or `.json` file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    stripped = text.lstrip()
    if path.endswith(".json") or stripped.startswith("{"):
        return from_json(json.loads(text), source=path)
    return parse_verilog(text, source=path)


# --------------------------------------------------------------------------
# writer
# --------------------------------------------------------------------------

_PLAIN_ID_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_$]*")


def vid(name: str) -> str:
    """Render a net/instance name as a legal Verilog identifier."""
    if name in CONSTANT_NETS:
        return name
    if _PLAIN_ID_RE.fullmatch(name):
        return name
    return "\\" + name + " "


def write_verilog(nl: Netlist) -> str:
    out: list[str] = []
    ports = nl.port_names()
    port_list = ",\n    ".join(vid(p) for p in ports)
    out.append(f"module {nl.top} ({port_list});")
    for p in nl.ports:
        out.append(f" {p.direction} {vid(p.name)};")
    out.append("")
    port_set = set(ports)
    for net in nl.nets:
        if net in port_set or net in CONSTANT_NETS:
            continue
        out.append(f" wire {vid(net)};")
    out.append("")
    for inst in nl.instances:
        if not inst.connections:
            out.append(f" {inst.cell} {vid(inst.name)} ();")
            continue
        pins = list(inst.connections.items())
        lines = [f".{pin}({vid(net)})" for pin, net in pins]
        out.append(f" {inst.cell} {vid(inst.name)} (" + (",\n    ".join(lines)) + ");")
    out.append("endmodule")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# classification helpers
# --------------------------------------------------------------------------


def base_cell(cell: str) -> str:
    """`sky130_fd_sc_hd__decap_3` -> `decap_3`."""
    return cell.split("__", 1)[1] if "__" in cell else cell


def is_fill(cell: str, prefixes: tuple[str, ...] = FILL_PREFIXES) -> bool:
    base = base_cell(cell)
    return any(base.startswith(p) for p in prefixes)
