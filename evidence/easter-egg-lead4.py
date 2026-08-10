"""Recover raster-to-counter membership from one-hot differential traces."""

from pathlib import Path

from tools.sim.seqmodel import simulate
from tools.sim.solve import load_design
from tools.sim.structure import analyze

design = load_design(Path('.sim-work/independent-review/puzzle-extracted.v'), work_dir=Path('.sim-work/easter-lead4/model'))
model = design.model
report = analyze(model)
pairs = [tuple(comp) for comp in report.sccs if len(comp) == 2]
ff_index = {ff.name: i for i, ff in enumerate(model.ffs)}

def run(bits):
    seq = []
    for t in range(130):
        i = t - 4
        active = 0 <= i < 121
        seq.append({'clk': 1, 'rst_n': int(t >= 3), 'enable': int(active),
                    'I': int(bits[i]) if active else 0})
    return simulate(model, seq).states

zero = run('0' * 121)
membership = []
for pos in range(121):
    states = run('0' * pos + '1' + '0' * (120 - pos))
    changed = []
    for group, pair in enumerate(pairs):
        idx = [ff_index[name] for name in pair]
        if any(tuple(row[i] for i in idx) != tuple(zrow[i] for i in idx)
               for row, zrow in zip(states, zero, strict=True)):
            changed.append(group)
    membership.append(changed)

print(f'two-flop feedback groups: {len(pairs)}')
print('one-hot group membership by 11x11 position:')
for row in range(11):
    print(' | '.join(','.join(map(str, membership[row * 11 + col])) for col in range(11)))
print('membership-count histogram:',
      ' '.join(f'{count}:{sum(len(x) == count for x in membership)}'
               for count in sorted({len(x) for x in membership})))
for group, pair in enumerate(pairs):
    positions = [pos for pos, groups in enumerate(membership) if group in groups]
    print(f'group {group}: cells={len(positions)} positions=' +
          ' '.join(f'r{p // 11}c{p % 11}' for p in positions) +
          ' flops=' + ','.join(pair))

column_groups = set(range(11))
region_groups = set(range(11, 22))
region_for_pos = []
for pos, groups in enumerate(membership):
    regions = region_groups & set(groups)
    assert len(regions) == 1, (pos, groups)
    region_for_pos.append(next(iter(regions)))
print('recovered region map (A=group11 through K=group21):')
for row in range(11):
    print(''.join(chr(ord('A') + region_for_pos[row * 11 + col] - 11) for col in range(11)))
accepted = '0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000'
region_counts = {group: 0 for group in region_groups}
for pos, bit in enumerate(accepted):
    if bit == '1':
        region_counts[region_for_pos[pos]] += 1
print('accepted region counts:', ' '.join(f'{chr(ord("A") + g - 11)}={region_counts[g]}' for g in sorted(region_groups)))
print('region cells total:', sum(sum(region_for_pos[p] == g for p in range(121)) for g in region_groups))

# Independently encode the recovered Star Battle rules, without using the
# gate-level model, and ask whether they uniquely determine the word.
from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver

pool = IDPool(start_from=122)
cnf = CNF()
for row in range(11):
    cnf.extend(CardEnc.equals([row * 11 + col + 1 for col in range(11)],
                              bound=2, vpool=pool, encoding=EncType.seqcounter))
for col in range(11):
    cnf.extend(CardEnc.equals([row * 11 + col + 1 for row in range(11)],
                              bound=2, vpool=pool, encoding=EncType.seqcounter))
for group in sorted(region_groups):
    cnf.extend(CardEnc.equals([pos + 1 for pos, region in enumerate(region_for_pos) if region == group],
                              bound=2, vpool=pool, encoding=EncType.seqcounter))
for a in range(121):
    ar, ac = divmod(a, 11)
    for b in range(a + 1, 121):
        br, bc = divmod(b, 11)
        if max(abs(ar - br), abs(ac - bc)) <= 1:
            cnf.append([-(a + 1), -(b + 1)])
solutions = []
with Solver(name='cadical195', bootstrap_with=cnf.clauses) as solver:
    while len(solutions) < 2 and solver.solve():
        positive = set(lit for lit in solver.get_model() if lit > 0)
        word = ''.join('1' if pos + 1 in positive else '0' for pos in range(121))
        solutions.append(word)
        solver.add_clause([-(pos + 1) if bit == '1' else pos + 1 for pos, bit in enumerate(word)])
print(f'independent recovered-rule CNF: vars={pool.top} clauses={len(cnf.clauses)} solutions_up_to_2={len(solutions)}')
for i, word in enumerate(solutions):
    print(f'recovered-rule solution {i}: {word}')
print('recovered rules unique and equal accepted:', solutions == [accepted])
