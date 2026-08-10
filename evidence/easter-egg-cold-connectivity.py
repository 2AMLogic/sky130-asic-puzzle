from collections import defaultdict, deque
from pathlib import Path

from tools.sim.solve import load_design
from tools.sim.seqmodel import eval_comb, initial_state
from tools.vcd import read_vcd

design = load_design(Path('.sim-work/independent-review/puzzle-extracted.v'), work_dir=Path('.sim-work/independent-review/model'))
model = design.model
vcd = read_vcd('puzzle/example_inputs.vcd')
clock = vcd.signal_history('clk')
rises = [t for (pt, pv), (t, v) in zip(clock, clock[1:]) if pv == '0' and v == '1']
inputs = [{n: int(vcd.value_at(n, t)) for n in ('I', 'enable', 'rst_n')} for t in rises]

def run(sequence, x_value):
    state = initial_state(model, x_value=x_value)
    histories = defaultdict(list)
    for inp in sequence:
        vals = dict(inp, clk=1)
        for ff, bit in zip(model.ffs, state, strict=True):
            vals[ff.q_net] = bit
            histories[ff.name].append(bit)
        eval_comb(model, vals)
        for gate in model.gates:
            histories[gate.inst].append(tuple(vals[n] for n in gate.out_nets if n is not None))
        state = tuple(ff.async_value if ff.async_pin and vals[ff.async_net] == 0 else vals[ff.d_net] for ff in model.ffs)
    return {inst for inst, h in histories.items() if len(set(h)) > 1}

all_cells = {ff.name for ff in model.ffs} | {g.inst for g in model.gates}
cold = all_cells - (run(inputs, 0) | run(inputs, 1))
drivers = {}
deps = {}
for ff in model.ffs:
    drivers[ff.q_net] = ff.name
    deps[ff.name] = [ff.d_net]
for gate in model.gates:
    for net in gate.out_nets:
        if net is not None:
            drivers[net] = gate.inst
    deps[gate.inst] = list(gate.in_nets)

def cone(outputs):
    cells, todo, seen = set(), list(outputs), set()
    while todo:
        net = todo.pop()
        if net in seen:
            continue
        seen.add(net)
        cell = drivers.get(net)
        if cell is not None and cell not in cells:
            cells.add(cell)
            todo.extend(deps[cell])
    return cells

o_cold = cold & cone([f'O[{i}]' for i in range(8)])
adj = {cell: set() for cell in o_cold}
directed_edges = []
for consumer in o_cold:
    for net in deps[consumer]:
        producer = drivers.get(net)
        if producer in o_cold:
            adj[producer].add(consumer)
            adj[consumer].add(producer)
            directed_edges.append((producer, consumer, net))

components = []
remaining = set(o_cold)
while remaining:
    root = min(remaining)
    comp, todo = set(), [root]
    while todo:
        cell = todo.pop()
        if cell in comp:
            continue
        comp.add(cell)
        todo.extend(adj[cell] - comp)
    remaining -= comp
    components.append(comp)
components.sort(key=lambda c: (-len(c), min(c)))

print(f'all cold cells ({len(cold)}):')
print(' '.join(sorted(cold)))
print(f'cold cells in O cone ({len(o_cold)}):')
print(' '.join(sorted(o_cold)))
print(f'induced directed edges: {len(directed_edges)}')
print(f'weak components: {len(components)}; sizes: {" ".join(map(str, (len(c) for c in components)))}')
for i, comp in enumerate(components, 1):
    print(f'component {i} ({len(comp)}): {" ".join(sorted(comp))}')

ones_sequence = []
for t in range(190):
    active = 4 <= t < 125
    ones_sequence.append({'clk': 1, 'rst_n': int(t >= 3), 'enable': int(active), 'I': int(active)})
activated = cold & (run(ones_sequence, 0) | run(ones_sequence, 1))
print(f'formerly cold cells toggled by all-ones witness: {len(activated)}')
print(' '.join(sorted(activated)))
print(f'formerly cold O-cone cells toggled by all-ones witness: {len(activated & o_cold)}')
