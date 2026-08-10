# Warm-up regression — recorded run

Per `CLAUDE.md` §5, this is what was actually executed, not what is believed to
work. Everything below is re-runnable by anyone with the repo checked out; the
one prerequisite is `./scripts/fetch-puzzle.sh`, because `puzzle/` is gitignored
(`CLAUDE.md` §3 — upstream carries no license, so its files are never committed
here).

**Status: fully green.** The comparator and its mutation suite run, and the
end-to-end half — `puzzle/warmup/04_final.gds → extract → compare` — now runs
too: `tools/extract` landed in #2, and `./scripts/warmup-regression.sh
--require-extract` (the flag CI now always passes) exits 0 with the extracted
netlist reported **equivalent** to `puzzle/warmup/01_netlist.v`. `--require-extract`
still exists to turn a future missing/non-functional `tools/extract` into a hard
CI failure rather than a silent skip — see §5's edge-case check.

Environment: macOS 25.6.0 (darwin), Python 3.14.6, repo at `8ac5d6d` plus this
branch. Date of run: 2026-08-10.

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
independent of the end-to-end half in §5.

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
79-instance correspondence. Before `tools/extract` existed, this was the
closest available proxy for the real end-to-end check in §5; it now exercises
the power-stripping and fill paths independently of the extractor.

## 5. The end-to-end half — extract, then compare against ground truth

`tools/extract` (issue #2) reads `04_final.gds` directly and emits a
gate-level Verilog netlist. Run manually here for a clean transcript; this is
exactly what `./scripts/warmup-regression.sh --require-extract` runs as its
step 4, and `--require-extract` is the flag CI now always passes (issue #9).

```console
$ ./tools/extract puzzle/warmup/04_final.gds -o build/warmup-extracted.v
tools/extract: wrote build/warmup-extracted.v
$ echo $?
0

$ ./tools/compare build/warmup-extracted.v puzzle/warmup/01_netlist.v
EQUIVALENT
  A: build/warmup-extracted.v  (module adder_demo)
  B: puzzle/warmup/01_netlist.v  (module adder_demo)

  ports            6 matched by name: A B S clk en rst_n
  signal cells    79 matched 1:1 (A has 79, B has 79)
  nets            84 matched (A has 84, B has 84)
  fill cells     151 matched by count (B has 151) [decap_3: 58, tapvpwrvgnd_1: 93]
  verification  independent re-check of the full mapping passed
$ echo $?
0
```

`build/` is gitignored: a netlist extracted from `04_final.gds` is a derived
representation of a file that carries no license, so committing it would be
vendoring the puzzle files by another route (`CLAUDE.md` §3). It never leaves
this machine; the *result* of comparing it is what gets recorded here.

The full harness reaches the same result through `scripts/warmup-regression.sh`,
which runs the comparator suite, the inventory/pins suite, and this end-to-end
step in sequence:

```console
$ ./scripts/warmup-regression.sh --no-fetch --require-extract
...
4. End-to-end: 04_final.gds -> extract -> compare against 01_netlist.v
------------------------------------------------------------
running: tools/extract .../puzzle/warmup/04_final.gds -o .../build/warmup-extracted.v
tools/extract: wrote .../build/warmup-extracted.v
running: tools/compare .../build/warmup-extracted.v .../puzzle/warmup/01_netlist.v
EQUIVALENT
  A: .../build/warmup-extracted.v  (module adder_demo)
  B: .../puzzle/warmup/01_netlist.v  (module adder_demo)

  ports            6 matched by name: A B S clk en rst_n
  signal cells    79 matched 1:1 (A has 79, B has 79)
  nets            84 matched (A has 84, B has 84)
  fill cells     151 matched by count (B has 151) [decap_3: 58, tapvpwrvgnd_1: 93]
  verification  independent re-check of the full mapping passed

------------------------------------------------------------
Warm-up regression complete.
$ echo $?
0
```

(Absolute worktree paths in the "running:" lines are elided to `...` above —
they are a local build artifact of where this was run from, not puzzle
content.)

**Edge case: a missing/non-functional extractor must turn CI red, not
yellow.** Verified by temporarily removing the executable bit from
`tools/extract` and re-running:

```console
$ chmod -x tools/extract
$ ./scripts/warmup-regression.sh --no-fetch --require-extract
...
4. End-to-end: 04_final.gds -> extract -> compare against 01_netlist.v
------------------------------------------------------------
SKIPPED — tools/extract does not exist yet.
  Cell-level extraction is issue #2 (blocked on #1). Until it lands, the
  end-to-end half of this regression cannot run; the comparator half above
  is the part that is green today.
FAILED — --require-extract was given but tools/extract is absent.
$ echo $?
1
$ chmod +x tools/extract
```

`--require-extract` is the flag `.github/workflows/ci.yml` passes on every
run, so this is exactly the failure mode CI would hit if the extractor ever
regresses to missing or non-executable.

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

- This is a **single-fixture** result: `tools/extract` recovers a netlist from
  `04_final.gds` that the comparator finds equivalent to `01_netlist.v`, on the
  one warm-up layout the repo ships. It is not a claim that extraction is
  correct in general, or that it will succeed unchanged on the (much larger)
  `puzzle.gds` — that is separate, embargoed work tracked elsewhere in this
  repo, not here.
- No claim at all is made about `puzzle.gds`. Nothing in this regression reads
  it (`CLAUDE.md` §1).
