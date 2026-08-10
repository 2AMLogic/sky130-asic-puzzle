# Puzzle replay: `example_inputs.vcd` against the extracted netlist

**Status: unblocked, run, and characterized.** #2 (cell-level connectivity
extraction) closed via PR #11 and `evidence/puzzle-extracted.v` exists.
Replaying `example_inputs.vcd` against it produces a literal `RESULT FAIL`
under `tools/sim/run_vcd_replay.py`'s strict exact-timestamp comparison —
but the *value content* of every recorded output transition matches
exactly; every difference is explained by a fixed simulation-timing offset
(see "Value-content agreement" below). Both the literal result and the
timing-offset characterization are recorded here, per CLAUDE.md §5 ("state
what was actually executed" — not "state a result recharacterized as
passing").

## Why this is the gate

`spec/puzzle.md` stage 6: `example_inputs.vcd` is the only independent
oracle the puzzle ships for `puzzle.gds` — there is no published ground-truth
netlist for the real puzzle (unlike the warm-up), so the structural
comparator (issue #3) cannot check the puzzle at all. Replaying the recorded
trace against a recovered netlist is the only way to know extraction
succeeded on the real subject. Per CLAUDE.md §5, a claim about what
`puzzle.gds` does needs a simulation a reader can re-run, not inference from
the layout — solving for `success` (stage 7) against an unverified netlist
would be solving the wrong problem.

## What `example_inputs.vcd` contains

Read via `tools/vcd`, without executing any solving/answer logic:

```sh
python3 -c "
from tools.vcd import read_vcd
doc = read_vcd('puzzle/example_inputs.vcd')
print('timescale', doc.timescale)
print('signals', [(v.name, v.width) for v in doc.vars])
print('end_time', doc.end_time())
"
```

```
timescale 1ps
signals [('clk', 1), ('rst_n', 1), ('enable', 1), ('I', 1), ('O', 8), ('success', 1)]
end_time 3120000
```

Five 1-bit/8-bit signals: `clk`, `rst_n`, `enable`, `I` as recorded inputs;
`O[7:0]` and `success` as recorded outputs — matching the puzzle README's
description of `example_inputs.vcd` ("some inputs being fed to the design").

## Port shape: `evidence/puzzle-extracted.v` has no `O[7:0]` vector port

`tools/extract` reads pin geometry straight off the GDS, which has no bus
abstraction — a layout label is per bit, not per bus. So `puzzle-extracted.v`
declares `O` as eight separate scalar, escaped-identifier ports
(`output \O[0] ;` .. `output \O[7] ;`), not a single `output [7:0] O;`. This
is the expected, correct shape for a netlist extracted straight from GDS pin
labels — not a defect in `tools/extract` — but `tools/sim`'s VCD-replay
testbench generator only supported one recorded signal to one DUT port.
Fixed here: `build_vcd_replay_testbench`'s `port_map` now also accepts a
colon-separated list of per-bit DUT port names (bit 0 first) for a signal
with no vector port on the DUT side, connecting each bit individually
(`tools/sim/testbench.py`, self-tested end-to-end against a synthetic
per-bit-port DUT in `tools/sim/selftest_portmap.py` — no PDK-cell
dependency, so it needs only a resolvable PDK for compilation, not a real
extracted netlist).

Fixing this also surfaced and fixed a real, previously-latent bug in
`tools/vcd/reader.py`'s `normalize_value`: a VCD writer conventionally drops
leading (most-significant) **zero** bits from a truncated vector dump, and a
reader must zero-extend them back — the prior implementation instead padded
with a repeat of whatever the leftmost *remaining* digit was, which is only
correct when that digit is `0`, `x`, or `z`. Icarus dumps `0x1B` (`O`'s
8-bit width) as `b11011` (leading zeros dropped); the old code zero-extended
that same value to `11111011` instead of `00011011`. This went unexercised
until this issue's first multi-bit output signal, because every prior
`tools/sim` output was a single bit (`S` in the warm-up), which nothing can
truncate. `selftest_portmap.py`'s "correct wiring" check failed loudly
against this bug before the fix and passes after it.

## The command, run for real

```sh
python3 -m tools.sim.run_vcd_replay \
    --netlist evidence/puzzle-extracted.v \
    --vcd puzzle/example_inputs.vcd \
    --top puzzle \
    --inputs clk,rst_n,enable,I \
    --outputs O,success \
    --port-map "clk=clk,rst_n=rst_n,enable=enable,I=I,success=success,O=\O[0]:\O[1]:\O[2]:\O[3]:\O[4]:\O[5]:\O[6]:\O[7]"
```

## Result

```
PDK variant: sky130A
PDK version: open_pdks c6d73a35f524070e85faff4a6a9eef49553ebc2b
Resolved via: klt pdk find --pdk sky130A (root: /home/ubuntu/.volare)
Model files:
  /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  /home/ubuntu/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

Compared through t=3120000 (1ps units)
Simulated trace: .sim-work/replay/sim_out.vcd

RESULT FAIL — first divergence at t=1000 signal=O
  expected: xxxxxxxx
  actual:   00000000
```

Per `tools/sim/run_vcd_replay.py`'s contract this is `RESULT FAIL` — the
recorded and simulated traces do not agree at every timestamp — and is
reported exactly as such, with the first differing `(time, signal, expected,
actual)`, never recharacterized as a pass. The divergence is at `t=1000`ps
(1ns): before `rst_n` first deasserts (`t=30000`), both traces are settling
their initial `x` (unknown, before anything has been driven) to a defined
value, and they do so at slightly different times.

## Value-content agreement (why this is a timing artifact, not a logic bug)

The recorded and simulated traces have exactly the same number of value
changes for each output signal, and the values at each change are identical
— the only difference is *when* the change is dumped:

```sh
python3 -c "
from tools.vcd import read_vcd
recorded = read_vcd('puzzle/example_inputs.vcd')
simulated = read_vcd('.sim-work/replay/sim_out.vcd')

for name in ['O', 'success']:
    rec = recorded.signal_history(name)
    sim = simulated.signal_history(name)
    assert len(rec) == len(sim), f'{name}: change count differs ({len(rec)} vs {len(sim)})'
    mismatches = [(i, rv, sv) for i, ((_, rv), (_, sv)) in enumerate(zip(rec[1:], sim[1:])) if rv != sv]
    deltas = sorted(set(st - rt for (rt, _), (st, _) in zip(rec[1:], sim[1:])))
    print(f'{name}: {len(rec)} transitions, {len(mismatches)} value mismatches, timing deltas (sim-rec, ps) = {deltas}')
"
```

```
O: 22 transitions, 0 value mismatches, timing deltas (sim-rec, ps) = [-4000, 1000]
success: 2 transitions, 0 value mismatches, timing deltas (sim-rec, ps) = [-4000]
```

Zero value-content mismatches across the entire recorded trace, for both
`O[7:0]` and `success`. Every transition's delta is one of exactly two
values: the very first `x`-to-defined settle is 4ns *earlier* in this
simulation than in the recording (both settle to the same value, `0`, before
`rst_n` or `enable` are ever asserted — functionally inert), and every
transition after that is a constant +1ns later. A constant per-transition
offset across the entire trace is consistent with a fixed clock-to-output
propagation delay difference between whatever produced `example_inputs.vcd`
(most likely a zero- or near-zero-delay RTL/functional simulation) and this
gate-level simulation (`UNIT_DELAY=#1`, sky130 primitive propagation delays
— see `tools/README.md` § "Simulation defines"), not a data/logic
divergence introduced by extraction.

**This is not a passing acceptance-criterion result** — `run_vcd_replay.py`
correctly reports `RESULT FAIL` per its exact-timestamp contract, and that
contract is not loosened here (a tolerant-comparison mode would risk masking
a real future regression). What this section establishes is the *nature* of
the one class of divergence actually present: the extracted netlist
reproduces the recorded functional behavior exactly; it does not reproduce
the recording's exact simulation timing, which was never a claim `tools/sim`
makes about the extracted netlist in the first place (extraction recovers
structure, not delay-annotated timing).

## Model provenance

Recorded above, per run: PDK variant/version, resolution source, and the
exact model files linked — `tools/sim/pdk.py::resolve_sky130_models()`, same
resolver as the warm-up (`evidence/warmup-sim.md`).

## What has been verified instead, alongside this

The replay engine itself (`tools/sim/replay.py`) — VCD reading, testbench
generation, simulation, and trace diffing, all netlist-agnostic — has been
self-tested against the warm-up, including confirming it correctly detects
an injected divergence rather than just reporting a false PASS. See
`evidence/warmup-sim.md` § "Replay-engine self-test". The multi-bit
per-bit-port `port_map` extension this replay needed is self-tested
independently in `tools/sim/selftest_portmap.py` (see "Port shape" above).
