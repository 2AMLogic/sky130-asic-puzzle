#!/usr/bin/env python3
"""Independent review addendum, claim 8: the met2 glyph, without a window.

Independent of evidence/easter-egg-met2-ring.py (klayout, fixed 20x20 um
window): uses gdstk, seeds from the 0.3 um tiles the committed window
contains, then flood-fills same-layer met2 connectivity across the ENTIRE
layout — so if the glyph continued past the committed window, or touched any
routing wire, the component would grow to include it. Electrical connectivity
is then tested directly: met2 can only connect downward through via1 (68/44)
and upward through via2 (69/44), so zero overlapping vias plus same-layer
isolation is proof of an unconnected island, not an appearance.

Also scans the whole die for any OTHER pure tile cluster (possible fourth
ring / tail / second glyph), and re-derives the ring structure with radial
bands taken from the measured radius histogram instead of hardcoded bands.

Run from the repo root:  python3 evidence/independent-review-addendum-met2.py
"""

import math
from collections import defaultdict
from pathlib import Path

import gdstk

REPO = Path(__file__).resolve().parent.parent
GDS = REPO / "puzzle" / "puzzle.gds"

MET2 = (69, 20)
VIA1 = (68, 44)  # met1 <-> met2
VIA2 = (69, 44)  # met2 <-> met3
SEED_WINDOW = (34.0, 33.0, 54.0, 53.0)  # the committed script's window, um
GRID = 5000  # nm spatial hash pitch


def load(top, layer):
    out = []
    for p in top.get_polygons(depth=None, layer=layer[0], datatype=layer[1]):
        pts = [(round(x * 1000), round(y * 1000)) for x, y in p.points]
        xs = [pt[0] for pt in pts]
        ys = [pt[1] for pt in pts]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        is_rect = len(pts) == 4 and len(set(xs)) == 2 and len(set(ys)) == 2
        out.append({"pts": pts, "bbox": bbox, "rect": is_rect})
    return out


def hash_polys(polys):
    grid = defaultdict(list)
    for i, p in enumerate(polys):
        x0, y0, x1, y1 = p["bbox"]
        for gx in range(x0 // GRID, x1 // GRID + 1):
            for gy in range(y0 // GRID, y1 // GRID + 1):
                grid[(gx, gy)].append(i)
    return grid


def bbox_touch(a, b):
    """Bboxes overlap or share an edge of positive length (not corner-only)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if ax0 > bx1 or bx0 > ax1 or ay0 > by1 or by0 > ay1:
        return False
    # exclude zero-length corner-only contact
    x_overlap = min(ax1, bx1) - max(ax0, bx0)
    y_overlap = min(ay1, by1) - max(ay0, by0)
    return not (x_overlap == 0 and y_overlap == 0)


def bbox_area_overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return min(ax1, bx1) > max(ax0, bx0) and min(ay1, by1) > max(ay0, by0)


def exact_touch(pa, pb):
    """Polygon-exact connectivity for non-rectangle cases."""
    if pa["rect"] and pb["rect"]:
        return bbox_touch(pa["bbox"], pb["bbox"])
    a = gdstk.Polygon([(x / 1000, y / 1000) for x, y in pa["pts"]])
    b = gdstk.Polygon([(x / 1000, y / 1000) for x, y in pb["pts"]])
    grown = gdstk.offset(a, 0.0005)  # half a db unit: catches edge abutment
    return bool(gdstk.boolean(grown, b, "and"))


def main():
    lib = gdstk.read_gds(str(GDS))
    top = lib.top_level()[0]
    met2 = load(top, MET2)
    via1 = load(top, VIA1)
    via2 = load(top, VIA2)
    print(f"met2 polygons: {len(met2)}; via1: {len(via1)}; via2: {len(via2)}")
    grid = hash_polys(met2)

    def is_tile(p):
        x0, y0, x1, y1 = p["bbox"]
        return p["rect"] and x1 - x0 == 300 and y1 - y0 == 300

    wx0, wy0, wx1, wy1 = (v * 1000 for v in SEED_WINDOW)
    seeds = [i for i, p in enumerate(met2)
             if is_tile(p) and wx0 < p["bbox"][0] and p["bbox"][2] < wx1
             and wy0 < p["bbox"][1] and p["bbox"][3] < wy1]
    print(f"seed tiles inside committed window: {len(seeds)}")

    # flood fill same-layer connectivity across the whole layout
    member = set(seeds)
    frontier = list(seeds)
    exact_fallbacks = 0
    while frontier:
        i = frontier.pop()
        pi = met2[i]
        x0, y0, x1, y1 = pi["bbox"]
        cands = set()
        for gx in range(x0 // GRID, x1 // GRID + 1):
            for gy in range(y0 // GRID, y1 // GRID + 1):
                cands.update(grid[(gx, gy)])
        for j in cands:
            if j in member:
                continue
            pj = met2[j]
            if not bbox_touch(pi["bbox"], pj["bbox"]):
                continue
            if pi["rect"] and pj["rect"]:
                touch = True
            else:
                exact_fallbacks += 1
                touch = exact_touch(pi, pj)
            if touch:
                member.add(j)
                frontier.append(j)
    comp = [met2[i] for i in member]
    non_tiles = [p for p in comp if not is_tile(p)]
    cx0 = min(p["bbox"][0] for p in comp)
    cy0 = min(p["bbox"][1] for p in comp)
    cx1 = max(p["bbox"][2] for p in comp)
    cy1 = max(p["bbox"][3] for p in comp)
    print(f"glyph connected component: {len(comp)} shapes "
          f"({len(non_tiles)} non-0.3um-tile), exact fallbacks used: {exact_fallbacks}")
    print(f"component extent um: ({cx0/1000:.2f},{cy0/1000:.2f}) - "
          f"({cx1/1000:.2f},{cy1/1000:.2f})")
    grew = (cx0 <= wx0 or cy0 <= wy0 or cx1 >= wx1 or cy1 >= wy1)
    print(f"component escapes committed window: {grew}")

    # electrical connectivity: vias overlapping any component shape
    comp_boxes = [p["bbox"] for p in comp]
    comp_grid = defaultdict(list)
    for i, b in enumerate(comp_boxes):
        for gx in range(b[0] // GRID, b[2] // GRID + 1):
            for gy in range(b[1] // GRID, b[3] // GRID + 1):
                comp_grid[(gx, gy)].append(i)

    def via_hits(vias):
        hits = 0
        touches = 0
        for v in vias:
            b = v["bbox"]
            cands = set()
            for gx in range(b[0] // GRID, b[2] // GRID + 1):
                for gy in range(b[1] // GRID, b[3] // GRID + 1):
                    cands.update(comp_grid[(gx, gy)])
            for i in cands:
                if bbox_area_overlap(b, comp_boxes[i]):
                    hits += 1
                elif bbox_touch(b, comp_boxes[i]):
                    touches += 1
        return hits, touches

    h1, t1 = via_hits(via1)
    h2, t2 = via_hits(via2)
    print(f"via1 (met1<->met2) overlapping component: {h1} (edge-touch: {t1})")
    print(f"via2 (met2<->met3) overlapping component: {h2} (edge-touch: {t2})")

    # any other pure tile cluster anywhere on the die?
    tiles = [i for i, p in enumerate(met2) if is_tile(p)]
    print(f"\n0.3um met2 tiles on the whole die: {len(tiles)}")
    tile_set = set(tiles)
    parent = {i: i for i in tiles}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in tiles:
        b = met2[i]["bbox"]
        cands = set()
        for gx in range(b[0] // GRID, b[2] // GRID + 1):
            for gy in range(b[1] // GRID, b[3] // GRID + 1):
                cands.update(grid[(gx, gy)])
        for j in cands:
            if j in tile_set and j > i and bbox_touch(b, met2[j]["bbox"]):
                parent[find(i)] = find(j)
    clusters = defaultdict(list)
    for i in tiles:
        clusters[find(i)].append(i)
    big = [c for c in clusters.values() if len(c) >= 10]
    print(f"tile clusters with >=10 tiles: {len(big)}")
    for c in sorted(big, key=len, reverse=True):
        bx0 = min(met2[i]["bbox"][0] for i in c)
        by0 = min(met2[i]["bbox"][1] for i in c)
        bx1 = max(met2[i]["bbox"][2] for i in c)
        by1 = max(met2[i]["bbox"][3] for i in c)
        # does this cluster touch non-tile met2 or overlap a via?
        routed = False
        for i in c:
            b = met2[i]["bbox"]
            cands = set()
            for gx in range(b[0] // GRID, b[2] // GRID + 1):
                for gy in range(b[1] // GRID, b[3] // GRID + 1):
                    cands.update(grid[(gx, gy)])
            if any(j not in tile_set and bbox_touch(b, met2[j]["bbox"])
                   for j in cands):
                routed = True
                break
        via_boxes = [v["bbox"] for v in via1 + via2]
        via_over = any(bbox_area_overlap(met2[i]["bbox"], vb)
                       for i in c for vb in via_boxes)
        print(f"  cluster n={len(c)} bbox um ({bx0/1000:.2f},{by0/1000:.2f})-"
              f"({bx1/1000:.2f},{by1/1000:.2f}) touches_routing={routed} "
              f"overlaps_via={via_over}")

    # ring structure, bands derived from the measured radius histogram
    centers = [((p["bbox"][0] + p["bbox"][2]) / 2000,
                (p["bbox"][1] + p["bbox"][3]) / 2000) for p in comp]
    cx = sum(c[0] for c in centers) / len(centers)
    cy = sum(c[1] for c in centers) / len(centers)
    radii = sorted(math.hypot(x - cx, y - cy) for x, y in centers)
    print(f"\nglyph center um: ({cx:.2f},{cy:.2f}); "
          f"radius range {radii[0]:.2f}..{radii[-1]:.2f}")
    hist = defaultdict(int)
    for r in radii:
        hist[round(r * 10)] += 1  # 0.1 um bins
    occupied = sorted(k for k in hist)
    bands = []
    cur = [occupied[0]]
    for k in occupied[1:]:
        if k - cur[-1] <= 1:
            cur.append(k)
        else:
            bands.append(cur)
            cur = [k]
    bands.append(cur)
    print(f"radial bands (from data): {len(bands)}")
    for band in bands:
        lo, hi = band[0] / 10, band[-1] / 10 + 0.1
        n = 0
        cov = [False] * 720
        for x, y in centers:
            r = math.hypot(x - cx, y - cy)
            if lo - 0.05 <= r <= hi + 0.05:
                n += 1
                ang = math.degrees(math.atan2(y - cy, x - cx)) % 360
                half = math.degrees(0.21 / max(r, 0.3))  # tile half-diagonal
                b0 = int((ang - half) / 0.5)
                b1 = int((ang + half) / 0.5)
                for b in range(b0, b1 + 1):
                    cov[b % 720] = True
        covered = sum(cov) / 2.0
        gaps = []
        i = 0
        if any(cov):
            start = cov.index(True)
            while i < 720:
                j = (start + i) % 720
                if not cov[j]:
                    k = i
                    while k < 720 and not cov[(start + k) % 720]:
                        k += 1
                    gaps.append((((start + i) % 720) * 0.5, (k - i) * 0.5))
                    i = k
                else:
                    i += 1
        gap_desc = ", ".join(f"{ln:.1f}deg@{a:.1f}deg" for a, ln in gaps)
        print(f"  band r={lo:.1f}-{hi:.1f}um: {n} tiles, covered "
              f"{covered:.1f}deg, gaps: {gap_desc or 'none'}")


if __name__ == "__main__":
    main()
