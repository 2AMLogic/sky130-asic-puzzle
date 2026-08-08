# tools/

Extraction, recognition, and simulation harness for this repo (see
`spec/puzzle.md` for the staged plan this implements against).

## `tools/vcd` — minimal VCD reader/writer

`tools/vcd/reader.py` / `tools/vcd/writer.py` parse and emit the subset of
IEEE 1364 VCD this repo needs: `$timescale`, `$scope`/`$var`/`$upscope`,
and `$dumpvars`/value-change sections with scalar and vector values. It is
deliberately not a general-purpose VCD library — the format is small enough
that a dependency is optional here, not required (see the module docstrings
in `tools/vcd/model.py`). Round-trips `puzzle/example_inputs.vcd` losslessly
(same signal histories in, same signal histories out).

## `tools/sim` — simulation harness

Builds on `tools/vcd` plus [Icarus Verilog](http://iverilog.icarus.com/)
(`iverilog`/`vvp`) to simulate gate-level `sky130_fd_sc_hd` netlists —
Icarus is what `klt functional-verification` already targets alongside
Verilator, and is sufficient for this repo's 92-flop scale.

| Module | Role |
|---|---|
| `tools/sim/pdk.py` | resolves `sky130_fd_sc_hd`'s behavioural Verilog models (see below) |
| `tools/sim/icarus.py` | thin `iverilog`/`vvp` wrapper with the compile defines the models need |
| `tools/sim/testbench.py` | generates directed-test and VCD-replay Verilog testbenches |
| `tools/sim/directed.py` | the `A + B == 496` directed test (stage 5) |
| `tools/sim/replay.py` | general VCD replay + trace diff (stage 6) |
| `tools/sim/selftest_replay.py` | self-tests `replay.py` against the warm-up (see `evidence/warmup-sim.md`) |
| `tools/sim/run_warmup_directed.py` | CLI for the directed warm-up test |
| `tools/sim/run_vcd_replay.py` | CLI for general VCD replay |

### Where the behavioural models come from, and how to install them

Simulating a `sky130_fd_sc_hd` netlist needs the standard-cell library's
behavioural Verilog (`sky130_fd_sc_hd.v` + its UDP primitives,
`primitives.v`) — genuinely external content, unlike the pin geometry the
KLayout tech stream carries. It is **not vendored** here: the sky130 PDK is
Apache-2.0, so vendoring would be permissible, but `CLAUDE.md` §3's fetch-
rather-than-vendor habit is the right default for this too, and a resolver
keeps the repo small and always current with whatever install is actually on
the machine.

`tools/sim/pdk.py::resolve_sky130_models()` resolves it, in order:

1. `klt pdk find --pdk sky130A --format json` — klayout-tools' own PDK
   resolver (its documented search order: `$PDK`/`$PDK_ROOT`, then
   well-known install roots including `~/.volare`), if `klt` is on `PATH`.
2. `$PDK_ROOT/sky130A/...` directly, if `klt` is unavailable or its
   resolution doesn't include a verilog dir.
3. `~/.volare/sky130A/...` directly, matching volare's default install
   location, as a last resort.

If none of these find both `primitives.v` and `sky130_fd_sc_hd.v`,
resolution fails with **one actionable line** and a non-zero exit — never a
silent skip or a green run against an empty model set:

```
No resolvable sky130 PDK found (looked for sky130_fd_sc_hd's behavioural
Verilog via `klt pdk find --pdk sky130A`, $PDK_ROOT, and ~/.volare). Install
one with volare: `pip install volare && volare enable
$(volare ls-remote sky130 --limit 1 -f '{version}')`, or point $PDK_ROOT at
an existing open_pdks sky130A install, then re-run.
```

Every evidence record this harness produces states which of the three
sources resolved, plus the PDK version and the exact model file paths used
(`ResolvedModels.describe()`) — a simulation whose model provenance is
unstated is not re-runnable (CLAUDE.md §5).

### Compile-time defines

`sky130_fd_sc_hd.v` selects among functional/timing and power-pin/no-power-
pin model variants via `` `ifdef ``. `tools/sim/icarus.py` always compiles
with:

- `FUNCTIONAL` defined — picks the simulation functional model, not the
  SDF-timing-oriented one (no setup/hold checks to violate at zero-delay).
- `USE_POWER_PINS` left **undefined** — this repo's netlists (both
  `warmup/01_netlist.v` and, once it exists, an extracted netlist) don't
  wire `VPWR`/`VGND`/`VPB`/`VNB` explicitly, so the port list without those
  pins is the one that matches.
- `UNIT_DELAY=#1` — the primitive instantiations inside the models
  (`` `UNIT_DELAY dff0 (...) ``) need this macro defined to compile at all;
  `#1` avoids zero-delay races without materially affecting a cycle-level
  functional check.

### Usage

Directed warm-up test (stage 5, no VCD or extractor needed):

```sh
python3 -m tools.sim.run_warmup_directed \
    --netlist puzzle/warmup/01_netlist.v \
    --random 50
```

VCD replay (stage 6, needs an extracted netlist):

```sh
python3 -m tools.sim.run_vcd_replay \
    --netlist <extracted-netlist.v> \
    --vcd puzzle/example_inputs.vcd \
    --top <top-module> \
    --inputs clk,rst_n,enable,I \
    --outputs O,success
```

Replay-engine self-test (exercises the full VCD replay path against the
warm-up, with no dependency on an extractor):

```sh
python3 -m tools.sim.selftest_replay
```

See `evidence/warmup-sim.md` and `evidence/puzzle-replay.md` for recorded
results and current status.
