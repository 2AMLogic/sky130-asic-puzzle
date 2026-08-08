# Warm-up regression — recorded run

Per `CLAUDE.md` §5, this is what was actually executed, not what is believed to
work. Everything below is re-runnable by anyone with the repo checked out; the
one prerequisite is `./scripts/fetch-puzzle.sh`, because `puzzle/` is gitignored
(`CLAUDE.md` §3 — upstream carries no license, so its files are never committed
here).

**Status: half green, half blocked.** The comparator and its mutation suite run
today. The end-to-end half — `puzzle/warmup/04_final.gds → extract → compare` —
needs `tools/extract`, which is issue #2 (itself downstream of #1). It is
reported as a loud SKIP rather than quietly passing; `./scripts/warmup-regression.sh
--require-extract` turns that skip into a failure once #2 lands.

Environment: macOS 25.6.0 (darwin), Python 3.14.6, repo at `a72c47c` plus this
branch. Date of run: 2026-08-08.

Identifiers from `puzzle/warmup/01_netlist.v` are elided as `<net-in-A>` /
`<instance>` below, per `CLAUDE.md` §3 ("Do not copy fragments of them into
documentation either"). Re-running the command prints the real names.

---

## 1. Setup

```console
$ ./scripts/fetch-puzzle.sh
cloning https://github.com/janestreet/asic-puzzle-2026.git -> puzzle/

Verifying the files we depend on:
  ok       puzzle.gds                                   1421700 bytes
  ok       example_inputs.vcd                           8438 bytes
  ok       warmup/00_source.v                           1205 bytes
  ok       warmup/01_netlist.v                          18887 bytes
  ok       warmup/03_post_place_and_route.def           111557 bytes
  ok       warmup/04_final.gds                          306242 bytes

puzzle/ ready. It is gitignored; do not commit its contents.
```

## 2. Comparator self-test — a renamed copy is equivalent (criterion 1)

`tools/rename` renames every instance and internal net, shuffles instance order
and pin order, and keeps only the six top-level port names — which is the actual
situation the puzzle creates. It does not use `tools/extract`, so this check is
independent of the blocked half.

```console
$ ./tools/rename puzzle/warmup/01_netlist.v --seed 7 -o /tmp/wu_renamed.v
$ ./tools/compare puzzle/warmup/01_netlist.v /tmp/wu_renamed.v
EQUIVALENT
  A: puzzle/warmup/01_netlist.v  (module adder_demo)
  B: /tmp/wu_renamed.v  (module adder_demo)

  ports            6 matched by name: A B S clk en rst_n
  signal cells    79 matched 1:1 (A has 79, B has 79)
  nets            84 matched (A has 84, B has 84)
  fill cells     151 matched by count (B has 151) [decap_3: 58, tapvpwrvgnd_1: 93]
  verification  independent re-check of the full mapping passed
$ echo $?
0
```

The 151 fill instances (93 tap, 58 decap) have no signal connectivity, so they
are matched by count as a separate class rather than 1:1 — requiring a bijection
on them would fail the regression for reasons that say nothing about extraction
quality.

The last line is load-bearing. "Equivalent" is only ever reported after the
completed mapping has been re-checked from scratch — every cell type, pin set,
pin-to-net image, net pin-multiset, and the port seeding — independently of the
search that produced it. A bug in the search can lose a match; it cannot
manufacture one.

## 3. Mutation tests — a comparator that passes everything is worthless

Each mutation damages the *renamed* copy in exactly one place. `tools/rename`
prints what it damaged on stderr; `tools/compare` must independently find it.

### 3a. Rewire one pin (criterion 2)

```console
$ ./tools/rename puzzle/warmup/01_netlist.v --seed 7 --mutate rewire-pin -o /tmp/wu_rewire.v
tools/rename: mutation rewire-pin: rewired instance u_00174 pin .B from n_00026 to n_00008
$ ./tools/compare puzzle/warmup/01_netlist.v /tmp/wu_rewire.v
NOT EQUIVALENT
  ...
First difference:
  reason: net-degree-mismatch
  corresponding nets '<net-in-A>' (A) and 'n_00008' (B) carry different pins
    net in A: <net-in-A>
    net in B: n_00008
    pins only on A's net: (none)
    pins only on B's net:
      - sky130_fd_sc_hd__and2_2 .B x1   [B instances: u_00174]
$ echo $?
1
```

It names the damaged instance (`u_00174`) and the damaged pin (`.B`) — the
instance and pin `tools/rename` says it rewired.

### 3b. Delete one instance (criterion 3)

```console
$ ./tools/rename puzzle/warmup/01_netlist.v --seed 7 --mutate drop-instance -o /tmp/wu_drop.v
tools/rename: mutation drop-instance: deleted instance u_00174 (sky130_fd_sc_hd__and2_2)
$ ./tools/compare puzzle/warmup/01_netlist.v /tmp/wu_drop.v
NOT EQUIVALENT
  ...
  cell-type histogram differences (signal cells):
      sky130_fd_sc_hd__and2_2: A 7 vs B 6

First difference:
  reason: net-degree-mismatch
  corresponding nets '<net-in-A>' (A) and 'n_00016' (B) carry different pins
    pins only on A's net:
      - sky130_fd_sc_hd__and2_2 .A x1   [A instances: <instance>]
    pins only on B's net: (none)
$ echo $?
1
```

Localised twice over: the cell-type histogram names the type that lost an
instance, and the first difference names the specific net and the surviving
neighbour whose counterpart went missing.

### 3c. Swap two cell types of equal pin count (criterion 4)

The histogram is unchanged by this mutation, so nothing global catches it.

```console
$ ./tools/rename puzzle/warmup/01_netlist.v --seed 7 --mutate swap-cells -o /tmp/wu_swap.v
tools/rename: mutation swap-cells: swapped cell types of u_00045 and u_00097
    (sky130_fd_sc_hd__and2_2 <-> sky130_fd_sc_hd__or2_2, both with pins A/B/X)
$ ./tools/compare puzzle/warmup/01_netlist.v /tmp/wu_swap.v
NOT EQUIVALENT
  ...
First difference:
  reason: net-degree-mismatch
  corresponding nets '<net-in-A>' (A) and 'n_00032' (B) carry different pins
    pins only on A's net:
      - sky130_fd_sc_hd__or2_2 .X x1   [A instances: <instance>]
    pins only on B's net:
      - sky130_fd_sc_hd__and2_2 .X x1   [B instances: u_00097]
$ echo $?
1
```

## 4. The full suite

`tools/test-compare` runs all of the above across three rename seeds and two
mutation seeds, plus thirteen synthetic checks that cover the cases that are
easy to get wrong: an automorphic circuit that only the backtracking search can
decide, a crossed-output pair with an identical cell histogram *and* degree
sequence, `.A`/`.B` swapped on a commutative gate, `assign` aliasing, fill-count
handling, and the JSON interchange form.

```console
$ ./tools/test-compare
tools/test-compare — self-test and mutation suite for tools/compare

[  ok  ] synthetic: a netlist is equivalent to itself
[  ok  ] synthetic: crossed outputs (same histogram, same degrees) are NOT equivalent
[  ok  ] synthetic: renamed + reordered copy is equivalent
[  ok  ] synthetic: automorphic circuit is decided by the backtracking search
[  ok  ] synthetic: swapping .A/.B on a commutative gate is reported (structural, not logical)
[  ok  ] synthetic: swapped cell types are NOT equivalent
[  ok  ] synthetic: cell-type swap failure names a cell type
[  ok  ] synthetic: `assign` aliases are folded, not treated as extra nets
[  ok  ] synthetic: extra fill cells do not break signal equivalence (default)
[  ok  ] synthetic: differing fill counts are reported as a separate class
[  ok  ] synthetic: --strict-fill makes a fill count difference fatal
[  ok  ] synthetic: a missing input exits 2 (error), not 1 (not equivalent)
[  ok  ] synthetic: JSON netlist form compares against Verilog

[  ok  ] warm-up: fixtures present — puzzle/warmup/01_netlist.v
[  ok  ] warm-up: renamed copy (seed 1) is equivalent
[  ok  ] warm-up: renamed copy (seed 7) is equivalent
[  ok  ] warm-up: renamed copy (seed 4242) is equivalent
[  ok  ] warm-up: 01_netlist.v vs 02_netlist_with_power_rails.v is equivalent (power pins dropped)
[  ok  ] warm-up: rewire-pin (seed 7) is detected
[  ok  ] warm-up: rewire-pin (seed 7) report names the damaged instance and pin
[  ok  ] warm-up: rewire-pin (seed 99) is detected
[  ok  ] warm-up: rewire-pin (seed 99) report names the damaged instance and pin
[  ok  ] warm-up: drop-instance (seed 7) is detected
[  ok  ] warm-up: drop-instance (seed 7) report localises the deletion
[  ok  ] warm-up: drop-instance (seed 99) is detected
[  ok  ] warm-up: drop-instance (seed 99) report localises the deletion
[  ok  ] warm-up: swap-cells (seed 7) is detected
[  ok  ] warm-up: swap-cells (seed 7) report names one of the swapped instances
[  ok  ] warm-up: swap-cells (seed 99) is detected
[  ok  ] warm-up: swap-cells (seed 99) report names one of the swapped instances

30 passed, 0 failed, 0 skipped
$ echo $?
0
```

One of those deserves calling out: **`01_netlist.v` vs
`02_netlist_with_power_rails.v` compares equivalent.** That is not a self-test —
`02` is a separate file produced by someone else's flow, with `VPWR`/`VGND`
pins on every instance and two extra top-level ports. The comparator drops
supply pins and nets by default (`--keep-power` to keep them) and finds the same
79-instance correspondence. It is the closest thing available to the real
end-to-end check until `tools/extract` exists.

## 5. The end-to-end half — blocked on #2

```console
$ ./scripts/warmup-regression.sh --no-fetch
...
2. End-to-end: 04_final.gds -> extract -> compare against 01_netlist.v
------------------------------------------------------------
SKIPPED — tools/extract does not exist yet.
  Cell-level extraction is issue #2 (blocked on #1). Until it lands, the
  end-to-end half of this regression cannot run; the comparator half above
  is the part that is green today.
$ echo $?
0

$ ./scripts/warmup-regression.sh --no-fetch --require-extract
...
FAILED — --require-extract was given but tools/extract is absent.
$ echo $?
1
```

When `tools/extract` lands, the script runs it into `build/warmup-extracted.v`
and compares that against `01_netlist.v`. Note the output path: `build/` is
gitignored. Issue #3 named `evidence/warmup-extracted.v`, but a netlist
extracted from `04_final.gds` is a derived representation of a file that carries
no license, so committing it would be vendoring the puzzle files by another
route (`CLAUDE.md` §3). It stays out of git; the *result* of comparing it is
what gets recorded here.

## 6. The whole chain

```console
$ npm run check:ci        # lint -> warm-up regression -> embargo check
...
Embargo check — today 2026-08-08, embargo lifts 2026-09-04

  ok    2AMLogic/sky130-asic-puzzle is PRIVATE
  ok    no upstream puzzle files tracked

Embargo check passed. Prose is still your judgement, not this script's.
$ echo $?
0
```

Failure propagation was verified rather than assumed: making `tools/compare`
non-executable makes `npm run check:ci` exit 1 at the lint stage without
reaching the later steps.

## What this does *not* yet claim

- Nothing here says the extractor is correct, because there is no extractor. It
  says the *comparator* is correct enough to be trusted as the judge when there
  is one.
- No claim at all is made about `puzzle.gds`. Nothing in this regression reads
  it (`CLAUDE.md` §1).
