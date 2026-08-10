"""Classify longer accepting inputs and decode structured failing inputs."""

from pathlib import Path

from tools.sim.answer import decode_output_cycles
from tools.sim.solve import enumerate_solutions, load_design, verify_by_simulation, windowed_scenario

NETLIST = Path('.sim-work/independent-review/puzzle-extracted.v')
WORK = Path('.sim-work/easter-lead3')
design = load_design(NETLIST, work_dir=WORK / 'model')
model = design.model
output_ports = [f'\\O[{i}]' for i in range(8)]
bare_ports = [f'O[{i}]' for i in range(8)]


def scenario(active_cycles, tail_cycles=65):
    return windowed_scenario(
        model, reset_cycles=3, idle_cycles=1, active_cycles=active_cycles,
        tail_cycles=tail_cycles, free_ports=['I'], enable_port='enable',
        reset_port='rst_n', goal_output='success')


print('== longer accepting windows ==')
baseline = None
representative = None
for active_cycles in (121, 122, 124, 128):
    sc = scenario(active_cycles, tail_cycles=5)
    report = enumerate_solutions(model, sc, free_ports=['I'], max_solutions=8)
    words = [''.join(map(str, sol.bits('I', sc.free_cycles('I')))) for sol in report.solutions]
    if active_cycles == 121:
        baseline = words[0]
    material = sum(word[:121] != baseline for word in words)
    suffixes = [word[121:] or '(none)' for word in words]
    print(f'active={active_cycles}: solutions_sampled={len(words)} exhausted={report.exhausted} '
          f'material_prefix_differences={material} suffixes={" ".join(suffixes)}')
    if active_cycles == 128:
        representative = words[-1]


def replay(label, active_bits):
    total = 190
    drive = {'rst_n': [], 'enable': [], 'I': []}
    for t in range(total):
        active_index = t - 4
        active = 0 <= active_index < len(active_bits)
        drive['rst_n'].append(int(t >= 3))
        drive['enable'].append(int(active))
        drive['I'].append(int(active_bits[active_index]) if active else 0)
    result = verify_by_simulation(
        design, drive=drive, watch=['success', *output_ports], expect=[],
        work_dir=WORK / label)
    decoded = decode_output_cycles(result.samples, bare_ports, list(range(125, total)))
    lsb = decoded['index0_lsb']
    success_cycles = [row['cycle'] for row in result.samples if row.get('success') == '1']
    print(f'{label}: sim={"PASS" if result.ok else "FAIL"} success_cycles={",".join(success_cycles) or "none"}')
    print(f'{label}: {lsb.rendered()}')
    print(f'{label}: longest_printable={lsb.message!r}')


print('== gate-level output decoding ==')
assert baseline is not None and representative is not None
replay('accepted-121', baseline)
replay('accepted-128-representative', representative)
patterns = {
    'fail-all-zero': '0' * 121,
    'fail-all-one': '1' * 121,
    'fail-alternating-01': '01' * 60 + '0',
    'fail-alternating-10': '10' * 60 + '1',
    'fail-accepted-complement': ''.join('1' if bit == '0' else '0' for bit in baseline),
    'fail-single-one-first': '1' + '0' * 120,
    'fail-single-one-last': '0' * 120 + '1',
}
for label, bits in patterns.items():
    replay(label, bits)
