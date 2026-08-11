"""Known-answer self-test for `tools/sim/answer.py`'s byte-order decode.

Stage 8 (`tools/sim/run_answer.py`) decodes `O[7:0]` into ASCII bytes
without knowing in advance whether output port index 0 is the byte's LSB or
its MSB — `evidence/puzzle-solve.md` §9 records that this was never
established by anything simulated. This exercises the decode mechanism end
to end against a tiny synthetic sequential design with a *known* message —
no sky130 cells, no GDS, nothing embargoed — so the bit-order
auto-selection and the message-extraction logic are proven correct (and
provably capable of failing) before `run_answer.py` is ever pointed at
`evidence/puzzle-extracted.v`.

Three checks, mirroring the positive/negative-control discipline the other
`tools/sim` self-tests use (`selftest_solve.py`, `selftest_portmap.py`):

  1. [control] A DUT wired "index 0 = bit 0" (the plain `O[7:0]` vector
     reading) reproduces a known 9-character message exactly, with that
     order selected.
  2. The *same* known message through a DUT wired the opposite way
     ("index 0 = bit 7") is still recovered exactly, with the *other*
     order selected — proving selection is driven by the sampled data,
     not a hardcoded shift direction.
  3. [negative control] A DUT wired with a scrambled (non-reversal)
     bit-to-port mapping does not decode to the known message under
     either candidate order — a checker that cannot fail is not a checker.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.sim.answer import decode_output_cycles, select_order
from tools.sim.icarus import compile_and_run
from tools.sim.testbench import build_sequence_testbench

MESSAGE = "STAGE8 OK"
WIDTH = 8
CYCLE_RE = re.compile(r"^CYCLE (\d+) (.*)$")


def _build_dut(*, bit_of: list[int] | range) -> str:
    """A tiny sequential DUT: on `en`, shifts out `MESSAGE` one byte per cycle.

    `bit_of[i]` names which bit of the internal byte register drives output
    port `\\Q[i]` — the wiring under test. No sky130 cells; pure behavioural
    Verilog, mirroring `selftest_portmap.py`'s synthetic-DUT pattern.
    """
    rom = [ord(c) for c in MESSAGE]
    n = len(rom)
    lines = ["module answerdut (clk, rst_n, en,"]
    lines += [f"    \\Q[{i}] ," for i in range(WIDTH - 1)]
    lines.append(f"    \\Q[{WIDTH - 1}] );")
    lines.append(" input clk, rst_n, en;")
    for i in range(WIDTH):
        lines.append(f" output \\Q[{i}] ;")
    lines.append(f" reg [7:0] rom [0:{n - 1}];")
    lines.append(" reg [7:0] idx;")
    lines.append(" reg [7:0] cur;")
    lines.append(" integer k;")
    lines.append(" initial begin")
    for i, b in enumerate(rom):
        lines.append(f"   rom[{i}] = 8'd{b};")
    lines.append(" end")
    lines.append(" always @(posedge clk or negedge rst_n) begin")
    lines.append("   if (!rst_n) begin idx <= 0; cur <= 8'h00; end")
    lines.append(f"   else if (en && idx < {n}) begin cur <= rom[idx]; idx <= idx + 1; end")
    lines.append("   else cur <= 8'h00;")
    lines.append(" end")
    for i in range(WIDTH):
        lines.append(f" assign \\Q[{i}]  = cur[{bit_of[i]}];")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def _run(dut_src: str, work_dir: Path) -> list[dict[str, str]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    dut_path = work_dir / "answerdut.v"
    dut_path.write_text(dut_src)

    n_cycles = len(MESSAGE) + 8
    drive = {
        "rst_n": [0 if t < 2 else 1 for t in range(n_cycles)],
        "en": [0 if t < 2 else 1 for t in range(n_cycles)],
    }
    watch = [f"\\Q[{i}]" for i in range(WIDTH)]
    tb_text = build_sequence_testbench(top="answerdut", clock_port="clk", drive=drive, watch=watch)
    tb_path = work_dir / "tb.v"
    tb_path.write_text(tb_text)

    sim = compile_and_run([tb_path, dut_path], top="tb", work_dir=work_dir)
    if not sim.compiled or not sim.ran:
        raise RuntimeError(f"simulation failed:\ncompile:\n{sim.compile_stderr}\nrun:\n{sim.run_stderr}")

    samples: list[dict[str, str]] = []
    for line in sim.run_stdout.splitlines():
        m = CYCLE_RE.match(line)
        if not m:
            continue
        row = {"cycle": m.group(1)}
        for token in m.group(2).split():
            k, _, v = token.partition("=")
            row[k] = v
        samples.append(row)
    return samples


def main() -> int:
    work_root = Path.cwd() / ".sim-work" / "selftest-answer"
    bare_ports = [f"Q[{i}]" for i in range(WIDTH)]
    cycles = list(range(len(MESSAGE) + 8))
    checks: list[tuple[str, bool]] = []

    print("== [control] index 0 = bit 0 wiring recovers the known message ==")
    samples_a = _run(_build_dut(bit_of=list(range(WIDTH))), work_root / "a")
    decoded_a = decode_output_cycles(samples_a, bare_ports, cycles)
    chosen_a = select_order(decoded_a)
    ok_a = chosen_a.message == MESSAGE and chosen_a.order.name == "index0_lsb"
    print(f"  decoded {chosen_a.message!r} via {chosen_a.order.name} "
          f"(want {MESSAGE!r} via index0_lsb)")
    checks.append(("[control] index0=bit0 wiring decodes exactly, correct order selected", ok_a))

    print("\n== index 0 = bit 7 wiring: same message, selection flips, still recovered ==")
    samples_b = _run(_build_dut(bit_of=list(reversed(range(WIDTH)))), work_root / "b")
    decoded_b = decode_output_cycles(samples_b, bare_ports, cycles)
    chosen_b = select_order(decoded_b)
    ok_b = chosen_b.message == MESSAGE and chosen_b.order.name == "index0_msb"
    print(f"  decoded {chosen_b.message!r} via {chosen_b.order.name} "
          f"(want {MESSAGE!r} via index0_msb)")
    checks.append(("index0=bit7 wiring still decodes exactly, order selection flips", ok_b))

    print("\n== [negative control] scrambled (non-reversal) wiring decodes to neither order ==")
    scramble = [3, 1, 4, 0, 6, 2, 7, 5]  # not range(8) or its reversal
    samples_c = _run(_build_dut(bit_of=scramble), work_root / "c")
    decoded_c = decode_output_cycles(samples_c, bare_ports, cycles)
    chosen_c = select_order(decoded_c)
    ok_c = chosen_c.message != MESSAGE
    print(f"  decoded {chosen_c.message!r} via {chosen_c.order.name} "
          f"(must NOT equal {MESSAGE!r})")
    checks.append(("scrambled wiring does not falsely decode to the known message", ok_c))

    print()
    passed = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")
        passed = passed and ok

    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'} "
          f"({sum(1 for _, ok in checks if ok)}/{len(checks)} checks passed)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
