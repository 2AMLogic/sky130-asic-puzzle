"""Per-cell pin abstracts, resolved from GDS label + shape geometry alone.

For each `sky130_fd_sc_hd__*` cell *definition* in a GDS stream, this builds
a map from pin name to the drawn geometry that pin occupies, in that cell's
own local coordinate system (no instance transform applied -- see
`tools/README.md` "Cell coordinates, not top-level coordinates").

Algorithm (see `gds_layers.py` for the layer table this walks):

1. For each of the four known pin-label sources (`LABEL_SOURCES`), collect
   every text shape in the cell: a (pin name, position) pair.
2. Group those by pin name -- a cell's `Y` pin, say, may carry several label
   occurrences at different points along its routed shape.
3. For each occurrence, look for the KLayout ".pin"-purpose shape (datatype
   16) on that label's `PIN_TARGET_LAYER` that contains the label's point.
   Not every occurrence needs to land inside one: some labels mark the same
   net at a second or third point along an internal wire without a distinct
   pin marker directly underneath (observed on `sky130_fd_sc_hd__and2b_2`,
   for instance) -- that is a redundant label, not evidence of anything.
4. A pin is resolved once *at least one* of its occurrences lands inside a
   ``.pin`` shape; its geometry is the de-duplicated union of every such
   shape found, across every occurrence.

Resolution is total-or-loud: a pin name with *zero* occurrences landing in a
``.pin`` shape is a hard error naming the cell and the pin -- never a
silently empty or skipped pin (issue #1's contract; this is what lets stage 4
treat the abstract as ground truth rather than a best-effort guess).

Both public views of this abstract -- `resolve_cell_pins` (JSON-ready
micron polygons) and `resolve_cell_pin_shapes` (native `db.Polygon` shapes
for `tools/gds_extract.py`) -- consume the same ordered match list from one
shared search, `_match_pin_shapes` (issue #164); each view then applies
only its own representation and deduplication rule.

Callers must have already made `klayout.db` importable (`klayout_env.py`)
before importing this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from gds_layers import LABEL_SOURCES, LIBRARY_PREFIX, PIN_DATATYPE, PIN_TARGET_LAYER
from klayout import db


class PinResolutionError(RuntimeError):
    """A pin could not be resolved from the stream. Names the cell and pin.

    Never raised for "this cell has no pins of this kind" (e.g. a fill cell
    with no signal pins) -- only for a label that was found but whose
    geometry could not be pinned down, which is the actual "guessing would
    be required past this point" case issue #1 asks to fail loudly on.
    """


Point = tuple[float, float]
Polygon = tuple[Point, ...]


@dataclass(frozen=True)
class PinGeometry:
    layer: tuple[int, int]  # (layer number, datatype) of the resolved shape
    polygons: tuple[Polygon, ...]

    def to_json(self) -> dict:
        return {
            "layer": f"{self.layer[0]}/{self.layer[1]}",
            "polygons": [[list(pt) for pt in poly] for poly in self.polygons],
        }


@dataclass
class CellPins:
    cell: str
    pins: dict[str, PinGeometry] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"pins": {name: geom.to_json() for name, geom in sorted(self.pins.items())}}


def _round_digits(dbu: float) -> int:
    """How many decimal (micron) digits round-trip the stream's own dbu grid."""
    return max(0, -round(math.log10(dbu)))


def _polygon_points(dbu: float, poly) -> Polygon:
    dpoly = poly.to_dtype(dbu)
    ndigits = _round_digits(dbu)
    return tuple((round(pt.x, ndigits), round(pt.y, ndigits)) for pt in dpoly.each_point_hull())


def _match_pin_shapes(layout, cell) -> dict[str, list[tuple[int, db.Polygon]]]:
    """The one label-to-shape search both public resolvers share (issue #164).

    Returns pin name -> every matching `(target_layer_number, db.Polygon)`
    pair in label-occurrence then shape order, with *no* deduplication:
    each resolver applies its own representation and dedup rule to the same
    match list, so the two can never disagree about which pins resolve.

    Raises `PinResolutionError` naming the cell, the pin and its occurrence
    count for the first name whose occurrences all miss -- the
    total-or-loud contract (issue #1), enforced once here instead of twice.
    """
    dbu = layout.dbu
    # name -> list of (target_layer_number, occurrence point, in dbu units)
    occurrences: dict[str, list[tuple[int, object]]] = {}
    for layer_num, datatype in LABEL_SOURCES:
        target_layer = PIN_TARGET_LAYER[(layer_num, datatype)]
        li = layout.layer(layer_num, datatype)
        for shape in cell.each_shape(li):
            if not shape.is_text():
                continue
            name = shape.text.string
            occurrences.setdefault(name, []).append((target_layer, shape.text_pos))

    matches: dict[str, list[tuple[int, db.Polygon]]] = {}
    for name, occs in sorted(occurrences.items()):
        found: list[tuple[int, db.Polygon]] = []
        for target_layer, pos in occs:
            # `text_pos` is a Point in dbu (integer) units; the shape
            # geometry is converted to microns via `to_dtype(dbu)`,
            # so the containment test needs the point in the same units.
            pt = db.DPoint(pos.x * dbu, pos.y * dbu)
            pin_li = layout.layer(target_layer, PIN_DATATYPE)
            for pshape in cell.each_shape(pin_li):
                if pshape.is_text():
                    continue
                poly = pshape.polygon
                if poly is None:
                    continue
                if not poly.to_dtype(dbu).inside(pt):
                    continue
                found.append((target_layer, poly))
        if not found:
            raise PinResolutionError(
                f"{cell.name}: pin {name!r} has {len(occs)} label occurrence(s) but none "
                f"land inside a .pin (datatype {PIN_DATATYPE}) shape on the expected "
                f"layer -- cannot resolve this pin's geometry from the stream"
            )
        matches[name] = found
    return matches


def resolve_cell_pins(layout, cell) -> CellPins:
    """Build the pin abstract for one cell definition.

    Raises `PinResolutionError` naming the cell and pin on the first pin
    that cannot be fully resolved.
    """
    dbu = layout.dbu
    result = CellPins(cell=cell.name)
    for name, found in _match_pin_shapes(layout, cell).items():
        seen_polys: set[Polygon] = set()
        polys: list[Polygon] = []
        resolved_layer: tuple[int, int] | None = None
        for target_layer, poly in found:
            points = _polygon_points(dbu, poly)
            if points not in seen_polys:
                seen_polys.add(points)
                polys.append(points)
            # Every matching occurrence re-affirms the layer, so a pin whose
            # geometry appears on more than one target layer reports the
            # last one -- where the native view below keeps the first.
            resolved_layer = (target_layer, PIN_DATATYPE)
        assert resolved_layer is not None
        result.pins[name] = PinGeometry(layer=resolved_layer, polygons=tuple(polys))
    return result


def resolve_cell_pin_shapes(layout, cell) -> dict[str, list[tuple[int, db.Polygon]]]:
    """Like `resolve_cell_pins`, but returns native, untransformed `db.Polygon`
    shapes (dbu-integer, cell-local coordinates) instead of JSON-ready micron
    tuples -- for a caller (`tools/gds_extract.py`, issue #2) that needs to
    apply an instance placement transform (`db.Trans`/`db.DCplxTrans`) to get
    top-level geometry, where re-parsing rounded micron floats back out of
    `resolve_cell_pins`' output would be lossy and redundant.

    Same total-or-loud contract as `resolve_cell_pins` and the same
    "at least one occurrence must land inside a `.pin` shape" rule -- both
    views consume the same ordered match list from `_match_pin_shapes`
    (issue #164), so they can never disagree about which pins resolve. Only
    the representation differs: this view deduplicates by native geometry
    and keeps the first layer a given geometry was found on, where
    `resolve_cell_pins` keeps micron rounding and reports the last matching
    layer.

    Returns: pin name -> list of `(target_layer_number, db.Polygon)`, one
    entry per distinct resolved shape (a pin's geometry may be more than one
    polygon, same as `resolve_cell_pins`).
    """
    result: dict[str, list[tuple[int, db.Polygon]]] = {}
    for name, found in _match_pin_shapes(layout, cell).items():
        seen: set[str] = set()
        shapes: list[tuple[int, db.Polygon]] = []
        for target_layer, poly in found:
            key = poly.to_s()
            if key not in seen:
                seen.add(key)
                shapes.append((target_layer, poly))
        result[name] = shapes
    return result


def library_cell_names(layout) -> list[str]:
    """Every distinct `sky130_fd_sc_hd__*` cell *definition* in the layout."""
    return sorted({c.name for c in layout.each_cell() if c.name.startswith(LIBRARY_PREFIX)})
