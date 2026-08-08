"""Thin wrapper around Icarus Verilog (`iverilog` + `vvp`).

Icarus is what `klt functional-verification` already targets alongside
Verilator (issue #5's rationale) and is sufficient for a 92-flop gate-level
design. This module just knows how to invoke it with the compile-time
defines a sky130_fd_sc_hd behavioural model set needs — it has no opinion
about what testbench or netlist is being compiled.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# sky130_fd_sc_hd.v selects among functional/timing and power-pin/no-power-pin
# variants via `` `ifdef ``. This repo's netlists are extracted/synthesized
# without explicit power-pin wiring, so:
#   - FUNCTIONAL is defined  -> pick the simulation functional model, not the
#     timing-check (SDF-oriented) model.
#   - USE_POWER_PINS is left undefined -> pick the port list that omits
#     VPWR/VGND/VPB/VNB, matching netlists that don't wire them.
#   - UNIT_DELAY is defined to `#1` -> the primitive instantiations
#     (`` `UNIT_DELAY dff0 (...) ``) need this macro defined to compile at
#     all; #1 avoids zero-delay races without materially affecting a
#     cycle-level functional check.
ICARUS_DEFINES = ["FUNCTIONAL", "UNIT_DELAY=#1"]


class IcarusNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class SimResult:
    compiled: bool
    ran: bool
    compile_stdout: str
    compile_stderr: str
    run_stdout: str
    run_stderr: str
    compile_returncode: int
    run_returncode: int | None


def require_icarus() -> tuple[str, str]:
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if iverilog is None or vvp is None:
        raise IcarusNotFoundError(
            "iverilog/vvp not found on PATH. Install Icarus Verilog "
            "(e.g. `brew install icarus-verilog` or `apt-get install "
            "iverilog`) and re-run."
        )
    return iverilog, vvp


def compile_and_run(
    sources: list[Path],
    *,
    top: str | None = None,
    timeout_s: float = 120.0,
    work_dir: Path | None = None,
) -> SimResult:
    """Compile `sources` with iverilog and run the result with vvp.

    `sources` should list the testbench first, then the netlist(s) under
    test, then the PDK model files (primitives.v, sky130_fd_sc_hd.v) —
    order doesn't matter to Icarus but keeping it consistent makes generated
    commands easier to read back in evidence records.
    """
    iverilog, vvp = require_icarus()

    own_tmp = work_dir is None
    tmp_ctx = tempfile.TemporaryDirectory(prefix="sim-") if own_tmp else None
    out_dir = Path(tmp_ctx.name) if own_tmp else work_dir.resolve()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        compiled_path = out_dir / "sim.vvp"

        # Resolve source paths to absolute *before* the vvp step below runs
        # with cwd=out_dir — a relative `sources`/`compiled_path` entry would
        # otherwise be re-interpreted relative to out_dir instead of the
        # caller's original working directory.
        compile_cmd = [iverilog, "-g2005", "-o", str(compiled_path)]
        for define in ICARUS_DEFINES:
            compile_cmd += ["-D", define]
        if top:
            compile_cmd += ["-s", top]
        compile_cmd += [str(Path(s).resolve()) for s in sources]

        compile_proc = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=timeout_s
        )
        if compile_proc.returncode != 0:
            return SimResult(
                compiled=False,
                ran=False,
                compile_stdout=compile_proc.stdout,
                compile_stderr=compile_proc.stderr,
                run_stdout="",
                run_stderr="",
                compile_returncode=compile_proc.returncode,
                run_returncode=None,
            )

        run_proc = subprocess.run(
            [vvp, str(compiled_path)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=out_dir,
        )
        return SimResult(
            compiled=True,
            ran=True,
            compile_stdout=compile_proc.stdout,
            compile_stderr=compile_proc.stderr,
            run_stdout=run_proc.stdout,
            run_stderr=run_proc.stderr,
            compile_returncode=compile_proc.returncode,
            run_returncode=run_proc.returncode,
        )
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()
