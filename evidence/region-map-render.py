"""Render the recovered Star Battle region map (evidence/easter-eggs.md,
Lead 4) with the accepted word's stars, as a PNG, so the shapes can be read
as a picture. Added 2026-09-08 after another solver's writeup described the
regions as spelling "JS"; see README "Other solutions".

    python3 evidence/region-map-render.py   # writes evidence/region-map.png
"""

from PIL import Image, ImageDraw

REGIONS = [
    "HHHHHCCKFFA",
    "HHIHHCKKFFA",
    "HHICCCCKKFA",
    "HHICGGGAKKA",
    "IHICGAAAAAA",
    "IIICGGGAEEE",
    "CCCCCCGAEBB",
    "CDDDGGGAEBB",
    "CDDJAAAAEBB",
    "CCDJJAAAEEE",
    "CDDJAAAAAAA",
]
ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
COLORS = {
    "A": (230, 25, 75),
    "B": (60, 180, 75),
    "C": (255, 225, 25),
    "D": (0, 130, 200),
    "E": (245, 130, 48),
    "F": (145, 30, 180),
    "G": (70, 240, 240),
    "H": (240, 50, 230),
    "I": (210, 245, 60),
    "J": (250, 190, 190),
    "K": (0, 128, 128),
}
S = 40
im = Image.new("RGB", (11 * S, 11 * S), "white")
d = ImageDraw.Draw(im)
for r in range(11):
    for c in range(11):
        d.rectangle(
            [c * S, r * S, (c + 1) * S - 1, (r + 1) * S - 1],
            fill=COLORS[REGIONS[r][c]],
            outline="black",
        )
        if ACCEPTED[r * 11 + c] == "1":
            d.ellipse(
                [c * S + 10, r * S + 10, c * S + S - 10, r * S + S - 10], fill="black"
            )
im.save("evidence/region-map.png")
for letter in sorted(COLORS):
    print(letter)
    print(
        "\n".join(
            "".join("#" if ch == letter else "." for ch in row) for row in REGIONS
        )
    )
    print()
