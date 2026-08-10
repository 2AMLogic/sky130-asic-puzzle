"""Known-answer self-test for the solver stack, against the warm-up.

The puzzle has no independent oracle: nothing outside Jane Street can say
whether a 121-bit answer is right.  The warm-up does — `warmup/00_source.v`
says `S` asserts exactly when `A + B == 496`, and `spec/puzzle.md` makes the
warm-up the regression fixture for precisely this reason.  So every piece of
machinery stage 7 relies on is exercised here first, on a netlist whose
answers are known in advance and computable in Python:

  1. **Model fidelity** — `tools/sim/seqmodel.py`'s cycle model must agree
     with Icarus, cycle for cycle, on random stimulus.  If the fast model
     and the simulator disagree, nothing downstream means anything.
  2. **Completeness** — enumerating *every* solution of "make `S` high after
     an 8-bit load" must return exactly the 15 pairs with `A + B == 496`
     (241+255 … 255+241) and nothing else.  This is the same block-and-
     re-solve loop the puzzle's uniqueness claim rests on, checked against a
     count derived independently in Python.
  3. **Soundness** — each solution replayed through Icarus must actually
     assert `S`.
  4. **Negative control** — a solution with one bit flipped must *not*
     assert `S`, in both the model and Icarus.  A checker that cannot fail
     is not a checker.
  5. **UNSAT control** — asking for `S` before enough bits have been shifted
     in must come back UNSAT, not "no answer found".

Nothing here reads `puzzle/puzzle.gds`, `example_inputs.vcd`, or the
extracted puzzle netlist: the warm-up is not embargoed (CLAUDE.md §4).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from tools.sim.seqmodel import simulate
from tools.sim.solve import (
    LoadedDesign,
    Scenario,
    enumerate_solutions,
    load_design,
    verify_by_simulation,
    windowed_scenario,
)
from tools.sim.testbench import SequenceExpectation

TARGET_SUM = 496
LOAD_BITS = 8
RESET_CYCLES = 2
TAIL_CYCLES = 2
# 8-bit A and B summing to 496: A from 241 to 255 inclusive.
EXPECTED_SOLUTION_COUNT = sum(
    1 for a in range(256) for b in range(256) if a + b == TARGET_SUM
)


def _bits_to_byte(bits: list[int]) -> int:
    """The warm-up shifts MSB first (`{parallel_out[6:0], serial_in}`)."""
    value = 0
    for b in bits:
        value = (value << 1) | b
    return value


def _scenario(design: LoadedDesign) -> Scenario:
    return windowed_scenario(
        design.model,
        reset_cycles=RESET_CYCLES,
        idle_cycles=0,
        active_cycles=LOAD_BITS,
        tail_cycles=TAIL_CYCLES,
        free_ports=["A", "B"],
        enable_port="en",
        reset_port="rst_n",
        goal_output="S",
    )


def _drive_from(scenario: Scenario, inputs: list[dict[str, int]]) -> dict[str, list[int]]:
    return {
        port: [inputs[t][port] for t in range(scenario.cycles)]
        for port in ("rst_n", "en", "A", "B")
    }


def check_model_matches_icarus(design: LoadedDesign, work_dir: Path, *, trials: int = 3) -> bool:
    rng = random.Random(496)
    ok = True
    for trial in range(trials):
        cycles = 40
        drive = {
            "rst_n": [0 if t < 2 else 1 for t in range(cycles)],
            "en": [rng.randint(0, 1) for _ in range(cycles)],
            "A": [rng.randint(0, 1) for _ in range(cycles)],
            "B": [rng.randint(0, 1) for _ in range(cycles)],
        }
        seq = [
            {"clk": 1, **{p: drive[p][t] for p in drive}}
            for t in range(cycles)
        ]
        trace = simulate(design.model, seq)
        result = verify_by_simulation(
            design,
            drive=drive,
            watch=["S"],
            expect=[],
            work_dir=work_dir / f"agree{trial}",
        )
        if not result.sim.compiled or not result.sim.ran:
            print(f"  trial {trial}: FAIL — simulation did not run\n{result.sim.compile_stderr}")
            return False
        got = [row["S"] for row in result.samples]
        want = [str(trace.outputs[t]["S"]) for t in range(cycles)]
        if got != want:
            first = next(i for i, (g, w) in enumerate(zip(got, want)) if g != w)
            print(f"  trial {trial}: FAIL — cycle model and Icarus differ first at cycle {first} "
                  f"(model {want[first]}, icarus {got[first]})")
            ok = False
        else:
            print(f"  trial {trial}: ok — {cycles} cycles agree")
    return ok


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    netlist = repo_root / "puzzle" / "warmup" / "01_netlist.v"
    if not netlist.exists():
        print(f"missing {netlist} — run ./scripts/fetch-puzzle.sh first", file=sys.stderr)
        return 1
    try:
        import pysat  # noqa: F401
    except ImportError:
        print(
            "python-sat is not installed. Install it with `pip install python-sat` "
            "(the solver back end tools/sim/bmc.py uses) and re-run.",
            file=sys.stderr,
        )
        return 1

    work_dir = repo_root / ".sim-work" / "selftest-solve"
    work_dir.mkdir(parents=True, exist_ok=True)
    design = load_design(netlist, work_dir=work_dir)
    failures = 0

    print("== 1. cycle model vs Icarus, random stimulus ==")
    if not check_model_matches_icarus(design, work_dir):
        failures += 1

    print()
    print(f"== 2. enumerate every solution of S=1 after an {LOAD_BITS}-bit load ==")
    scenario = _scenario(design)
    active = scenario.free_cycles("A")
    report = enumerate_solutions(
        design.model,
        scenario,
        free_ports=["A", "B"],
        max_solutions=EXPECTED_SOLUTION_COUNT + 5,
    )
    pairs = sorted(
        (_bits_to_byte(s.bits("A", active)), _bits_to_byte(s.bits("B", active)))
        for s in report.solutions
    )
    print(f"  bound {report.bound} cycles, {report.stats['vars']} vars, "
          f"{report.stats['clauses_total']} clauses, {report.seconds_total:.2f}s total")
    print(f"  {len(pairs)} solutions: {pairs}")
    if len(pairs) != EXPECTED_SOLUTION_COUNT:
        print(f"  FAIL — expected exactly {EXPECTED_SOLUTION_COUNT} solutions")
        failures += 1
    elif any(a + b != TARGET_SUM for a, b in pairs):
        print(f"  FAIL — some solution does not satisfy A + B == {TARGET_SUM}")
        failures += 1
    elif not report.exhausted:
        print("  FAIL — the solver did not report the space as exhausted")
        failures += 1
    else:
        print(f"  ok — exactly the {EXPECTED_SOLUTION_COUNT} pairs with "
              f"A + B == {TARGET_SUM}, and no more")

    if not report.solutions:
        print("no solutions to verify; aborting")
        return 1

    print()
    print("== 3. Icarus confirms a solved sequence asserts S ==")
    solution = report.solutions[0]
    drive = _drive_from(scenario, solution.inputs)
    result = verify_by_simulation(
        design,
        drive=drive,
        watch=["S"],
        expect=[SequenceExpectation(cycle=scenario.goal_cycle, signal="S", value=1)],
        work_dir=work_dir / "verify",
    )
    a, b = _bits_to_byte(solution.bits("A", active)), _bits_to_byte(solution.bits("B", active))
    print(f"  A={a} B={b} (sum {a + b})")
    if result.ok:
        print("  ok — RESULT PASS from Icarus")
    else:
        print(f"  FAIL — {result.sim.run_stdout.strip().splitlines()[-1:]}")
        failures += 1

    print()
    print("== 4. negative control: one flipped bit must not assert S ==")
    corrupted = {k: list(v) for k, v in drive.items()}
    last = active[-1]
    corrupted["A"][last] ^= 1
    neg_seq = [{"clk": 1, **{p: corrupted[p][t] for p in corrupted}} for t in range(scenario.cycles)]
    neg_trace = simulate(design.model, neg_seq)
    model_says = neg_trace.outputs[scenario.goal_cycle]["S"]
    neg = verify_by_simulation(
        design,
        drive=corrupted,
        watch=["S"],
        expect=[SequenceExpectation(cycle=scenario.goal_cycle, signal="S", value=0)],
        work_dir=work_dir / "negative",
    )
    if model_says == 0 and neg.ok:
        print("  ok — model and Icarus both report S=0 for the corrupted sequence")
    else:
        print(f"  FAIL — model S={model_says}, Icarus ok={neg.ok}")
        failures += 1

    print()
    print("== 5. UNSAT control: S cannot be high before the load completes ==")
    early = windowed_scenario(
        design.model,
        reset_cycles=RESET_CYCLES,
        idle_cycles=0,
        active_cycles=LOAD_BITS // 2,
        tail_cycles=1,
        free_ports=["A", "B"],
        enable_port="en",
        reset_port="rst_n",
        goal_output="S",
    )
    early_report = enumerate_solutions(design.model, early, free_ports=["A", "B"], max_solutions=1)
    if early_report.unsat:
        print(f"  ok — UNSAT at bound {early.cycles} ({early_report.seconds_total:.2f}s)")
    else:
        print("  FAIL — expected UNSAT with only half the bits shifted in")
        failures += 1

    print()
    if failures:
        print(f"RESULT FAIL {failures}")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
