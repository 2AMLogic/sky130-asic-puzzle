#!/usr/bin/env python3
"""Independent re-derivation of claim 7 with different tooling.

`easter-egg-morse-strip.py` reads layer 200/0 through KLayout. This script
shares none of that path: it parses the GDSII stream binary itself —
records, structures, BOUNDARY/XY payloads, SREF placements — using only the
Python standard library, resolves the 200/0 rectangles through the
placement transforms, and decodes the Morse geometry with its own table.
Agreement between the two scripts is agreement between two unrelated
readers of the same bytes.

Run from the repo root:

    python3 evidence/easter-egg-morse-independent.py
"""

import os
import struct

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDS = os.path.join(REPO, "puzzle", "puzzle.gds")

# GDSII record types used
BGNSTR, STRNAME, ENDSTR = 0x0502, 0x0606, 0x0700
BOUNDARY, SREF, AREF = 0x0800, 0x0A00, 0x0B00
LAYER, DATATYPE, XY, ENDEL = 0x0D02, 0x0E02, 0x1003, 0x1100
SNAME, STRANS, MAG, ANGLE = 0x1206, 0x1A01, 0x1B05, 0x1C05
UNITS, ENDLIB = 0x0305, 0x0400

MORSE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z",
}


def gds_real(b):
    """GDSII 8-byte real: sign bit, excess-64 base-16 exponent, 7-byte mantissa."""
    if len(b) != 8:
        raise ValueError("bad real length")
    sign = -1.0 if b[0] & 0x80 else 1.0
    exp = (b[0] & 0x7F) - 64
    mant = 0
    for byte in b[1:]:
        mant = (mant << 8) | byte
    return sign * mant * (16.0 ** exp) / (2.0 ** 56)


def records(path):
    data = open(path, "rb").read()
    i = 0
    while i < len(data):
        (length,) = struct.unpack(">H", data[i:i + 2])
        rectype = struct.unpack(">H", data[i + 2:i + 4])[0]
        payload = data[i + 4:i + length]
        yield rectype, payload
        if rectype == ENDLIB:
            return
        i += length


def main():
    cells = {}      # name -> list of (layer, datatype, [(x,y)...])
    placements = {}  # name -> list of (sname, x, y, mirror, angle_deg)
    cur = None
    elem = None
    for rectype, payload in records(GDS):
        if rectype == STRNAME:
            cur = payload.rstrip(b"\x00").decode()
            cells[cur] = []
            placements[cur] = []
        elif rectype == ENDSTR:
            cur = None
        elif rectype == BOUNDARY:
            elem = {"kind": "boundary"}
        elif rectype in (SREF, AREF):
            elem = {"kind": "sref", "mirror": False, "angle": 0.0}
        elif rectype == LAYER and elem is not None:
            elem["layer"] = struct.unpack(">h", payload)[0]
        elif rectype == DATATYPE and elem is not None:
            elem["datatype"] = struct.unpack(">h", payload)[0]
        elif rectype == SNAME and elem is not None:
            elem["sname"] = payload.rstrip(b"\x00").decode()
        elif rectype == STRANS and elem is not None:
            elem["mirror"] = bool(struct.unpack(">H", payload)[0] & 0x8000)
        elif rectype == ANGLE and elem is not None:
            elem["angle"] = gds_real(payload)
        elif rectype == MAG and elem is not None:
            mag = gds_real(payload)
            if abs(mag - 1.0) > 1e-9:
                raise SystemExit(f"unsupported MAG {mag}")
        elif rectype == XY and elem is not None:
            n = len(payload) // 4
            coords = struct.unpack(f">{n}i", payload)
            elem["xy"] = list(zip(coords[0::2], coords[1::2]))
        elif rectype == ENDEL and elem is not None:
            if elem["kind"] == "boundary":
                cells[cur].append((elem.get("layer"), elem.get("datatype"),
                                   elem["xy"]))
            else:
                x, y = elem["xy"][0]
                placements[cur].append((elem["sname"], x, y,
                                        elem["mirror"], elem["angle"]))
            elem = None

    print(f"structures parsed: {len(cells)}")

    # which cells hold 200/0 geometry directly?
    carriers = {n: [(l, d, xy) for (l, d, xy) in geo if l == 200 and d == 0]
                for n, geo in cells.items()}
    carriers = {n: g for n, g in carriers.items() if g}
    print("cells with 200/0 geometry:",
          {n: len(g) for n, g in sorted(carriers.items())})

    # resolve through top-cell placements (translation-only expected)
    rects = []
    for sname, x, y, mirror, angle in placements["puzzle"]:
        if sname not in carriers:
            continue
        if mirror or angle not in (0.0,):
            raise SystemExit(
                f"placement of {sname} uses mirror={mirror} angle={angle}; "
                "this independent decoder only handles translation")
        for _, _, xy in carriers[sname]:
            xs = [px + x for px, _ in xy]
            ys = [py + y for _, py in xy]
            rects.append((min(xs), max(xs), min(ys), max(ys)))
    rects.sort()
    print(f"placed 200/0 rectangles: {len(rects)}")
    ys0 = {r[2] for r in rects}
    ys1 = {r[3] for r in rects}
    print(f"strip y (dbu): bottom {sorted(ys0)} top {sorted(ys1)}")

    widths = sorted(r[1] - r[0] for r in rects)
    unit = widths[0]
    print(f"widths (dbu): min {widths[0]} max {widths[-1]} unit {unit}")

    def units(v):
        q, r = divmod(v, unit)
        if r:
            raise SystemExit(f"{v} dbu is not a whole number of units")
        return q

    words, letter = [""], ""
    prev = None
    for left, right, _, _ in rects:
        w = units(right - left)
        sym = {1: ".", 3: "-"}[w]
        gap = units(left - prev) if prev is not None else 0
        if gap >= 7:
            words[-1] += MORSE[letter]
            words.append("")
            letter = ""
        elif gap >= 3:
            words[-1] += MORSE[letter]
            letter = ""
        letter += sym
        prev = right
    words[-1] += MORSE[letter]
    print("INDEPENDENT DECODE:", " ".join(words))


if __name__ == "__main__":
    main()
