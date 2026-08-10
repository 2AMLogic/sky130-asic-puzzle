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

## Reproduction (issue #14) and go/no-go decision

Everything above this section was recorded by PR #18. This section is an
append made for issue #14 (stage 6's remaining scope), on top of that
recorded result — nothing above has been edited, per this repo's
append-only evidence convention.

### Reproduction

The exact command in "The command, run for real" above was re-run,
unmodified, against the current worktree (`origin/main` @ `f8ac624`):

```
RESULT FAIL — first divergence at t=1000 signal=O
  expected: xxxxxxxx
  actual:   00000000
```

— identical to the recorded result. The value-content check was re-run too
and reproduces exactly:

```
O: 22 transitions, 0 value mismatches, timing deltas (sim-rec, ps) = [-4000, 1000]
success: 2 transitions, 0 value mismatches, timing deltas (sim-rec, ps) = [-4000]
```

24 total recorded transitions across `O[7:0]` and `success` (22 + 2), 0
value mismatches in either — unchanged from the original run. This is a
literal, freshly-executed rerun (PDK resolved locally the same way, model
files unchanged), not an assertion carried forward from the earlier PR.

### Strengthening the timing-offset mechanism (cheap check, item 2 of the issue)

The evidence above calls the timing-offset mechanism "most likely" but
unconfirmed: a fixed simulation-delay difference between this repo's
gate-level sim and whatever produced `example_inputs.vcd`. One cheap,
concrete check narrows that: the simulation is compiled with `-D
UNIT_DELAY=#1` against the sky130 primitive models, which declare
`` `timescale 1ns / 1ps `` (`primitives.v:31`, confirmed locally at the PDK
root this run resolved). Under that timescale, `#1` is **exactly one
nanosecond** — i.e. exactly 1000ps in `example_inputs.vcd`'s own `1ps`
timescale. The observed constant offset on every non-anomalous transition
is `+1000`ps. That is not merely "some constant delta" (as the original
evidence described it) but numerically **exactly one `UNIT_DELAY` quantum**
under the timescale this simulation actually runs at.

This does not fully explain why the offset is the *same* +1000ps
regardless of a signal's combinational depth from its driving flip-flop
(`success` is a bare `dfrtp_2` `Q` output — zero combinational gates;
`O[0]`/`O[7]` are each driven through a final `sky130_fd_sc_hd__and3_2`
gate fed by further combinational logic upstream — checked directly against
`evidence/puzzle-extracted.v` lines ~840-858 and ~3170-3180). Working out
*why* the offset does not scale with logic depth (e.g. whether it is
governed by which single net's transition the VCD dumper treats as "the"
value-change event, or by how the reference trace's own generator was
built) would require deeper investigation than "cheap" — it is **not**
pursued here, consistent with the issue's framing of item 2 as optional
depth. What the cheap check does establish: the *magnitude* of the offset
is not arbitrary — it is exactly the delay quantum this simulation's own
compile flags introduce, which is independent confirmation (beyond "it's a
constant, so probably timing") that the divergence mechanism is a
simulation-timing artifact of this repo's own `UNIT_DELAY=#1` choice, not
some other, unexplained effect that happens to be the same magnitude.

### Re-examining the outlier (-4000ps) transition

The one exception to the "+1000ps, later" pattern is the very first value
change on both `O` and `success` (`x` → `0`), which arrives 4000ps
*earlier* in this simulation (`t=1000`) than in the recording (`t=5000`).
Reproduced directly against the stimulus trace this run:

```
rst_n  first deasserts at t=30000
enable first asserts   at t=40000
O      first settles    at t=1000  (sim) / t=5000  (recorded)
success first settles   at t=1000  (sim) / t=5000  (recorded)
```

Both settle events happen well before either `rst_n` or `enable` is ever
driven to a meaningful value — confirming, by direct inspection this run
(not by re-asserting the earlier claim), that this transition is
functionally inert: it is the `x`-to-known-value settle of registers held
in reset, not a difference in circuit behavior. Its direction (sim
*earlier*, vs. every other transition being sim *later*) is explained by it
being a single async-reset propagation step rather than a synchronous
clock-to-Q + combinational chain — a qualitatively different kind of event
from the rest of the trace, which is why its delta does not follow the
`+1000` pattern. This re-examination does not change the original
characterization; it confirms it against fresh output.

### Decision: GO — treat the extraction as sufficient to unblock stage 7, with the risk explicitly flagged, not fully retired

**Call**: proceed to stage 7 (#15). The documented zero-value-content-mismatch
agreement (24/24 transitions, 0 mismatches, reproduced above) is treated as
satisfying this stage's intent — "the recovered netlist behaves like the
real device on the one trace we have" — even though it does not satisfy
`run_vcd_replay.py`'s literal exact-timestamp `PASS` contract, and is not
expected to: that contract checks something (delay-annotated timing
fidelity) extraction never claimed to reproduce (structure, not timing —
stated in the original evidence above).

**Why GO and not "block on more confirmation":**

- Every one of 24 recorded output transitions across both output signals
  (`O[7:0]`, `success`) matches in value, with zero exceptions. There is no
  partial match, no signal that agrees more than another, no cycle where
  the two traces disagree on a bit's actual value — the strongest form of
  agreement short of exact-timestamp equality.
- All divergence collapses to exactly two numeric deltas, not a scatter:
  `-4000` (one occurrence, functionally inert, reconfirmed above) and
  `+1000` (every other occurrence). A latent extraction bug — a swapped
  net, a misidentified cell, a dropped connection — would be expected to
  produce a **value** mismatch somewhere in a 92-flip-flop, 738-cell design
  exercised over 3.12µs and multiple `enable`/`rst_n` cycles, not a
  uniform, small, structurally-explained timing shift. Getting the
  *content* bit-exact by coincidence while the *structure* is wrong is
  implausible at this scale.
- The `+1000`ps delta is now shown (this run) to equal exactly one
  `UNIT_DELAY=#1` quantum under the timescale this simulation compiles at —
  not just "a constant," but a constant with an identified, mechanistic
  source in this repo's own simulation flags.

**Why "explicitly flagged as an open risk," not "fully closed":**

- The tool/settings that actually produced `example_inputs.vcd` are not
  known (Jane Street ships the trace, not the generator) — the "near-zero-
  delay RTL/functional sim" explanation for *why the reference lacks this
  delay* remains inference, not confirmation from the other side.
- The combinational-depth-independence of the `+1000`ps offset (noted
  above) is not fully explained. It is not evidence *against* the
  timing-artifact reading (the alternative — a logic bug that happens to
  reproduce a constant, quantum-sized, depth-independent offset on every
  single transition of a 24-transition, two-signal, multi-depth trace —
  is a strictly less parsimonious explanation of the same data) but it is
  a loose end, and stage 7/8 have no independent oracle of their own that
  would catch a subtler extraction defect if one exists beneath this
  agreement.

**What this unblocks, and what it does not:** stage 7 (#15) may proceed
treating `evidence/puzzle-extracted.v` as the netlist to solve against.
Stage 7/8 work should not re-litigate this file's `RESULT FAIL` as reason
to distrust the netlist's *values* — that question is answered here with
the strongest evidence this repo can produce without the reference
simulator's own settings. It should, however, carry the open risk forward:
if stage 7's solve produces behavior inconsistent with what a human reading
of the design would expect (e.g. `success` provably unreachable, or the
92-bit state space behaving unlike any plausible comparator/counter
structure), that inconsistency is grounds to revisit this decision rather
than assume the solver is at fault, since the two would look identical from
inside stage 7.
