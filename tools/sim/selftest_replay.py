"""Self-test the VCD replay engine against the warm-up, before it is ever
pointed at the puzzle.

`puzzle/example_inputs.vcd` is the only recorded trace this repo has, and
it's for `puzzle.gds` — which has no extracted netlist yet (blocked on #2).
So `tools/sim/replay.py`'s reader -> testbench -> simulate -> diff pipeline
would otherwise go completely unexercised until it's pointed at embargoed
content for the first time. Instead:

  1. Record a VCD of a *directed* warm-up simulation (several shift-load
     cases against `warmup/01_netlist.v`, dumped via `$dumpvars`) — this
     becomes the "recorded" trace, playing the same role
     `example_inputs.vcd` will play for the puzzle.
  2. Replay it back through `run_vcd_replay` against the *same* netlist and
     confirm zero divergence — this exercises the exact reader -> testbench
     -> simulate -> diff path stage 6 needs.
  3. Corrupt one bit of the recording at one timestamp and replay again,
     confirming the engine reports that exact (time, signal) as the first
     divergence — a passing self-test that can't actually detect a mismatch
     would be worse than no self-test at all.

Nothing here touches `puzzle/`; only `warmup/`, which CLAUDE.md §4 says is
not embargoed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tools.sim.directed import DEFAULT_PORTS
from tools.sim.icarus import compile_and_run
from tools.sim.pdk import resolve_sky130_models
from tools.sim.replay import run_vcd_replay
from tools.sim.testbench import ShiftLoadCase, UNIT_DELAY_TIMESCALE
from tools.vcd.reader import read_vcd
from tools.vcd.writer import document_to_vcd

# `example_inputs.vcd`'s signal names are the DUT's own top-level port
# names for the puzzle; the warm-up's recorded trace here uses the same
# convention (the recorder testbench below dumps signals literally named
# clk/rst_n/en/A/B/S), so replay's port_map is the identity map.
REPLAY_PORT_MAP = {"clk": "clk", "rst_n": "rst_n", "en": "en", "A": "A", "B": "B", "S": "S"}

RECORD_CASES = [
    ShiftLoadCase(a=248, b=248, expected_s=True, label="exact"),
    ShiftLoadCase(a=255, b=240, expected_s=False, label="near-miss-low"),
    ShiftLoadCase(a=255, b=242, expected_s=False, label="near-miss-high"),
    ShiftLoadCase(a=10, b=20, expected_s=False, label="small"),
]


def _build_recorder_testbench(top: str, ports: dict[str, str], cases: list[ShiftLoadCase], dump_path: Path) -> str:
    """A shift-load driver that dumps a real VCD instead of self-checking.

    Distinct from `tools.sim.testbench.build_shift_load_testbench` (which
    self-checks in Verilog) because the point here is to produce a VCD
    artifact to replay, not a pass/fail — kept separate rather than
    overloading that generator with a dump-or-check mode switch.
    """
    lines: list[str] = []
    lines.append(f"`timescale {UNIT_DELAY_TIMESCALE}")
    lines.append("module tb;")
    lines.append("  reg clk = 0, rst_n = 0, en = 0, A = 0, B = 0;")
    lines.append("  wire S;")
    lines.append("  integer i, case_idx;")
    n = len(cases)
    lines.append(f"  reg [7:0] a_vals [0:{n - 1}];")
    lines.append(f"  reg [7:0] b_vals [0:{n - 1}];")
    lines.append(
        f"  {top} dut (.{ports['clk']}(clk), .{ports['rst_n']}(rst_n), .{ports['en']}(en), "
        f".{ports['a']}(A), .{ports['b']}(B), .{ports['s']}(S));"
    )
    lines.append("  always #5 clk = ~clk;")
    lines.append("  initial begin")
    lines.append(f'    $dumpfile("{dump_path}");')
    lines.append("    $dumpvars(0, clk, rst_n, en, A, B, S);")
    for idx, case in enumerate(cases):
        lines.append(f"    a_vals[{idx}] = 8'd{case.a};")
        lines.append(f"    b_vals[{idx}] = 8'd{case.b};")
    lines.append(f"    for (case_idx = 0; case_idx < {n}; case_idx = case_idx + 1) begin")
    lines.append("      @(negedge clk);")
    lines.append("      rst_n = 0; en = 0;")
    lines.append("      @(negedge clk);")
    lines.append("      rst_n = 1;")
    lines.append("      for (i = 7; i >= 0; i = i - 1) begin")
    lines.append("        A = a_vals[case_idx][i];")
    lines.append("        B = b_vals[case_idx][i];")
    lines.append("        en = 1;")
    lines.append("        @(negedge clk);")
    lines.append("      end")
    lines.append("      en = 0;")
    lines.append("      #20;")
    lines.append("    end")
    lines.append("    #20;")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def record_warmup_vcd(netlist: Path, out_vcd: Path, work_dir: Path) -> None:
    models = resolve_sky130_models()
    work_dir.mkdir(parents=True, exist_ok=True)
    tb_source = _build_recorder_testbench("adder_demo", DEFAULT_PORTS, RECORD_CASES, out_vcd)
    tb_path = work_dir / "tb_record.v"
    tb_path.write_text(tb_source)
    sim = compile_and_run([tb_path, netlist, *models.model_files()], work_dir=work_dir)
    if not sim.compiled or not sim.ran or not out_vcd.exists():
        raise RuntimeError(f"failed to record warm-up VCD:\n{sim.compile_stderr}\n{sim.run_stderr}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    netlist = repo_root / "puzzle" / "warmup" / "01_netlist.v"
    if not netlist.exists():
        print(f"missing {netlist} — run ./scripts/fetch-puzzle.sh first", file=sys.stderr)
        return 1

    work_dir = repo_root / ".sim-work" / "selftest"
    work_dir.mkdir(parents=True, exist_ok=True)
    recorded_vcd = work_dir / "recorded.vcd"

    print("== recording a directed warm-up VCD (this is the 'recorded' trace for the self-test) ==")
    record_warmup_vcd(netlist, recorded_vcd, work_dir / "record")
    print(f"recorded: {recorded_vcd}")

    print("\n== replaying the recording back against the same netlist (expect zero divergence) ==")
    clean_result = run_vcd_replay(
        [netlist],
        recorded_vcd,
        top="adder_demo",
        port_map=REPLAY_PORT_MAP,
        input_names=["clk", "rst_n", "en", "A", "B"],
        output_names=["S"],
        work_dir=work_dir / "replay-clean",
    )
    print(f"ok={clean_result.ok} compared_through={clean_result.compared_through}")
    if clean_result.first_divergence:
        d = clean_result.first_divergence
        print(f"UNEXPECTED divergence: t={d.time} signal={d.signal} expected={d.expected} actual={d.actual}")

    print("\n== replaying a corrupted recording (expect a reported divergence) ==")
    doc = read_vcd(recorded_vcd)
    s_hist = doc.signal_history("S")
    # Flip the last recorded S value at its timestamp — the mutation must
    # land on the *recorded* side, not the simulator, so a genuine mismatch
    # exists for the diff to find.
    flip_time, flip_value = s_hist[-1]
    flipped = "1" if flip_value == "0" else "0"
    mutated_changes = [c for c in doc.changes if not (c.identifier == doc.var_by_name("S").identifier and c.time == flip_time)]
    doc.changes = mutated_changes + [
        type(doc.changes[0])(time=flip_time, identifier=doc.var_by_name("S").identifier, value=flipped)
    ]
    corrupted_vcd = work_dir / "corrupted.vcd"
    document_to_vcd(doc, corrupted_vcd)

    corrupt_result = run_vcd_replay(
        [netlist],
        corrupted_vcd,
        top="adder_demo",
        port_map=REPLAY_PORT_MAP,
        input_names=["clk", "rst_n", "en", "A", "B"],
        output_names=["S"],
        work_dir=work_dir / "replay-corrupt",
    )
    print(f"ok={corrupt_result.ok} compared_through={corrupt_result.compared_through}")
    detected = False
    if corrupt_result.first_divergence:
        d = corrupt_result.first_divergence
        detected = d.time == flip_time and d.signal == "S"
        print(f"reported divergence: t={d.time} signal={d.signal} expected={d.expected} actual={d.actual}")
        print(f"expected divergence at t={flip_time} signal=S: {'MATCH' if detected else 'MISMATCH — bug in the diff engine'}")
    else:
        print("no divergence reported — BUG: the mutation should have been caught")

    passed = clean_result.ok and (not corrupt_result.ok) and detected
    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
