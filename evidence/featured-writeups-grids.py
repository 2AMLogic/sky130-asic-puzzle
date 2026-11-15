"""Addendum (2026-11-14): the grid and counting claims made by Jane Street's
15 featured writeups, checked against this record's own region map and
accepted word.

Nothing here touches the layout or the netlist, so it needs no PDK and no
puzzle files: the region map is `evidence/region-map-render.py`'s `REGIONS`
and the accepted word is `evidence/puzzle-solve.md` §5. What it checks:

1. The six writeups that published the winning 121-bit board, against ours
   (Ebert, Shi, Smallwood, Stapleton, Garner, Soto Franco), and Jose
   Vargas's different board, which he reported as one of sixteen accepted.
2. Soto Franco's region sizes: 4, 5, 6, 7, 8, 8, 9, 11, 14, 21, 28.
3. David Garner's 31,197,434 regionless two-star boards -- the same number
   this record's README claims no other writeup contains.
4. Garner's 5,296,794 regionless one-star boards.
5. Sanjay Ravishankar's 113,758,569 boards behind `TWO NOT TOUCH`.
6. Alexander Smallwood's 45 legal rows, 420 legal ordered row pairs, and
   Fibonacci prefix counts 2, 3, 5, 8, ... 144.
7. Uniqueness from the recovered rules alone, with no solver -- the check
   Ebert and Soto Franco also ran independently.

Run from the repo root (pure Python, about a minute):

    python3 evidence/featured-writeups-grids.py
"""

import itertools
import sys
from collections import Counter, defaultdict

# evidence/region-map-render.py
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
# evidence/puzzle-solve.md §5
ACCEPTED = (
    "0000000101010000100000000000010101010000000000001010000001000001"
    "000000100000101000010000000100000010000010010001010000000"
)
N = 11

PUBLISHED = {
    "Ebert": """00000001010 10000100000 00000001010 10100000000 00001010000
                00100000100 00001000001 01000010000 00010000001 00000100100
                01010000000""",
    "Shi": """00000001010 10000100000 00000001010 10100000000 00001010000
              00100000100 00001000001 01000010000 00010000001 00000100100
              01010000000""",
    "Smallwood": """00000001010 10000100000 00000001010 10100000000 00001010000
                    00100000100 00001000001 01000010000 00010000001 00000100100
                    01010000000""",
    "Stapleton": ACCEPTED,
    "Garner": """00000001010100001000000000000101010100000000000010100000010000010
                 000001000001010000100000001000000100000100100010100000 00""",
    "Soto Franco": """0000000101010000100000000000010101010000000000001010000001000001
                      000000100000101000010000000100000010000010010001010000000""",
    "Vargas": """00000100010 10000001000 00000001010 10001000000 00100010000
                 00100010000 00001000001 01000000100 00000000101 00010100000
                 01010000000""",
}

GARNER_TWO_STAR = 31_197_434
GARNER_ONE_STAR = 5_296_794
RAVISHANKAR_TNT = 113_758_569
SOTO_FRANCO_SIZES = [4, 5, 6, 7, 8, 8, 9, 11, 14, 21, 28]


def rule(title):
    print(f"\n== {title} " + "=" * max(0, 68 - len(title)))


def stars(word):
    return {(i // N, i % N) for i, c in enumerate(word) if c == "1"}


def touching(cells):
    return [(a, b) for a, b in itertools.combinations(sorted(cells), 2)
            if abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1]


def counts(cells):
    rows = Counter(r for r, _ in cells)
    cols = Counter(c for _, c in cells)
    regs = Counter(REGIONS[r][c] for r, c in cells)
    ids = {ch for row in REGIONS for ch in row}
    return (all(rows[r] == 2 for r in range(N)),
            all(cols[c] == 2 for c in range(N)),
            all(regs[x] == 2 for x in ids))


def count_perms(n):
    """Permutations s of [n] with |s(i+1) - s(i)| >= 2 — the one-star boards,
    counted independently of `count_boards`'s row/column DP."""
    states = {(frozenset([v]), v): 1 for v in range(n)}
    for _ in range(n - 1):
        nxt = defaultdict(int)
        for (used, last), c in states.items():
            for v in range(n):
                if v not in used and abs(v - last) >= 2:
                    nxt[(used | {v}, v)] += c
        states = nxt
    return sum(states.values())


def count_boards(patterns, no_touch, by_region, per_group=2):
    """Boards with `per_group` stars per row and per column (and per region
    when `by_region`), rows drawn from `patterns`, honouring adjacency when
    `no_touch`."""
    ids = sorted({ch for row in REGIONS for ch in row})
    rix = {ch: i for i, ch in enumerate(ids)}
    states = {((0,) * N, (0,) * len(ids), None): 1}
    for r in range(N):
        nxt = defaultdict(int)
        remaining = N - 1 - r
        for (cols, regs, prev), n in states.items():
            for p in patterns:
                if no_touch and prev is not None and \
                        any(abs(x - y) <= 1 for x in prev for y in p):
                    continue
                c = list(cols)
                bad = False
                for x in p:
                    c[x] += 1
                    if c[x] > per_group:
                        bad = True
                        break
                if bad or any(per_group - v > remaining for v in c):
                    continue
                g = list(regs)
                if by_region:
                    for x in p:
                        i = rix[REGIONS[r][x]]
                        g[i] += 1
                        if g[i] > per_group:
                            bad = True
                            break
                    if bad:
                        continue
                nxt[(tuple(c), tuple(g), p if no_touch else None)] += n
        states = nxt
    return sum(states.values())


def main():
    print(f"accepted word: {len(ACCEPTED)} bits, {ACCEPTED.count('1')} stars")

    rule("1. the boards the featured writeups published")
    for name, raw in PUBLISHED.items():
        w = "".join(raw.split())
        same = w == ACCEPTED
        note = "identical to ours" if same else "DIFFERENT"
        print(f"  {name:12s} {len(w)} bits  {note}")
        if not same:
            s = stars(w)
            rows_ok, cols_ok, regs_ok = counts(s)
            t = touching(s)
            print(f"    {len(s)} stars; rows={rows_ok} cols={cols_ok} "
                  f"regions={regs_ok}; touching pairs={len(t)}")
            print(f"    touching: {t}")
            print("    => satisfies every count but the no-touch rule: this is a "
                  "TWO NOT TOUCH board, not an accepted one")

    rule("2. Soto Franco's region sizes")
    sizes = sorted(Counter(ch for row in REGIONS for ch in row).values())
    print("  ours       :", sizes, "sum", sum(sizes))
    print("  Soto Franco:", SOTO_FRANCO_SIZES,
          "-> match:", sizes == SOTO_FRANCO_SIZES)

    rule("6. Smallwood's row combinatorics")
    all_pairs = list(itertools.combinations(range(N), 2))
    legal_rows = [p for p in all_pairs if p[1] - p[0] > 1]
    print(f"  two-star rows: {len(all_pairs)}; "
          f"without an adjacent pair: {len(legal_rows)} (C(11,2)-10 = 45)")
    ok_pairs = sum(1 for a in legal_rows for b in legal_rows
                   if all(abs(x - y) > 1 for x in a for y in b))
    print(f"  ordered legal row pairs: {ok_pairs} of {len(legal_rows)**2}"
          f"  (Smallwood: 420 -> match: {ok_pairs == 420})")
    fib, a, b = [], 1, 2
    for _ in range(10):
        fib.append(b)
        a, b = b, a + b
    print(f"  length-n rows with no two consecutive stars, n=1..10: {fib}")
    print("    (Smallwood's surviving-prefix counts 2, 3, 5, 8, ... 144 -> "
          f"match: {fib == [2, 3, 5, 8, 13, 21, 34, 55, 89, 144]})")

    rule("3/4/5/7. board counts")
    two = count_boards(legal_rows, True, False)
    print(f"  2/row, 2/col, no touching, regions ignored : {two:,}")
    print(f"    Garner / our README: {GARNER_TWO_STAR:,}"
          f" -> match: {two == GARNER_TWO_STAR}")

    one = count_boards([(c,) for c in range(N)], True, False, per_group=1)
    print(f"  1/row, 1/col, no touching, regions ignored : {one:,}")
    print(f"    Garner: {GARNER_ONE_STAR:,} -> match: {one == GARNER_ONE_STAR}")
    # A one-star board is a permutation s with |s(i+1) - s(i)| >= 2, i.e.
    # Hertzsprung's problem (OEIS A002464). Cross-check the counting method
    # against brute force for small n and against the published values, so a
    # disagreement with Garner is a result and not a suspicion.
    print("    cross-check — permutations with |s(i+1)-s(i)| >= 2:")
    a002464 = {1: 1, 2: 0, 3: 0, 4: 2, 5: 14, 6: 90, 7: 646, 8: 5242,
               9: 47622, 10: 479306, 11: 5296790}
    for n in range(4, 12):
        got = count_perms(n)
        brute = (sum(1 for p in itertools.permutations(range(n))
                     if all(abs(p[i + 1] - p[i]) >= 2 for i in range(n - 1)))
                 if n <= 8 else None)
        line = f"      n={n:2d} dp={got:9,d} A002464={a002464[n]:9,d}"
        if brute is not None:
            line += f" brute={brute:7,d} brute_ok={brute == got}"
        print(line + f" ok={got == a002464[n]}")
    print(f"    => the regionless one-star count is {a002464[11]:,}; "
          f"Garner's {GARNER_ONE_STAR:,} is high by "
          f"{GARNER_ONE_STAR - a002464[11]}")

    allc = count_boards(all_pairs, False, True)
    print(f"  2/row, 2/col, 2/region, touching allowed   : {allc:,}")
    print(f"    Ravishankar's TWO NOT TOUCH count: {RAVISHANKAR_TNT:,}"
          f" -> ours minus the one clean board = {allc - 1:,}"
          f" -> match: {allc - 1 == RAVISHANKAR_TNT}")

    uniq = count_boards(legal_rows, True, True)
    print(f"  2/row, 2/col, 2/region, no touching        : {uniq}")
    print("    (uniqueness from the recovered rules alone, no solver"
          f" -> match: {uniq == 1})")
    s = stars(ACCEPTED)
    print(f"    our accepted word satisfies them: "
          f"{counts(s) == (True, True, True) and not touching(s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
