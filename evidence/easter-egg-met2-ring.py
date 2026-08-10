#!/usr/bin/env python3
"""Lead 1: characterize the concentric-ring glyph on met2 (GDS 69/20).

met2 signal wires in this layout are long thin paths; the glyph is a compact
cluster of ~0.3 um axis-aligned tiles forming three concentric broken rings,
electrically connected to nothing. This script re-derives the cluster from
the GDS (no coordinates are assumed beyond a generous search window), prints
its statistics, computes each ring's angular arc/gap structure, and writes a
to-scale SVG.

Run from the repo root (needs an interpreter with the `klayout` module, e.g.
the one behind `klt`; `tools/klayout_env.py` resolves it):

    PYTHONPATH=. python3 evidence/easter-egg-met2-ring.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.klayout_env import ensure_klayout

ensure_klayout()
import klayout.db as db  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDS = os.path.join(REPO, "puzzle", "puzzle.gds")
SVG = os.path.join(REPO, "evidence", "easter-egg-met2-ring.svg")

WINDOW = (34.0, 33.0, 54.0, 53.0)  # x0,y0,x1,y1 um search window
BANDS = [(3.5, 5.0), (5.3, 7.0), (7.4, 8.8)]  # ring radial bands, um
NBINS = 720  # 0.5 degree angular bins


def main():
    ly = db.Layout()
    ly.read(GDS)
    top = ly.top_cell()
    dbu = ly.dbu
    li = ly.layer(69, 20)

    x0, y0, x1, y1 = WINDOW
    tiles = []
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        sh = it.shape()
        p = sh.polygon.transformed(it.trans())
        bb = p.bbox()
        if (x0 < bb.left * dbu and bb.right * dbu < x1
                and y0 < bb.bottom * dbu and bb.top * dbu < y1):
            tiles.append((bb.left * dbu, bb.bottom * dbu,
                          bb.right * dbu, bb.top * dbu))
        it.next()

    print(f"met2 tiles inside window {WINDOW}: {len(tiles)}")
    ws = sorted(t[2] - t[0] for t in tiles)
    hs = sorted(t[3] - t[1] for t in tiles)
    print(f"tile width um: min {ws[0]:.3f} med {ws[len(ws)//2]:.3f} max {ws[-1]:.3f}")
    print(f"tile height um: min {hs[0]:.3f} med {hs[len(hs)//2]:.3f} max {hs[-1]:.3f}")

    cx = sum((t[0] + t[2]) / 2 for t in tiles) / len(tiles)
    cy = sum((t[1] + t[3]) / 2 for t in tiles) / len(tiles)
    print(f"glyph center um: ({cx:.2f},{cy:.2f})")
    rmax = max(math.hypot(max(abs(t[0]-cx), abs(t[2]-cx)),
                          max(abs(t[1]-cy), abs(t[3]-cy))) for t in tiles)
    print(f"outer radius um: {rmax:.2f}")

    for lo, hi in BANDS:
        cov = [False] * NBINS
        n = 0
        for tx0, ty0, tx1, ty1 in tiles:
            mx, my = (tx0 + tx1) / 2, (ty0 + ty1) / 2
            r = math.hypot(mx - cx, my - cy)
            if not (lo <= r <= hi):
                continue
            n += 1
            corners = [(tx0, ty0), (tx0, ty1), (tx1, ty0), (tx1, ty1)]
            angs = sorted(math.degrees(math.atan2(py - cy, px - cx)) % 360
                          for px, py in corners)
            b0 = int(angs[0] / 360 * NBINS)
            b1 = int(angs[-1] / 360 * NBINS)
            if angs[-1] - angs[0] > 180:  # tile straddles the 0-degree cut
                for b in range(b1, NBINS):
                    cov[b] = True
                for b in range(0, b0 + 1):
                    cov[b] = True
            else:
                for b in range(b0, b1 + 1):
                    cov[b] = True
        gaps = []
        i = 0
        start = cov.index(True) if True in cov else 0
        while i < NBINS:
            j = (start + i) % NBINS
            if not cov[j]:
                k = i
                while k < NBINS and not cov[(start + k) % NBINS]:
                    k += 1
                a_beg = ((start + i) % NBINS) * 360.0 / NBINS
                gaps.append((a_beg, (k - i) * 360.0 / NBINS))
                i = k
            else:
                i += 1
        covered = sum(cov) * 360.0 / NBINS
        gap_desc = ", ".join(f"{l:.1f} deg at {a:.1f} deg" for a, l in gaps)
        print(f"ring r={lo}-{hi} um: {n} tiles, covered {covered:.1f} deg, "
              f"gaps: {gap_desc if gaps else 'none'}")

    # to-scale SVG
    gx0 = min(t[0] for t in tiles) - 0.5
    gy0 = min(t[1] for t in tiles) - 0.5
    gx1 = max(t[2] for t in tiles) + 0.5
    gy1 = max(t[3] for t in tiles) + 0.5
    sx = 800.0 / (gx1 - gx0)
    h = int((gy1 - gy0) * sx)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{h}" '
        f'viewBox="0 0 800 {h}">',
        f'<rect width="800" height="{h}" fill="white"/>',
    ]
    for tx0, ty0, tx1, ty1 in tiles:
        parts.append(
            f'<rect x="{(tx0-gx0)*sx:.1f}" y="{(gy1-ty1)*sx:.1f}" '
            f'width="{(tx1-tx0)*sx:.1f}" height="{(ty1-ty0)*sx:.1f}" '
            f'fill="black"/>')
    parts.append("</svg>")
    with open(SVG, "w") as fh:
        fh.write("\n".join(parts))
    print(f"wrote {os.path.relpath(SVG, REPO)}")


if __name__ == "__main__":
    main()
