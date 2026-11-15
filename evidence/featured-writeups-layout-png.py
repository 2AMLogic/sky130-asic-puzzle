"""Reproducer for the `layout.png` figures quoted in easter-eggs.md, entry 6
(Lokesh Aravapalli's `EGG'` string): where the string sits in the file, that
it disappears when the image data is decompressed, and how many other runs of
four or more ASCII letters the file holds — the basis for this record's
"unverified and almost certainly coincidental" call.

Reads only `puzzle/layout.png` (gitignored; `scripts/fetch-puzzle.sh`). Run
from the repo root:

    python3 evidence/featured-writeups-layout-png.py
"""

import re
import sys
import zlib
from pathlib import Path

PNG = Path("puzzle/layout.png")


def idat_bytes(raw):
    pos, idat = 8, bytearray()
    while pos < len(raw):
        length = int.from_bytes(raw[pos:pos + 4], "big")
        if raw[pos + 4:pos + 8] == b"IDAT":
            idat += raw[pos + 8:pos + 8 + length]
        pos += 12 + length
    return bytes(idat)


def main():
    raw = PNG.read_bytes()
    print(f"layout.png: {len(raw):,} bytes")
    eggs = [m.start() for m in re.finditer(rb"EGG'", raw)]
    print("EGG' offsets in the raw file:", eggs)
    runs = re.findall(rb"[A-Za-z]{4,}", raw)
    print(f"runs of >=4 ASCII letters in the raw file: {len(runs)}")

    inflated = zlib.decompress(idat_bytes(raw))
    print(f"inflated IDAT bytes: {len(inflated):,}")
    print("EGG' occurrences after decompression:",
          len(re.findall(rb"EGG'", inflated)))
    print("runs of >=4 ASCII letters after decompression:",
          len(re.findall(rb"[A-Za-z]{4,}", inflated)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
