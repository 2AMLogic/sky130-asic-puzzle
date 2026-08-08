"""Shared GDS layer/cell-name knowledge for `tools/inventory` and `tools/pins`.

Everything here was derived empirically by reading `warmup/04_final.gds` and
`puzzle.gds` with KLayout's Python API and cross-checking the result against
`warmup/01_netlist.v` -- see `tools/README.md` ("In-stream labels, no PDK
required") for the reconnaissance this generalizes from. Nothing here reads
or needs a PDK: cell identity, layer numbers, and label placement all survive
in the GDS stream itself.

The cell-family lists (`FILL_FAMILIES`, `SEQUENTIAL_FAMILIES`) are sky130
PDK-wide public naming convention -- which family names exist in
`sky130_fd_sc_hd`, not anything specific to this puzzle's content.
"""

from __future__ import annotations

VIA_PREFIX = "VIA_"
LIBRARY_PREFIX = "sky130_fd_sc_hd__"

# Fill cell families: no signal connectivity, present purely to satisfy
# physical design rules (decoupling capacitance / N+P well taps under the
# power rail).
FILL_FAMILIES = frozenset({"tapvpwrvgnd", "decap"})

# sky130_fd_sc_hd's sequential (flip-flop / latch) cell families -- the full
# set the library defines, not just the ones a given design happens to use.
SEQUENTIAL_FAMILIES = frozenset(
    {
        "dfxtp",
        "dfrtp",
        "dfstp",
        "dfbbn",
        "dfrbp",
        "dfsbp",
        "sdfxtp",
        "sdfxbp",
        "sdfrtp",
        "sdfrbp",
        "sdfstp",
        "sdfsbp",
        "sedfxtp",
        "sedfxbp",
        "edfxtp",
        "dlxtp",
        "dlxtn",
        "dlxbp",
        "dlxbn",
        "dlrtp",
        "dlrtn",
        "dlrbp",
        "dlrbn",
        "dlclkp",
    }
)


def cell_family(cell_name: str) -> str:
    """Strip a `sky130_fd_sc_hd__` prefix and the trailing `_<drive strength>`.

    ``sky130_fd_sc_hd__dfrtp_2`` -> ``dfrtp``. A name with no numeric suffix
    (nothing in this design has one, but classification should not silently
    misfire on one) is returned with the library prefix stripped only.
    """
    base = cell_name
    if base.startswith(LIBRARY_PREFIX):
        base = base[len(LIBRARY_PREFIX) :]
    prefix, _, suffix = base.rpartition("_")
    if prefix and suffix.isdigit():
        return prefix
    return base


class InstanceClass:
    LOGIC = "logic"
    SEQUENTIAL = "sequential"
    FILL = "fill"
    VIA = "via"
    OTHER = "other"

    ALL = (LOGIC, SEQUENTIAL, FILL, VIA, OTHER)


def classify(cell_name: str) -> str:
    """Classify a top-level instance's cell name into an `InstanceClass`.

    `OTHER` is a deliberate, reported bucket -- not a silent default. A name
    that is neither a `VIA_*` routing cell nor a `sky130_fd_sc_hd__*` library
    cell (e.g. the P&R tool's own bookkeeping cells) is surfaced as `other`
    rather than folded into `logic` on a guess.
    """
    if cell_name.startswith(VIA_PREFIX):
        return InstanceClass.VIA
    if cell_name.startswith(LIBRARY_PREFIX):
        family = cell_family(cell_name)
        if family in FILL_FAMILIES:
            return InstanceClass.FILL
        if family in SEQUENTIAL_FAMILIES:
            return InstanceClass.SEQUENTIAL
        return InstanceClass.LOGIC
    return InstanceClass.OTHER


# ---------------------------------------------------------------------------
# Pin label resolution (`tools/pins`)
# ---------------------------------------------------------------------------

# (layer, datatype) pairs that carry a pin NAME as GDS text, inside a
# standard-cell *definition* (not an instance placement).
LABEL_SOURCES = (
    (67, 5),  # li1.label   -- signal pin names (A, B, X, Y, D, Q, CLK, ...)
    (68, 5),  # met1.label  -- VPWR / VGND
    (64, 5),  # nwell.label -- VPB (n-well bias)
    (64, 59),  # VNB -- see PIN_TARGET_LAYER below for why this isn't 64/16
)

# The (layer, datatype=16 -- KLayout's ".pin" purpose) shape a label's text
# position is expected to land inside, keyed by the label's own (layer,
# datatype).
#
# This is *not* always "same layer number, datatype 16": (64, 59)'s VNB
# label sits at nwell's layer number (64) by GDS-export convention, but the
# substrate-tap pin shape it actually marks is drawn on the p-well layer,
# 122 -- confirmed by an exhaustive point-in-polygon search across all 69
# sky130_fd_sc_hd cells `puzzle.gds` uses (zero unresolved pins; see
# `tools/test-pins`). Do not "simplify" this to a same-layer-number rule
# without re-running that search -- it would silently break VNB resolution.
PIN_TARGET_LAYER = {
    (67, 5): 67,
    (68, 5): 68,
    (64, 5): 64,
    (64, 59): 122,
}

PIN_DATATYPE = 16  # ".pin" purpose, on whichever layer number it lives

# Top-level (chip) port labels, read directly off the top cell -- not a
# standard-cell definition, so a different set of layers. Keyed by
# (layer, datatype) -> a human-readable description of what the layer is,
# used verbatim as a report heading by `tools/inventory`.
TOP_PORT_LABEL_SOURCES = {
    (70, 5): "signal (met3.label, 70/5)",
    (71, 5): "VPWR (met4.label, 71/5)",
    (72, 5): "VGND (met5.label, 72/5)",
}
