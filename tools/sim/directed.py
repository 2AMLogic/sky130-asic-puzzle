"""Directed `A + B == 496` test against a shift-register/adder/comparator netlist.

This is stage 5 of `spec/puzzle.md`: calibrate the simulation harness against
the warm-up, which has both a source-level behavioural description
(`warmup/00_source.v`) and a gate-level netlist (`warmup/01_netlist.v`) that
must reproduce it. `00_source.v` says the design asserts `S` when
`A + B == 496` after shifting eight bits into each of two shift registers —
this module builds that check as an independent oracle (`case.expected_s`
below is computed in Python from the case values, never read back from the
netlist) and runs it against whichever netlist file(s) are passed in.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from tools.sim.icarus import SimResult, compile_and_run
from tools.sim.pdk import ResolvedModels, resolve_sky130_models
from tools.sim.testbench import ShiftLoadCase, build_shift_load_testbench

TARGET_SUM = 496

# Default warm-up top-level port names (warmup/00_source.v's `adder_demo`,
# preserved verbatim in warmup/01_netlist.v since top-level ports aren't
# renamed by synthesis/PnR — only internal nets are).
DEFAULT_PORTS = {"clk": "clk", "rst_n": "rst_n", "en": "en", "a": "A", "b": "B", "s": "S"}


def default_cases(*, extra_random: int = 0, seed: int = 496) -> list[ShiftLoadCase]:
    """At least one passing case and several near-misses, plus optional randoms.

    All expected values are computed independently in Python — this is the
    oracle the netlist is checked against, not a re-derivation from it.
    """
    cases = [
        ShiftLoadCase(a=248, b=248, expected_s=(248 + 248 == TARGET_SUM), label="exact-248-248"),
        ShiftLoadCase(a=255, b=241, expected_s=(255 + 241 == TARGET_SUM), label="exact-255-241"),
        ShiftLoadCase(a=241, b=255, expected_s=(241 + 255 == TARGET_SUM), label="exact-241-255"),
        ShiftLoadCase(a=250, b=246, expected_s=(250 + 246 == TARGET_SUM), label="exact-250-246"),
        ShiftLoadCase(a=255, b=240, expected_s=(255 + 240 == TARGET_SUM), label="near-miss-495"),
        ShiftLoadCase(a=255, b=242, expected_s=(255 + 242 == TARGET_SUM), label="near-miss-497"),
        ShiftLoadCase(a=248, b=247, expected_s=(248 + 247 == TARGET_SUM), label="near-miss-495b"),
        ShiftLoadCase(a=248, b=249, expected_s=(248 + 249 == TARGET_SUM), label="near-miss-497b"),
        ShiftLoadCase(a=0, b=0, expected_s=(0 + 0 == TARGET_SUM), label="zero"),
        ShiftLoadCase(a=255, b=255, expected_s=(255 + 255 == TARGET_SUM), label="max"),
    ]
    if extra_random:
        rng = random.Random(seed)
        for i in range(extra_random):
            a = rng.randint(0, 255)
            b = rng.randint(0, 255)
            cases.append(ShiftLoadCase(a=a, b=b, expected_s=(a + b == TARGET_SUM), label=f"random-{i}"))
    return cases


@dataclass(frozen=True)
class CaseOutcome:
    label: str
    a: int
    b: int
    expected_s: bool
    got_s: bool | None
    matched: bool


@dataclass(frozen=True)
class DirectedTestResult:
    ok: bool
    outcomes: list[CaseOutcome]
    models: ResolvedModels
    sources: list[Path]
    sim: SimResult


def _parse_outcomes(cases: list[ShiftLoadCase], stdout: str) -> list[CaseOutcome]:
    outcomes: list[CaseOutcome] = []
    lines = [ln for ln in stdout.splitlines() if ln.startswith("CASE ")]
    for case, line in zip(cases, lines, strict=False):
        parts = line.split()
        # "CASE <idx> OK a=<a> b=<b> s=<bit>" or "... MISMATCH a=<a> b=<b> expected_s=<bit> got_s=<bit>"
        status = parts[2]
        got_s = None
        for tok in parts:
            if tok.startswith("s=") or tok.startswith("got_s="):
                got_s = tok.split("=", 1)[1] == "1"
        matched = status == "OK"
        outcomes.append(
            CaseOutcome(
                label=case.label,
                a=case.a,
                b=case.b,
                expected_s=case.expected_s,
                got_s=got_s,
                matched=matched,
            )
        )
    return outcomes


def run_directed_test(
    netlist_files: list[Path],
    *,
    top: str = "adder_demo",
    ports: dict[str, str] | None = None,
    cases: list[ShiftLoadCase] | None = None,
    work_dir: Path | None = None,
) -> DirectedTestResult:
    ports = ports or DEFAULT_PORTS
    cases = cases if cases is not None else default_cases()
    models = resolve_sky130_models()

    tb_source = build_shift_load_testbench(top=top, ports=ports, cases=cases)

    if work_dir is None:
        work_dir = Path.cwd() / ".sim-work" / "directed"
    work_dir.mkdir(parents=True, exist_ok=True)
    tb_path = work_dir / "tb_directed.v"
    tb_path.write_text(tb_source)

    sources = [tb_path, *netlist_files, *models.model_files()]
    sim = compile_and_run(sources, work_dir=work_dir)

    if not sim.compiled or not sim.ran:
        return DirectedTestResult(ok=False, outcomes=[], models=models, sources=sources, sim=sim)

    outcomes = _parse_outcomes(cases, sim.run_stdout)
    ok = bool(outcomes) and all(o.matched for o in outcomes) and "RESULT PASS" in sim.run_stdout
    return DirectedTestResult(ok=ok, outcomes=outcomes, models=models, sources=sources, sim=sim)
