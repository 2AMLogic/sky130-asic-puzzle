#!/usr/bin/env python3
"""Independent review addendum, claim 7: re-read the layer 200/0 strip.

Independent of evidence/easter-egg-morse-strip.py: uses gdstk (not klayout)
to flatten the layout, measures every polygon on layer 200/0 in database
units (no unit inference from the smallest width — the dot/dash threshold is
derived from the measured width histogram instead), and decodes with its own
Morse table. Reports every rectangle's exact width and gap so a reader can
re-derive the decode by hand.

Run from the repo root:  python3 evidence/independent-review-addendum-morse.py
"""

import sys
from pathlib import Path

import gdstk

REPO = Path(__file__).resolve().parent.parent
GDS = REPO / "puzzle" / "puzzle.gds"

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}
FROM_MORSE = {v: k for k, v in MORSE.items()}


def main():
    lib = gdstk.read_gds(str(GDS))
    print(f"gdstk {gdstk.__version__}; unit={lib.unit} precision={lib.precision}")
    tops = lib.top_level()
    print(f"top cells: {[c.name for c in tops]}")
    top = tops[0]
    polys = top.get_polygons(depth=None, layer=200, datatype=0)
    print(f"layer 200/0 polygons (flattened): {len(polys)}")

    # gdstk returns coordinates in microns; snap to integer nanometres so
    # equality tests are exact (the GDS database grid is 1 nm here).
    rects = []
    for p in polys:
        pts = [(round(x * 1000), round(y * 1000)) for x, y in p.points]
        xs = sorted(pt[0] for pt in pts)
        ys = sorted(pt[1] for pt in pts)
        # verify each polygon is an axis-aligned rectangle
        if len(pts) != 4 or len(set(xs)) != 2 or len(set(ys)) != 2:
            print(f"NON-RECTANGLE on 200/0: {pts}")
            sys.exit(1)
        rects.append((xs[0], xs[-1], ys[0], ys[-1]))
    rects.sort()

    x0 = min(r[0] for r in rects)
    x1 = max(r[1] for r in rects)
    y0 = min(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    print(f"strip bbox um: ({x0/1000:.2f},{y0/1000:.2f}) - "
          f"({x1/1000:.2f},{y1/1000:.2f})")
    heights = sorted({r[3] - r[2] for r in rects})
    print(f"distinct heights nm: {heights}")

    widths = sorted({r[1] - r[0] for r in rects})
    print(f"distinct widths nm: {widths}")
    if len(widths) != 2:
        print("EXPECTED exactly two distinct widths (dot, dash)")
        sys.exit(1)
    dot_w, dash_w = widths
    print(f"dash/dot width ratio: {dash_w / dot_w:.4f}")

    print("\nidx  left_nm  width_nm  gap_before_nm  symbol  gap_units")
    symbols = []
    prev_right = None
    for i, (left, right, _, _) in enumerate(rects):
        w = right - left
        sym = "." if w == dot_w else "-"
        gap = left - prev_right if prev_right is not None else 0
        gap_units, resid = divmod(gap, dot_w) if prev_right is not None else (0, 0)
        if prev_right is not None and resid != 0:
            print(f"NON-INTEGER GAP at idx {i}: {gap} nm")
            sys.exit(1)
        print(f"{i:3d}  {left:8d}  {w:8d}  {gap:13d}  {sym:^6}  {gap_units}")
        symbols.append((sym, gap_units))
        prev_right = right

    # decode: gap 1 = intra-letter, 3 = letter break, 7 = word break
    words, letter = [[]], ""
    for sym, gap in symbols:
        if gap >= 7:
            words[-1].append(letter)
            words.append([])
            letter = ""
        elif gap >= 3:
            words[-1].append(letter)
            letter = ""
        letter += sym
    words[-1].append(letter)
    decoded = " ".join("".join(FROM_MORSE.get(tok, f"<{tok}?>") for tok in w)
                       for w in words)
    print("\nmorse letters:", " / ".join(" ".join(w) for w in words))
    print("DECODED:", decoded)


if __name__ == "__main__":
    main()
