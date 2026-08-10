#!/usr/bin/env python3
"""Lead 1: decode the off-die strip on GDS layer 200/0 of puzzle/puzzle.gds.

The strip sits below the die (y = -52.72..-50.00 um) and is composed of the
36 INTERNAL_3 / INTERNAL_7 placements (one rectangle each). Rectangle widths
come in exactly two sizes with a 1:3 ratio, and inter-rectangle gaps come in
1, 3, and 7 units — International Morse code geometry. Everything below is
measured from the GDS; nothing is assumed.

Run from the repo root (needs an interpreter with the `klayout` module, e.g.
the one behind `klt`; `tools/klayout_env.py` resolves it):

    PYTHONPATH=. python3 evidence/easter-egg-morse-strip.py

Also writes `evidence/easter-egg-morse-strip.svg`, a to-scale rendering.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.klayout_env import ensure_klayout

ensure_klayout()
import klayout.db as db  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDS = os.path.join(REPO, "puzzle", "puzzle.gds")
SVG = os.path.join(REPO, "evidence", "easter-egg-morse-strip.svg")

MORSE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
    ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9",
}


def main():
    ly = db.Layout()
    ly.read(GDS)
    top = ly.top_cell()
    dbu = ly.dbu
    li = ly.layer(200, 0)

    rects = []
    it = top.begin_shapes_rec(li)
    while not it.at_end():
        sh = it.shape()
        p = sh.polygon.transformed(it.trans())
        bb = p.bbox()
        rects.append((bb.left, bb.right, bb.bottom, bb.top, it.cell().name))
        it.next()
    rects.sort()

    print(f"layer 200/0 shapes: {len(rects)}")
    cells = sorted({r[4] for r in rects})
    print(f"defining cells: {', '.join(cells)}")
    y0 = min(r[2] for r in rects) * dbu
    y1 = max(r[3] for r in rects) * dbu
    x0 = min(r[0] for r in rects) * dbu
    x1 = max(r[1] for r in rects) * dbu
    print(f"strip bbox um: ({x0:.2f},{y0:.2f}) - ({x1:.2f},{y1:.2f})")

    widths = sorted(r[1] - r[0] for r in rects)
    unit = widths[0]
    print(f"rect widths um: min {widths[0]*dbu:.2f} max {widths[-1]*dbu:.2f} "
          f"(unit = {unit*dbu:.2f})")

    def units(v):
        return round(v / unit)

    symbols = []
    prev_right = None
    for left, right, _, _, _ in rects:
        w = units(right - left)
        sym = {1: ".", 3: "-"}.get(w)
        assert sym is not None, f"width {w} units is neither dot(1) nor dash(3)"
        gap = units(left - prev_right) if prev_right is not None else 0
        symbols.append((sym, gap))
        prev_right = right

    print("gaps seen (units):", sorted({g for _, g in symbols if g}))

    words, letter = [""], ""
    for sym, gap in symbols:
        if gap >= 7:
            words[-1] += MORSE.get(letter, f"<{letter}?>")
            words.append("")
            letter = ""
        elif gap >= 3:
            words[-1] += MORSE.get(letter, f"<{letter}?>")
            letter = ""
        letter += sym
    words[-1] += MORSE.get(letter, f"<{letter}?>")

    print("morse:", " ".join(s for s, _ in symbols))
    print("DECODED:", " ".join(words))

    # to-scale SVG record
    sx = 2000.0 / (x1 - x0)
    h = max(1, int((y1 - y0) * sx))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="{h}" '
        f'viewBox="0 0 2000 {h}">',
        f'<rect width="2000" height="{h}" fill="white"/>',
    ]
    for left, right, bot, top_, _ in rects:
        rx = (left * dbu - x0) * sx
        rw = (right - left) * dbu * sx
        ry = (y1 - top_ * dbu) * sx
        rh = (top_ - bot) * dbu * sx
        parts.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" '
                     f'height="{rh:.1f}" fill="black"/>')
    parts.append("</svg>")
    with open(SVG, "w") as fh:
        fh.write("\n".join(parts))
    print(f"wrote {os.path.relpath(SVG, REPO)}")


if __name__ == "__main__":
    main()
