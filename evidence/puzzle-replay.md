# Puzzle replay: `example_inputs.vcd` against the extracted netlist

**Status: blocked on #2.** There is no extracted puzzle netlist yet — cell-
level connectivity extraction (#2) is itself blocked on #1 (extraction
harness), and both are open at the time this file was written. This is not
a result; it documents the exact command that will produce one once an
extracted netlist exists, so that the next step is "run this" rather than
"figure out what to run."

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
This structural read is not embargoed content by itself (it is the same
information the puzzle README states about the file's signal set); the
actual value trace and any replay result against a recovered netlist would
be, and are not reproduced here.

## The command that will run once unblocked

```sh
python3 -m tools.sim.run_vcd_replay \
    --netlist evidence/puzzle-extracted.v \
    --vcd puzzle/example_inputs.vcd \
    --top puzzle \
    --inputs clk,rst_n,enable,I \
    --outputs O,success
```

(`--top` and the exact extracted-netlist path are placeholders pending #2 —
`klt cells`/`klt extract` output determines the actual top-cell name and
port names; `run_vcd_replay.py --port-map` exists if extraction produces
different top-level port names than the recorded VCD's signal names.)

`tools/sim/run_vcd_replay.py` prints model provenance, then either `RESULT
PASS` (zero divergence over the entire recorded trace) or `RESULT FAIL` with
the first differing `(time, signal, expected, actual)` — never a bare
pass/fail, per issue #5's acceptance criteria.

## What has been verified instead, in the meantime

The replay engine itself (`tools/sim/replay.py`) — VCD reading, testbench
generation, simulation, and trace diffing, all netlist-agnostic — has been
self-tested against the warm-up, including confirming it correctly detects
an injected divergence rather than just reporting a false PASS. See
`evidence/warmup-sim.md` § "Replay-engine self-test".
