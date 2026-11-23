"""CLI main() return-contract self-test for the five tools/sim entry points.

Nothing in the repo exercised these CLIs' main() functions (issue #102): the
selftest_* modules import the *library* functions, and the CI pipeline only
ever observed the shell exit status. The gap is not theoretical — PR #101
reused the name `rc` for an `int | None` helper result, clobbering
`rc = EXIT_OK`, so run_solve.main() returned None instead of 0 on the
--verify success path while the shell still saw exit 0
(`raise SystemExit(None)`). Only a test that inspects main()'s *return
value* can catch that class of regression.

Contracts asserted here:

1. `main([])` — missing required args — RAISES SystemExit with code exactly
   int 2 in all five CLIs. An exception, not a return value; asserted with
   assertRaises, and `type(code) is int` so a bool or None cannot pass.
2. A nonexistent netlist (plus each CLI's other required args) makes main()
   RETURN exactly int 2, with one stderr line naming the missing file and no
   traceback, in all five CLIs. On run_solve/run_answer this check precedes
   the lazy `import pysat`, and the other three test file existence inline,
   so the assertion holds whether or not python-sat and iverilog are
   installed (host-independent by construction).
3. run_solve.main()'s `return rc` tail — the statement the motivating clobber
   corrupted — is reached with the real main() and patched collaborators on
   both the --verify success path (returns exactly int 0) and the --verify
   failure path (returns exactly int 2). The collaborators are patched as
   bound in the CLI module (from-imports, so patching tools.sim.solve would
   not take effect) — `load_design_for_cli` since the #101 preamble refactor
   (issue #113), whose patch bypasses the lazy `import pysat` gate; a stdlib
   module stub in sys.modules keeps that gate satisfied should the patch
   boundary move back inside the preamble.
4. An unresolvable sky130 PDK (issue #100) makes run_solve.main() and
   run_answer.main() RETURN exactly int 2, with one stderr line carrying the
   install hint and no traceback — the contract both CLIs' docstrings state.
   The failure is injected in-process (`tools.sim.solve.load_design`, where
   the shared `load_design_for_cli` helper looks it up, patched to raise
   `PdkResolutionError`), so the assertion holds on any runner: no PDK-less
   host, no HOME/PATH scrubbing. The pysat stub keeps the preamble's import
   gate satisfied so the run reaches the injected failure.

5. Both solver CLIs keep their compile-failure format and send runtime
   failures to stderr before printing any simulation results.

Needs no PDK, no iverilog, no python-sat and no puzzle/ file: every input is
synthetic (CLAUDE.md §3 — nothing from puzzle/ is ever read) and every
scratch path lives under tempfile.mkdtemp(), so the run leaves the working
tree clean (run_solve's default --work-dir is the relative
`.sim-work/solve`; an explicit --work-dir under the tempdir overrides it).
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from tools.sim import (
    run_answer,
    run_solve,
    run_vcd_replay,
    run_warmup_cross_check,
    run_warmup_directed,
)
from tools.sim.icarus import SimResult
from tools.sim.pdk import INSTALL_HINT, PdkResolutionError

# The five CLI entry points under test, in module order.
CLIS = {
    "tools.sim.run_solve": run_solve.main,
    "tools.sim.run_answer": run_answer.main,
    "tools.sim.run_vcd_replay": run_vcd_replay.main,
    "tools.sim.run_warmup_cross_check": run_warmup_cross_check.main,
    "tools.sim.run_warmup_directed": run_warmup_directed.main,
}

# Arguments that make each CLI's file-existence check the first gate reached:
# "{missing}" is replaced with a nonexistent path under a tempdir, and every
# other required option is supplied so argparse accepts the command line.
# run_warmup_cross_check's netlists are --reference/--candidate rather than
# --netlist; --reference is checked first, so it is the one that must miss.
# run_vcd_replay checks netlists before the --vcd, so the placeholder drives
# the return even though the other required flags are dummy values.
BAD_INPUT_ARGS = {
    "tools.sim.run_solve": ["--netlist", "{missing}"],
    "tools.sim.run_answer": ["--netlist", "{missing}"],
    "tools.sim.run_vcd_replay": [
        "--netlist", "{missing}", "--vcd", "recorded.vcd",
        "--top", "top", "--inputs", "a,b", "--outputs", "s",
    ],
    "tools.sim.run_warmup_cross_check": [
        "--reference", "{missing}", "--candidate", "candidate.v",
    ],
    "tools.sim.run_warmup_directed": ["--netlist", "{missing}"],
}


def _missing_argv(name: str, missing: Path) -> list[str]:
    return [str(missing) if arg == "{missing}" else arg for arg in BAD_INPUT_ARGS[name]]


def _patched_collaborators(calls: dict, ok: bool, sim: SimResult):
    """Fakes for run_solve's four collaborators, recording each call.

    Shaped so the real main() walks its full solve-then-verify body:
    `load_design_for_cli` returns the `(design, free_ports)` tuple the shared
    preamble contract promises (one free input `I`), a 5-cycle scenario, one
    SAT solution, and a verification result that compiles and passes (or
    fails, per `ok`) through result.ok — the branch that assigns
    `rc = EXIT_ERROR` before the `return rc` tail.
    """
    scenario_cycles = 5
    design = SimpleNamespace(
        pdk=SimpleNamespace(describe=lambda: "fake PDK (selftest_cli)"),
        netlist=SimpleNamespace(top="top"),
        tables={},
        model=SimpleNamespace(inputs=["clk", "I"]),
    )
    scenario = SimpleNamespace(
        cycles=scenario_cycles,
        goal_cycle=4,
        free_cycles=lambda port: [1, 2, 3],
    )
    solution = SimpleNamespace(
        bits=lambda port, cycles: [1] * len(cycles),
        inputs=[{"I": 1}] * scenario_cycles,
    )
    report = SimpleNamespace(
        stats={"vars": 2, "clauses_total": 4},
        solver="fake-solver",
        seconds_total=0.0,
        unsat=False,
        solutions=[solution],
        exhausted=True,
    )
    result = SimpleNamespace(
        sim=sim,
        samples=[{"cycle": scenario.goal_cycle, "success": "1"}],
        testbench="tb.v",
        command_note="fake command note",
        ok=ok,
    )

    def load_design_for_cli(args):
        calls["load_design_for_cli"] = {"netlist": args.netlist, "work_dir": args.work_dir}
        return design, ["I"]

    def windowed_scenario(model, **kwargs):
        calls["windowed_scenario"] = kwargs
        return scenario

    def enumerate_solutions(model, scen, free_ports=None, max_solutions=None, solver_name=None):
        calls["enumerate_solutions"] = {"free_ports": free_ports, "max_solutions": max_solutions}
        return report

    def verify_by_simulation(dsn, drive=None, watch=None, expect=None, work_dir=None,
                             clock_period_ns=None):
        calls["verify_by_simulation"] = {"drive": drive, "work_dir": work_dir}
        return result

    return load_design_for_cli, windowed_scenario, enumerate_solutions, verify_by_simulation


class CliArgparseAndUsageExitTest(unittest.TestCase):
    """Contract 1: missing required args raise SystemExit, code exactly int 2."""

    def test_main_no_args_raises_systemexit_2_in_all_five(self):
        for name, main in CLIS.items():
            with self.subTest(cli=name), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    main([])
                code = ctx.exception.code
                self.assertIs(type(code), int)
                self.assertEqual(code, 2)


class CliBadInputExitTest(unittest.TestCase):
    """Contract 2: a nonexistent netlist returns exactly int 2, one stderr line."""

    def test_nonexistent_netlist_returns_exact_int_2_in_all_five(self):
        with tempfile.TemporaryDirectory(prefix="cli-selftest-") as tmp:
            missing = Path(tmp) / "no-such-netlist.v"
            for name, main in CLIS.items():
                with self.subTest(cli=name):
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        rc = main(_missing_argv(name, missing))
                    self.assertIs(type(rc), int)
                    self.assertEqual(rc, 2)
                    lines = err.getvalue().splitlines()
                    self.assertEqual(len(lines), 1, f"expected one stderr line: {lines}")
                    self.assertTrue(lines[0].strip())
                    self.assertIn(str(missing), lines[0])
                    self.assertNotIn("Traceback", err.getvalue())


class CliPdkResolutionErrorExitTest(unittest.TestCase):
    """Contract 4: an unresolvable PDK returns exactly int 2, one error line.

    The failure is injected where the shared preamble looks `load_design` up
    (`tools.sim.solve`), so both solver CLIs are covered by one patch and the
    test needs neither a PDK-less host nor HOME/PATH scrubbing.
    """

    def test_pdk_resolution_error_returns_exact_int_2_in_both_solver_clis(self):
        solver_clis = {
            "tools.sim.run_solve": run_solve.main,
            "tools.sim.run_answer": run_answer.main,
        }
        with tempfile.TemporaryDirectory(prefix="cli-selftest-") as tmp:
            netlist = Path(tmp) / "synthetic.v"
            netlist.touch()
            for name, main in solver_clis.items():
                with self.subTest(cli=name):
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(
                            mock.patch.dict(sys.modules, {"pysat": ModuleType("pysat")}))
                        stack.enter_context(mock.patch(
                            "tools.sim.solve.load_design",
                            mock.Mock(side_effect=PdkResolutionError(INSTALL_HINT))))
                        with contextlib.redirect_stderr(io.StringIO()) as err:
                            rc = main(["--netlist", str(netlist)])
                    self.assertIs(type(rc), int)
                    self.assertEqual(rc, 2)
                    lines = err.getvalue().splitlines()
                    self.assertEqual(len(lines), 1, f"expected one stderr line: {lines}")
                    self.assertTrue(lines[0].startswith("error: "))
                    self.assertIn(INSTALL_HINT, lines[0])
                    self.assertNotIn("Traceback", err.getvalue())


class RunSolveReturnContractTest(unittest.TestCase):
    """Contract 3: the `return rc` tail, reached with the real main().

    This is the load-bearing case: `rc = EXIT_OK` sits after every early
    return the two contracts above exercise, so only this path detects a
    clobber of `rc` between its assignment and `return rc` (the regression
    PR #101 reached review with).
    """

    def _run_verify(self, ok: bool, cli=run_solve, sim: SimResult | None = None):
        calls: dict = {}
        captured = {}
        with tempfile.TemporaryDirectory(prefix="cli-selftest-") as tmp:
            tmp_path = Path(tmp)
            work_dir = tmp_path / "solve-work"
            netlist = tmp_path / "synthetic.v"
            netlist.touch()
            if sim is None:
                sim = SimResult("", "", "RESULT PASS\n", "", 0, 0)
            fakes = _patched_collaborators(calls, ok, sim)
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.dict(sys.modules, {"pysat": ModuleType("pysat")}))
                for fake in fakes:
                    stack.enter_context(mock.patch.object(cli, fake.__name__, fake))
                stdout = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                stderr = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                argv = ["--netlist", str(netlist), "--work-dir", str(work_dir)]
                if cli is run_solve:
                    argv.append("--verify")
                rc = cli.main(argv)
                captured["stdout"] = stdout.getvalue()
                captured["stderr"] = stderr.getvalue()
        captured["calls"] = calls
        captured["work_dir"] = work_dir
        return rc, captured

    def _assert_tail_reached(self, rc, captured, expected_rc, expected_marker):
        self.assertIs(type(rc), int)
        self.assertEqual(rc, expected_rc)
        self.assertEqual(
            sorted(captured["calls"]),
            ["enumerate_solutions", "load_design_for_cli", "verify_by_simulation",
             "windowed_scenario"],
        )
        self.assertEqual(
            captured["calls"]["load_design_for_cli"]["work_dir"], captured["work_dir"])
        self.assertEqual(
            captured["calls"]["verify_by_simulation"]["work_dir"], captured["work_dir"])
        self.assertIn(expected_marker, captured["stdout"])

    def test_verify_success_returns_exact_int_0(self):
        rc, captured = self._run_verify(ok=True)
        self._assert_tail_reached(rc, captured, 0, "VERIFIED")

    def test_verify_failure_returns_exact_int_2(self):
        rc, captured = self._run_verify(ok=False)
        self._assert_tail_reached(rc, captured, 2, "VERIFICATION FAILED")

    def test_runtime_failure_precedes_result_output_in_both_solver_clis(self):
        sim = SimResult("", "", "RESULT PASS\nFATAL: runtime failure\n", "loading simulation\n", 0, 1)
        for cli in (run_solve, run_answer):
            with self.subTest(cli=cli.__name__):
                rc, captured = self._run_verify(False, cli, sim)
                self.assertEqual(rc, 2)
                self.assertNotIn("RESULT PASS", captured["stdout"])
                self.assertIn("SIMULATION FAILED (exit 1)", captured["stderr"])
                self.assertIn("FATAL: runtime failure", captured["stderr"])
                self.assertIn("loading simulation", captured["stderr"])

    def test_compile_failure_format_in_both_solver_clis(self):
        sim = SimResult("", "syntax error", "", "", 1, None)
        for cli in (run_solve, run_answer):
            with self.subTest(cli=cli.__name__):
                rc, captured = self._run_verify(False, cli, sim)
                self.assertEqual(rc, 2)
                self.assertTrue(captured["stdout"].endswith("compile FAILED\nsyntax error\n"))
                self.assertEqual(captured["stderr"], "")


def main() -> int:
    print("== tools/sim CLI main() return-contract self-test (collaborators mocked) ==")
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.wasSuccessful()
    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'} "
          f"({result.testsRun} tests, {len(result.failures) + len(result.errors)} not passed)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
