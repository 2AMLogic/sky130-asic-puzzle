"""Port-direction parsing self-test for tools/sim/celltable.py.

parse_port_directions() reads each cell's port directions off the PDK's
behavioural models with _DIR_RE, and derive_cell_tables() turns a missing
direction entry into a CellTableError. Issue #98 is the regression this
guards: open_pdks switched its port declarations from the bare `input A1;`
form to `input wire A1;`, the regex matched only the former, and every
signal pin on a current install parsed as nothing — so load_design()
failed out of the box on hosts resolving the newer vintage, and the
error said the module was "not defined" about a module defined four
times behind ifdefs.

Five contracts asserted here, all against a few-line inline fixture —
no PDK, no iverilog and no fetched upstream file is touched, so the
test can run in CI ahead of the fetch step and its coverage does not
depend on which open_pdks the runner happens to have:

1. The typed declaration style (`input wire A1;` / `output wire X;`)
   parses to the same direction map as the bare style — the #98 fix.
2. The reg/logic variants parse too (forward cover; neither appears in
   either open_pdks install today, so no grammar beyond the optional
   type keyword is assumed).
3. A module whose entire port list is supply rails produces no
   direction entry — the decap/fill/tap behaviour must not change
   (14 physical-only cells are legitimately absent on both installs).
4. The optional type keyword does not eat a net whose name merely
   *starts* with a type word (`input wire_sel;` still parses, pin
   `wire_sel` — the failure mode that made the normalise-the-text
   alternative to the regex widening a non-starter).
5. derive_cell_tables() raises two textually distinct CellTableErrors:
   "defined ... port declaration style is not recognised" for a module
   whose ports it cannot read, and "not defined" for a name absent
   from the model file — the misleading-message half of #98.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from tools.sim.celltable import (
    CellTableError,
    derive_cell_tables,
    parse_port_directions,
)
from tools.sim.pdk import ResolvedModels

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


def main() -> int:
    print("== tools/sim celltable port-direction self-test (inline fixtures, no PDK) ==")
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.wasSuccessful()
    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'} "
          f"({result.testsRun} tests, {len(result.failures) + len(result.errors)} not passed)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
