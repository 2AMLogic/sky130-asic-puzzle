# Puzzle `klt lvs` — recorded run (append-only)

`CLAUDE.md` §5: this is what was actually executed. Re-run it with
`./scripts/puzzle-klt-lvs.sh` (needs `puzzle/`, fetched by
`./scripts/fetch-puzzle.sh`, and a sky130 PDK).

This is scope item 3 of #47, the one item `evidence/warmup-klt-lvs.md`'s
closing "Not done" line left unrun. Unlike the warm-up (`evidence/warmup-klt-lvs.md`)
there is no published ground truth here: the reference, `evidence/puzzle-extracted.v`,
was extracted from the same GDS by this repository's own `tools/extract`. So a
match is **self-consistency between two independent readers of one layout**, not
a correctness proof of either. What it buys is scale and shape the 79-cell
warm-up cannot reach — 1,618 instances over 69 cell types, the full met1–met5
routing stack, 13 top-level pins taken from in-GDS labels rather than a DEF, and
one net that is known to be undriven.

Nothing is elided. The warm-up record elides reference-side names because its
reference is the unlicensed upstream `01_netlist.v`; here the reference is our
own committed file and the layout-side names are already in it. The extracted
layout netlist stays in `build/` (gitignored) — it is derived from a file that
carries no license (`CLAUDE.md` §3).

## Run 1 — 2026-11-14

Environment: Linux (AWS dispatch worker), `klt 0.9.2.dev1025+ga90545db9ea6`,
klayout 0.30.13, PDK `sky130A` (open_pdks `f6eeac7dad08…`, found under
`~/.ciel`). klayout-tools commit `a90545db9ea6a2a464259b315572ca06e4bff3c8`
(from the envelope's `provenance`). `klt` warns on every compare that 0.30.13 is
not the klayout it was tested against (0.30.12) and that report *counts* may
differ; `provenance.klayout_version_mismatch` is `true` in the envelope. The
verdict is unaffected, and the verdict is what is recorded below.

**Two `klt` builds are named below, deliberately.** The host tool is provisioned
fleet-wide and it bumped mid-session, from `0.9.2.dev1024+g8da9718f0cb6`
(`8da9718f0cb6…`) to the `dev1025` above. The upstream isolation — the
five-variant table and the two direct-call site probes — was done on `dev1024`,
and that is the build the upstream issue's "Environment" names; the artifacts
and every number in this record come from a clean re-run on `dev1025`. The two
agree exactly: identical counts, identical verdicts, the same verbatim stage-2
error, and the cited `verilog_netlist.py` lines (180, 200, 350, 366, 405, 411)
unmoved. So the finding is not an artifact of either build.

Both are past the `0.9.2.dev1022+g2a9c52b27ce7` build
`evidence/warmup-klt-lvs.md` Run 2 names as carrying the klayout-tools#3748 and
#3749 fixes. Both fixes are still in.

**Headline: the compare against the committed reference never ran.** `klt lvs`
refuses to read `evidence/puzzle-extracted.v` as a `gate-level-verilog`
reference and exits 1 before any compare, so there is no `status`, no
`power_connectivity.status`, and no envelope. That is a toolkit defect, now
filed as klayout-tools#5693; it is not worked around in any committed path
(`CLAUDE.md` §2), exactly as `evidence/warmup-klt-lvs.md` Run 2 left
klayout-tools#5631 red and reported. The measurement the run was for comes from
the isolating probe below, which differs from the refused request in the port
*spelling* alone.

### Commands (as scripted, `scripts/puzzle-klt-lvs.sh`)

```
klt extract puzzle/puzzle.gds --deck sky130 --pdk sky130A --top puzzle \
  --abstract-cells 'sky130_fd_sc_hd__*' \
  --abstract-cell-lef <libs_ref>/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef \
  -o build/puzzle-klt-lvs.spice --format json
klt lvs - --format json   # request on stdin, once per reference below
  # {"layout": {"netlist": "build/puzzle-klt-lvs.spice", "top": "puzzle"},
  #  "reference": {"netlist": "<ref>", "top": "puzzle",
  #                "form": "gate-level-verilog", "library": "sky130_fd_sc_hd",
  #                "pdk": "sky130A"}}
```

No `--def-pins`: upstream ships no DEF for the puzzle (`scripts/fetch-puzzle.sh`
checks only `warmup/03_post_place_and_route.def`), so the top-level pins come
from in-GDS labels. `--abstract-cell-lef` is passed so this script extracts
identically to the warm-up one and the klayout-tools#3749 fix engages; it is not
strictly needed for a signal-only reference. The request goes in on stdin so
every path is relative to the repo root — the base `klt lvs --check` resolves
against when re-run from there.

### Extraction — succeeded

`status: extracted`, 869 nets, 16 pins, **1,618 abstracted instances over 69
cell types, 0 extracted devices** (everything is a black box, as intended).

The 16 layout pins are `I O[0] O[1] O[2] O[3] O[4] O[5] O[6] O[7] VGND VPWR clk
enable rst_n success vsubs` — the 13 signal pins the reference also declares,
plus `VGND`/`VPWR` and the deck's synthesized substrate global `vsubs`. The
reference is signal-only (no `VPWR`/`VGND` ports), so this is the warm-up's
matching `01` shape, not its mismatching `02` shape, and the extra three pins are
expected to sit outside the compare rather than break it.

68 of the 69 cell types record a `lef_path`; the exception is
`sky130_fd_sc_hd__tapvpwrvgnd_1`, whose two pins the in-cell labels already
supplied, so nothing was merged into it. Identical to the warm-up's Run 2
behaviour.

Instance mix, from `build/puzzle-klt-lvs-extract.json`: 676
`tapvpwrvgnd_1` + 204 `decap_3` + 84 `dfrtp_2` + 49 `nor2_2` + 39 `nand2_2` +
31 `o21a_2` + the remaining 63 cell types, 1,618 in total. That agrees with
`evidence/puzzle-extracted.v`'s own 1,618 instances.

Four extraction advisories, all expected, none a finding:

- **696 instances resolved two separately declared pins onto one net**, every
  grouping being `pins VPB, VPWR -> net 'VPWR'`. Not `VGND, VNB`. The warm-up's
  Run 2 saw the same shape, and saw it identically with the LEF flag omitted, so
  it is not a consequence of the merge.
- **3,189 routing-stack clusters (4,972 shapes on 67/20, 67/44, 68/20, 69/20)
  join no extracted net** — dead metal. This layout is known to carry
  deliberate artwork on the met layers (`evidence/easter-eggs.md`,
  `evidence/independent-review-addendum-met2.py`), so unreferenced metal is the
  expected finding here, not a missing connection.
- **15 layers carrying 1,255 shapes are outside the `sky130` deck's
  connectivity graph** (64/16, 64/59, 66/15, 67/16, 68/16, 70/16, 71/16, 72/16,
  81/4, 83/44, 95/20, 122/16, **200/0**, 235/4, 236/0). 200/0 is where the
  `INTERNAL_3`/`INTERNAL_7` artwork sits. This is the informational
  `ignored_layers` advisory klayout-tools#619 is about, already filed.
- **Two declared MOS flavours (`hvi` 75/20, `lvt` 125/44) have no shapes.**
  Vacuous at `device_count: 0`.

### Stage 2 — `evidence/puzzle-extracted.v` as committed: no report produced

`klt lvs` exits **1** and writes an error envelope instead of a report. Verbatim
(`error.message` from the JSON on stdout):

```
could not convert gate-level-verilog reference netlist
'<repo>/evidence/puzzle-extracted.v' to plain-element form: 'module puzzle' port
list entry '\\O[0]' is not a plain port name -- ANSI-style inline port
declarations ('module name(input a, output b);') are not supported, only
'module name(a, b); input a; output b;'
```

**No report was produced**, so there is no `status`, no
`power_connectivity.status`, no `body_verification.status`, no mismatch counts,
and no `evidence/puzzle-klt-lvs-01.json`. The script writes the envelope under
`build/` first and installs it into `evidence/` only when a verdict exists,
precisely so a refused run leaves no zero-byte placeholder in the committed
tree.

`evidence/puzzle-extracted.v` declares its eight output bits as eight escaped
scalar ports `\O[0] … \O[7] ` (lines 2–9 and 15–22), which is the form
`tools/verilog_netlist.py` emits. The reader rejects any port-list entry whose
name contains a bracket. The error text also misattributes the cause: the file
uses exactly the non-ANSI style the message says *is* supported.

The warm-up could never have surfaced this — its references' ports are plain
scalars (`A B S VGND VPWR clk en rst_n`). Reaching it needed a reference with a
bit-blasted bus port, which is what this one has.

**Filed upstream as
[klayout-tools#5693](https://github.com/2AMLogic/klayout-tools/issues/5693)**;
see "Upstream finding" below for the isolation.

### Stage 1 — the isolating probe: `match`

A `build/`-only reference derived from `evidence/puzzle-extracted.v` by the one
change the reader objects to: the eight `\O[N] ` escaped scalar ports become a
single `output [7:0] O;` bus, and the eight `.X(\O[N] )` body connections become
`.X(O[N])`. Everything else — all 1,618 instances, all 726 internal wires, the
other five ports — is byte-identical, and the request (layout, top, form,
library, PDK) is the same one stage 2 uses. So whatever stage 2's error is, it is
attributable to the port spelling alone, and the rest of the compare is measured
here.

**This is a probe, not a deliverable.** It lives in
`build/puzzle-klt-lvs-busport.v` and `build/puzzle-klt-lvs-probe.json`, both
gitignored; nothing committed depends on it, and it is not a substitute for the
stage-2 result. It runs *before* stage 2 in the script, because stage 2's exit 1
aborts the run.

| | |
|---|---|
| `status` | **match** |
| `power_connectivity.status` | `match` |
| `body_verification.status` | `unchecked` |
| `mismatch_count` | 2 (both `severity: warning`); `error_count` 0 |
| `counts.nets` | layout 869, reference 739, matched 1,300 |
| `counts.pins` | layout 16, reference 13, matched 574 |
| envelope | `build/puzzle-klt-lvs-probe.json`, 152,826 bytes |

The two warnings are the same informational pair the warm-up `01` emits:

- `topology.power_only_pruned` — `SKY130_FD_SC_HD__TAPVPWRVGND_1` is a
  power-only master on both sides, so all 676 of its instances are removed from
  both before comparing.
- `topology.top_level_pins_anchored` — 13 pins (`CLK ENABLE I O[0]…O[7] RST_N
  SUCCESS`) matched by name, so two topologically interchangeable boundary nets
  (e.g. two bits of `O`) cannot silently swap.

`power_connectivity: match` with **0 findings over all 1,618 instances**. The
power-pin universe `["VGND", "VPWR"]` was derived by rule
`declared-by-every-instantiated-master` from 69 masters, `corroborated: true` —
the same derivation the warm-up `01` run used, here over 69 masters rather than
18. As in the warm-up, this is a statement about the layout's power wiring as
seen through the black boxes' power pins, not about transistor bodies.

`body_verification` is `unchecked`, `klt`'s own stated reason being that a
pre-extracted `layout.netlist` carries no deck, "so nothing establishes this
layout's substrate/well-tap convention". `device_count` is 0.

The extra `vsubs` net does not disturb the compare, matching Run 2's warm-up
observation: a signal-only reference declares no body pins, so nothing is
asserted about them. (This is also why klayout-tools#5632 does not bite here —
that defect needs a PG-pin reference, and there is none in this repository.)

### How the undriven net is reported: as an ordinary matched net

`net_00575` is the known-undriven net — it feeds the `A1` pin of one `a31oi_2`
(`evidence/puzzle-extracted.v` l. 2435) and one `a311o_2` (l. 2457) and nothing
drives it. In the probe's `net_correspondence` it appears exactly once:

```json
{"layout": "\\$840", "reference": "NET_00575", "pin": false, "heuristic": false}
```

Matched, non-heuristically, with **no mismatch, no warning, and no category of
its own**. The layout side confirms the shape independently: `\$840` occurs
exactly twice in `build/puzzle-klt-lvs.spice`, as the first connection of
`Xsky130_fd_sc_hd__a311o_2_1` and `Xsky130_fd_sc_hd__a31oi_2_0` — the same two
`A1` sinks, no driver.

So **`klt lvs` has no opinion about a floating net**, and that is correct for
what it is: a topological equivalence compare asks whether the two netlists
agree, and here they agree that this net has two sinks and no driver. Finding
undriven nets is a different question, and in this repository it is
`tools/floating-nets`' job (run by `scripts/puzzle-regression.sh`), not LVS's.
Worth stating because "LVS passed" is easy to misread as "the netlist has no floating
nets"; it does not mean that, on either side.

(The reference name is uppercased to `NET_00575` because the gate-level-verilog
reader converts to plain-element form via SPICE, which is case-insensitive. The
layout name is the anonymous `\$840` because `--def-net-names` was not used — it
needs DEF net-name properties on the GDS shapes, which a GDS from another flow
does not carry, and there is no puzzle DEF at all.)

### `klt lvs --check` — both modes exit 0

Measured on `build/puzzle-klt-lvs-probe.json`, the only envelope this run
produced, from the repo root:

```
$ klt lvs --check build/puzzle-klt-lvs-probe.json
report: build/puzzle-klt-lvs-probe.json
status: match
  [OK] environment.layout_sha256
  [OK] environment.reference_sha256
                                                              # exit 0

$ klt lvs --check build/puzzle-klt-lvs-probe.json --rerun
report: build/puzzle-klt-lvs-probe.json
status: match
                                                              # exit 0
```

**klayout-tools#5631 does not bite this envelope**, and that is the structural
difference from the warm-up. Both of its inputs live inside *this* repository
(`build/puzzle-klt-lvs.spice`, `build/puzzle-klt-lvs-busport.v`), both recorded
`scope: "repo"`, so the path klt records and the path `--check` resolves share a
root. The warm-up envelopes fail only because *their* reference lives inside the
nested `puzzle/` clone. Full mode works too, as Run 2 predicted it would once the
path problem is out of the way: the envelope carries the
`reference_conversion` block (`{"form": "gate-level-verilog", "library":
"sky130_fd_sc_hd", "pdk": "sky130A", "pdk_root": null, "pin_order_files":
null}`), so the reference form survives reconstruction and klayout-tools#2250
does not apply.

Note the flag order: `--check REPORT --rerun`. `klt lvs --check --rerun REPORT`
is an argparse error (exit 2, `argument --check: expected one argument`).

**A fresh clone still cannot re-verify any of this**, the same caveat the
warm-up record carries and for the same reason: every recorded input is
gitignored. `build/puzzle-klt-lvs.spice` is derived from an unlicensed upstream
GDS (`CLAUDE.md` §3) and the probe reference is `build/`-only, so re-verification
needs `./scripts/fetch-puzzle.sh`, a sky130 PDK, and a fresh run of the script —
and the extraction is the step that needs the PDK. `--check` itself needs no
PDK; its inputs do.

**No envelope is committed under `evidence/`.** Stage 2 produced none, and the
probe's is deliberately `build/`-only — committing it would put a committed
artifact's provenance on a reference that no committed path reproduces, and
would also read as a verdict on the committed netlist, which it is not.

### Hard errors — exercised, no silent skip

All three `exit 2` paths were run against this worktree:

| Condition | Observed |
|---|---|
| `klt` off `PATH` (`env PATH=/usr/bin:/bin`) | `puzzle-klt-lvs: klt not found on PATH`, **exit 2** |
| `PDK=sky130-nonexistent` | `no 'sky130-nonexistent' PDK found. Point PDK_ROOT at a sky130 install`, **exit 2** |
| PDK resolves but the std-cell LEF is absent (`PDK_ROOT` pointed at a scratch tree with an empty `sky130A/libs.ref/`) | `'sky130A' resolved to libs_ref '…' but its sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef is missing`, **exit 2** |

None printed a skip, and none proceeded. The third matters because a missing
cell LEF silently changes the verdict rather than failing — it is the condition
that made the warm-up's Run 1 record a result on a build that already contained
the klayout-tools#3749 fix.

### Upstream finding (filed toolkit-first, synthetic reproducer)

[**2AMLogic/klayout-tools#5693**](https://github.com/2AMLogic/klayout-tools/issues/5693):
the `gate-level-verilog` reader rejects escaped/bracketed names in the module
port list and in the port direction declarations, so a reference whose bus ports
were bit-blasted into escaped scalars cannot be read at all. A follow-up to
closed **#1371** (whose fix reached connection expressions and net declarations)
and closed **#4810** (whose fix reached the module name).

**The trigger is the bracket, not the escaping.** Five synthetic references —
three cells each (`inv_2`, `inv_2`, `buf_2`) against a hand-written 3-card SPICE
layout, same `form`/`library`/`pdk` — run in `/tmp`, outside this repository:

| variant | reference port form | result |
|---|---|---|
| a | `\foo ` — escaped, no brackets | exit 0, `status: match` |
| b | `O[0]` — unescaped bracket in the port list | **exit 1** |
| c | plain ports; escaped bracketed name on an internal `wire \net[1] ;` | exit 0, `status: match` |
| d | real bus `output [1:0] O;`, bits used in the body | exit 0, `status: match` |
| e | `\O[0] ` — escaped bracket in the port list | **exit 1** |

c and d are the controls that matter: a bracketed escaped name on an internal
wire is accepted (#1371's fix), and a genuine bus port is accepted. Only a
bracketed name *in the port list* fails — so net declarations, connection
binding and netlist construction already handle the shape.

**Two validation sites, both in `klayout_tools/verilog_netlist.py`**, isolated by
calling the two functions directly (read-only; the installed file was not
modified):

- `_parse_module_chunk`'s port-list loop (~l. 366–372) checks each entry against
  `_IDENT_RE` (l. 180, `\\?[A-Za-z_$][A-Za-z0-9_$]*` — optional backslash, no
  brackets). One line earlier (l. 350) the module *name* is checked against
  `_IDENT_RE` **or** `_ESCAPED_IDENT_RE`; the port entries never got #4810's fix.
- `_parse_direction_statement` (~l. 405–412) re-validates the **already
  unescaped** name against `_IDENT_RE`, so `output \O[0] ;` → `O[0]` is rejected
  too. It accepts `\foo`, `[7:0] O` and `O0`. **Fixing only the first site moves
  the error to this one** — which is why the issue names both.

`_IDENT_RE`'s own comment (l. 175–179) states the premise that fails: it
validates "module/port/direction-statement names, where the escape only ever
guards against a keyword collision". An escaped *port* name routinely guards a
bracket instead, because that is how a bus port survives bit-blasting.
`_ESCAPED_IDENT_RE`'s own docstring (l. 182–190) — the regex the fix should
reach for — already states the principle: such a name "is one atomic token and
must never be re-parsed for an embedded bit-select: the `[0]` in it is part of
the name, not a bus index." These two checks have not been told.

The reproducer carries no puzzle content and no reference to this repository.

### Not changed

`evidence/puzzle-extracted.v` is untouched, deliberately. It is the golden file
`scripts/puzzle-regression.sh` compares both extractors against (`$GOLDEN`,
l. 36), and the netlist `tools/sim/run_solve`, `run_answer` and
`run_vcd_replay` simulate; rewriting its port list to suit the
reader would be working around a toolkit defect locally (`CLAUDE.md` §2) — and
would also change the artifact under test. `scripts/warmup-klt-lvs.sh` is
untouched too, so the warm-up regression (`CLAUDE.md` §4) stays green
independently of anything here.

Not added to CI: CI installs no PDK and does not fetch `puzzle/`, the same
reason `evidence/warmup-klt-lvs.md` gives for the warm-up LVS.
