"""Record a warm-up shift-load simulation to a real VCD.

Shared by two consumers of the same "drive a netlist through the shift-load
protocol, dump a VCD" step:

  - `tools/sim/selftest_replay.py` records against `01_netlist.v` and
    replays the result back against the *same* netlist, as an engine
    self-test (no ground truth needed — zero divergence is definitionally
    correct).
  - `tools/sim/run_warmup_cross_check.py` records against `01_netlist.v`
    and replays the result against a *second* netlist (e.g.
    `evidence/warmup-extracted.v`), diffing the two — the functional
    counterpart to the structural comparator (issue #5 acceptance
    criterion 2).

Kept separate from `tools.sim.testbench.build_shift_load_testbench` (which
self-checks entirely in Verilog, producing a pass/fail line per case, no
VCD) because the point here is a VCD artifact to replay elsewhere, not an
in-simulation verdict. The shift-load *protocol* itself — the part that
has to match the hardware — is one definition, emitted by
`tools.sim.testbench._emit_shift_load_protocol` for both generators; only
the verdict-vs-dump tail differs.
"""

from __future__ import annotations

from pathlib import Path

from tools.sim.directed import DEFAULT_PORTS
from tools.sim.icarus import compile_and_run
from tools.sim.pdk import resolve_sky130_models
from tools.sim.testbench import ShiftLoadCase, _emit_shift_load_protocol

# The recorder testbench always dumps signals under these fixed local
# names (see `build_shift_load_recorder_testbench` below), matching the
# convention `puzzle/example_inputs.vcd` uses for the puzzle (recorded
# signal name == DUT top-level port name) — so replaying a recording made
# by this module against a netlist with the same port names uses the
# identity port_map.
REPLAY_PORT_MAP = {"clk": "clk", "rst_n": "rst_n", "en": "en", "A": "A", "B": "B", "S": "S"}


def build_shift_load_recorder_testbench(
    *,
    top: str,
    ports: dict[str, str],
    cases: list[ShiftLoadCase],
    dump_path: Path,
    clock_period_ns: int = 10,
) -> str:
    """Drive `cases` through `top` via the shift-load protocol, dumping a VCD.

    The dumped signal names are always the fixed local names `clk`,
    `rst_n`, `en`, `A`, `B`, `S` — `ports` maps those roles to the DUT's
    own port names for the instance connection, exactly like
    `build_shift_load_testbench`. The protocol half is the shared
    `_emit_shift_load_protocol` (which also validates `ports`); only the
    `$dumpfile`/`$dumpvars` prologue and the settle tail are defined here.
    """
    lines = _emit_shift_load_protocol(
        top=top,
        ports=ports,
        cases=cases,
        local_names=("A", "B", "S"),
        clock_period_ns=clock_period_ns,
        verdict_registers=False,
        initial_prologue=[
            f'    $dumpfile("{dump_path}");',
            "    $dumpvars(0, clk, rst_n, en, A, B, S);",
        ],
    )
    lines.append("      #20;")
    lines.append("    end")
    lines.append("    #20;")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def record_shift_load_vcd(
    netlist: Path,
    cases: list[ShiftLoadCase],
    out_vcd: Path,
    work_dir: Path,
    *,
    top: str = "adder_demo",
    ports: dict[str, str] | None = None,
    clock_period_ns: int = 10,
) -> None:
    """Simulate `netlist` through `cases` and dump D/A/B/S history to `out_vcd`."""
    ports = ports or DEFAULT_PORTS
    models = resolve_sky130_models()
    work_dir.mkdir(parents=True, exist_ok=True)
    tb_source = build_shift_load_recorder_testbench(
        top=top, ports=ports, cases=cases, dump_path=out_vcd, clock_period_ns=clock_period_ns
    )
    tb_path = work_dir / "tb_record.v"
    tb_path.write_text(tb_source)
    sim = compile_and_run([tb_path, netlist, *models.model_files()], work_dir=work_dir)
    failure = sim.failure_message()
    if failure is not None:
        raise RuntimeError(f"failed to record warm-up VCD:\n{failure}")
    if not out_vcd.exists():
        raise RuntimeError(f"failed to record warm-up VCD: {out_vcd} was not created\n"
                           f"{sim.compile_stderr}\n{sim.run_stderr}")
