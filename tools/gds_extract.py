"""Cell-level connectivity extraction: a placed-and-routed sky130 GDS stream
-> a gate-level netlist (`verilog_netlist.Netlist`).

Backs `tools/extract` (issue #2). Builds on issue #1's cell inventory
(`gds_layers.classify`) and pin abstracts (`gds_pins.resolve_cell_pin_shapes`)
to do the one thing neither of those does: trace physical connectivity
through the routing stack and turn it into a netlist.

Algorithm (see `tools/README.md` "Conductor stack and via handling" for the
narrative version):

1. **Instances.** Top-cell instances split into standard cells
   (`sky130_fd_sc_hd__*`, further split into logic/sequential/fill by
   `gds_layers.classify`), routing cells (`VIA_*`), and an `other` bucket
   (`INTERNAL_*` bookkeeping cells in `puzzle.gds` -- confirmed empirically to
   carry no shapes on any layer this module reads, so excluding them from the
   netlist loses no connectivity; see `tools/README.md`).
2. **Terminals.** Each standard-cell instance's pin shapes
   (`gds_pins.resolve_cell_pin_shapes`, cell-local) are transformed into
   top-level coordinates by the instance's placement (`db.Instance.trans` --
   sky130 rows place with plain rotation/mirror, never magnification;
   confirmed directly, see `tools/README.md` "Pin-transform correctness").
3. **Conductors.** Top-level shapes on `li1`/`met1`-`met5` (67-72, datatype
   20), collected from both what the top cell draws directly and what every
   `VIA_*` instance's cell definition draws (also transformed) -- a `VIA_*`
   cell's shapes include the routing-layer pads on both sides of the via, not
   only the via cut itself (see `tools/README.md`).
4. **Vertical connections.** `mcon`/`via`/`via2`/`via3`/`via4` (67-71,
   datatype 44) drawn shapes, gathered the same way (top cell + `VIA_*`
   instances), bridge conductor layer N to N+1.
5. **Nets.** Union-find over same-layer touching/overlapping conductors (via
   `db.Region.merged()`) plus via-bridged islands across layers.
6. **Naming.** Top-level GDS text labels (`gds_layers.TOP_PORT_LABEL_SOURCES`)
   name nets; everything else gets a generated name. `VPWR`/`VGND`/`VPB`/`VNB`
   pins are never resolved geometrically -- see `SUPPLY_PIN_NET` below.

Callers must have already made `klayout.db` importable (`klayout_env.py`)
before importing this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gds_pins
import verilog_netlist as vn
from gds_layers import TOP_PORT_LABEL_SOURCES, InstanceClass, cell_family, classify
from klayout import db

# The conductor stack this reads, in bottom-to-top order. `datatype 20` is
# KLayout's convention for "drawn" shapes on each of these GDS layer numbers.
CONDUCTOR_LAYERS: tuple[int, ...] = (67, 68, 69, 70, 71, 72)
CONDUCTOR_NAME = {67: "li1", 68: "met1", 69: "met2", 70: "met3", 71: "met4", 72: "met5"}

# Via cut layers (`datatype 44`). Via layer N electrically bridges conductor
# layer N and conductor layer N+1 -- see `tools/README.md` for how this was
# confirmed empirically (every `VIA_*` cell definition draws shapes on
# exactly the layer pair its own via-cut layer number predicts).
VIA_LAYERS: tuple[int, ...] = (67, 68, 69, 70, 71)
VIA_NAME = {67: "mcon", 68: "via", 69: "via2", 70: "via3", 71: "via4"}

# Pin names that collapse directly to one of the two global supply nets by
# NAME, never by geometry. Two independent reasons converge on the same rule:
#   - VPB/VNB (n-well / substrate bias) resolve to shapes on layers 64/122
#     (nwell.pin / pwell.pin) -- outside the li1-met5 stack this module
#     traces entirely. There is no top-level routing model for a well tie to
#     resolve against.
#   - VPWR/VGND *do* have top-level routing (met1 rails, met4/met5 mesh), but
#     ground-truth gate-level netlists (`warmup/01_netlist.v`) never wire
#     power pins at all, and this repo's own simulation harness
#     (`tools/sim/icarus.py`) compiles behavioural models *without*
#     `USE_POWER_PINS`, i.e. expects instances not to name these pins.
# Emitted instances therefore never carry these connections at all (see the
# `pin_name in SUPPLY_PIN_NET` branches in `extract()` below). The geometric
# supply network is still traced -- the same union-find that resolves signal
# nets, run across the same full conductor stack -- purely to catch a real
# short between a signal net and a supply rail (the `root_labels` pass in
# `extract()`), which is exactly the kind of bug a name-only collapse alone
# would hide.
SUPPLY_PIN_NET = {"VPWR": "VPWR", "VPB": "VPWR", "VGND": "VGND", "VNB": "VGND"}
SUPPLY_NET_NAMES = frozenset(SUPPLY_PIN_NET.values())

# sky130_fd_sc_hd's only *driven* (output) pin names, derived empirically
# from every pin name across all 69 cells `puzzle.gds` uses
# (`evidence/pins-sky130_fd_sc_hd.json`): X/Y for combinational cells, Q for
# flip-flops/latches. Every other pin name in the library (A*, B*, C, D, S,
# CLK, RESET_B, SET_B, ...) is an input. Used only to guess a top-level
# port's direction for the emitted Verilog `input`/`output` declaration --
# `tools/compare` does not use direction at all (net *names* are what it
# matches), so a wrong guess here cannot cause a false equivalence failure.
OUTPUT_PIN_NAMES = frozenset({"X", "Y", "Q"})

# The (layer, datatype) pairs that carry a top-level net's name as GDS text
# (`gds_layers.TOP_PORT_LABEL_SOURCES`): met3 for signal port names, met4 and
# met5 for supply rail names -- both of the latter carry *both* "VPWR" and
# "VGND" text (the rail mesh is routed on both layers), so which of the two
# a label counts as is decided by the string itself, not by which of these
# layers it sits on.
_ALL_LABEL_SOURCES = tuple(TOP_PORT_LABEL_SOURCES)


class ExtractionError(RuntimeError):
    """A pin could not be resolved to exactly one net, or the geometric
    connectivity trace found a real defect (a signal net shorted to a supply
    rail, or the two supply rails shorted to each other). Always names the
    instance + pin, or the two conflicting net labels -- never a silent skip.
    """


# ---------------------------------------------------------------------------
# union-find over (layer, island-index) nodes
# ---------------------------------------------------------------------------


class _UnionFind:
    __slots__ = ("parent",)

    def __init__(self) -> None:
        self.parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(self, x: tuple[int, int]) -> tuple[int, int]:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if rb < ra:
            ra, rb = rb, ra
        self.parent[rb] = ra

    def groups(self) -> dict[tuple[int, int], set[tuple[int, int]]]:
        out: dict[tuple[int, int], set[tuple[int, int]]] = {}
        for node in self.parent:
            out.setdefault(self.find(node), set()).add(node)
        return out


# ---------------------------------------------------------------------------
# per-layer merged islands + spatial lookup
# ---------------------------------------------------------------------------


@dataclass
class _LayerIslands:
    layer: int
    region: db.Region  # merged, disjoint polygons
    polygons: list  # db.Polygon, index = island id
    index_by_key: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, layer: int, raw: db.Region) -> _LayerIslands:
        merged = raw.merged()
        polys = list(merged.each())
        index_by_key = {p.to_s(): i for i, p in enumerate(polys)}
        return cls(layer=layer, region=merged, polygons=polys, index_by_key=index_by_key)

    def query(self, poly) -> list[int]:
        """Island ids whose merged shape touches/overlaps `poly`."""
        q = db.Region()
        q.insert(poly)
        hits = self.region.interacting(q)
        return [self.index_by_key[p.to_s()] for p in hits.each()]


def _box_contains(outer, inner) -> bool:
    """Whether `inner` (a `Box`/`DBox`) lies entirely within `outer`."""
    return (
        outer.left <= inner.left
        and outer.bottom <= inner.bottom
        and outer.right >= inner.right
        and outer.top >= inner.top
    )


def _tiny_box(pt, half: int = 1):
    """A `half`-dbu square around an integer-dbu point, for containment
    queries against a text label's position (a point has zero area, and
    `Region.interacting` needs a shape)."""
    return db.Polygon(db.Box(pt.x - half, pt.y - half, pt.x + half, pt.y + half))


# ---------------------------------------------------------------------------
# geometry gathering
# ---------------------------------------------------------------------------


def _expand_pin_shapes(layout, cell, raw_pins: dict[str, list[tuple[int, object]]]):
    """Expand each non-power pin's narrow `.pin`-marker shape(s) to the full
    cell-local conductor island they sit on.

    A `.pin`-purpose shape marks a *legal via landing spot* for a pin, not
    necessarily the pin's entire physical extent inside the cell. A
    high-drive-strength cell (multiple parallel transistor legs, e.g.
    `clkbuf_16`) exposes several separate `.pin` tabs for the same pin, all
    tied together by one much larger underlying `li1` "draw"-purpose shape
    -- and a P&R via-insertion pass is free to land its via anywhere on that
    larger shape, not only inside the narrow marker rectangle (confirmed
    empirically on `warmup/04_final.gds`: an `sky130_fd_sc_hd__clkbuf_16`
    instance's real output via touches none of its six `.pin` markers, but
    does touch the single wide `li1` shape all six markers themselves sit
    on). Using only the marker would misreport a real, connected pin as
    unconnected.

    Supply pins (`SUPPLY_PIN_NET`) are passed through unchanged -- they are
    never resolved geometrically at all (see that constant's docstring).
    """
    expanded: dict[str, list[tuple[int, object]]] = {}
    local_islands: dict[int, _LayerIslands] = {}

    def _local_islands_for(layer: int) -> _LayerIslands:
        cached = local_islands.get(layer)
        if cached is not None:
            return cached
        raw = db.Region()
        li = layout.layer(layer, 20)
        for shape in cell.each_shape(li):
            if shape.is_text():
                continue
            poly = shape.polygon
            if poly is not None:
                raw.insert(poly)
        cached = _LayerIslands.build(layer, raw)
        local_islands[layer] = cached
        return cached

    for pin_name, shapes in raw_pins.items():
        if pin_name in SUPPLY_PIN_NET:
            expanded[pin_name] = shapes
            continue
        out: list[tuple[int, object]] = []
        seen: set[str] = set()
        for target_layer, poly in shapes:
            islands = _local_islands_for(target_layer)
            hits = islands.query(poly)
            candidates = [islands.polygons[i] for i in hits] if hits else [poly]
            for cand in candidates:
                key = cand.to_s()
                if key not in seen:
                    seen.add(key)
                    out.append((target_layer, cand))
        expanded[pin_name] = out
    return expanded


def _gather_regions(layout, top) -> tuple[dict[int, db.Region], dict[int, db.Region]]:
    """Raw (unmerged) conductor + via regions in top-level coordinates.

    Sources: the top cell's own drawn shapes, plus **every** placed
    instance's own drawn shapes (`VIA_*` routing cells and standard cells
    alike), transformed by its placement.

    Standard cells are treated as black boxes for *naming* (only their
    declared pins, `gds_pins`/`_expand_pin_shapes`, ever become net
    connections) but their `li1` geometry still has to participate in the
    top-level conductor pool, not just `VIA_*` cells' -- confirmed
    empirically on `warmup/04_final.gds`: `sky130_fd_sc_hd__dfrtp_2`'s
    `RESET_B` pin (fanning out to all 16 flops, matching
    `warmup/01_netlist.v`'s `.RESET_B(rst_n)` on every instance) has no
    `VIA_*` cell landing anywhere near its own pin shape at all -- the
    reset signal is distributed via **direct `li1` abutment between
    adjacent standard-cell instances**, only reaching an actual via well
    away from any single flop's own footprint. Restricting `li1` (or any
    other conductor layer) to `VIA_*`-instance-contributed shapes would
    silently misreport that pin (and 20 others in the same design) as
    unconnected. See `tools/README.md` "Conductor stack and via handling".
    """
    conductor_raw = {L: db.Region() for L in CONDUCTOR_LAYERS}
    via_raw = {L: db.Region() for L in VIA_LAYERS}

    def _insert_all(cell, trans, layer: int, datatype: int, dest: db.Region) -> None:
        li = layout.layer(layer, datatype)
        for shape in cell.each_shape(li):
            if shape.is_text():
                continue
            poly = shape.polygon
            if poly is None:
                continue
            dest.insert(poly if trans is None else poly.transformed(trans))

    for L in CONDUCTOR_LAYERS:
        _insert_all(top, None, L, 20, conductor_raw[L])
    for L in VIA_LAYERS:
        _insert_all(top, None, L, 44, via_raw[L])

    for inst in top.each_inst():
        if classify(inst.cell.name) == InstanceClass.OTHER:
            # Confirmed empirically to carry no shapes on any layer this
            # module reads (`tools/README.md`) -- nothing to contribute.
            continue
        t = inst.trans
        cell = inst.cell
        for L in CONDUCTOR_LAYERS:
            _insert_all(cell, t, L, 20, conductor_raw[L])
        for L in VIA_LAYERS:
            _insert_all(cell, t, L, 44, via_raw[L])

    return conductor_raw, via_raw


# ---------------------------------------------------------------------------
# extraction result
# ---------------------------------------------------------------------------


@dataclass
class ExtractionStats:
    source: str
    top_cell: str
    instances_total: int = 0
    instances_by_class: dict[str, int] = field(default_factory=dict)
    instances_excluded_other: tuple[str, ...] = ()
    emitted_instances: int = 0
    fill_instances: int = 0
    flip_flops: int = 0
    flip_flops_by_family: dict[str, int] = field(default_factory=dict)
    nets_total: int = 0
    named_ports: int = 0
    via_bridge_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    supply_pin_connections: dict[str, int] = field(default_factory=dict)
    supply_islands: dict[str, int] = field(default_factory=dict)

    def render(self) -> str:
        lines = [
            f"extraction: {self.source}  (top cell {self.top_cell!r})",
            f"  instances (top cell, all classes): {self.instances_total}",
        ]
        for cls in ("logic", "sequential", "fill", "via", "other"):
            if cls in self.instances_by_class:
                lines.append(f"    {cls}: {self.instances_by_class[cls]}")
        if self.instances_excluded_other:
            lines.append(
                f"    excluded 'other' cell names: {', '.join(self.instances_excluded_other)}"
            )
        lines.append(f"  emitted signal instances: {self.emitted_instances}")
        lines.append(f"  emitted fill instances: {self.fill_instances}")
        lines.append(f"  flip-flops: {self.flip_flops} {dict(sorted(self.flip_flops_by_family.items()))}")
        lines.append(f"  nets: {self.nets_total}  named ports: {self.named_ports}")
        lines.append("  via bridging (drawn + VIA_* cell shapes, merged per via layer):")
        for name, counts in self.via_bridge_counts.items():
            lines.append(f"    {name}: bridged={counts['bridged']} unmatched={counts['unmatched']}")
        lines.append(
            "  supply pin connections (name-collapsed, not geometrically resolved): "
            + ", ".join(f"{k}={v}" for k, v in sorted(self.supply_pin_connections.items()))
        )
        lines.append(
            "  supply rail islands found by the geometric trace (sanity check only): "
            + ", ".join(f"{k}={v}" for k, v in sorted(self.supply_islands.items()))
        )
        return "\n".join(lines) + "\n"


@dataclass
class ExtractionResult:
    netlist: vn.Netlist
    stats: ExtractionStats


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


def extract(layout, source: str, top_name: str | None = None) -> ExtractionResult:
    """Extract a gate-level netlist from an already-`.read()` `db.Layout`.

    Raises `ExtractionError` (naming the instance/pin, or the conflicting net
    labels) on the first unresolved pin or spurious short found -- never
    emits a partial/best-effort netlist.
    """
    top = layout.cell(layout.cell_by_name(top_name)) if top_name else layout.top_cell()

    # -- 1. classify top-cell instances ------------------------------------
    by_class: dict[str, list] = {c: [] for c in InstanceClass.ALL}
    for inst in top.each_inst():
        by_class[classify(inst.cell.name)].append(inst)

    stats = ExtractionStats(
        source=source,
        top_cell=top.name,
        instances_total=sum(len(v) for v in by_class.values()),
        instances_by_class={c: len(v) for c, v in by_class.items() if v},
        instances_excluded_other=tuple(sorted({i.cell.name for i in by_class[InstanceClass.OTHER]})),
    )

    # -- 2/3/4. gather conductor + via geometry, build islands, bridge -----
    conductor_raw, via_raw = _gather_regions(layout, top)
    islands = {L: _LayerIslands.build(L, conductor_raw[L]) for L in CONDUCTOR_LAYERS}

    uf = _UnionFind()
    for L in CONDUCTOR_LAYERS:
        for i in range(len(islands[L].polygons)):
            uf.find((L, i))  # register every island, even one nothing bridges to

    for L in VIA_LAYERS:
        below, above = islands[L], islands[L + 1]
        merged_via = via_raw[L].merged()
        bridged = 0
        unmatched = 0
        for via_poly in merged_via.each():
            below_hits = below.query(via_poly)
            above_hits = above.query(via_poly)
            if not below_hits or not above_hits:
                unmatched += 1
                continue
            keys = [(L, i) for i in below_hits] + [(L + 1, j) for j in above_hits]
            first = keys[0]
            for k in keys[1:]:
                uf.union(first, k)
            bridged += 1
        stats.via_bridge_counts[VIA_NAME[L]] = {"bridged": bridged, "unmatched": unmatched}

    # -- 5/6. name nets from top-level GDS text labels ----------------------
    root_labels: dict[tuple[int, int], set[str]] = {}
    for layer_num, datatype in _ALL_LABEL_SOURCES:
        li = layout.layer(layer_num, datatype)
        layer_islands = islands[layer_num]
        for shape in top.each_shape(li):
            if not shape.is_text():
                continue
            name = shape.text.string
            hits = layer_islands.query(_tiny_box(shape.text_pos))
            if not hits:
                raise ExtractionError(
                    f"top-level label {name!r} on layer {layer_num}/{datatype} lands on no "
                    f"conductor shape at all -- cannot name a net for it"
                )
            roots = {uf.find((layer_num, i)) for i in hits}
            # A label always names one physical net; if the point somehow
            # straddled two disjoint islands, they are electrically the same
            # thing at that point, so union them rather than erroring.
            root_list = sorted(roots)
            for other in root_list[1:]:
                uf.union(root_list[0], other)
            root = uf.find(root_list[0])
            root_labels.setdefault(root, set()).add(name)

    root_name: dict[tuple[int, int], str] = {}
    supply_island_counts = {"VPWR": 0, "VGND": 0}
    for root, names in root_labels.items():
        supply_names = names & SUPPLY_NET_NAMES
        signal_names = names - SUPPLY_NET_NAMES
        if len(supply_names) > 1:
            raise ExtractionError(
                f"spurious supply short: net carries both {sorted(supply_names)} labels "
                f"on the same physically connected island -- VPWR and VGND are shorted "
                f"together somewhere in this layout"
            )
        if supply_names and signal_names:
            raise ExtractionError(
                "spurious supply short: signal port(s) "
                f"{sorted(signal_names)} and supply rail {sorted(supply_names)} resolve to "
                "the same physically connected net"
            )
        if len(signal_names) > 1:
            raise ExtractionError(
                f"top-level ports {sorted(signal_names)} resolve to the same physically "
                "connected net -- two distinct ports appear to be shorted together"
            )
        if supply_names:
            (name,) = supply_names
            root_name[root] = name
            supply_island_counts[name] += 1
        else:
            (name,) = signal_names
            root_name[root] = name
    stats.supply_islands = supply_island_counts

    # -- resolve every standard-cell instance's pins ------------------------
    pin_shape_cache: dict[str, dict[str, list[tuple[int, object]]]] = {}

    def _pins_for(cell_name: str) -> dict[str, list[tuple[int, object]]]:
        cached = pin_shape_cache.get(cell_name)
        if cached is None:
            cell = layout.cell(layout.cell_by_name(cell_name))
            raw_pins = gds_pins.resolve_cell_pin_shapes(layout, cell)
            cached = _expand_pin_shapes(layout, cell, raw_pins)
            pin_shape_cache[cell_name] = cached
        return cached

    unlabeled_counter = [0]

    def _name_for_root(root: tuple[int, int]) -> str:
        name = root_name.get(root)
        if name is not None:
            return name
        unlabeled_counter[0] += 1
        name = f"net_{unlabeled_counter[0]:05d}"
        root_name[root] = name
        return name

    instances: list[vn.Instance] = []
    supply_pin_connections: dict[str, int] = {"VPWR": 0, "VGND": 0}
    net_signal_pins: dict[str, list[tuple[str, str]]] = {}  # net name -> [(inst, pin)]
    ff_by_family: dict[str, int] = {}

    def _instance_name(cell_name: str, inst) -> str:
        base = vn.base_cell(cell_name)
        # The instance's own transformed bounding box, not `trans.disp`
        # (the raw placement pivot): a rotated (e.g. `r180`) and an
        # unrotated (`r0`) instance can legitimately share the same pivot
        # point while occupying disjoint footprints in adjacent standard-
        # cell rows -- confirmed on `warmup/04_final.gds`, two distinct
        # `sky130_fd_sc_hd__and2_2` instances at `disp` (69920, 38080).
        # The transformed bbox's lower-left corner is unique per instance
        # (no two placed instances may legally overlap) and deterministic.
        b = inst.bbox()
        return f"{base}_{b.left}_{b.bottom}"

    for cls in (InstanceClass.LOGIC, InstanceClass.SEQUENTIAL):
        for inst in by_class[cls]:
            cell_name = inst.cell.name
            t = inst.trans
            pins = _pins_for(cell_name)
            bbox = inst.cell.dbbox().transformed(inst.dcplx_trans)
            name = _instance_name(cell_name, inst)
            connections: dict[str, str] = {}
            for pin_name, shapes in pins.items():
                if pin_name in SUPPLY_PIN_NET:
                    net = SUPPLY_PIN_NET[pin_name]
                    supply_pin_connections[net] += 1
                    continue  # never emitted -- see SUPPLY_PIN_NET's docstring
                pin_roots: set[tuple[int, int]] = set()
                for target_layer, poly in shapes:
                    top_poly = poly.transformed(t)
                    # Pin-transform correctness assertion (issue #2's
                    # highest-risk step): a correctly transformed pin must
                    # lie inside its own instance's bounding box.
                    top_dpoly = top_poly.to_dtype(layout.dbu)
                    if not _box_contains(bbox.enlarged(0.01, 0.01), top_dpoly.bbox()):
                        raise ExtractionError(
                            f"{name}.{pin_name}: transformed pin polygon "
                            f"{top_dpoly.bbox()} falls outside instance bounding box "
                            f"{bbox} -- likely a placement transform bug"
                        )
                    hits = islands[target_layer].query(top_poly)
                    for i in hits:
                        pin_roots.add(uf.find((target_layer, i)))
                if not pin_roots:
                    raise ExtractionError(
                        f"unconnected pin: instance {name!r} ({cell_name}) pin "
                        f"{pin_name!r} touches no conductor shape on layer "
                        f"{CONDUCTOR_NAME.get(shapes[0][0], shapes[0][0])}"
                    )
                root_list = sorted(pin_roots)
                for other in root_list[1:]:
                    uf.union(root_list[0], other)
                net = _name_for_root(uf.find(root_list[0]))
                connections[pin_name] = net
                net_signal_pins.setdefault(net, []).append((name, pin_name))
            instances.append(vn.Instance(name=name, cell=cell_name, connections=connections))
            if cls == InstanceClass.SEQUENTIAL:
                fam = cell_family(cell_name)
                ff_by_family[fam] = ff_by_family.get(fam, 0) + 1

    for inst in by_class[InstanceClass.FILL]:
        cell_name = inst.cell.name
        pins = _pins_for(cell_name)
        name = _instance_name(cell_name, inst)
        for pin_name in pins:
            if pin_name in SUPPLY_PIN_NET:
                supply_pin_connections[SUPPLY_PIN_NET[pin_name]] += 1
            # Fill cells carry no signal pins at all (issue #2's algorithm,
            # step 1); anything else would be a real, reportable surprise,
            # but none of sky130_fd_sc_hd's fill families expose one.
        instances.append(vn.Instance(name=name, cell=cell_name, connections={}))

    stats.emitted_instances = len(by_class[InstanceClass.LOGIC]) + len(by_class[InstanceClass.SEQUENTIAL])
    stats.fill_instances = len(by_class[InstanceClass.FILL])
    stats.flip_flops = sum(ff_by_family.values())
    stats.flip_flops_by_family = ff_by_family
    stats.supply_pin_connections = supply_pin_connections

    # -- ports + direction ---------------------------------------------------
    port_order: list[str] = []
    seen_ports: set[str] = set()
    for layer_num, datatype in _ALL_LABEL_SOURCES:
        if layer_num != 70:  # only the signal label layer defines module ports
            continue
        li = layout.layer(layer_num, datatype)
        for shape in top.each_shape(li):
            if not shape.is_text():
                continue
            nm = shape.text.string
            if nm not in seen_ports:
                seen_ports.add(nm)
                port_order.append(nm)

    ports: list[vn.Port] = []
    for nm in port_order:
        pins_on_net = net_signal_pins.get(nm, [])
        direction = "input"
        for _inst_name, pin_name in pins_on_net:
            if pin_name in OUTPUT_PIN_NAMES:
                direction = "output"
                break
        ports.append(vn.Port(name=nm, direction=direction))
    stats.named_ports = len(ports)

    net_set: set[str] = set(seen_ports)
    for inst in instances:
        net_set.update(inst.connections.values())
    stats.nets_total = len(net_set)

    netlist = vn.Netlist(top=top.name, ports=ports, nets=sorted(net_set), instances=instances, source=source)
    return ExtractionResult(netlist=netlist, stats=stats)
