"""Minimal VCD reader.

Handles the subset of IEEE 1364 VCD that `example_inputs.vcd` and Icarus
Verilog's own `$dumpfile`/`$dumpvars` output use: `$date`/`$version`/
`$timescale`/`$comment` headers, nested `$scope`/`$var`/`$upscope`
declarations, and `$dumpvars`/`$dumpall`/`$dumpon`/`$dumpoff` value-change
sections with scalar (`0!`) and vector (`b0000000 %`) value changes. Real
(`r`) values are tokenized but not interpreted (this repo's signals are all
2-state digital).

Deliberately not a general-purpose VCD library — see model.py's docstring.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import ValueChange, VcdDocument, VcdVar

_TOKEN_RE = re.compile(r"\S+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def normalize_value(raw: str, width: int) -> str:
    """Pad/truncate a value-change bit string to exactly `width` characters.

    Per the VCD spec, a vector value shorter than its declared width is
    extended using its own most-significant (leftmost) character — so
    dumping 0 as "b0" for an 8-bit signal means "b00000000", and dumping X
    as "bx" means all-X. A value longer than `width` (shouldn't happen from
    a well-formed dump) is truncated to its low-order bits.
    """
    if width <= 0:
        return raw
    if len(raw) == width:
        return raw
    if len(raw) > width:
        return raw[-width:]
    if not raw:
        return "x" * width
    fill = raw[0]
    return (fill * (width - len(raw))) + raw


def read_vcd(path: str | Path) -> VcdDocument:
    text = Path(path).read_text()
    tokens = _tokenize(text)

    timescale = "1s"
    vars_: list[VcdVar] = []
    changes: list[ValueChange] = []
    scope_stack: list[str] = []
    current_time = 0
    in_definitions = True

    i = 0
    n = len(tokens)

    def consume_until_end() -> list[str]:
        nonlocal i
        collected = []
        while i < n and tokens[i] != "$end":
            collected.append(tokens[i])
            i += 1
        if i < n:
            i += 1  # skip $end
        return collected

    while i < n:
        tok = tokens[i]

        if tok == "$timescale":
            i += 1
            body = consume_until_end()
            timescale = "".join(body)
            continue

        if tok in ("$date", "$version", "$comment"):
            i += 1
            consume_until_end()
            continue

        if tok == "$scope":
            i += 1
            body = consume_until_end()  # [type, name]
            name = body[1] if len(body) > 1 else (body[0] if body else "")
            scope_stack.append(name)
            continue

        if tok == "$upscope":
            i += 1
            consume_until_end()
            if scope_stack:
                scope_stack.pop()
            continue

        if tok == "$var":
            i += 1
            body = consume_until_end()  # [type, size, id, name, ...bitselect]
            if len(body) < 4:
                continue
            var_type, size_str, ident, name = body[0], body[1], body[2], body[3]
            vars_.append(
                VcdVar(
                    var_type=var_type,
                    width=int(size_str),
                    identifier=ident,
                    name=name,
                    scope=tuple(scope_stack),
                )
            )
            continue

        if tok == "$enddefinitions":
            i += 1
            consume_until_end()
            in_definitions = False
            continue

        if tok in ("$dumpvars", "$dumpall", "$dumpon", "$dumpoff"):
            i += 1
            continue  # value changes until the matching $end follow as plain tokens

        if tok == "$end":
            i += 1
            continue

        if tok.startswith("$"):
            # Unknown keyword block — skip forward-compatibly.
            i += 1
            consume_until_end()
            continue

        if in_definitions:
            # Stray token before $enddefinitions — ignore.
            i += 1
            continue

        if tok.startswith("#"):
            current_time = int(tok[1:])
            i += 1
            continue

        first = tok[0]
        if first in "01xXzZ":
            ident = tok[1:]
            if ident:
                changes.append(ValueChange(time=current_time, identifier=ident, value=first.lower()))
            i += 1
            continue

        if first in "bB":
            value_str = tok[1:]
            i += 1
            if i < n:
                ident = tokens[i]
                i += 1
                changes.append(ValueChange(time=current_time, identifier=ident, value=value_str.lower()))
            continue

        if first in "rR":
            i += 1
            if i < n:
                i += 1  # skip identifier — real values are tokenized, not modeled
            continue

        # Unrecognized token — skip.
        i += 1

    var_widths = {v.identifier: v.width for v in vars_}
    normalized_changes = [
        ValueChange(
            time=c.time,
            identifier=c.identifier,
            value=normalize_value(c.value, var_widths.get(c.identifier, len(c.value))),
        )
        for c in changes
    ]

    return VcdDocument(timescale=timescale, vars=vars_, changes=normalized_changes)
