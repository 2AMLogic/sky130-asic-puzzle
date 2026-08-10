"""VCD replay: drive a recorded VCD's inputs into a netlist, diff the outputs.

This is the engine stage 6 of `spec/puzzle.md` needs: replay
`puzzle/example_inputs.vcd` against the extracted puzzle netlist once it
exists (blocked on #2 at the time this module was written — see
`evidence/puzzle-replay.md`). It is deliberately netlist-agnostic: nothing
here encodes the warm-up's shift-register/comparator shape, only "some named
input signals drive some named output signals of some top module."

It is self-tested against the warm-up in `tools/sim/selftest_replay.py`,
which needs no recorded VCD of its own — it records one from a directed
warm-up simulation and replays it back, so the reader/testbench/diff path is
exercised end-to-end before it is ever pointed at the puzzle.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.sim.icarus import SimResult, compile_and_run
from tools.sim.pdk import ResolvedModels, resolve_sky130_models
from tools.sim.testbench import build_vcd_replay_testbench
from tools.vcd.model import VcdDocument
from tools.vcd.reader import read_vcd


@dataclass(frozen=True)
class Divergence:
    time: int
    signal: str
    expected: str
    actual: str


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    compared_through: int
    first_divergence: Divergence | None
    models: ResolvedModels
    sources: list[Path]
    sim: SimResult
    simulated_vcd_path: Path | None
    recorded: VcdDocument | None = None
    simulated: VcdDocument | None = None


def diff_output_traces(
    recorded: VcdDocument,
    simulated: VcdDocument,
    output_names: list[str],
) -> Divergence | None:
    """Return the first (time, signal, expected, actual) divergence, or None.

    Compares at every timestamp where either trace changes any output
    signal, using held-value ("last change at or before t") semantics —
    the same semantics a waveform viewer uses — rather than requiring
    identical change timestamps.
    """
    end = recorded.end_time()
    change_times: set[int] = {0}
    for name in output_names:
        for t, _v in recorded.signal_history(name):
            if t <= end:
                change_times.add(t)
        for t, _v in simulated.signal_history(name):
            if t <= end:
                change_times.add(t)

    for t in sorted(change_times):
        for name in output_names:
            expected = recorded.value_at(name, t)
            actual = simulated.value_at(name, t)
            if expected is None:
                continue
            if actual is None or actual != expected:
                return Divergence(time=t, signal=name, expected=expected or "?", actual=actual or "<no value>")
    return None


def run_vcd_replay(
    netlist_files: list[Path],
    recorded_vcd_path: Path,
    *,
    top: str,
    port_map: dict[str, str | list[str]],
    input_names: list[str],
    output_names: list[str],
    work_dir: Path | None = None,
    margin: int = 1000,
) -> ReplayResult:
    models = resolve_sky130_models()
    recorded = read_vcd(recorded_vcd_path)

    if work_dir is None:
        work_dir = Path.cwd() / ".sim-work" / "replay"
    work_dir.mkdir(parents=True, exist_ok=True)
    # Absolute: `$dumpfile()` is written into the generated testbench, and
    # icarus.compile_and_run runs vvp with cwd=work_dir — a relative
    # dump_path here would be re-interpreted relative to work_dir *again*
    # (the same class of bug icarus.py's compiled_path fix addresses).
    work_dir = work_dir.resolve()

    dump_path = work_dir / "sim_out.vcd"
    tb_source = build_vcd_replay_testbench(
        top=top,
        port_map=port_map,
        input_names=input_names,
        output_names=output_names,
        recorded=recorded,
        dump_path=str(dump_path),
        margin=margin,
    )
    tb_path = work_dir / "tb_replay.v"
    tb_path.write_text(tb_source)

    sources = [tb_path, *netlist_files, *models.model_files()]
    sim = compile_and_run(sources, work_dir=work_dir)

    if not sim.compiled or not sim.ran or not dump_path.exists():
        return ReplayResult(
            ok=False,
            compared_through=0,
            first_divergence=None,
            models=models,
            sources=sources,
            sim=sim,
            simulated_vcd_path=dump_path if dump_path.exists() else None,
            recorded=recorded,
        )

    simulated = read_vcd(dump_path)
    divergence = diff_output_traces(recorded, simulated, output_names)

    return ReplayResult(
        ok=divergence is None,
        compared_through=recorded.end_time(),
        first_divergence=divergence,
        models=models,
        sources=sources,
        sim=sim,
        simulated_vcd_path=dump_path,
        recorded=recorded,
        simulated=simulated,
    )
