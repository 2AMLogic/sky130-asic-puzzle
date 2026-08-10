"""Stage 8: decode the message a recovered output generator emits.

`spec/puzzle.md` stage 8 is "simulate the output generator with the solved
inputs" — mechanical, once stage 7 (`tools/sim/solve.py`) has produced a
proven input sequence. The one genuinely open question is the byte-bit
ordering: does output port index 0 (`O[0]`) carry the byte's LSB or its
MSB? `evidence/puzzle-solve.md` §9 records that this was *not* established
by anything simulated — a "nine printable ASCII characters" observation was
a human read of a VCD, not a decode this repo had checked. This module
checks it instead of assuming it: both orderings are always computed from
the same sampled bits, and the one that actually produces printable ASCII
is reported, alongside the one that doesn't, so the choice is visible in
the evidence record rather than hidden inside a hardcoded shift direction.

`tools/sim/selftest_answer.py` proves this mechanism against a synthetic,
non-embargoed fixture before `tools/sim/run_answer.py` ever points it at
the puzzle netlist.
"""

from __future__ import annotations

from dataclasses import dataclass

PRINTABLE_LO = 0x20
PRINTABLE_HI = 0x7F  # exclusive


@dataclass(frozen=True)
class ByteOrder:
    """One candidate mapping from 8 per-cycle output bits to a byte value.

    `index0_is_msb=False` treats output port index 0 as bit 0 (weight
    2**0, i.e. the byte's LSB) and index 7 as bit 7 (the MSB) — the
    "plain vector" reading of `O[7:0]`. `index0_is_msb=True` is the
    opposite: index 0 is the MSB. Both are checked; neither is assumed.
    """

    name: str
    index0_is_msb: bool

    def value(self, bits: list[int]) -> int:
        if self.index0_is_msb:
            return sum(b << (7 - i) for i, b in enumerate(bits))
        return sum(b << i for i, b in enumerate(bits))


ORDERS: tuple[ByteOrder, ...] = (
    ByteOrder("index0_lsb", index0_is_msb=False),
    ByteOrder("index0_msb", index0_is_msb=True),
)


def sample_bits(
    samples: list[dict[str, str]], output_ports: list[str], *, cycle_key: str = "cycle"
) -> dict[int, list[int]]:
    """`cycle -> [bit(port0), bit(port1), ...]` for every fully-sampled row.

    `output_ports` are the *bare* (no leading backslash) names to look up in
    a `VerifyResult.samples` row — Icarus drops the backslash from an
    escaped Verilog identifier (`\\O[0]`) when it renders that identifier
    inside a `$display` string literal, so a sampled row's key is the bare
    token `O[0]`, not the escaped DUT port name `\\O[0]` used to declare or
    connect it. This was confirmed empirically (not assumed) while building
    this module: a `$display("... \\O[0]=%b ...")` format string in Icarus
    prints `O[0]=<bit>` in its stdout, silently dropping the backslash
    (Verilog string literals treat `\\` followed by a non-special character
    as an unrecognized escape; Icarus passes the character through and
    drops the backslash). A row missing any requested port, or whose value
    is not `0`/`1` (e.g. `x` during reset), is skipped rather than guessed.
    """
    out: dict[int, list[int]] = {}
    for row in samples:
        if cycle_key not in row or not all(p in row for p in output_ports):
            continue
        raw = [row[p] for p in output_ports]
        if any(v not in ("0", "1") for v in raw):
            continue
        out[int(row[cycle_key])] = [int(v) for v in raw]
    return out


def longest_printable_run(byte_seq: list[int]) -> tuple[int, int]:
    """`[start, end)` indices of the longest contiguous run of printable ASCII.

    Ties keep the first (earliest) run. An input with no printable bytes at
    all returns `(0, 0)` (an empty run), not an error — the caller decides
    what an empty message means.
    """
    best = (0, 0)
    i, n = 0, len(byte_seq)
    while i < n:
        if PRINTABLE_LO <= byte_seq[i] < PRINTABLE_HI:
            j = i
            while j < n and PRINTABLE_LO <= byte_seq[j] < PRINTABLE_HI:
                j += 1
            if j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    return best


@dataclass
class DecodeResult:
    order: ByteOrder
    cycles: list[int]
    bytes_all: list[int]
    message_start: int
    message_end: int

    @property
    def message_bytes(self) -> list[int]:
        return self.bytes_all[self.message_start : self.message_end]

    @property
    def message_cycles(self) -> list[int]:
        return self.cycles[self.message_start : self.message_end]

    @property
    def message(self) -> str:
        return "".join(chr(b) for b in self.message_bytes)

    @property
    def printable_count(self) -> int:
        return sum(1 for b in self.bytes_all if PRINTABLE_LO <= b < PRINTABLE_HI)

    def rendered(self) -> str:
        """The full observed byte sequence, non-printable bytes shown as `.`."""
        return "".join(chr(b) if PRINTABLE_LO <= b < PRINTABLE_HI else "." for b in self.bytes_all)


def decode_output_cycles(
    samples: list[dict[str, str]], output_ports: list[str], cycles: list[int]
) -> dict[str, DecodeResult]:
    """Decode watched per-cycle output bits under every candidate byte order.

    Returns one `DecodeResult` per `ORDERS` entry, keyed by its `name` —
    nothing here picks a winner (see `select_order`), so both stay
    available for the evidence record even after one is chosen.
    """
    by_cycle = sample_bits(samples, output_ports)
    present = [t for t in cycles if t in by_cycle]
    results: dict[str, DecodeResult] = {}
    for order in ORDERS:
        byte_seq = [order.value(by_cycle[t]) for t in present]
        start, end = longest_printable_run(byte_seq)
        results[order.name] = DecodeResult(
            order=order,
            cycles=present,
            bytes_all=byte_seq,
            message_start=start,
            message_end=end,
        )
    return results


def select_order(results: dict[str, DecodeResult]) -> DecodeResult:
    """Pick the byte order with the longest printable run (ties: more printable bytes total)."""
    return max(
        results.values(),
        key=lambda r: (r.message_end - r.message_start, r.printable_count),
    )
