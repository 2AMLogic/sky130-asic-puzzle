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

Callers must have already made `klayout.db` importable (`klayout_env.py`)
before importing this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import klayout.db as db

from gds_layers import LABEL_SOURCES, LIBRARY_PREFIX, PIN_DATATYPE, PIN_TARGET_LAYER


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
    return max(0, -int(round(math.log10(dbu))))


def _polygon_points(dbu: float, shape) -> Polygon:
    poly = shape.polygon
    if poly is None:
        return ()
    dpoly = poly.to_dtype(dbu)
    ndigits = _round_digits(dbu)
    return tuple((round(pt.x, ndigits), round(pt.y, ndigits)) for pt in dpoly.each_point_hull())


def resolve_cell_pins(layout, cell) -> CellPins:
    """Build the pin abstract for one cell definition.

    Raises `PinResolutionError` naming the cell and pin on the first pin
    that cannot be fully resolved.
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

    result = CellPins(cell=cell.name)
    for name, occs in sorted(occurrences.items()):
        seen_polys: set[Polygon] = set()
        polys: list[Polygon] = []
        resolved_layer: tuple[int, int] | None = None
        for target_layer, pos in occs:
            # `text_pos` is a Point in dbu (integer) units; the shape
            # geometry below is converted to microns via `to_dtype(dbu)`,
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
                points = _polygon_points(dbu, pshape)
                if points not in seen_polys:
                    seen_polys.add(points)
                    polys.append(points)
                resolved_layer = (target_layer, PIN_DATATYPE)
        if not polys:
            raise PinResolutionError(
                f"{cell.name}: pin {name!r} has {len(occs)} label occurrence(s) but none "
                f"land inside a .pin (datatype {PIN_DATATYPE}) shape on the expected "
                f"layer -- cannot resolve this pin's geometry from the stream"
            )
        assert resolved_layer is not None
        result.pins[name] = PinGeometry(layer=resolved_layer, polygons=tuple(polys))
    return result


def library_cell_names(layout) -> list[str]:
    """Every distinct `sky130_fd_sc_hd__*` cell *definition* in the layout."""
    return sorted({c.name for c in layout.each_cell() if c.name.startswith(LIBRARY_PREFIX)})
