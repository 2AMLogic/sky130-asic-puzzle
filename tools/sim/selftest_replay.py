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

from tools.sim.replay import run_vcd_replay
from tools.sim.testbench import ShiftLoadCase
from tools.sim.warmup_recorder import REPLAY_PORT_MAP, record_shift_load_vcd
from tools.vcd.reader import read_vcd
from tools.vcd.writer import document_to_vcd

RECORD_CASES = [
    ShiftLoadCase(a=248, b=248, expected_s=True, label="exact"),
    ShiftLoadCase(a=255, b=240, expected_s=False, label="near-miss-low"),
    ShiftLoadCase(a=255, b=242, expected_s=False, label="near-miss-high"),
    ShiftLoadCase(a=10, b=20, expected_s=False, label="small"),
]


def record_warmup_vcd(netlist: Path, out_vcd: Path, work_dir: Path) -> None:
    record_shift_load_vcd(netlist, RECORD_CASES, out_vcd, work_dir)


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
