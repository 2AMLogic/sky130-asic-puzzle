"""Self-test for `tools/sim/icarus.py`'s success semantics (issue #178).

`SimResult` used to store `compiled`/`ran` booleans that both return paths
of `compile_and_run` set to the same value, so a `vvp` that exited nonzero
after printing `RESULT PASS` still reported `ran=True` — and every evidence
check gated on `sim.ran` (solve.py's `ok`, the VCD replay gates, the
recorders) accepted a runtime failure as a pass. Success is now derived
from the stored exit codes: `compiled` is `compile_returncode == 0`, `ran`
is `run_returncode == 0`, and `run_returncode is None` means the simulator
never ran.

Checks against tiny PDK-free testbenches (iverilog only — no sky130
models, no fetched netlist, no solver):

  1. [control] A clean testbench that prints `RESULT PASS` and finishes
     reports compile and run success, and no CLI failure report.
  2. A testbench that fails to compile skips simulation: not compiled,
     `run_returncode is None`, not ran, `COMPILE FAILED` reported.
  3. [the bug] A testbench that prints `RESULT PASS` and then calls
     `$fatal` exits nonzero: `ran` must be False despite the pass text,
     and the CLI failure report must name the exit code and surface the
     captured diagnostic (Icarus writes `$fatal` output to stdout, so the
     diagnostic arrives via run_stdout with run_stderr empty).
  4. The same fatal-after-pass shape driven through the real
     `verify_by_simulation` gate (a synthetic DUT that prints the pass
     text and then fatals): the verification must fail. A well-behaved
     DUT through the same gate must still pass — the gate tightened, it
     did not stop accepting clean runs. The fatal DUT also writes to stderr,
     so the report must retain the fatal line from stdout alongside it.
  5. A reference DUT that fails after the recorder opens its VCD produces
     a recording error with the simulator exit and the fatal diagnostic.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools.sim import run_warmup_cross_check
from tools.sim.icarus import compile_and_run, report_sim_failure
from tools.sim.solve import verify_by_simulation
from tools.testutil import report_checks

CLEAN_TB = """\
module tb;
  initial begin
    $display("RESULT PASS");
    $finish;
  end
endmodule
"""

BROKEN_TB = """\
module tb;
  initial begin
    $display("no endmodule below");
  end
"""

FATAL_TB = """\
module tb;
  initial begin
    $display("RESULT PASS");
    $fatal(1, "runtime failure");
  end
endmodule
"""

FATAL_DUT = """\
module fataldut (clk, rst_n, en, s);
 input clk, rst_n, en;
 output s;
 reg s;
 always @(posedge clk or negedge rst_n) begin
   if (!rst_n) s <= 1'b0;
   else s <= en;
 end
 initial begin
   #1 $display("RESULT PASS");
   $fdisplay(32'h80000002, "loading simulation");
   #2 $fatal(1, "runtime failure");
 end
endmodule
"""

CLEAN_DUT = """\
module cleandut (clk, rst_n, en, s);
 input clk, rst_n, en;
 output s;
 reg s;
 always @(posedge clk or negedge rst_n) begin
   if (!rst_n) s <= 1'b0;
   else s <= en;
 end
endmodule
"""

FATAL_REFERENCE = """\
`timescale 1ns/1ps
module adder_demo(input clk, rst_n, en, A, B, output S);
  initial #1 $fatal(1, "reference failed");
endmodule
"""


def _run_tb(tb_source: str, work_dir: Path):
    """Compile-and-run one hand-written testbench through the wrapper."""
    work_dir.mkdir(parents=True, exist_ok=True)
    tb_path = work_dir / "tb.v"
    tb_path.write_text(tb_source, encoding="utf-8")
    return compile_and_run([tb_path], work_dir=work_dir)


def _failure_report(sim) -> tuple[int | None, str]:
    """Run report_sim_failure with stderr captured; return (rc, text)."""
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        rc = report_sim_failure(sim)
    return rc, captured.getvalue()


def _verify_dut(dut_source: str, module: str, work_dir: Path):
    """Drive one synthetic DUT through the real verify_by_simulation gate.

    The design stand-in carries everything `verify_by_simulation` reads
    (`netlist.top`, `model.clock_net`, `source`, `pdk.model_files()`) with
    no PDK model files, so the gate runs end to end — generated testbench,
    iverilog, vvp — against pure behavioural Verilog. `module` must name
    the DUT's Verilog module: the generated testbench instantiates it by
    that name.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    dut_path = work_dir / f"{module}.v"
    dut_path.write_text(dut_source, encoding="utf-8")
    design = SimpleNamespace(
        netlist=SimpleNamespace(top=module),
        model=SimpleNamespace(clock_net="clk"),
        pdk=SimpleNamespace(model_files=list),
        source=dut_path,
    )
    return verify_by_simulation(
        design,
        drive={"rst_n": [0, 1, 1, 1], "en": [0, 1, 1, 1]},
        watch=["s"],
        expect=[],
        work_dir=work_dir,
    )


def main() -> int:
    work_root = Path.cwd() / ".sim-work" / "selftest-icarus"
    checks: list[tuple[str, bool]] = []

    print("== [control] clean run: pass text, exit 0, no failure report ==")
    clean = _run_tb(CLEAN_TB, work_root / "clean")
    rc_clean, report_clean = _failure_report(clean)
    ok_clean = (
        clean.compiled
        and clean.ran
        and clean.run_returncode == 0
        and "RESULT PASS" in clean.run_stdout
        and rc_clean is None
        and report_clean == ""
    )
    print(f"  compiled={clean.compiled} ran={clean.ran} "
          f"run_exit={clean.run_returncode} report_rc={rc_clean}")
    checks.append(("[control] clean run reports success and no failure report", ok_clean))

    print("\n== compile error skips simulation ==")
    broken = _run_tb(BROKEN_TB, work_root / "broken")
    rc_broken, report_broken = _failure_report(broken)
    ok_broken = (
        not broken.compiled
        and broken.compile_returncode != 0
        and broken.run_returncode is None
        and not broken.ran
        and rc_broken == 1
        and "COMPILE FAILED" in report_broken
        and broken.compile_stderr in report_broken
    )
    print(f"  compiled={broken.compiled} run_exit={broken.run_returncode} report_rc={rc_broken}")
    checks.append(("compile error skips simulation, reports COMPILE FAILED", ok_broken))

    print("\n== [the bug] fatal after pass text must not count as ran ==")
    fatal = _run_tb(FATAL_TB, work_root / "fatal")
    rc_fatal, report_fatal = _failure_report(fatal)
    ok_fatal = (
        fatal.compiled
        and fatal.run_returncode == 1
        and not fatal.ran
        and "RESULT PASS" in fatal.run_stdout
        and rc_fatal == 1
        and "exit 1" in report_fatal
        and "runtime failure" in report_fatal
        and fatal.run_stderr == ""
    )
    print(f"  compiled={fatal.compiled} ran={fatal.ran} run_exit={fatal.run_returncode} "
          f"report_rc={rc_fatal}")
    checks.append(("fatal after pass text: ran False, report names exit and diagnostic", ok_fatal))

    print("\n== fatal-after-pass DUT through verify_by_simulation fails verification ==")
    fatal_result = _verify_dut(FATAL_DUT, "fataldut", work_root / "verify-fatal")
    ok_fatal_gate = (
        fatal_result.sim.run_returncode == 1
        and "RESULT PASS" in fatal_result.sim.run_stdout
        and not fatal_result.ok
    )
    print(f"  sim_exit={fatal_result.sim.run_returncode} "
          f"pass_text={'RESULT PASS' in fatal_result.sim.run_stdout} ok={fatal_result.ok}")
    checks.append(("verify_by_simulation fails a fatal-after-pass run", ok_fatal_gate))

    rc_mixed, report_mixed = _failure_report(fatal_result.sim)
    ok_mixed = (
        rc_mixed == 1
        and "loading simulation" in fatal_result.sim.run_stderr
        and "runtime failure" in fatal_result.sim.run_stdout
        and "loading simulation" in report_mixed
        and "runtime failure" in report_mixed
        and "exit 1" in report_mixed
    )
    checks.append(("runtime report retains diagnostics from both streams", ok_mixed))

    print("\n== [control] clean DUT through the same gate still verifies ==")
    clean_result = _verify_dut(CLEAN_DUT, "cleandut", work_root / "verify-clean")
    ok_clean_gate = clean_result.ok and clean_result.sim.run_returncode == 0
    print(f"  sim_exit={clean_result.sim.run_returncode} ok={clean_result.ok}")
    checks.append(("[control] verify_by_simulation still passes a clean run", ok_clean_gate))

    print("\n== failed reference recording reports the simulator diagnostic ==")
    with tempfile.TemporaryDirectory(dir=work_root) as tmp:
        record_dir = Path(tmp)
        reference = record_dir / "reference.v"
        reference.write_text(FATAL_REFERENCE, encoding="utf-8")
        with (
            mock.patch("tools.sim.warmup_recorder.resolve_sky130_models",
                       return_value=SimpleNamespace(model_files=list)),
            contextlib.redirect_stderr(io.StringIO()) as err,
        ):
            rc = run_warmup_cross_check.main([
                "--reference", str(reference), "--candidate", str(reference),
                "--cases", "0", "--work-dir", str(record_dir),
            ])
        message = err.getvalue()
        checks.append(("failed reference recording rejects VCD and reports exit and fatal output",
                       rc == 1 and (record_dir / "recorded.vcd").is_file()
                       and "error recording reference stimulus" in message
                       and "exit 1" in message and "reference failed" in message))

    return report_checks(checks)


if __name__ == "__main__":
    raise SystemExit(main())
