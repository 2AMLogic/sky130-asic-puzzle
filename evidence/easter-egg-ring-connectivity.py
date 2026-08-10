#!/usr/bin/env python3
"""Attack claim 8's weakest assertion: the met2 ring glyph is "connected to
nothing". The original claim came from cluster isolation; this script tests
it geometrically with KLayout boolean Region interactions instead — a
different method than the one that produced the claim.

Electrical connection to a met2 shape requires met2-to-met2 contact or a
via1/via2 landing on it; met1/met3 crossing the same XY without a via is an
underpass/overpass, not a connection, and is reported as information only.
The same interaction test is applied to the 36 Morse rectangles on 200/0
against every other layer in the stream.

Run from the repo root:

    PYTHONPATH=. python3 evidence/easter-egg-ring-connectivity.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.klayout_env import ensure_klayout

ensure_klayout()
import klayout.db as db  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDS = os.path.join(REPO, "puzzle", "puzzle.gds")

WINDOW = db.DBox(34.0, 33.0, 54.0, 53.0)  # um, generous around the glyph
TILE = 0.300  # um, the glyph's tile size


def region_of(ly, top, layer, datatype, clip=None):
    li = ly.layer(layer, datatype)
    r = db.Region(top.begin_shapes_rec(li))
    if clip is not None:
        r &= db.Region(clip.to_itype(ly.dbu))
    return r


def main():
    ly = db.Layout()
    ly.read(GDS)
    top = ly.top_cell()
    dbu = ly.dbu

    met2 = region_of(ly, top, 69, 20, WINDOW)
    tiles = db.Region()
    other_met2 = db.Region()
    for p in met2.each():
        bb = p.bbox()
        if (abs(bb.width() * dbu - TILE) < 1e-6
                and abs(bb.height() * dbu - TILE) < 1e-6):
            tiles.insert(p)
        else:
            other_met2.insert(p)
    print(f"glyph tiles: {tiles.count()}  "
          f"other met2 shapes in window: {other_met2.count()}")

    electrical = [
        ("met2 (non-tile)", other_met2),
        ("via1 68/44", region_of(ly, top, 68, 44, WINDOW)),
        ("via2 69/44", region_of(ly, top, 69, 44, WINDOW)),
    ]
    informational = [
        ("met1 68/20", region_of(ly, top, 68, 20, WINDOW)),
        ("met3 70/20", region_of(ly, top, 70, 20, WINDOW)),
    ]
    all_clear = True
    for name, reg in electrical:
        n = reg.interacting(tiles).count()
        all_clear &= (n == 0)
        print(f"  electrical {name}: {reg.count()} shapes in window, "
              f"{n} interacting with glyph tiles")
    for name, reg in informational:
        n = reg.interacting(tiles).count()
        print(f"  projection-only {name}: {reg.count()} shapes in window, "
              f"{n} crossing under/over the glyph (no via -> no connection)")
    print("RING VERDICT:",
          "ELECTRICALLY UNCONNECTED — no met2 contact and no via lands on it"
          if all_clear else "CONNECTED — see electrical interactions above")

    # Morse strip: 200/0 versus every other layer in the stream
    strip = region_of(ly, top, 200, 0)
    print(f"\nmorse strip shapes: {strip.count()}")
    dirty = 0
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        if info.layer == 200 and info.datatype == 0:
            continue
        reg = db.Region(top.begin_shapes_rec(li))
        n = reg.interacting(strip).count()
        if n:
            print(f"  {info}: {n} shapes interacting with strip")
            dirty += n
    print("STRIP VERDICT:",
          "ISOLATED — no other layer's geometry touches the strip"
          if dirty == 0 else "NOT ISOLATED — see interactions above")


if __name__ == "__main__":
    main()
