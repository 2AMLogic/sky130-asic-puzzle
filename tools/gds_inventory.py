"""Top-cell instance census + top-level port names, read from a GDS stream.

Backs `tools/inventory`. Everything here reads only the GDS structure (cell
names, instance placements, and a handful of label layers on the top cell) --
no PDK, no netlist. See `gds_layers.py` for the layer/classification table.

Callers must have already made `klayout.db` importable (`klayout_env.py`)
before importing this module.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from gds_layers import TOP_PORT_LABEL_SOURCES, InstanceClass, classify


@dataclass
class Census:
    source: str
    top_cell: str
    total_instances: int
    by_class: dict[str, int]
    by_cell: dict[str, int]  # cell name -> instance count, every class
    other_cells: tuple[str, ...]  # cell names classified InstanceClass.OTHER
    distinct_library_cells: int
    top_ports: dict[str, list[str]]  # label source description -> names

    def to_json(self) -> dict:
        return {
            "schema": "sky130-asic-puzzle/inventory@1",
            "source": self.source,
            "top_cell": self.top_cell,
            "total_instances": self.total_instances,
            "by_class": dict(self.by_class),
            "by_cell": dict(sorted(self.by_cell.items())),
            "other_cells": list(self.other_cells),
            "distinct_library_cells": self.distinct_library_cells,
            "top_ports": self.top_ports,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Inventory: `{self.source}`",
            "",
            f"Top cell: `{self.top_cell}`  ",
            f"Total placed instances: **{self.total_instances}**  ",
            f"Distinct `sky130_fd_sc_hd` library cells: **{self.distinct_library_cells}**",
            "",
            "| Class | Count |",
            "|---|---|",
        ]
        for cls in InstanceClass.ALL:
            count = self.by_class.get(cls, 0)
            if count or cls != InstanceClass.OTHER:
                lines.append(f"| {cls} | {count} |")
        if self.other_cells:
            lines.append("")
            lines.append(
                "`other` cell names (neither `VIA_*` nor `sky130_fd_sc_hd__*`): "
                + ", ".join(f"`{c}`" for c in self.other_cells)
            )
        lines.append("")
        lines.append("## Signal ports (top cell)")
        for label, names in self.top_ports.items():
            lines.append(f"- **{label}**: {', '.join(names) if names else '(none found)'}")
        lines.append("")
        lines.append("## Instances by cell")
        lines.append("")
        lines.append("| Count | Cell |")
        lines.append("|---|---|")
        for name, count in sorted(self.by_cell.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| {count} | `{name}` |")
        return "\n".join(lines) + "\n"


def census(layout, source: str) -> Census:
    top = layout.top_cell()
    by_cell: Counter[str] = Counter()
    for inst in top.each_inst():
        by_cell[inst.cell.name] += 1

    by_class: Counter[str] = Counter()
    other_cells: list[str] = []
    for name, count in by_cell.items():
        cls = classify(name)
        by_class[cls] += count
        if cls == InstanceClass.OTHER:
            other_cells.append(name)

    non_library_classes = (InstanceClass.VIA, InstanceClass.OTHER)
    distinct_library_cells = sum(
        1 for name in by_cell if classify(name) not in non_library_classes
    )

    top_ports: dict[str, list[str]] = {}
    for (layer_num, datatype), label in TOP_PORT_LABEL_SOURCES.items():
        li = layout.layer(layer_num, datatype)
        names = sorted(
            {shape.text.string for shape in top.each_shape(li) if shape.is_text()}
        )
        top_ports[label] = names

    return Census(
        source=source,
        top_cell=top.name,
        total_instances=sum(by_cell.values()),
        by_class=dict(by_class),
        by_cell=dict(by_cell),
        other_cells=tuple(sorted(other_cells)),
        distinct_library_cells=distinct_library_cells,
        top_ports=top_ports,
    )
