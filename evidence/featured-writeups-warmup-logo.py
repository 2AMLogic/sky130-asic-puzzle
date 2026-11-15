"""Addendum (2026-11-14): the Jane Street logo is in the warm-up layout too.

Two of the 15 featured writeups say so in passing -- Sanjay Ravishankar
("the Jane Street logo inscribed into both the warmup and puzzle layouts")
and David Garner ("the logo had been drawn in MET2 on the lower-left of the
puzzle, which was also the case with the warmup albeit in that case in the
upper-right"). This record found the glyph in `puzzle.gds` only
(`evidence/easter-egg-met2-ring.py`, 1,366 tiles) and never looked at
`warmup/04_final.gds`.

This script isolates the isolated small met2 (69/20) squares in both layouts,
counts them, reports where each sits relative to its own die, and then
normalises both tile sets to their own lower-left corner and compares them,
so "the same glyph" is a set equality rather than an impression.

Run from the repo root after `./scripts/fetch-puzzle.sh` (needs an
interpreter with the `klayout` module, which `tools/klayout_env.py` resolves):

    PYTHONPATH=. python3 evidence/featured-writeups-warmup-logo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.klayout_env import ensure_klayout

ensure_klayout()
import klayout.db as db  # noqa: E402

MET2 = (69, 20)
MAX_SIDE = 0.6   # um; routing wires on met2 are far longer than the glyph tiles
SQUARE_TOL = 0.05

LAYOUTS = [
    ("puzzle", "puzzle/puzzle.gds"),
    ("warm-up", "puzzle/warmup/04_final.gds"),
]


def glyph_tiles(path):
    layout = db.Layout()
    layout.read(path)
    top = layout.top_cell()
    dbu = layout.dbu
    layer = layout.layer(*MET2)
    total = 0
    tiles = []
    it = top.begin_shapes_rec(layer)
    while not it.at_end():
        bb = it.shape().polygon.transformed(it.trans()).bbox()
        w = (bb.right - bb.left) * dbu
        h = (bb.top - bb.bottom) * dbu
        total += 1
        if abs(w - h) < SQUARE_TOL and w < MAX_SIDE:
            tiles.append((round(bb.left * dbu, 3), round(bb.bottom * dbu, 3), round(w, 3)))
        it.next()
    return total, tiles, top.dbbox()


def main():
    results = {}
    for name, path in LAYOUTS:
        if not os.path.exists(path):
            print(f"missing {path} — run ./scripts/fetch-puzzle.sh", file=sys.stderr)
            return 2
        total, tiles, die = glyph_tiles(path)
        xs = [t[0] for t in tiles]
        ys = [t[1] for t in tiles]
        sides = sorted({t[2] for t in tiles})
        print(f"{name}:")
        print(f"  met2 shapes: {total}; isolated square tiles: {len(tiles)}; "
              f"tile side(s) um: {sides}")
        print(f"  glyph bbox um: x[{min(xs):.1f}, {max(xs):.1f}] "
              f"y[{min(ys):.1f}, {max(ys):.1f}]")
        print(f"  die bbox um:   x[{die.left:.1f}, {die.right:.1f}] "
              f"y[{die.bottom:.1f}, {die.top:.1f}]")
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        half_x = (die.left + die.right) / 2
        half_y = (die.bottom + die.top) / 2
        where = ("upper" if cy > half_y else "lower") + "-" + \
                ("right" if cx > half_x else "left")
        print(f"  position on the die: {where}")
        results[name] = (min(xs), min(ys), tiles)

    (px, py, pt), (wx, wy, wt) = results["puzzle"], results["warm-up"]
    print(f"\noffset warm-up -> puzzle: dx={wx - px:+.3f} um dy={wy - py:+.3f} um")
    norm_p = {(round(x - px, 3), round(y - py, 3)) for x, y, _ in pt}
    norm_w = {(round(x - wx, 3), round(y - wy, 3)) for x, y, _ in wt}
    print(f"normalised tile sets: puzzle {len(norm_p)}, warm-up {len(norm_w)}")
    print(f"symmetric difference: {len(norm_p ^ norm_w)}")
    print(f"identical glyph: {norm_p == norm_w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
