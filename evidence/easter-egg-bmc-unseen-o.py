from pathlib import Path

from tools.sim import bmc
from tools.sim.answer import decode_output_cycles
from tools.sim.solve import load_design, verify_by_simulation, windowed_scenario
from tools.sim.testbench import SequenceExpectation
from tools.vcd import read_vcd

design = load_design(Path('.sim-work/independent-review/puzzle-extracted.v'), work_dir=Path('.sim-work/independent-review/model'))
model = design.model
scenario = windowed_scenario(
    model, reset_cycles=3, idle_cycles=1, active_cycles=121, tail_cycles=65,
    free_ports=['I'], enable_port='enable', reset_port='rst_n', goal_output='success')
unrolling = bmc.unroll(model, cycles=scenario.cycles, input_schedule=scenario.schedule)

vcd = read_vcd('puzzle/example_inputs.vcd')
clock = vcd.signal_history('clk')
rises = [t for (pt, pv), (t, v) in zip(clock, clock[1:]) if pv == '0' and v == '1']
observed = set()
for t in rises:
    bits = vcd.value_at('O', t)
    if set(bits) <= {'0', '1'}:
        observed.add(int(bits, 2))
# The expected-input VCD samples O on the rising edge, one simulator delta
# before the documented +1000 ps output update.  Include the independently
# gate-level-decoded message so its first/last bytes are not false "unseen"
# witnesses due solely to that offset.
observed.update(b'(* TWO STARS *)')
print('recorded O bytes:', ' '.join(f'{value:02x}' for value in sorted(observed)))

found = None
for cycle in range(125, scenario.cycles):
    row = unrolling.output_lits[cycle]
    for value in range(256):
        if value in observed:
            continue
        assumptions = []
        for i in range(8):
            lit = row[f'O[{i}]']
            assumptions.append(lit if value >> i & 1 else -lit)
        outcome = bmc.solve_cnf(unrolling, assumptions=assumptions)
        if outcome.sat:
            found = cycle, value, outcome
            break
    if found:
        break

if not found:
    print('UNSAT: no unseen O byte at cycles 125..189')
    raise SystemExit

cycle, value, outcome = found
active = [outcome.inputs[t]['I'] for t in scenario.free_cycles('I')]
print(f'SAT: cycle={cycle} O=0x{value:02x} solver={outcome.solver} seconds={outcome.seconds:.6f}')
print('active I bits:', ''.join(map(str, active)))
def lit_value(lit):
    bit = bool(outcome.model_bits[abs(lit)])
    return int(bit if lit > 0 else not bit)
print('success at target:', lit_value(unrolling.output_lits[cycle]['success']))

drive = {
    port: [outcome.inputs[t].get(port, 0) for t in range(scenario.cycles)]
    for port in model.inputs if port != 'clk'
}
watch = [f'\\O[{i}]' for i in range(8)] + ['success']
expect = [SequenceExpectation(cycle=cycle, signal=f'\\O[{i}]', value=(value >> i) & 1) for i in range(8)]
verified = verify_by_simulation(
    design, drive=drive, watch=watch, expect=expect,
    work_dir=Path('.sim-work/independent-review/unseen-o-verify'))
print('gate-level verification:', 'PASS' if verified.ok else 'FAIL')
for line in verified.sim.run_stdout.splitlines():
    if line.startswith(('RESULT ', 'EXPECT FAIL')):
        print(line)
decoded = decode_output_cycles(verified.samples, [f'O[{i}]' for i in range(8)], list(range(125, scenario.cycles)))
for name, result in decoded.items():
    print(f'{name}: {result.rendered()}')
    print(f'{name} longest printable: {result.message!r}')
