# Upstream findings

`CLAUDE.md` §2: a defect or gap in `klt` is filed on
[`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools), not
worked around here quietly. This file is the local traceability record for
what has been filed.

| Gap (one line) | Upstream issue | Local linkage |
|---|---|---|
| `EXTRACTION_DECK.metals`/`vias` (sky130 deck) stop connectivity at met2 while `_ROUTING_LAYER_RANGE` promises `klt place-and-route` output may use met1–met5, and a routing layer outside the deck's connectivity is only an informational `ignored_layers` line, not a correctness warning | [2AMLogic/klayout-tools#619](https://github.com/2AMLogic/klayout-tools/issues/619) | Filed for #4. Blocks #1/#2/#3's device-level extraction from being connectivity-complete against a placed-and-routed sky130hd block; informs the reference implementation's need to collect conductors across the full met1–met5 stack itself. |
| `klt extract` has no cell-level (black-box + resolved pins) extraction mode — only flat, device-level output; `black_box_regions` excludes marked regions rather than abstracting them into pinned instances | [2AMLogic/klayout-tools#620](https://github.com/2AMLogic/klayout-tools/issues/620) | Filed for #4. Motivates #2's planned `tools/extract` reference implementation and the gate-level-LVS gap tracked in `2AMLogic/sky130-modexp#8`. |

Both issues are written toolkit-first: reproducers are `klt draw`/`klt
extract` (Issue 1) and a described input/output contract (Issue 2), built
entirely from `klt`'s own artefacts. Neither references this repository, the
puzzle, or any file under `puzzle/` — see `CLAUDE.md` §1.
