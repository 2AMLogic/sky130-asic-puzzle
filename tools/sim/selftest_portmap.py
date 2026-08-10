"""Self-test the multi-bit `port_map` connection logic in `tools/sim/testbench.py`.

`tools/extract`'s netlists declare one scalar port per bit for a bus
(`\\O[0]` .. `\\O[7]`), not a `[7:0]` vector port — layouts have no bus
abstraction, only per-bit pin labels. Issue #5's puzzle replay
(`evidence/puzzle-replay.md`) needs `run_vcd_replay` to connect a recorded
multi-bit signal to that shape, so `build_vcd_replay_testbench`'s `port_map`
was extended to accept a list of per-bit DUT port names (bit 0 first)
instead of a single name. This exercises that path end-to-end against a
tiny synthetic DUT — no sky130 cells, no GDS, nothing embargoed — so the
bit-wiring logic is proven correct before it is ever pointed at the real
extracted puzzle netlist.

Like `selftest_replay.py`, the reference trace is recorded via a real
simulation run rather than hand-built: a dumped VCD's raw timestamps are
expressed in whatever precision the whole compiled design resolves to
(governed by the finest `` `timescale `` among all compiled sources,
including the PDK model files `run_vcd_replay` always links in) — a
hand-constructed `VcdDocument` with an arbitrary timescale would not match
that resolved precision, and `diff_output_traces` compares raw timestamps
directly with no unit conversion. Recording through the same compile
pipeline the replay itself uses sidesteps that entirely.

Three checks, mirroring the positive/negative-control discipline the other
`tools/sim` self-tests use (`selftest_pdk.py`, `selftest_replay.py`) so a
broken implementation cannot pass vacuously:

  1. [control] Correct bit-order wiring reproduces the recorded trace
     exactly (zero divergence) for a non-palindromic 8-bit pattern.
  2. Reversed bit-order wiring against the *same* recording is caught as a
     divergence — proving check 1 is not passing merely because bit order
     doesn't matter for this DUT.
  3. A single corrupted bit in the recording is reported at exactly its
     (time, signal) — the same corruption-detection discipline
     `selftest_replay.py` uses for the single-port path.

Requires a resolvable sky130 PDK (same as `selftest_replay.py`) even though
the DUT itself has no sky130 dependency — `run_vcd_replay` unconditionally
resolves and compiles the model files alongside every netlist it is given.
"""

from __future__ import annotations

from pathlib import Path

from tools.sim.icarus import compile_and_run
from tools.sim.pdk import PdkResolutionError, resolve_sky130_models
from tools.sim.replay import run_vcd_replay
from tools.vcd.model import ValueChange
from tools.vcd.reader import read_vcd
from tools.vcd.writer import document_to_vcd

WIDTH = 8
# Deliberately non-palindromic per value (and across values) so a reversed
# bit order changes the sampled value at every step — see check 2.
D_VALUES = ["10100101", "00011011", "11110000", "01000010"]


def _build_tinydut() -> str:
    """A tiny combinational passthrough with one scalar port per output bit.

    `\\Q[i] = D[i]` for each i — no clock, no sky130 cells. Mirrors the
    port shape `tools/extract` produces for a bus (issue #5's "Affected
    Files" note): a bus pin label on the GDS has no vector abstraction, so
    extraction emits one scalar port per bit.
    """
    lines = ["module tinydut (D,"]
    lines += [f"    \\Q[{i}] ," for i in range(WIDTH - 1)]
    lines.append(f"    \\Q[{WIDTH - 1}] );")
    lines.append(f" input [{WIDTH - 1}:0] D;")
    for i in range(WIDTH):
        lines.append(f" output \\Q[{i}] ;")
    for i in range(WIDTH):
        lines.append(f" assign \\Q[{i}]  = D[{i}];")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def _build_recorder_testbench(dump_path: Path) -> str:
    """Drive D through `D_VALUES` and dump D/Q from a *direct* instantiation.

    Uses the same per-bit escaped-port connection shape `tinydut` exposes
    (not `build_vcd_replay_testbench` — recording is deliberately a
    separate, independently-written path from what's under test, same as
    `selftest_replay.py`'s own recorder).
    """
    conns = ", ".join([".D(D)"] + [f".\\Q[{i}] (Q[{i}])" for i in range(WIDTH)])
    lines = [
        "`timescale 1ns/1ps",
        "module tb_record;",
        f"  reg [{WIDTH - 1}:0] D = 'b0;",
        f"  wire [{WIDTH - 1}:0] Q;",
        f"  tinydut dut ({conns});",
        "  initial begin",
        f'    $dumpfile("{dump_path}");',
        "    $dumpvars(0, D, Q);",
    ]
    for value in D_VALUES:
        lines.append(f"    D = {WIDTH}'b{value};")
        lines.append("    #20;")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def _record(netlist: Path, work_dir: Path) -> Path:
    models = resolve_sky130_models()
    work_dir.mkdir(parents=True, exist_ok=True)
    dump_path = (work_dir / "recorded.vcd").resolve()
    tb_path = work_dir / "tb_record.v"
    tb_path.write_text(_build_recorder_testbench(dump_path))
    sim = compile_and_run([tb_path, netlist, *models.model_files()], work_dir=work_dir)
    if not sim.compiled or not sim.ran or not dump_path.exists():
        raise RuntimeError(f"failed to record reference VCD:\n{sim.compile_stderr}\n{sim.run_stderr}")
    return dump_path


def _run(
    netlist: Path, recorded_vcd: Path, port_map: dict[str, str | list[str]], work_dir: Path
) -> tuple[bool, str]:
    try:
        result = run_vcd_replay(
            [netlist],
            recorded_vcd,
            top="tinydut",
            port_map=port_map,
            input_names=["D"],
            output_names=["Q"],
            work_dir=work_dir,
        )
    except PdkResolutionError as e:
        return False, f"PDK resolution failed: {e}"
    if not result.sim.compiled:
        return False, f"compile failed:\n{result.sim.compile_stderr}"
    if not result.sim.ran:
        return False, f"simulation did not run:\n{result.sim.run_stderr}"
    if result.ok:
        return True, "no divergence"
    d = result.first_divergence
    if d is None:
        return False, "no comparable trace produced"
    return False, f"divergence at t={d.time} signal={d.signal} expected={d.expected} actual={d.actual}"


def main() -> int:
    work_root = Path.cwd() / ".sim-work" / "selftest-portmap"
    work_root.mkdir(parents=True, exist_ok=True)

    netlist_path = work_root / "tinydut.v"
    netlist_path.write_text(_build_tinydut())

    correct_port_map = {"D": "D", "Q": [f"\\Q[{i}]" for i in range(WIDTH)]}
    reversed_port_map = {"D": "D", "Q": [f"\\Q[{WIDTH - 1 - i}]" for i in range(WIDTH)]}

    checks: list[tuple[str, bool]] = []

    print("== recording a reference D/Q trace from a direct tinydut instantiation ==")
    try:
        recorded_vcd = _record(netlist_path, work_root / "record")
    except (PdkResolutionError, RuntimeError) as e:
        print(f"FAILED to record: {e}")
        return 1
    print(f"recorded: {recorded_vcd}")

    print("\n== [control] correct bit-order wiring reproduces the recording exactly ==")
    ok, detail = _run(netlist_path, recorded_vcd, correct_port_map, work_root / "correct")
    print(f"ok={ok} ({detail})")
    checks.append(("[control] correct wiring -> PASS", ok))

    print("\n== reversed bit-order wiring against the same recording is caught ==")
    ok_reversed, detail = _run(netlist_path, recorded_vcd, reversed_port_map, work_root / "reversed")
    print(f"ok={ok_reversed} ({detail})")
    checks.append(("reversed wiring -> reported as a divergence", not ok_reversed))

    print("\n== a single corrupted recorded bit is reported at its exact (time, signal) ==")
    doc = read_vcd(recorded_vcd)
    q_var = doc.var_by_name("Q")
    q_hist = doc.signal_history("Q")
    flip_time, flip_value = q_hist[-1]
    flipped = "".join("1" if c == "0" else "0" for c in flip_value)
    doc.changes = [c for c in doc.changes if not (c.identifier == q_var.identifier and c.time == flip_time)]
    doc.changes.append(ValueChange(time=flip_time, identifier=q_var.identifier, value=flipped))
    corrupted_vcd = work_root / "corrupted.vcd"
    document_to_vcd(doc, corrupted_vcd)

    try:
        result = run_vcd_replay(
            [netlist_path],
            corrupted_vcd,
            top="tinydut",
            port_map=correct_port_map,
            input_names=["D"],
            output_names=["Q"],
            work_dir=work_root / "corrupt",
        )
        detected = (
            not result.ok
            and result.first_divergence is not None
            and result.first_divergence.time == flip_time
            and result.first_divergence.signal == "Q"
        )
        if result.first_divergence:
            d = result.first_divergence
            print(f"reported divergence: t={d.time} signal={d.signal} expected={d.expected} actual={d.actual}")
        else:
            print("no divergence reported")
    except PdkResolutionError as e:
        detected = False
        print(f"PDK resolution failed: {e}")
    checks.append((f"corrupted bit at t={flip_time} detected at the right (time, signal)", detected))

    print()
    passed = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")
        passed = passed and ok

    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'} ({sum(1 for _, ok in checks if ok)}/{len(checks)} checks passed)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
