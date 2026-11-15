"""Self-test `tools/sim/celltable.parse_port_directions`'s supply-pin filter.

`parse_port_directions` reads port directions for every `sky130_fd_sc_hd__*`
module in the PDK's behavioural Verilog with raw-text regexes.  The regexes
ignore `` `ifdef `` boundaries, so the `` `ifdef USE_POWER_PINS `` branch's
supply-port declarations are visible regardless of the compile defines
(`ICARUS_DEFINES` leaves `USE_POWER_PINS` undefined — `tools/sim/icarus.py`),
and the filter that drops them is load-bearing: unfiltered, a supply pin is
classified as an `input` and would be swept as one.  The filter is
`verilog_netlist.POWER_PINS` (issue #106 — previously a narrower local copy
of the same four names).

Two checks:

  1. [fixture, no PDK] a synthetic slice of the model file — signal pins
     survive, all of `verilog_netlist.POWER_PINS` (including `KAPWR`, which
     the pre-#106 local copy missed) is dropped, a supply-only cell is
     omitted from the map entirely, and the first module definition wins
     across the power-pin/no-power-pin variants.
  2. [control, no PDK] the same fixture parsed with the pre-#106 narrow set
     patched back in keeps `KAPWR` — proving check 1 is sensitive to
     exactly the change issue #106 made rather than passing for any filter
     (the positive/negative-control discipline `selftest_portmap.py` uses).
  3. [golden, needs the PDK install the baseline names] re-parses the exact
     model file `evidence/portmap-sky130_fd_sc_hd.json` was recorded from
     and asserts the port map for the 69 cells `puzzle.gds` uses
     (`evidence/pins-sky130_fd_sc_hd.json`) is unchanged.  The baseline was
     recorded 2026-11-15 with the pre-#106 filter, so a green check here
     proves the swap to `verilog_netlist.POWER_PINS` did not move it.

The golden check pins the baseline's own provenance path rather than
`resolve_sky130_models()`: on a `~/.ciel` open_pdks install the models
declare ports as ``input wire X;``, which `_DIR_RE` does not parse at all
(issue #98), so no cell parses there under either filter and a resolved-
path comparison would only report #98's regex gap back as a failure here.

Run it with:

    python3 -m tools.sim.selftest_celltable

Check 1 needs no PDK and no simulator; check 3 needs the volare install
named in the baseline's `source` (skipped with an explanatory line when
that file is not present).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tools import verilog_netlist as vn
from tools.sim.celltable import parse_port_directions
from tools.testutil import report_checks

# The pre-#106 local copy — exactly the four names it carried.  Used only by
# the negative-control check, never by the filter under test.
PRE_106_NARROW_SET = frozenset({"VPWR", "VGND", "VPB", "VNB"})

BASELINE = Path(__file__).resolve().parents[2] / "evidence" / "portmap-sky130_fd_sc_hd.json"
PINS_EVIDENCE = Path(__file__).resolve().parents[2] / "evidence" / "pins-sky130_fd_sc_hd.json"


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
        got = parse_port_directions(path)

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
    models_v = Path(baseline["source"]["behavioural_v"])
    if not models_v.exists():
        print(
            f"\n[skip] golden 69-cell check — baseline's model file not present: {models_v}\n"
            "       (record the baseline on this machine to enable the check; see the note in the JSON)"
        )
        return

    got = parse_port_directions(models_v)
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

    Without this, check 1 would also pass against a filter that drops
    *everything* — this pins its sensitivity to the one name issue #106
    widened.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture_models.v"
        path.write_text(_fixture_v(), encoding="utf-8")
        with mock.patch.object(vn, "POWER_PINS", PRE_106_NARROW_SET):
            got = parse_port_directions(path)
    ok = got["sky130_fd_sc_hd__fx_kapwrbuf"].get("KAPWR") == "input"
    checks.append(("control: the pre-#106 narrow set keeps KAPWR (the delta this issue closes)", ok))
    if not ok:
        print(f"  kapwrbuf with the narrow set: {got['sky130_fd_sc_hd__fx_kapwrbuf']}")


def main() -> int:
    print("== tools/sim celltable parse_port_directions self-test ==")
    checks: list[tuple[str, bool]] = []

    print("\n== [fixture] synthetic model slice, no PDK needed ==")
    _run_fixture_check(checks)

    print("\n== [control] pre-#106 narrow set keeps KAPWR on the same fixture ==")
    _run_negative_control(checks)

    print("\n== [golden] 69-cell port map vs the committed baseline ==")
    _run_golden_check(checks)

    return report_checks(checks)


if __name__ == "__main__":
    sys.exit(main())
