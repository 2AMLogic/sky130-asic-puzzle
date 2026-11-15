"""Self-test `tools/sim/celltable.py`'s port-direction parsing and supply-pin filter.

`parse_port_directions()` reads each cell's port directions off the PDK's
behavioural models with raw-text regexes, and `derive_cell_tables()` turns a
missing direction entry into a `CellTableError`.

Two regression families live here:

**#98 — declaration-style parsing.** open_pdks switched its port declarations
from the bare `input A1;` form to `input wire A1;`, the regex matched only the
former, and every signal pin on a current install parsed as nothing — so
load_design() failed out of the box on hosts resolving the newer vintage, and
the error said the module was "not defined" about a module defined four times
behind ifdefs.  Five contracts asserted against inline fixtures:

1. The typed declaration style (`input wire A1;` / `output wire X;`) parses to
   the same direction map as the bare style — the #98 fix.
2. The reg/logic variants parse too (forward cover; neither appears in either
   open_pdks install today, so no grammar beyond the optional type keyword is
   assumed).
3. A module whose entire port list is supply rails produces no direction
   entry — the decap/fill/tap behaviour must not change (14 physical-only
   cells are legitimately absent on both installs).
4. The optional type keyword does not eat a net whose name merely *starts*
   with a type word (`input wire_sel;` still parses, pin `wire_sel` — the
   failure mode that made the normalise-the-text alternative to the regex
   widening a non-starter).
5. `derive_cell_tables()` raises two textually distinct `CellTableError`s:
   "defined ... port declaration style is not recognised" for a module whose
   ports it cannot read, and "not defined" for a name absent from the model
   file — the misleading-message half of #98.

**#106 — the supply-pin filter.**  The regexes ignore `` `ifdef `` boundaries,
so the `` `ifdef USE_POWER_PINS `` branch's supply-port declarations are
visible regardless of the compile defines (`ICARUS_DEFINES` leaves
`USE_POWER_PINS` undefined — `tools/sim/icarus.py`), and the filter that drops
them is load-bearing: unfiltered, a supply pin is classified as an `input` and
would be swept as one.  The filter is `verilog_netlist.POWER_PINS` (issue
#106 — previously a narrower local copy of four of the same names).  Checks:

  a. [fixture, no PDK] a synthetic slice of the model file — signal pins
     survive, all of `verilog_netlist.POWER_PINS` (including `KAPWR`, which
     the pre-#106 local copy missed) is dropped, a supply-only cell is
     omitted from the map entirely, and the first module definition wins
     across the power-pin/no-power-pin variants.
  b. [control, no PDK] the same fixture parsed with the pre-#106 narrow set
     patched back in keeps `KAPWR` — proving check a is sensitive to exactly
     the change issue #106 made rather than passing for any filter (the
     positive/negative-control discipline `selftest_portmap.py` uses).
  c. [golden, needs a resolvable sky130 install] resolves the models with
     `resolve_sky130_models()` and asserts the port map for the 69 cells
     `puzzle.gds` uses (`evidence/pins-sky130_fd_sc_hd.json`) is unchanged
     vs `evidence/portmap-sky130_fd_sc_hd.json`.  The baseline was
     recorded 2026-11-15 with the pre-#106 filter, so a green check here
     proves the swap to `verilog_netlist.POWER_PINS` did not move it.

The golden check resolves its models instead of re-reading the baseline's
recorded path: measured (2026-11-15) the 69-cell map is identical across the
volare `c6d73a35` install the baseline was recorded from and the ciel
`f6eeac7d` install CI provisions — the two use the two declaration styles #98
widened `_DIR_RE` for, and both parse to the same port directions — so the
check may resolve whatever install the host has, and a skip happens only when
no PDK resolves at all.  The run prints the baseline's recorded provenance —
the install the map was first parsed from, plus the recording host's resolver
version (`source.version`) when the baseline carries one — next to the version
this host resolved, so a future drift failure names all sides.

Contracts 1–5 need no PDK, no iverilog and no fetched upstream file; checks
a–b likewise, and check c needs a resolvable sky130 install (skipped with an
explanatory line when `resolve_sky130_models()` finds none).

Run it with:

    python3 -m tools.sim.selftest_celltable
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import verilog_netlist as vn
from tools.sim.celltable import (
    CellTableError,
    derive_cell_tables,
    parse_port_directions,
)
from tools.sim.pdk import PdkResolutionError, ResolvedModels, resolve_sky130_models
from tools.testutil import report_checks

# The pre-#106 local copy — exactly the four names it carried.  Used only by
# the negative-control check, never by the filter under test.
PRE_106_NARROW_SET = frozenset({"VPWR", "VGND", "VPB", "VNB"})

BASELINE = Path(__file__).resolve().parents[2] / "evidence" / "portmap-sky130_fd_sc_hd.json"
PINS_EVIDENCE = Path(__file__).resolve().parents[2] / "evidence" / "pins-sky130_fd_sc_hd.json"

MODULE_HEADER = "module {name} ("
MODULE_FOOTER = ");\nendmodule\n"


def _fixture_model(*bodies: str) -> Path:
    """Write a minimal behavioural-model file with the given module bodies."""
    tmp = tempfile.mkdtemp(prefix="celltable-selftest-")
    path = Path(tmp) / "sky130_fd_sc_hd.v"
    path.write_text("".join(bodies), encoding="utf-8")
    return path


def _module(name: str, decls: str) -> str:
    return MODULE_HEADER.format(name=name) + MODULE_FOOTER + decls


TYPED_BODY = _module(
    "sky130_fd_sc_hd__a2111oi_2",
    "input wire A1;\ninput wire A2;\ninput wire B1;\n"
    "input wire C1;\ninput wire D1;\noutput wire Y;\n"
    "input wire VPWR;\ninput wire VGND;\n"
    "input wire VPB;\ninput wire VNB;\n",
)
BARE_BODY = _module(
    "sky130_fd_sc_hd__a2111oi_2",
    "input A1;\ninput A2;\ninput B1;\ninput C1;\ninput D1;\noutput Y;\n"
    "input VPWR;\ninput VGND;\ninput VPB;\ninput VNB;\n",
)
POWER_ONLY_BODY = _module(
    "sky130_fd_sc_hd__decap_3",
    "input VPWR;\ninput VGND;\n",
)
A2111OI_2_DIRS = {
    "Y": "output",
    "A1": "input",
    "A2": "input",
    "B1": "input",
    "C1": "input",
    "D1": "input",
}


class ParseTypedDeclarationTest(unittest.TestCase):
    """Contract 1: `input wire A1;` parses to the map the bare form gives."""

    def test_typed_and_bare_styles_parse_identically(self):
        for label, body in (("typed", TYPED_BODY), ("bare", BARE_BODY)):
            with self.subTest(style=label):
                directions, defined = parse_port_directions(_fixture_model(body))
                self.assertEqual(defined, {"sky130_fd_sc_hd__a2111oi_2"})
                self.assertEqual(directions["sky130_fd_sc_hd__a2111oi_2"], A2111OI_2_DIRS)


class ParseRegLogicVariantsTest(unittest.TestCase):
    """Contract 2: the reg/logic type keywords parse as the type token."""

    def test_reg_and_logic_typed_declarations_parse(self):
        body = (
            _module("sky130_fd_sc_hd__regform_1", "input reg D;\n")
            + _module("sky130_fd_sc_hd__logicform_1", "input logic EN;\noutput logic Q;\n")
        )
        directions, _ = parse_port_directions(_fixture_model(body))
        self.assertEqual(directions["sky130_fd_sc_hd__regform_1"], {"D": "input"})
        self.assertEqual(
            directions["sky130_fd_sc_hd__logicform_1"], {"EN": "input", "Q": "output"}
        )


class PowerOnlyCellAbsentTest(unittest.TestCase):
    """Contract 3: a supply-rails-only module yields no direction entry."""

    def test_power_only_module_is_absent_from_direction_map(self):
        directions, defined = parse_port_directions(_fixture_model(POWER_ONLY_BODY))
        self.assertEqual(defined, {"sky130_fd_sc_hd__decap_3"})
        self.assertNotIn("sky130_fd_sc_hd__decap_3", directions)


class TypeKeywordDoesNotEatNetNamesTest(unittest.TestCase):
    """Contract 4: `input wire_sel;` parses pin `wire_sel`, not nothing."""

    def test_net_named_wire_sel_parses_as_a_pin(self):
        body = _module("sky130_fd_sc_hd__wiresel_1", "input wire_sel;\noutput wire_out;\n")
        directions, _ = parse_port_directions(_fixture_model(body))
        self.assertEqual(
            directions["sky130_fd_sc_hd__wiresel_1"],
            {"wire_sel": "input", "wire_out": "output"},
        )


class DeriveCellTablesErrorDiscriminationTest(unittest.TestCase):
    """Contract 5: "defined but unparseable" and "not defined" differ."""

    def _models(self, behavioural_v: Path) -> ResolvedModels:
        return ResolvedModels(
            variant="sky130A (selftest_celltable fixture)",
            version="fixture",
            resolved_via="selftest",
            libs_ref=behavioural_v.parent,
            primitives_v=behavioural_v,
            behavioural_v=behavioural_v,
        )

    def _assert_raises_with_message(self, cells, fixture_body) -> str:
        with tempfile.TemporaryDirectory(prefix="celltable-selftest-") as tmp:
            models = self._models(_fixture_model(fixture_body))
            with self.assertRaises(CellTableError) as ctx:
                derive_cell_tables(
                    cells, models, work_dir=Path(tmp) / "work"
                )
        return str(ctx.exception)

    def test_defined_but_unparseable_message(self):
        message = self._assert_raises_with_message(
            {"sky130_fd_sc_hd__decap_3": {"VPWR"}}, POWER_ONLY_BODY
        )
        self.assertIn("sky130_fd_sc_hd__decap_3 is defined in", message)
        self.assertIn("port declaration style is not recognised", message)

    def test_absent_cell_message(self):
        message = self._assert_raises_with_message(
            {"sky130_fd_sc_hd__not_a_cell": {"A1"}}, TYPED_BODY
        )
        self.assertIn("sky130_fd_sc_hd__not_a_cell is not defined in", message)

    def test_the_two_messages_differ(self):
        unparseable = self._assert_raises_with_message(
            {"sky130_fd_sc_hd__decap_3": {"VPWR"}}, POWER_ONLY_BODY
        )
        absent = self._assert_raises_with_message(
            {"sky130_fd_sc_hd__not_a_cell": {"A1"}}, TYPED_BODY
        )
        self.assertNotEqual(unparseable, absent)


# --------------------------------------------------------------------------
# issue #106: the supply-pin filter reads verilog_netlist.POWER_PINS
# --------------------------------------------------------------------------


def _fixture_v() -> str:
    """A synthetic slice of the behavioural models exercising the filter.

    Shapes mirror the real file (ports declared one per line, comma-list in
    the header, power-pin variant behind `` `ifdef USE_POWER_PINS ``) but
    with no sky130 content at all — pure fixture, runs without a PDK.
    """
    return """\
// synthetic fixture for tools/sim/selftest_celltable.py — not a PDK file
// two full module definitions of one cell, like the real file's
// power-pin / no-power-pin variants: the first definition wins
module sky130_fd_sc_hd__fx_dup (
    X,
    A
);
    output X;
    input  A;
endmodule

`ifdef USE_POWER_PINS
module sky130_fd_sc_hd__fx_dup (
    X   ,
    A   ,
    VPWR,
    VGND,
    VPB ,
    VNB
);
    output X   ;
    input  A   ;
    inout  VPWR;
    input  VGND;
    input  VPB ;
    input  VNB ;
endmodule
`endif

module sky130_fd_sc_hd__fx_and2 (
    X   ,
    A   ,
    B   ,
    VPWR,
    VGND,
    VPB ,
    VNB
);
    output X   ;
    input  A   ;
    input  B   ;
    input  VPWR;
    input  VGND;
    input  VPB ;
    input  VNB ;
endmodule

module sky130_fd_sc_hd__fx_kapwrbuf (
    X   ,
    A   ,
    KAPWR,
    VPWR,
    VGND
);
    output X    ;
    input  A    ;
    input  KAPWR;
    input  VPWR ;
    input  VGND ;
endmodule

module sky130_fd_sc_hd__fx_decap (
    VPWR,
    VGND
);
    input VPWR;
    input VGND;
endmodule
"""


def _run_fixture_check(checks: list[tuple[str, bool]]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture_models.v"
        path.write_text(_fixture_v(), encoding="utf-8")
        got, _defined = parse_port_directions(path)

    expected = {
        # first definition wins, and the raw-text regex sees the `ifdef
        # USE_POWER_PINS branch only through that rule — the variant's
        # inout VPWR must not leak into the entry
        "sky130_fd_sc_hd__fx_dup": {"X": "output", "A": "input"},
        "sky130_fd_sc_hd__fx_and2": {"X": "output", "A": "input", "B": "input"},
        # KAPWR is a supply rail (verilog_netlist.POWER_PINS carries it even
        # though the pre-#106 local copy did not) — dropped, not swept
        "sky130_fd_sc_hd__fx_kapwrbuf": {"X": "output", "A": "input"},
        # supply-only cell: nothing survives the filter, so the whole entry
        # is omitted (same rule that keeps decap/tap cells out of the map)
    }
    ok = got == expected
    checks.append(("fixture: filter keeps signal pins, drops all POWER_PINS, first definition wins", ok))
    if not ok:
        print(f"  got:      {got}")
        print(f"  expected: {expected}")


def _run_golden_check(checks: list[tuple[str, bool]]) -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    cells69 = sorted(json.loads(PINS_EVIDENCE.read_text(encoding="utf-8"))["cells"])
    try:
        resolved = resolve_sky130_models()
    except PdkResolutionError as e:
        print(
            f"\n[skip] golden 69-cell check — no resolvable sky130 PDK install: {e}\n"
            "       (the check needs resolve_sky130_models() to find the behavioural models)"
        )
        return
    source = baseline["source"]
    print(f"  baseline: map first parsed from {source['install']} ({source['behavioural_v']})")
    if "version" in source:
        print(f"  resolver at record time: {source['version']} (source.version)")
    print(f"  this host resolved:     {resolved.version} (via {resolved.resolved_via})")

    got, _defined = parse_port_directions(resolved.behavioural_v)
    expected = baseline["cells"]
    absent_expected = sorted(baseline["cells_absent_after_filter"])
    absent_now = sorted(c for c in cells69 if c not in got)

    drifted = [c for c in cells69 if c in expected and got.get(c) != expected[c]]
    unexpected_absent = sorted(set(absent_now) - set(absent_expected))

    ok = not drifted and not unexpected_absent
    label = (
        f"golden: 69-cell port map unchanged vs baseline ({len(expected)} parsed, "
        f"{len(absent_expected)} supply-only-absent)"
    )
    checks.append((label, ok))
    if not ok:
        for c in drifted:
            print(f"  drifted: {c}\n    baseline: {expected[c]}\n    now:      {got.get(c)}")
        for c in unexpected_absent:
            print(f"  unexpectedly absent from the parsed map: {c}")


def _run_negative_control(checks: list[tuple[str, bool]]) -> None:
    """Re-parse the fixture with the pre-#106 narrow set: `KAPWR` must come back.

    Without this, check a would also pass against a filter that drops
    *everything* — this pins its sensitivity to the one name issue #106
    widened.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture_models.v"
        path.write_text(_fixture_v(), encoding="utf-8")
        with mock.patch.object(vn, "POWER_PINS", PRE_106_NARROW_SET):
            got, _defined = parse_port_directions(path)
    ok = got["sky130_fd_sc_hd__fx_kapwrbuf"].get("KAPWR") == "input"
    checks.append(("control: the pre-#106 narrow set keeps KAPWR (the delta this issue closes)", ok))
    if not ok:
        print(f"  kapwrbuf with the narrow set: {got['sky130_fd_sc_hd__fx_kapwrbuf']}")


def main() -> int:
    print("== tools/sim celltable self-test: port directions + supply-pin filter ==")
    checks: list[tuple[str, bool]] = []

    print("\n== [fixture] synthetic model slice, no PDK needed ==")
    _run_fixture_check(checks)

    print("\n== [control] pre-#106 narrow set keeps KAPWR on the same fixture ==")
    _run_negative_control(checks)

    print("\n== [golden] 69-cell port map vs the committed baseline ==")
    _run_golden_check(checks)

    rc_checks = report_checks(checks)

    print("\n== [contracts] declaration-style unittest suite ==")
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    rc_contracts = 0 if result.wasSuccessful() else 1
    print(
        f"\nCONTRACT SELF-TEST {'PASS' if rc_contracts == 0 else 'FAIL'} "
        f"({result.testsRun} tests, {len(result.failures) + len(result.errors)} not passed)"
    )

    return rc_checks | rc_contracts


if __name__ == "__main__":
    sys.exit(main())
