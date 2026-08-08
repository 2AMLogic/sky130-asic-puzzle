"""Optional cross-check of `tools/pins`' derived pin *names* against a PDK.

This is deliberately not on the critical path: issue #1 established that pin
geometry is fully recoverable from the GDS stream alone, so a PDK is a
cross-check, never a dependency. `tools/pins --pdk-crosscheck` uses this
module when a PDK happens to be resolvable; it reports disagreement, it
never fails the run because of one (see `tools/pins`'s `--format` output --
a crosscheck section is additive, not a pass/fail gate).

The comparison is of pin *names* only (a set per cell) -- the PDK's
behavioural Verilog carries no polygon geometry to compare against the
stream-derived kind.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim.pdk import PdkResolutionError, ResolvedModels, resolve_sky130_models  # noqa: E402

# `sky130_fd_sc_hd.v` defines each cell multiple times, guarded by
# `` `ifdef FUNCTIONAL``/`` `ifdef USE_POWER_PINS`` -- once with VPWR/VGND/
# VPB/VNB in the port list and once without. `tools/pins` resolves power and
# well-bias pins too, so the right comparison set is the *union* of every
# `module <cell> ( ... );` header's ports across all `ifdef` variants, not
# just whichever one happens to compile first.
_MODULE_HEADER_RE = re.compile(
    r"module\s+(sky130_fd_sc_hd__\w+)\s*\(([^)]*)\)\s*;", re.S
)


@dataclass(frozen=True)
class CrosscheckResult:
    resolved: ResolvedModels
    # cell name -> (only in stream-derived pins, only in library's own ports)
    disagreements: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
    cells_checked: int
    cells_not_found_in_library: tuple[str, ...]

    def to_json(self) -> dict:
        return {
            "pdk_variant": self.resolved.variant,
            "pdk_version": self.resolved.version,
            "resolved_via": self.resolved.resolved_via,
            "behavioural_verilog": str(self.resolved.behavioural_v),
            "cells_checked": self.cells_checked,
            "cells_not_found_in_library": list(self.cells_not_found_in_library),
            "agreement": not self.disagreements and not self.cells_not_found_in_library,
            "disagreements": {
                cell: {"only_in_stream": list(only_stream), "only_in_library": list(only_lib)}
                for cell, (only_stream, only_lib) in sorted(self.disagreements.items())
            },
        }


def _library_pin_names(behavioural_v: str, cell_names: set[str]) -> dict[str, set[str]]:
    with open(behavioural_v, "r", encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    names_by_cell: dict[str, set[str]] = {}
    for match in _MODULE_HEADER_RE.finditer(text):
        cell = match.group(1)
        if cell not in cell_names:
            continue
        ports = {p.strip() for p in match.group(2).split(",") if p.strip()}
        names_by_cell.setdefault(cell, set()).update(ports)
    return names_by_cell


def crosscheck(cell_pins: dict[str, set[str]]) -> CrosscheckResult:
    """Compare derived pin name sets (cell -> set of pin names) to the PDK.

    Raises `PdkResolutionError` if no PDK is resolvable -- callers decide
    whether that's fatal (it never should be for a normal `tools/pins` run;
    `--pdk-crosscheck` is opt-in specifically so this can be skipped).
    """
    resolved = resolve_sky130_models()
    library_names = _library_pin_names(str(resolved.behavioural_v), set(cell_pins))

    disagreements: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    not_found: list[str] = []
    for cell, stream_names in cell_pins.items():
        lib_names = library_names.get(cell)
        if lib_names is None:
            not_found.append(cell)
            continue
        only_stream = tuple(sorted(stream_names - lib_names))
        only_lib = tuple(sorted(lib_names - stream_names))
        if only_stream or only_lib:
            disagreements[cell] = (only_stream, only_lib)

    return CrosscheckResult(
        resolved=resolved,
        disagreements=disagreements,
        cells_checked=len(cell_pins) - len(not_found),
        cells_not_found_in_library=tuple(sorted(not_found)),
    )


__all__ = ["crosscheck", "CrosscheckResult", "PdkResolutionError"]
