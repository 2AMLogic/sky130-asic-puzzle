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

## 🔓 Private until 2026-09-04 — lifted

**Lifted.** Submissions closed 2026-09-04 and this repository is public (verified against the
GitHub API 2026-09-08). The section below is kept as the record of why it stayed dark; see
[Other solutions](#other-solutions) for what has been published since.


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

Reconnaissance on `puzzle.gds` (1,421,700 bytes), before any solving — reproduced from the
stream itself by `tools/inventory` (`evidence/inventory-puzzle.json`; see `tools/README.md`
for how, and CLAUDE.md §4 for why this is the priority):

| Property | Value |
|---|---|
| Top cell | `puzzle`, 200.0 × 352.7 µm |
| Total placed instances | 9,875 |
| — of which routing vias (`VIA_*`) | 8,221 |
| — tap / decap fill | 880 |
| — unclassified (`INTERNAL_3`/`INTERNAL_7`, see below) | 36 |
| **Logic + sequential cells** | **738** |
| Flip-flops | **92** (84 `dfrtp_2`, 4 `dfstp_2`, 4 `dfxtp_2`) |
| Distinct library cells | 69, all `sky130_fd_sc_hd` |
| Polygons / vertices | 14,638 / 65,898 |
| Top-level ports | `I O[0..7] clk enable rst_n success` — matches `example_inputs.vcd`'s declared variables |

`INTERNAL_3`/`INTERNAL_7` (36 instances total) are single unlabelled shapes on a layer no
other cell uses, sized to the standard-cell row height — neither a `VIA_*` routing cell nor a
`sky130_fd_sc_hd__*` library cell, so `tools/inventory` reports them by name in an `other`
bucket rather than guessing which bucket they belong in. (An earlier version of this table
carried 8,214 vias and "~781" logic+sequential, derived by subtraction before these 36
instances were accounted for; the numbers above are what the stream itself says and supersede
it — see `tools/README.md`.)

The warm-up (`warmup/04_final.gds`, 27 cells) reproduces the same way: 1,099 top-level
instances, 79 logic+sequential cells, 93 `sky130_fd_sc_hd__tapvpwrvgnd_1`, 58
`sky130_fd_sc_hd__decap_3`, top-level ports `A B S clk en rst_n`
(`evidence/inventory-warmup.json`).

**Pin geometry, not just cell identity, survives too.** All 69 standard cells retain their full
`sky130_fd_sc_hd__*` names *including drive strength*, and (per `tools/README.md`) every
cell's pins are directly readable from GDS text-label layers — no PDK needed. What was
stripped is net and instance names. So the puzzle is a **connectivity** problem, not a
pattern-recognition or pin-geometry problem — and connectivity extraction from a
placed-and-routed layout is exactly the capability under test.

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

**Solved and submitted.** The answer is `(* TWO STARS *)`, emitted after a unique 121-bit
word drives `success` (`evidence/puzzle-solve.md`, `evidence/puzzle-answer.md`); the form
went in 2026-08-10 (`SUBMISSION.md`). The chip is a two-star Star Battle verifier whose
11 regions were withheld and recovered from the circuit (`evidence/easter-eggs.md`).

Stage 4 (`tools/extract`, see `tools/README.md`) is done: `warmup/04_final.gds`
extracts to a gate-level netlist that `tools/compare` reports **equivalent** to
`warmup/01_netlist.v` — the primary regression fixture (`CLAUDE.md` §4) is green.
`puzzle.gds` extracts too (738 logic+sequential instances, 92 flip-flops); its
result has no published ground truth to compare against yet — see
`evidence/extraction-notes.md`.

## Other solutions

Submissions closed 2026-09-04 and writeups are appearing. Ours is the evidence trail in
`evidence/`; these are the others found so far (add to this table as more surface). Every
one that states an answer agrees with ours — `(* TWO STARS *)` from the same 121-bit word.
Two presentation traps when comparing: Jagadeesh's bitstring is the same word printed
MSB-first (his grid, not his string, is in feed order), and Dan Xie's has a trailing 122nd
cycle bit.

| Writeup | Extraction | Solve | Eggs reported |
|---|---|---|---|
| [Jagadeesh Mummana](https://mummanajagadeesh.github.io/blogs/janestreet-asic-puzzle/) | gdstk + shapely polygon union, pins from the PDK macro LEF | SymbiYosys `cover(success)` on bitwuzla, ~105 s; uniqueness by blocking the witness → UNSAT | VCD header hint and leap-second timestamp; Morse strip; regions read as "JS"; `TWO NOT TOUCH` |
| [Dan Xie, SemiWiki](https://semiwiki.com/forum/threads/25827) (2026-09-04) | KLayout LVS deck → transistor-level SPICE → structural Verilog (with Claude) | Z3 bounded model checking over all 92 flops; proves `success` cannot assert before cycle 122 | `EMPTY SKY` / `BIG BANG` / `TRY AGAIN`; layer 200/0 Morse |
| [Kjartan van Driel & Leander Post](https://kjartanvandriel.github.io/asic/) | li1/metal tracing from pin labels, own cycle simulator | block-by-block inference; region map read directly from the 4-wire lookup table | Morse; region patches of 4–28 cells "with rather odd outlines" |
| [jestoph](https://jestoph.com/2026/09/04/jane-street-challenge.html) (2026-09-04, [code](https://github.com/jestoph/jane-street-puzzle)) | gdstk, own connectivity extraction and simulator | Z3 constraints per hand-mapped subcircuit | `EMPTY SKY` / `BIG BANG` / `TRY AGAIN`; **reported the undriven net to Jane Street, who confirmed it as a design bug** |
| [Sunaabh](https://sunaabh.com/systems/2026/08/18/jspuzzle.html) (2026-08-18) | KLayout Python API → IR → Verilog, Yosys | Yosys `sat -seq 140 -set-at 125 success 1` | four ROM messages including `TWO NOT TOUCH`; the Jane Street logo on met2 |
| [Hacker News thread](https://news.ycombinator.com/item?id=49200933) | — | — | a 30-year chip designer reports solving it in ~6 hours with KLayout, Surfer and Icarus; no writeup |

Jane Street's promised follow-up post had not appeared on their blog as of 2026-09-08.

## What the other solutions taught us

Corrections to our own record. Each was verified here before being written down
(`CLAUDE.md` §5); the original evidence files are append-only, so the corrections live in
addenda there and are summarised here.

1. **The fifth message is `TWO NOT TOUCH`, not `TWO"NOT TOUCH`.** The ditto mark was an
   artifact. `net_00575` is the extracted netlist's one undriven net; the cycle model fills
   undriven nets with a constant, and the 0x22 byte is what that constant produces. Icarus,
   which leaves the net `x`, reports bit `O[1]` as `x` at exactly that byte — and again at
   three cycles around the final `H`. The 2026-08-11 addendum attributed those `x` cycles to
   the unresettable flops; they are the floating net. jestoph reported the same net as a bug
   and Jane Street confirmed it, so on silicon the byte is undefined and the intended text,
   as Sunaabh read it from the ROM, is `TWO NOT TOUCH`. Reproducer:
   `evidence/easter-egg-floating-net-ditto.py`. The draft supplement email in
   `SUBMISSION.md` was never sent; do not send it as written.
2. **The met2 glyph is the Jane Street logo.** Three concentric broken rings with rotating
   gaps is Jane Street's registered concentric-circle mark. We recorded it faithfully
   (`evidence/easter-egg-met2-ring.svg`) and misread it as a maze or a record. Sunaabh and
   jestoph both recognised it on sight.
3. **We never read the VCD header.** `example_inputs.vcd` opens with
   `$date Sat Dec 31 23:59:60 2016` — the 2016 leap second, a timestamp that existed for
   one second — and `$version Leave no stone unturned! But for this file, consider looking
   at it in a waveform viewer instead.` Jagadeesh ties the date to Jane Street's December
   2016 puzzle "Star Search" and calls it a Star Battle variant; Jane Street's own solution
   page says that puzzle was movie trivia (answer: *Inception*), so read the link as a pun on
   "star", not as a rules reference.
4. **The regions may spell "JS".** We recovered the region map structurally and never looked
   at it as a picture — the exact mistake Lead 1 of `EASTER-EGG-HUNT.md` warned about.
   Rendered (`evidence/region-map.png`, from `evidence/region-map-render.py`), region G is an
   unmistakable block-letter S and region A reads as a J (bar, stem, hook) wrapped around
   it. Jagadeesh reads the whole map as "JS"; we would call the S certain and the J
   plausible.

Things in our record that no other writeup so far contains: the complete message map,
*proven* — exactly two failure streams exist besides the three constant ones — the
31,197,434-grid enumeration showing that the withheld regions are what make the answer
unique, and the SAT-independent uniqueness check from the recovered rules alone.
