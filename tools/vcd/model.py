"""Data model shared by the VCD reader and writer.

Deliberately minimal — this covers what `tools/sim` needs (scalar and vector
`wire`/`reg` signals, `$timescale`, value-change events) and nothing else. It
is not a general-purpose VCD library: no `$comment` round-tripping, no real
(`r`) values, no strength/port-driver encodings. Extend it if a future
consumer needs more, rather than reaching for a third-party VCD package —
the format is small enough that a minimal reader/writer is the documented
choice for this issue (tools/README.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VcdVar:
    """One `$var` declaration."""

    var_type: str  # "wire", "reg", ... (kept verbatim, not interpreted)
    width: int
    identifier: str  # the short VCD identifier code, e.g. "!" or "%"
    name: str  # reference name, e.g. "O" (bit-select suffix stripped)
    scope: tuple[str, ...] = field(default_factory=tuple)

    @property
    def path(self) -> str:
        """Dotted hierarchical path, e.g. "puzzle.O"."""
        return ".".join((*self.scope, self.name))


@dataclass(frozen=True)
class ValueChange:
    """A single value-change event at an absolute time."""

    time: int
    identifier: str
    value: str  # raw value digits, no leading b/r and no sign: "0", "1",
    # "x", "z", or a multi-character bit string for vectors, always
    # normalized to `VcdVar.width` characters (see reader.normalize_value).


@dataclass
class VcdDocument:
    """A parsed (or to-be-written) VCD file."""

    timescale: str  # e.g. "1ps", verbatim from $timescale
    vars: list[VcdVar]
    changes: list[ValueChange]

    def vars_by_id(self) -> dict[str, VcdVar]:
        return {v.identifier: v for v in self.vars}

    def var_by_name(self, name: str) -> VcdVar:
        for v in self.vars:
            if v.name == name or v.path == name:
                return v
        raise KeyError(f"no $var named {name!r} in this VCD")

    def signal_history(self, name: str) -> list[tuple[int, str]]:
        """Return the (time, value) history of one signal, time-ordered.

        `value` is a normalized bit string, always exactly `width` characters
        (see `reader.normalize_value`). Only actual changes are returned
        (identical consecutive values are still returned since dumps can
        legitimately restate the same value; callers doing hold-value
        sampling should just take the last entry with time <= t).
        """
        v = self.var_by_name(name)
        hist = [(c.time, c.value) for c in self.changes if c.identifier == v.identifier]
        hist.sort(key=lambda tv: tv[0])
        return hist

    def value_at(self, name: str, t: int) -> str | None:
        """Held value of `name` at time `t` (last change at or before `t`)."""
        hist = self.signal_history(name)
        result = None
        for time, value in hist:
            if time > t:
                break
            result = value
        return result

    def end_time(self) -> int:
        return max((c.time for c in self.changes), default=0)
