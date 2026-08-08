# Warm-up simulation: `A + B == 496`

Stage 5 of `spec/puzzle.md`: calibrate `tools/sim` against the warm-up before
it is ever pointed at the puzzle. `warmup/00_source.v` says the design
asserts `S` when `A + B == 496` after shifting eight bits (MSB first) into
each of two 8-bit shift registers. This is a directed test against
`warmup/01_netlist.v` — not a re-derivation from it: every `expected_s` value
below is computed in Python from the case's `(a, b)` pair
(`tools/sim/directed.py::default_cases`), independent of what the netlist
actually does.

This content is not embargoed — `warmup/` is published by Jane Street and
CLAUDE.md §4 designates the warm-up regression as not subject to the
embargo.

## Model provenance

Every simulation run below used:

```
PDK variant: sky130A
PDK version: open_pdks c6d73a35f524070e85faff4a6a9eef49553ebc2b
Resolved via: klt pdk find --pdk sky130A (root: ~/.volare)
Model files:
  <PDK root>/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  <PDK root>/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
```

Resolved by `tools/sim/pdk.py::resolve_sky130_models()`. See
`tools/README.md` for the resolution order and what to do if this fails on a
different machine — `klt pdk find --pdk sky130A` resolved a **local volare
install** at the time this was run; that install location is a fact about
this workstation, not something pinned in the repo (CLAUDE.md §3's fetch-not-
vendor habit).

Simulator: Icarus Verilog version 13.0 (stable) (v13_0), invoked via
`tools/sim/icarus.py` with `-g2005 -D FUNCTIONAL -D UNIT_DELAY=#1` (functional
simulation models, no power-pin ports — matching how `warmup/01_netlist.v`
instantiates cells, i.e. without VPWR/VGND wired).

## Command

```sh
python3 -m tools.sim.run_warmup_directed \
    --netlist puzzle/warmup/01_netlist.v \
    --random 50 --seed 496
```

`--random 50` adds 50 additional randomized `(A, B)` pairs (seeded, so this
exact command reproduces the exact case list below) on top of ten fixed
directed cases: four combinations summing to exactly 496, four near-misses
(495 and 497, from two different `(A, B)` pairs each), and the `A=B=0` /
`A=B=255` boundary cases.

## Result

```
PDK variant: sky130A
PDK version: open_pdks c6d73a35f524070e85faff4a6a9eef49553ebc2b
Resolved via: klt pdk find --pdk sky130A (root: /Users/rwalters/.volare)
Model files:
  /Users/rwalters/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  /Users/rwalters/.volare/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

OK        exact-248-248    a=248 b=248 expected_s=1 got_s=True
OK        exact-255-241    a=255 b=241 expected_s=1 got_s=True
OK        exact-241-255    a=241 b=255 expected_s=1 got_s=True
OK        exact-250-246    a=250 b=246 expected_s=1 got_s=True
OK        near-miss-495    a=255 b=240 expected_s=0 got_s=False
OK        near-miss-497    a=255 b=242 expected_s=0 got_s=False
OK        near-miss-495b   a=248 b=247 expected_s=0 got_s=False
OK        near-miss-497b   a=248 b=249 expected_s=0 got_s=False
OK        zero             a=  0 b=  0 expected_s=0 got_s=False
OK        max              a=255 b=255 expected_s=0 got_s=False
OK        random-0         a=231 b=193 expected_s=0 got_s=False
OK        random-1         a= 62 b=162 expected_s=0 got_s=False
OK        random-2         a=123 b= 91 expected_s=0 got_s=False
OK        random-3         a=112 b= 73 expected_s=0 got_s=False
OK        random-4         a=164 b=192 expected_s=0 got_s=False
OK        random-5         a=219 b= 22 expected_s=0 got_s=False
OK        random-6         a=116 b= 55 expected_s=0 got_s=False
OK        random-7         a=147 b= 89 expected_s=0 got_s=False
OK        random-8         a=119 b=112 expected_s=0 got_s=False
OK        random-9         a= 82 b=158 expected_s=0 got_s=False
OK        random-10        a= 95 b=108 expected_s=0 got_s=False
OK        random-11        a=113 b=133 expected_s=0 got_s=False
OK        random-12        a=234 b=199 expected_s=0 got_s=False
OK        random-13        a= 66 b=204 expected_s=0 got_s=False
OK        random-14        a= 65 b=112 expected_s=0 got_s=False
OK        random-15        a=253 b= 22 expected_s=0 got_s=False
OK        random-16        a=140 b= 75 expected_s=0 got_s=False
OK        random-17        a= 54 b=214 expected_s=0 got_s=False
OK        random-18        a= 73 b=106 expected_s=0 got_s=False
OK        random-19        a=212 b=217 expected_s=0 got_s=False
OK        random-20        a= 14 b=138 expected_s=0 got_s=False
OK        random-21        a=108 b= 79 expected_s=0 got_s=False
OK        random-22        a=236 b= 14 expected_s=0 got_s=False
OK        random-23        a= 92 b=189 expected_s=0 got_s=False
OK        random-24        a= 43 b=  7 expected_s=0 got_s=False
OK        random-25        a=197 b=133 expected_s=0 got_s=False
OK        random-26        a= 86 b=220 expected_s=0 got_s=False
OK        random-27        a= 19 b=200 expected_s=0 got_s=False
OK        random-28        a=185 b=194 expected_s=0 got_s=False
OK        random-29        a=180 b= 36 expected_s=0 got_s=False
OK        random-30        a=190 b=183 expected_s=0 got_s=False
OK        random-31        a= 83 b=185 expected_s=0 got_s=False
OK        random-32        a=233 b= 96 expected_s=0 got_s=False
OK        random-33        a=236 b=143 expected_s=0 got_s=False
OK        random-34        a= 95 b= 76 expected_s=0 got_s=False
OK        random-35        a=  0 b=231 expected_s=0 got_s=False
OK        random-36        a=225 b=229 expected_s=0 got_s=False
OK        random-37        a=130 b= 24 expected_s=0 got_s=False
OK        random-38        a=154 b= 94 expected_s=0 got_s=False
OK        random-39        a= 84 b=152 expected_s=0 got_s=False
OK        random-40        a= 29 b= 13 expected_s=0 got_s=False
OK        random-41        a= 15 b=101 expected_s=0 got_s=False
OK        random-42        a= 81 b=101 expected_s=0 got_s=False
OK        random-43        a=118 b=141 expected_s=0 got_s=False
OK        random-44        a=100 b= 79 expected_s=0 got_s=False
OK        random-45        a=122 b=197 expected_s=0 got_s=False
OK        random-46        a=145 b= 50 expected_s=0 got_s=False
OK        random-47        a=114 b=  7 expected_s=0 got_s=False
OK        random-48        a=137 b=246 expected_s=0 got_s=False
OK        random-49        a= 15 b= 32 expected_s=0 got_s=False

RESULT PASS (60 cases)
```

All 60 cases matched their Python-computed oracle (`(a + b) == 496`) —
`S` asserts on every exact-496 case and stays low on every near-miss (495,
497) and every random pair, `exit 0`.

## Replay-engine self-test (not a formal acceptance criterion, extra confidence)

`tools/sim/replay.py` implements the general VCD-replay path stage 6 needs,
but this repo's only recorded VCD (`puzzle/example_inputs.vcd`) is for the
puzzle, and there is no extracted puzzle netlist yet (blocked on #2; see
`evidence/puzzle-replay.md`). So the replay engine has instead been
self-tested against the warm-up, exercising the exact reader ->
testbench-generation -> simulate -> diff path without touching embargoed
content:

```sh
python3 -m tools.sim.selftest_replay
```

```
== recording a directed warm-up VCD (this is the 'recorded' trace for the self-test) ==
recorded: <repo>/.sim-work/selftest/recorded.vcd

== replaying the recording back against the same netlist (expect zero divergence) ==
ok=True compared_through=470000

== replaying a corrupted recording (expect a reported divergence) ==
ok=False compared_through=470000
reported divergence: t=341000 signal=S expected=1 actual=0
expected divergence at t=341000 signal=S: MATCH

SELF-TEST PASS
```

Step 1 records a VCD from a directed multi-case warm-up simulation. Step 2
replays it back against the same netlist and confirms zero divergence. Step
3 flips one recorded output bit at one timestamp and confirms the engine
reports exactly that `(time, signal)` as the first divergence — a
self-test that couldn't detect an injected mismatch would be worse than no
self-test at all.

## PDK-resolver self-test (acceptance criterion 4: missing models fail loudly)

Issue #5 requires that a missing model set produces one actionable install
instruction and a non-zero exit, never a silent skip. That path cannot be
exercised on this workstation as it stands — a sky130A install resolves here
via `klt pdk find` (see "Model provenance" above) — so it is covered by a
committed self-test that pins all three sources in the documented search
order (`klt` on `PATH`, `$PDK_ROOT`, `~/.volare`) at controlled temporary
directories. It needs no PDK, no `klt` and no simulator, so it runs
identically on a machine with a PDK and on one without:

```sh
python3 -m tools.sim.selftest_pdk
```

```
== tools/sim/pdk.py resolution-order self-test (all three sources mocked) ==
[PASS] no PDK anywhere -> PdkResolutionError carrying the install hint
         raised PdkResolutionError; message is INSTALL_HINT with install instructions: True
[PASS] klt present but exits non-zero -> falls through, still fails loudly
         klt failure fell through to PdkResolutionError
[PASS] klt emits unparseable JSON -> falls through, no leaked JSONDecodeError
         unparseable klt output fell through to PdkResolutionError
[PASS] partial install (no sky130_fd_sc_hd.v) -> rejected, not half-resolved
         partial install rejected; PdkResolutionError raised
[PASS] [control] complete $PDK_ROOT install -> resolves via $PDK_ROOT
         resolved via '$PDK_ROOT (<tmp>/pdk-root)'
[PASS] [control] complete ~/.volare install -> resolves via ~/.volare
         resolved via '~/.volare (<tmp>/volare-home/.volare)'
[PASS] [control] klt-reported install -> resolves via klt, ahead of $PDK_ROOT
         resolved via 'klt pdk find --pdk sky130A (root: <tmp>/klt-root)' (version 0.0.0-selftest)

SELF-TEST PASS (7/7 checks passed)
```

(The three `[control]` lines' `<tmp>` paths are the per-check
`tempfile.TemporaryDirectory()` roots; they differ run to run. Everything
else is byte-for-byte reproducible.)

The three positive controls are there so the failure checks cannot pass
vacuously — a harness that never finds a PDK would make "raises when there
is no PDK" true for the wrong reason. The suite was also checked against a
deliberately broken resolver (one returning a fabricated `ResolvedModels`
instead of raising): all 7 checks fail and the run exits 1, including the
`no PDK anywhere` check reporting `NO exception raised — silently returned
'fabricated'`. A test that cannot fail is not evidence (CLAUDE.md §5).

## What this does not cover yet

Acceptance criterion 2 from issue #5 — the same directed-test harness run on
`evidence/warmup-extracted.v`, agreeing with `01_netlist.v` cycle-for-cycle
over >=1,000 cycles of shared randomized stimulus — is blocked on #2
(cell-level extraction) and is **not** covered here. `run_directed_test()`
in `tools/sim/directed.py` already accepts an arbitrary list of netlist
files, so once `evidence/warmup-extracted.v` exists this is pointing the
same CLI at it and comparing against a Python model of `01_netlist.v`'s
behaviour (or running both netlists side by side and diffing their `S`
traces directly) — no new simulation machinery, just a new invocation.
