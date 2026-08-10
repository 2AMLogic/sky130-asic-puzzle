#!/usr/bin/env python3
"""Close the fixed-window caveat on claim 8: survey the ENTIRE die for
met2 glyph candidates, instead of trusting the 20x20 um search window.

A glyph candidate is what the known ring is: a dense cluster of 0.30 um
square met2 tiles with no ordinary met2 wiring inside its bounding box.
This script collects every exactly-0.30-um-square met2 shape in the whole
layout, clusters them by 2 um adjacency, and reports each cluster with its
tile count, bounding box, and the number of non-tile met2 shapes whose
bounding boxes overlap the cluster box. Clusters interleaved with routing
are wire stubs/jogs; a dense cluster with zero interleave is artwork.

Run from the repo root (needs an interpreter with the `klayout` module;
`tools/klayout_env.py` resolves it):

    PYTHONPATH=. python3 evidence/easter-egg-glyph-survey.py
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.klayout_env import ensure_klayout

ensure_klayout()
import klayout.db as db  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDS = os.path.join(REPO, "puzzle", "puzzle.gds")

TILE = 0.300     # um
GRID = 2.0       # um clustering adjacency
MIN_TILES = 50   # report clusters at least this large


def main():
    ly = db.Layout()
    ly.read(GDS)
    top = ly.top_cell()
    dbu = ly.dbu
    li = ly.layer(69, 20)

    tiles, others = [], []
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        bb = it.shape().polygon.transformed(it.trans()).bbox()
        w, h = bb.width() * dbu, bb.height() * dbu
        box = (bb.left * dbu, bb.bottom * dbu, bb.right * dbu, bb.top * dbu)
        if abs(w - TILE) < 1e-6 and abs(h - TILE) < 1e-6:
            tiles.append(box)
        else:
            others.append(box)
        it.next()
    print(f"met2 shapes: {len(tiles)} exact {TILE} um tiles, "
          f"{len(others)} other")

    # cluster tiles on a GRID um lattice with 8-neighbour merging
    grid = defaultdict(list)
    for b in tiles:
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        grid[(int(cx // GRID), int(cy // GRID))].append(b)
    seen, clusters = set(), []
    for c in grid:
        if c in seen:
            continue
        stack, members = [c], []
        seen.add(c)
        while stack:
            cell = stack.pop()
            members.extend(grid[cell])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (cell[0] + dx, cell[1] + dy)
                    if n in grid and n not in seen:
                        seen.add(n)
                        stack.append(n)
        clusters.append(members)

    print(f"clusters (>= {MIN_TILES} tiles) over the whole die:")
    artwork = []
    for members in sorted(clusters, key=len, reverse=True):
        if len(members) < MIN_TILES:
            continue
        x0 = min(b[0] for b in members)
        y0 = min(b[1] for b in members)
        x1 = max(b[2] for b in members)
        y1 = max(b[3] for b in members)
        interleave = sum(1 for o in others
                         if o[2] > x0 and o[0] < x1
                         and o[3] > y0 and o[1] < y1)
        kind = "ARTWORK-LIKE (no wiring inside)" if interleave == 0 \
            else "routing stubs"
        if interleave == 0:
            artwork.append((len(members), x0, y0, x1, y1))
        print(f"  {len(members):5d} tiles  "
              f"bbox ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})  "
              f"non-tile met2 overlapping bbox: {interleave:4d}  -> {kind}")
    print(f"SURVEY VERDICT: {len(artwork)} artwork-like cluster(s) "
          f"on met2 across the whole die")
    for n, x0, y0, x1, y1 in artwork:
        print(f"  -> {n} tiles at ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")


if __name__ == "__main__":
    main()
