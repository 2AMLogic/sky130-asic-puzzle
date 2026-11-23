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

> **2026-11-23 (Run 2): three statements in Run 1 below have stopped being true
> of this record.** klayout-tools#5693 is closed (by PR #7452, merge
> `6ca7e00`), and on a build carrying the fix stage 2 produces its first report
> — so an envelope **is** now committed under `evidence/`, the verdict is
> **mismatch**, not the probe's old `match` (a new tool-side finding, filed as
> klayout-tools#7561), and the run is now *gated*, not just recorded (#165):
> `evidence/puzzle-klt-lvs-expected.json` pins the verdict and
> `scripts/puzzle-klt-lvs.sh` exits nonzero if it moves. Run 1's text is left
> as recorded.

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

`klt lvs` exits **1** and writes an `{"error": ...}` envelope instead of a
report — on **stderr**. Stdout stays empty, so the file the script stages under
`build/` for a refused run is zero bytes, not an error envelope. Verbatim
(`error.message`, as the JSON decodes it — `klt` doubles the backslash in the
raw JSON string):

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

## Run 2 — 2026-11-23

Why: klayout-tools#5693 closed (PR #7452, merge `6ca7e00`, 2026-11-23) — no
released klt carries the fix yet (latest is 0.9.2), so per #165's guidance the
baseline ran on a throwaway build of exactly that merge commit, and the CI pin
stays at 0.9.2. This is the **first stage 2 report ever recorded**: the
committed reference, `evidence/puzzle-extracted.v`, read as committed, escaped
bracket ports and all.

Environment: Linux (AWS dispatch worker), throwaway `uv venv` inside the
worktree's gitignored `build/` from
`git+https://github.com/2AMLogic/klayout-tools@6ca7e001c1879e588a3cf0e10faeee02d15c7cfe`
— `klt 0.9.3.dev3831+g6ca7e001c187`, klayout 0.30.14 (klt warns on every
compare that it was tested against 0.30.12 and that report *counts* may differ;
`provenance.klayout_version_mismatch` is `true` in the envelope). PDK `sky130A`
(open_pdks `f6eeac7dad08…`, under `~/.ciel`). Commands as scripted,
`scripts/puzzle-klt-lvs.sh`, unchanged from Run 1 apart from the verdict gate
this run lands (#165).

**Headline: the reader fix works — and the verdict it reveals is `mismatch`,
tool-side.** Stage 2 reads the reference and compares, exit 3 (a verdict):
`mismatch`, 31 mismatches (29 errors). That is not what Run 1's isolating
probe recorded (`match`, 2 warnings) on klt 0.9.2.dev1025 — and the probe
*also* moved, to the identical `mismatch` 31, so the move is not about port
spelling at all. Attribution below pins it to one upstream commit.

### Two-build attribution (same host, same PDK, same engine)

| klt | klayout | extract nets | probe | stage 2 |
|---|---|---|---|---|
| `0.9.2.dev1025+ga90545db9ea6` (Run 1's build, re-run here) | 0.30.14 | 869 | **match**, 2 warnings | exit 1, reader error (Run 1 verbatim) |
| `0.9.3.dev2924+g262c5454952a` (parent of the suspect) | 0.30.14 | 869 | *(not re-run; extraction identical to the above)* | — |
| `0.9.3.dev2925+g9edf835f5ac6` | 0.30.14 | **864** | *(not re-run)* | — |
| `0.9.3.dev3831+g6ca7e001c187` (#7452 merge; baseline) | 0.30.14 | 864 | **mismatch 31/29** | **mismatch 31/29** |
| `0.9.3.dev3993+g922fd6747463` (host tool) | 0.30.12 | 864 | mismatch 31/29 | mismatch 31/29 |

The old build's re-run (first row) reproduces Run 1 exactly on this host —
869 nets, probe `match`, stage 2 refused with the same reader error — and its
run also demonstrates the error path #165 requires: the script propagated
exit 1 and left the previously installed envelope in `evidence/` untouched.
The flip is at **`9edf835f5ac6`** ("Join routed pads of an abstract cell pin
without shorting named nets", #6742): its parent extracts 869 nets, it
extracts 864. Engine-independent (0.30.12 and 0.30.14 agree).

### What changed in the extraction

`klt extract --abstract-cells` now emits two new warnings, verbatim:

```
--abstract-cells joined routed pads of the same pin: sky130_fd_sc_hd__a31oi_2_0.A1: $840 and $788; sky130_fd_sc_hd__diode_2_1.VNB: VGND and $663; sky130_fd_sc_hd__diode_2_2.VNB: VGND and $169; sky130_fd_sc_hd__diode_2_6.VNB: VGND and $1401; sky130_fd_sc_hd__diode_2_7.VNB: VGND and $358
--abstract-cells pin pads have conflicting net names, kept separate: sky130_fd_sc_hd__diode_2_0.VNB: VGND, enable
```

(The first is one physical line, semicolon-joined; wrapped here. Net names are
the extractor's own anonymous `$N` ids and globals.)

Five joins. Four of them absorb an anonymous net into `VGND` through a
**`diode_2` `VNB` pad**: `\$663` (13 instance connections), `\$169` (6),
`\$358` (5), `\$1401` (3) — 27 connections in all. The fifth joins two
anonymous nets — `a31oi_2_0.A1: $840 and $788` — where `\$840` is the layout
name Run 1 documents for the known-undriven `net_00575`; the join makes
`\$840` the survivor, so the two instance pins that were on `\$788` (e.g.
`and2_2_13`'s last connection, `\$788` → `\$840` in the emitted SPICE) now
read `\$840`. 869 − 864 = the five absorbed nets. The second warning is the
guard working as designed when **both** sides are named (`enable` is a
top-level pin): kept separate. The four `VGND`-and-anonymous joins are the
same situation with the unnamed side, and `AbstractPinJoins.apply()`'s
conflict check counts names, so one named + one anonymous passes and joins.

The absorbed nets are real driven signals, not decoration: in
`evidence/puzzle-extracted.v`, `net_00102` is driven by a cell `.X` and feeds
three `diode_2` `.DIODE` pins and a `.B`; `net_00124` by `.LO`;
`net_00283`/`net_00557` likewise carry driven output-to-input connections.
A net that were genuinely tied to ground could not carry a functioning
signal — and this netlist is functionally validated (it is the netlist the
solve simulated, `evidence/puzzle-solve.md`). So the join is a mis-read, not
a discovery. **Filed as
[klayout-tools#7561](https://github.com/2AMLogic/klayout-tools/issues/7561)**
with a unit-level synthetic reproducer against `AbstractPinJoins` itself.

### Stage 2 — the first report, and its verdict

| | |
|---|---|
| `status` | **mismatch** |
| `power_connectivity.status` | `match` (0 findings over all 1,618 instances, as Run 1's probe) |
| `body_verification.status` | `unchecked` |
| `mismatch_count` | 31 (29 errors, 2 warnings); `error_count` 29 |
| categories | `topology` 23, `net.merged` 4, `net.split` 2, + the same two informational warnings as Run 1 (`power_only_pruned`, `top_level_pins_anchored`) |
| `counts.nets` | layout 864, reference 739, matched 1,291 |
| `counts.pins` | layout 16, reference 13, matched 574 |
| envelope | `evidence/puzzle-klt-lvs-01.json`, 234,953 bytes — **committed** (the reference is our own file; nothing is elided, Run 1's stance) |

The anatomy lines up with the extraction change exactly: the 4 `net.merged`
errors are the four absorbed nets (`net_00102`, `net_00124`, `net_00283`,
`net_00557` — "multiple reference nets were collapsed into one layout net");
the 2 `net.split` are `VPWR` and `VSUBS`; the 23 `topology` errors are the
unmatched instances downstream of those (e.g. layout
`SKY130_FD_SC_HD__AND4_2_3` vs reference `AND4_2_77090_37840`). The probe
envelope (bus-port form, `build/`-only as ever) reports the same 31/29 —
expected, since it differs from stage 2 in port spelling alone.

### The verdict gate (#165)

`evidence/puzzle-klt-lvs-expected.json` pins `01` to this run's verdict —
`mismatch`, 31, 29 — with `upstream.issue`
2AMLogic/klayout-tools#7561, and `scripts/puzzle-klt-lvs.sh` now ends in
`exec tools/lvs-verdict evidence/puzzle-klt-lvs-expected.json
01:evidence/puzzle-klt-lvs-01.json`, replacing the old "exit 0 means both
stages completed" contract Run 1's header carried. Measured here:

- the gated script re-run end to end on the baseline build: exit 0,
  `lvs-verdict: 01 verdict as pinned`;
- a copy of the envelope with `mismatch_count` altered to 27: exit 1,
  `01 mismatch_count moved: pinned 31, got 27 (-4)`;
- a `match` envelope against the pin: exit 1, reported as a stale pin naming
  #7561 — the upstream fix landing is a promotion (re-record and bump the
  pin), never a pass;
- `tools/test-lvs-verdict` grew the puzzle pin's cases (as pinned, count
  moved, now-match) plus a contract check on the committed expected file:
  20 checks, all passing, no PDK, no `puzzle/` file.

The confirming cross-check row above (host `0.9.3.dev3993`, klayout 0.30.12)
reproduced the verdict and counts exactly before the gate landed.

### `klt lvs --check` on the committed envelope

From the repo root, baseline build:

```
$ klt lvs --check evidence/puzzle-klt-lvs-01.json
report: evidence/puzzle-klt-lvs-01.json
status: match
  [OK] environment.layout_sha256
  [OK] environment.reference_sha256
                                                               # exit 0
$ klt lvs --check evidence/puzzle-klt-lvs-01.json --rerun
report: evidence/puzzle-klt-lvs-01.json
status: match
                                                               # exit 0
```

As in Run 1, both inputs live inside this repository, so klayout-tools#5631
does not bite. A fresh clone still needs `./scripts/fetch-puzzle.sh`, a sky130
PDK and a full re-run to re-verify (every recorded input is gitignored);
`--check` itself needs no PDK.

### Not changed

`evidence/puzzle-extracted.v` is untouched (still the golden file
`scripts/puzzle-regression.sh` gates on). The probe stays `build/`-only and
unpinned — pinning it is Out of Scope in #165, and it is diagnostic, not a
deliverable. Still not in CI: CI installs no PDK and does not fetch `puzzle/`.
