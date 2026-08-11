# Upstream findings

`CLAUDE.md` §2: a defect or gap in `klt` is filed on
[`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools), not
worked around here quietly. This file is the local traceability record for
what has been filed.

| Gap (one line) | Upstream issue | Local linkage |
|---|---|---|
| `EXTRACTION_DECK.metals`/`vias` (sky130 deck) stop connectivity at met2 while `_ROUTING_LAYER_RANGE` promises `klt place-and-route` output may use met1–met5, and a routing layer outside the deck's connectivity is only an informational `ignored_layers` line, not a correctness warning | [2AMLogic/klayout-tools#619](https://github.com/2AMLogic/klayout-tools/issues/619) | Filed for #4. Blocks #1/#2/#3's device-level extraction from being connectivity-complete against a placed-and-routed sky130hd block; informs the reference implementation's need to collect conductors across the full met1–met5 stack itself. |
| `klt extract` has no cell-level (black-box + resolved pins) extraction mode — only flat, device-level output; `black_box_regions` excludes marked regions rather than abstracting them into pinned instances | [2AMLogic/klayout-tools#620](https://github.com/2AMLogic/klayout-tools/issues/620) | Filed for #4. Motivates #2's planned `tools/extract` reference implementation and the gate-level-LVS gap tracked in `2AMLogic/sky130-modexp#8`. |
| `klt render` cannot select layer/datatype pairs or crop to a physical bounding box, so small features disappear at full-layout extent | [2AMLogic/klayout-tools#673](https://github.com/2AMLogic/klayout-tools/issues/673) | Found during the physical-layout inspection; the generic issue requests repeatable layer selection, a micrometre bbox, aspect preservation, and JSON extent reporting. |
| No generic command reports geometric connected components across a caller-selected conductor/via stack, including unnamed device-free islands | [2AMLogic/klayout-tools#674](https://github.com/2AMLogic/klayout-tools/issues/674) | Found while independently checking electrical isolation; the generic issue distinguishes projection overlap from via-mediated connectivity using a synthetic fixture. |
| `klt layers` lacks an instantiated/flattened shape-and-text census with physical extents and contributor attribution | [2AMLogic/klayout-tools#675](https://github.com/2AMLogic/klayout-tools/issues/675) | Found during the all-layer audit; the generic issue requests definition versus flattened counts, transformed bboxes, contributor counts, and optional text inventory. |

All issues are written toolkit-first, using generic contracts or synthetic
fixtures. None references this repository, the puzzle, or any file under
`puzzle/` — see `CLAUDE.md` §1.
