"""Verilog testbench generation.

Two shapes are generated, both against whatever gate-level netlist is passed
in — the generators do not encode assumptions about cell types or the
"two shift registers into a comparator" warm-up shape (spec/puzzle.md is
explicit that shape is only a prior for the real puzzle):

  - `build_shift_load_testbench`: a *directed* test. It serially shifts a
    known byte into each of two named 1-bit serial inputs over 8 rising
    clock edges (MSB first) — the load protocol the warm-up's
    `shift_register` uses — then samples a named 1-bit output and checks it
    against a caller-supplied expected value. This drives the design itself
    rather than replaying a recording, so it needs no VCD.

  - `build_vcd_replay_testbench`: replays a previously-recorded VCD's input
    signal history verbatim (including the recorded clock edges — this is a
    literal replay, not a re-generated clock) into the DUT, and dumps a new
    VCD of the same signal set for the caller to diff against the original.
"""

from __future__ import annotations

from dataclasses import dataclass

from tools.vcd.model import VcdDocument

UNIT_DELAY_TIMESCALE = "1ns/1ps"


@dataclass(frozen=True)
class ShiftLoadCase:
    a: int
    b: int
    expected_s: bool
    label: str = ""


def build_shift_load_testbench(
    *,
    top: str,
    ports: dict[str, str],
    cases: list[ShiftLoadCase],
    clock_period_ns: int = 10,
) -> str:
    """Generate a directed shift-load-and-compare testbench.

    `ports` maps the DUT's own port names to the roles this generator drives:
    keys "clk", "rst_n", "en", "a", "b", "s" (all required). This is what
    lets the same generator target both `warmup/01_netlist.v` and, once
    available, an extracted netlist with the same top-level port names.
    """
    required = {"clk", "rst_n", "en", "a", "b", "s"}
    missing = required - set(ports)
    if missing:
        raise ValueError(f"ports mapping missing roles: {sorted(missing)}")

    half_period = clock_period_ns // 2
    n = len(cases)

    lines: list[str] = []
    lines.append(f"`timescale {UNIT_DELAY_TIMESCALE}")
    lines.append("module tb;")
    lines.append("  reg clk = 0, rst_n = 0, en = 0, a_in = 0, b_in = 0;")
    lines.append("  wire s_out;")
    lines.append("  integer i, case_idx;")
    lines.append("  integer failures = 0;")
    lines.append(f"  reg [7:0] a_vals [0:{n - 1}];")
    lines.append(f"  reg [7:0] b_vals [0:{n - 1}];")
    lines.append(f"  reg expected_vals [0:{n - 1}];")
    lines.append("")
    lines.append(
        f"  {top} dut ("
        f".{ports['clk']}(clk), .{ports['rst_n']}(rst_n), .{ports['en']}(en), "
        f".{ports['a']}(a_in), .{ports['b']}(b_in), .{ports['s']}(s_out));"
    )
    lines.append("")
    lines.append(f"  always #{half_period} clk = ~clk;")
    lines.append("")
    lines.append("  initial begin")
    for idx, case in enumerate(cases):
        lines.append(f"    a_vals[{idx}] = 8'd{case.a};")
        lines.append(f"    b_vals[{idx}] = 8'd{case.b};")
        lines.append(f"    expected_vals[{idx}] = 1'b{1 if case.expected_s else 0};")
    lines.append("    for (case_idx = 0; case_idx < " + str(n) + "; case_idx = case_idx + 1) begin")
    lines.append("      @(negedge clk);")
    lines.append("      rst_n = 0; en = 0;")
    lines.append("      @(negedge clk);")
    lines.append("      rst_n = 1;")
    lines.append("      for (i = 7; i >= 0; i = i - 1) begin")
    lines.append("        a_in = a_vals[case_idx][i];")
    lines.append("        b_in = b_vals[case_idx][i];")
    lines.append("        en = 1;")
    lines.append("        @(negedge clk);")
    lines.append("      end")
    lines.append("      en = 0;")
    lines.append("      #1;")
    lines.append("      if (s_out !== expected_vals[case_idx]) begin")
    lines.append("        failures = failures + 1;")
    lines.append(
        "        $display(\"CASE %0d MISMATCH a=%0d b=%0d expected_s=%b got_s=%b\", "
        "case_idx, a_vals[case_idx], b_vals[case_idx], expected_vals[case_idx], s_out);"
    )
    lines.append("      end else begin")
    lines.append(
        "        $display(\"CASE %0d OK a=%0d b=%0d s=%b\", "
        "case_idx, a_vals[case_idx], b_vals[case_idx], s_out);"
    )
    lines.append("      end")
    lines.append("    end")
    lines.append('    if (failures == 0) $display("RESULT PASS");')
    lines.append('    else $display("RESULT FAIL %0d", failures);')
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def _verilog_literal(value: str, width: int) -> str:
    # `value` is already normalized to `width` characters of 0/1/x/z by
    # tools.vcd.reader.normalize_value.
    return f"{width}'b{value}" if width > 1 else f"1'b{value}"


def build_vcd_replay_testbench(
    *,
    top: str,
    port_map: dict[str, str | list[str]],
    input_names: list[str],
    output_names: list[str],
    recorded: VcdDocument,
    dump_path: str,
    margin: int = 1000,
) -> str:
    """Generate a testbench that replays `recorded`'s input history into `top`.

    `port_map` maps recorded-VCD signal names (both inputs and outputs) to
    the DUT's own port names — they need not match (net/instance renaming is
    exactly what stage 4 of spec/puzzle.md strips, but top-level port names
    should survive; port_map exists so a mismatch there doesn't require
    touching this generator).

    A `port_map` value is either a single DUT port name (connects the whole
    recorded signal to one DUT port, scalar or vector — the original,
    unchanged behaviour) or a list of `width` DUT port names, one per bit,
    ordered bit 0 (LSB) first. The list form is for netlists extracted
    straight from GDS pin labels, which have no bus abstraction and so
    declare one scalar port per bit (e.g. `\\O[0]` .. `\\O[7]`) rather than a
    single `[7:0]` vector port — exactly the shape `tools/extract` produces.

    The generated testbench's own wires/regs are named identically to the
    *recorded* VCD signal names and are what gets dumped to `dump_path` — so
    the resulting VCD is directly comparable to `recorded` via
    `tools.vcd.read_vcd` without any further name translation.
    """
    missing_ports = [n for n in input_names + output_names if n not in port_map]
    if missing_ports:
        raise ValueError(f"port_map missing entries for: {missing_ports}")

    widths: dict[str, int] = {}
    for name in input_names + output_names:
        widths[name] = recorded.var_by_name(name).width

    for name in input_names + output_names:
        mapped = port_map[name]
        if isinstance(mapped, list) and len(mapped) != widths[name]:
            raise ValueError(
                f"port_map[{name!r}] has {len(mapped)} entries but the recorded "
                f"signal is {widths[name]} bits wide — provide one DUT port name per bit"
            )

    events: list[tuple[int, str, str]] = []
    for name in input_names:
        for time, value in recorded.signal_history(name):
            events.append((time, name, value))
    events.sort(key=lambda e: (e[0], e[1]))

    lines: list[str] = []
    lines.append(f"`timescale {recorded.timescale}/{recorded.timescale}")
    lines.append("module tb;")
    for name in input_names:
        w = widths[name]
        decl = f"[{w - 1}:0] " if w > 1 else ""
        lines.append(f"  reg {decl}{name} = 'bx;")
    for name in output_names:
        w = widths[name]
        decl = f"[{w - 1}:0] " if w > 1 else ""
        lines.append(f"  wire {decl}{name};")
    lines.append("")

    def _connections(name: str) -> list[str]:
        mapped = port_map[name]
        # Trailing space after the DUT port name is required, not
        # cosmetic: an escaped Verilog identifier (`\O[0]`) is only
        # terminated by whitespace, so `.{port}(...)` with no space would
        # be mis-tokenized as part of the identifier itself.
        if isinstance(mapped, list):
            return [f".{mapped[i]} ({name}[{i}])" for i in range(widths[name])]
        return [f".{mapped} ({name})"]

    port_conns = ", ".join(conn for n in input_names + output_names for conn in _connections(n))
    lines.append(f"  {top} dut ({port_conns});")
    lines.append("")
    lines.append("  initial begin")
    lines.append(f'    $dumpfile("{dump_path}");')
    dump_sig_list = ", ".join(input_names + output_names)
    lines.append(f"    $dumpvars(0, {dump_sig_list});")

    last_time = 0
    for time, name, value in events:
        delay = time - last_time
        if delay > 0:
            lines.append(f"    #{delay};")
            last_time = time
        lines.append(f"    {name} = {_verilog_literal(value, widths[name])};")

    lines.append(f"    #{margin};")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class SequenceExpectation:
    """Assert `signal` (a watched DUT output) equals `value` at `cycle`."""

    cycle: int
    signal: str
    value: int


def build_sequence_testbench(
    *,
    top: str,
    clock_port: str,
    drive: dict[str, list[int]],
    watch: list[str],
    expect: list[SequenceExpectation] | None = None,
    clock_period_ns: int = 10,
    sample_lead_ns: int = 1,
) -> str:
    """Generate a testbench that drives a caller-supplied per-cycle bit sequence.

    Unlike `build_vcd_replay_testbench`, nothing here is replayed from a
    recording: `drive` maps each 1-bit DUT input port to an explicit list of
    per-cycle values, which is what a *solver-produced* stimulus looks like
    (`tools/sim/bmc.py`). All lists must be the same length.

    Timing matches the cycle model in `tools/sim/seqmodel.py`: cycle `t`
    starts at `t * clock_period_ns`, the inputs for that cycle are applied
    there, the rising clock edge follows half a period later, and the
    watched outputs are sampled `sample_lead_ns` before the *next* cycle's
    edge — i.e. the values a design settles to with cycle `t`'s inputs and
    the state it entered cycle `t` with.

    Each sampled cycle prints one `CYCLE <t> <sig>=<bit> ...` line;
    `expect` entries are checked against those samples and summarised as a
    final `RESULT PASS` / `RESULT FAIL <n>` line.
    """
    if not drive:
        raise ValueError("drive must name at least one input port")
    lengths = {len(v) for v in drive.values()}
    if len(lengths) != 1:
        raise ValueError(f"drive sequences have differing lengths: { {k: len(v) for k, v in drive.items()} }")
    n_cycles = lengths.pop()
    if clock_period_ns < 2 or clock_period_ns % 2:
        raise ValueError("clock_period_ns must be an even number of ns >= 2")
    if not 0 < sample_lead_ns < clock_period_ns // 2:
        raise ValueError("sample_lead_ns must fall between the cycle start and the rising edge")
    expect = expect or []
    unknown = {e.signal for e in expect} - set(watch)
    if unknown:
        raise ValueError(f"expectations name unwatched signals: {sorted(unknown)}")

    half = clock_period_ns // 2
    sample_at = half - sample_lead_ns
    reg_names = {port: f"drv_{i}" for i, port in enumerate(drive)}
    wire_names = {port: f"obs_{i}" for i, port in enumerate(watch)}

    lines = [f"`timescale {UNIT_DELAY_TIMESCALE}", "module tb;"]
    lines.append("  reg clk = 0;")
    lines.append("  integer t;")
    lines.append("  integer failures = 0;")
    for port, reg in reg_names.items():
        lines.append(f"  reg {reg} = 1'b0;   // -> {port}")
    for port, wire in wire_names.items():
        lines.append(f"  wire {wire};        // <- {port}")
    for port, reg in reg_names.items():
        lines.append(f"  reg [{max(n_cycles - 1, 0)}:0] {reg}_vec;")
    lines.append("")
    # A trailing space after each port name is required for escaped
    # identifiers (`\O[0] `), which are only terminated by whitespace.
    conns = [f".{clock_port} (clk)"]
    conns += [f".{p} ({r})" for p, r in reg_names.items()]
    conns += [f".{p} ({w})" for p, w in wire_names.items()]
    lines.append(f"  {top} dut ({', '.join(conns)});")
    lines.append("")
    lines.append(f"  always #{half} clk = ~clk;")
    lines.append("")
    lines.append("  initial begin")
    for port, reg in reg_names.items():
        bits = "".join(str(b) for b in reversed(drive[port]))
        lines.append(f"    {reg}_vec = {n_cycles}'b{bits};")
    lines.append(f"    for (t = 0; t < {n_cycles}; t = t + 1) begin")
    for port, reg in reg_names.items():
        lines.append(f"      {reg} = {reg}_vec[t];")
    lines.append(f"      #{sample_at};")
    fmt = " ".join(f"{p}=%b" for p in watch)
    args = ", ".join(wire_names[p] for p in watch)
    lines.append(f'      $display("CYCLE %0d {fmt}", t{", " + args if args else ""});')
    for e in expect:
        lines.append(f"      if (t == {e.cycle} && {wire_names[e.signal]} !== 1'b{e.value}) begin")
        lines.append("        failures = failures + 1;")
        lines.append(
            f'        $display("EXPECT FAIL cycle=%0d signal={e.signal} '
            f'want={e.value} got=%b", t, {wire_names[e.signal]});'
        )
        lines.append("      end")
    lines.append(f"      #{clock_period_ns - sample_at};")
    lines.append("    end")
    lines.append('    if (failures == 0) $display("RESULT PASS");')
    lines.append('    else $display("RESULT FAIL %0d", failures);')
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"
