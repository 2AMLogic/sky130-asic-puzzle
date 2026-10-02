"""Post-results (2026-10-02): the message hidden in example_inputs.vcd.

Jane Street's results post says the two failed attempts in the example VCD
decode as 7-bit ASCII to "THE NIGHT SKY AWAITS", without saying how. This
script finds the encoding: each attempt is the usual 121-bit word fed one
bit per enabled clock, read as an 11x11 grid in feed order; the first seven
cells of each row, LSB first, are one character. Eleven rows per attempt,
two attempts, 22 characters.

Run from the repo root after `./scripts/fetch-puzzle.sh`:

    python3 evidence/easter-egg-vcd-night-sky.py
"""

import re
from pathlib import Path

VCD = Path("puzzle/example_inputs.vcd")
CLK, RST_N, EN, I = "!", '"', "#", "$"


def attempts(path):
    """Sample I on each rising clk edge while rst_n and enable are high."""
    state = {CLK: "0", RST_N: "0", EN: "0", I: "0"}
    words, cur = [], []
    for line in path.read_text().splitlines():
        m = re.fullmatch(r"([01x])([!\"#$])", line.strip())
        if not m:
            continue
        value, sig = m.groups()
        if sig == CLK and value == "1" and state[CLK] == "0":
            if state[RST_N] == "1" and state[EN] == "1":
                cur.append(state[I])
            elif cur:
                words.append("".join(cur))
                cur = []
        state[sig] = value
    if cur:
        words.append("".join(cur))
    return words


def decode(word):
    rows = [word[r * 11:(r + 1) * 11] for r in range(11)]
    return "".join(chr(int(row[:7][::-1], 2)) for row in rows)


words = attempts(VCD)
print(f"attempts: {len(words)}, lengths {[len(w) for w in words]}")
for n, w in enumerate(words):
    print(f"attempt {n}: {w}")
    for r in range(11):
        row = w[r * 11:(r + 1) * 11]
        print(f"  row {r:2}: {row[:7]} {row[7:]}  -> {decode(row + '0' * 110)[0]!r}")
message = "".join(decode(w) for w in words)
print(f"message: {message!r}")
assert message.strip().upper() == "THE NIGHT SKY AWAITS", message
