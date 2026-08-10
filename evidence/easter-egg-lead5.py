"""Trace the unusual flops and floating net through the Boolean model."""

from collections import defaultdict, deque
from pathlib import Path

from tools.sim.solve import load_design
from tools.sim.seqmodel import eval_comb, initial_state

design = load_design(Path('.sim-work/independent-review/puzzle-extracted.v'), work_dir=Path('.sim-work/easter-lead5/model'))
model = design.model
special = [ff for ff in model.ffs if ff.cell in ('dfstp_2', 'dfxtp_2')]

consumers = defaultdict(list)
for gate in model.gates:
    for net in gate.in_nets:
        consumers[net].append(gate.inst)
for ff in model.ffs:
    consumers[ff.d_net].append(ff.name)

cell_outputs = {}
for gate in model.gates:
    cell_outputs[gate.inst] = [n for n in gate.out_nets if n]
for ff in model.ffs:
    cell_outputs[ff.name] = [ff.q_net]

def reaches(start_net):
    cells, nets, todo = set(), {start_net}, [start_net]
    while todo:
        net = todo.pop()
        for cell in consumers[net]:
            if cell in cells:
                continue
            cells.add(cell)
            for out in cell_outputs[cell]:
                if out not in nets:
                    nets.add(out)
                    todo.append(out)
    return cells, nets

print('== unusual flop structure ==')
for ff in special:
    cells, nets = reaches(ff.q_net)
    targets = [name for name in ['success', *[f'O[{i}]' for i in range(8)]] if name in nets]
    print(f'{ff.name}: cell={ff.cell} D={ff.d_net} Q={ff.q_net} async={ff.async_pin or "none"} '
          f'async_value={ff.async_value} forward_cells={len(cells)} reaches={",".join(targets) or "none"}')

def sequence(bits):
    rows = []
    for t in range(190):
        i = t - 4
        active = 0 <= i < 121
        rows.append({'clk': 1, 'rst_n': int(t >= 3), 'enable': int(active),
                     'I': int(bits[i]) if active else 0})
    return rows

def trace(bits, x_value, undriven):
    state = initial_state(model, x_value=x_value)
    out = []
    specials = []
    for inp in sequence(bits):
        vals = {**inp, **{net: undriven for net in model.undriven_nets}}
        for ff, bit in zip(model.ffs, state, strict=True):
            vals[ff.q_net] = bit
        eval_comb(model, vals)
        out.append(tuple(vals[f'O[{i}]'] for i in range(8)) + (vals['success'],))
        specials.append(tuple(vals[ff.q_net] for ff in special))
        state = tuple(ff.async_value if ff.async_pin and vals[ff.async_net] == 0 else vals[ff.d_net] for ff in model.ffs)
    return out, specials

accepted = '0000000101010000100000000000010101010000000000001010000001000001000000100000101000010000000100000010000010010001010000000'
patterns = {'accepted': accepted, 'all-zero': '0' * 121, 'all-one': '1' * 121,
            'alternating': '01' * 60 + '0'}
print('== special-flop activity and floating-net sensitivity ==')
for label, bits in patterns.items():
    base_out, base_states = trace(bits, 0, 0)
    init1_out, init1_states = trace(bits, 1, 0)
    float1_out, _ = trace(bits, 0, 1)
    changed = [special[i].name for i in range(len(special))
               if len({row[i] for row in base_states}) > 1]
    convergence = next((t for t in range(len(base_states))
                        if base_states[t:] == init1_states[t:]), None)
    print(f'{label}: special_flops_toggled={len(changed)} names={",".join(changed) or "none"} '
          f'dfxtp_initializations_converge_at_cycle={convergence} '
          f'dfxtp_init_changes_outputs={base_out != init1_out} '
          f'net_00575_changes_outputs={base_out != float1_out}')
    if label == 'accepted':
        print('accepted special state cycles 0..6:',
              ' '.join(f'{t}:{"".join(map(str, base_states[t]))}' for t in range(7)))
        print('accepted special state cycles 123..142:',
              ' '.join(f'{t}:{"".join(map(str, base_states[t]))}' for t in range(123, 143)))

floating_cells = [gate.inst for gate in model.gates if 'net_00575' in gate.in_nets]
print('== net_00575 forward reachability ==')
print('consumers:', ' '.join(floating_cells))
cells, nets = reaches('net_00575')
targets = [name for name in ['success', *[f'O[{i}]' for i in range(8)]] if name in nets]
print(f'forward_cells={len(cells)} reaches={",".join(targets) or "none"}')
