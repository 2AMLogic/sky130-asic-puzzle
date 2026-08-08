# sky130-asic-puzzle

**A reverse-engineering canary for [klayout-tools](https://github.com/2AMLogic/klayout-tools).**

Every other canary in the fleet extracts a layout that `klt` itself produced. That is a
closed loop: it cannot catch *"our extractor only understands our own output."* This repo
exists to break that loop by pointing the toolkit at a layout built by someone else's flow,
with objective ground truth to check the answer against.

The subject is Jane Street's 2026 ASIC reverse-engineering puzzle
([blog post](https://blog.janestreet.com/can-you-reverse-engineer-an-asic/),
[files](https://github.com/janestreet/asic-puzzle-2026)): a sky130 standard-cell design
distributed as GDSII with net and instance names stripped. The task is to recover the
gate-level netlist, work out what the circuit does, and simulate it.

---

## 🔒 Private until 2026-09-04

Jane Street asks solvers to **refrain from posting spoilers or a full writeup online until
submissions close on September 4th, 2026.**

This repository is **private**, which is how that request is honored: work proceeds normally
inside it — including the recovered netlist, the solve, and the answer — because a private
repo is not a public post. What is constrained is the *boundary*:

- **Do not make this repository public before 2026-09-04.** Visibility flips are operator-only
  across the fleet, and this one is also a commitment to a third party.
- **Do not post any of its content elsewhere** before that date — not in `marketing`, not on
  the site or the pulse, not in a public issue or PR on `klayout-tools`.

After submissions close, publishing is explicitly welcomed: Jane Street offers to link
solutions in a follow-up post. That is the moment this repo flips public and the writeup
in `evidence/` becomes the deliverable.

See [`CLAUDE.md`](CLAUDE.md) for how this binds agents.

---

## Why this design is a good test subject

Reconnaissance on `puzzle.gds` (1,421,700 bytes), before any solving:

| Property | Value |
|---|---|
| Top cell | `puzzle`, 200.0 × 352.7 µm |
| Total placed instances | 9,875 |
| — of which routing vias | 8,214 |
| — tap / decap fill | 880 |
| **Logic + sequential cells** | **~781** |
| Flip-flops | **92** (84 `dfrtp_2`, 4 `dfstp_2`, 4 `dfxtp_2`) |
| Distinct library cells | 69, all `sky130_fd_sc_hd` |
| Polygons / vertices | 14,638 / 65,898 |

**Cell identity is not the hard part.** All 69 standard cells retain their full
`sky130_fd_sc_hd__*` names *including drive strength*. What was stripped is net and instance
names. So the puzzle is a **connectivity** problem, not a pattern-recognition problem — and
connectivity extraction from a placed-and-routed layout is exactly the capability under test.

## The capability gap this exercises

`klt extract` produces a **device-level** SPICE netlist — transistors and nets. This puzzle
needs **cell-level** extraction: treat each standard cell as a black box with known pins,
trace nets through `li1`/`met1`–`met5` and the via cells, and emit a gate-level Verilog
netlist.

That is the same capability required to run **LVS against a synthesized Verilog netlist**,
a seam flagged as possibly unwired in
[`2AMLogic/sky130-modexp#8`](https://github.com/2AMLogic/sky130-modexp/issues/8). Closing the
gap here closes it there. Findings against the toolkit are filed **upstream on
`klayout-tools`**, not here; this repo holds the harness and the evidence.

Two gaps behind this are filed upstream, toolkit-first, with `klt`-only reproducers:

- [`2AMLogic/klayout-tools#619`](https://github.com/2AMLogic/klayout-tools/issues/619) —
  the sky130 extraction deck's connectivity stack (`metals`/`vias`) stops at met2 while
  `klt place-and-route`'s own `_ROUTING_LAYER_RANGE` promises met1–met5, so nets joined
  above met2 extract as separate nets, silently.
- [`2AMLogic/klayout-tools#620`](https://github.com/2AMLogic/klayout-tools/issues/620) —
  `klt extract` has no cell-level (black-box + resolved pins) extraction mode to emit a
  hierarchical or gate-level netlist; it is flat and device-level only.

See [`evidence/upstream.md`](evidence/upstream.md) for the full traceability record.

## Ground truth

The puzzle ships a warm-up that is close to an ideal regression fixture — the same design at
every stage of the flow:

| File | Role |
|---|---|
| `warmup/00_source.v` | original Verilog |
| `warmup/01_netlist.v` | synthesized gate-level netlist — **the expected output** |
| `warmup/02_netlist_with_power_rails.v` | with VDD/GND |
| `warmup/03_post_place_and_route.def` | placement + routing |
| `warmup/04_final.gds` | final layout — **the input** |

So `04_final.gds → extract → compare against 01_netlist.v` is an objective pass/fail test,
independent of whether the real puzzle is ever solved. That test is the primary deliverable
and it is **not** embargoed — it is tooling, and the warm-up is published by Jane Street as a
worked example.

## The puzzle files are not vendored

`janestreet/asic-puzzle-2026` carries **no license**, so its files are not copied into this
repository. Fetch them locally:

```sh
./scripts/fetch-puzzle.sh      # clones upstream into puzzle/ (gitignored)
```

## Layout

```
spec/       what "solved" means, and the staged plan
tools/      extraction / recognition / solving harness
scripts/    fetch + embargo check
evidence/   extraction results, simulation logs, the solve, the writeup draft
puzzle/     upstream files, gitignored, never committed
```

## Status

Just opened. Nothing extracted yet.
