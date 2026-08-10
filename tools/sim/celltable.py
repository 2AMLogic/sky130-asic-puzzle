"""Derive each standard cell's Boolean function from the PDK's own models.

Any solver that reasons about a gate-level netlist needs to know what each
cell *computes*.  Writing that table from memory ("`a21bo` is `(A1 & A2) |
~B1_N`, probably") is exactly the kind of unbacked claim `CLAUDE.md` §5
rules out: a single transcription slip silently changes the circuit the
solver is reasoning about, and the mistake is invisible until the answer is
wrong.

So the tables are not written down here at all — they are *measured*.  This
module generates a Verilog testbench that instantiates each requested cell
once, sweeps every input combination, and prints the resulting outputs; the
same `sky130_fd_sc_hd` behavioural models `tools/sim` already simulates
against (`tools/sim/pdk.py`) are the authority.  The result is a truth table
per cell, cached as JSON so a rerun is cheap and so the table used by a
solve can be committed alongside the evidence for it.

Only *combinational* cells can be characterised this way.  Sequential cells
(`df*`) are excluded by the caller and modelled explicitly in
`tools/sim/seqmodel.py`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from tools.sim.icarus import compile_and_run
from tools.sim.pdk import ResolvedModels

SCHEMA = "sky130-asic-puzzle/celltables@1"

# Pins that exist on the models but are never wired by an extracted netlist
# (USE_POWER_PINS is left undefined — see tools/sim/icarus.py).
_POWER_PINS = frozenset({"VPWR", "VGND", "VPB", "VNB"})

_MODULE_RE = re.compile(r"^module\s+(sky130_fd_sc_hd__\w+)\s*\(", re.MULTILINE)
_DIR_RE = re.compile(r"^\s*(input|output|inout)\s+([A-Za-z_]\w*)\s*;", re.MULTILINE)


class CellTableError(RuntimeError):
    pass


@dataclass(frozen=True)
class CellTable:
    """A combinational cell's complete truth table.

    `rows[pattern]` holds the output values for the input assignment whose
    bit `j` (LSB first) is `inputs[j]`; each row is a string of `'0'`/`'1'`
    in `outputs` order.
    """

    cell: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    rows: tuple[str, ...]

    def output_value(self, out_pin: str, pattern: int) -> int:
        return int(self.rows[pattern][self.outputs.index(out_pin)])

    def to_json(self) -> dict:
        return {
            "cell": self.cell,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "rows": list(self.rows),
        }

    @staticmethod
    def from_json(obj: dict) -> CellTable:
        return CellTable(
            cell=obj["cell"],
            inputs=tuple(obj["inputs"]),
            outputs=tuple(obj["outputs"]),
            rows=tuple(obj["rows"]),
        )


# --------------------------------------------------------------------------
# port directions, read off the PDK models rather than assumed
# --------------------------------------------------------------------------


def parse_port_directions(behavioural_v: Path) -> dict[str, dict[str, str]]:
    """`{cell: {pin: 'input'|'output'}}` for every module in the model file.

    The model file defines each cell several times behind ``ifdef``s
    (power-pin / no-power-pin, functional / timing).  Signal-pin directions
    are identical across those variants, so the first definition wins and
    power pins are dropped.
    """
    text = behavioural_v.read_text(encoding="utf-8", errors="replace")
    starts = [(m.start(), m.group(1)) for m in _MODULE_RE.finditer(text)]
    out: dict[str, dict[str, str]] = {}
    for idx, (pos, cell) in enumerate(starts):
        if cell in out:
            continue
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
        body = text[pos:end]
        dirs = {
            pin: direction
            for direction, pin in _DIR_RE.findall(body)
            if pin not in _POWER_PINS
        }
        if dirs:
            out[cell] = dirs
    return out


# --------------------------------------------------------------------------
# characterisation
# --------------------------------------------------------------------------


def _build_probe_testbench(specs: list[tuple[str, tuple[str, ...], tuple[str, ...]]]) -> str:
    """Testbench that sweeps every input pattern of every cell in `specs`."""
    lines = ["`timescale 1ns/1ps", "module tb;", "  integer n;", ""]
    for idx, (cell, ins, outs) in enumerate(specs):
        width = max(len(ins), 1)
        lines.append(f"  reg [{width - 1}:0] in{idx};")
        for j, pin in enumerate(outs):
            lines.append(f"  wire o{idx}_{j};")
        conns = [f".{pin}(in{idx}[{j}])" for j, pin in enumerate(ins)]
        conns += [f".{pin}(o{idx}_{j})" for j, pin in enumerate(outs)]
        lines.append(f"  {cell} u{idx} ({', '.join(conns)});")
        lines.append("")
    lines.append("  initial begin")
    for idx, (cell, ins, outs) in enumerate(specs):
        n_pat = 1 << len(ins)
        bits = ", ".join(f"o{idx}_{j}" for j in range(len(outs)))
        fmt = "%b" * len(outs)
        lines.append(f"    for (n = 0; n < {n_pat}; n = n + 1) begin")
        lines.append(f"      in{idx} = n[{max(len(ins), 1) - 1}:0];")
        lines.append("      #10;")
        lines.append(f'      $display("ROW {idx} %0d {fmt}", n, {bits});')
        lines.append("    end")
    lines.append('    $display("PROBE DONE");')
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def derive_cell_tables(
    cells: dict[str, set[str]],
    models: ResolvedModels,
    *,
    work_dir: Path,
    timeout_s: float = 300.0,
) -> dict[str, CellTable]:
    """Characterise `cells` (`{cell_name: set_of_pins_used_by_the_netlist}`).

    Only the pins the netlist actually wires are driven/observed, which is
    also what keeps power pins out of the sweep.
    """
    directions = parse_port_directions(models.behavioural_v)
    specs: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    for cell in sorted(cells):
        if cell not in directions:
            raise CellTableError(f"{cell} is not defined in {models.behavioural_v}")
        dirs = directions[cell]
        used = cells[cell]
        unknown = used - set(dirs)
        if unknown:
            raise CellTableError(f"{cell}: pins {sorted(unknown)} are not ports of the model")
        ins = tuple(p for p in dirs if dirs[p] == "input" and p in used)
        outs = tuple(p for p in dirs if dirs[p] == "output")
        if not outs:
            raise CellTableError(f"{cell}: no output pins")
        if len(ins) > 8:
            raise CellTableError(f"{cell}: {len(ins)} inputs is too wide to enumerate")
        specs.append((cell, ins, outs))

    work_dir.mkdir(parents=True, exist_ok=True)
    tb_path = work_dir / "cell_probe_tb.v"
    tb_path.write_text(_build_probe_testbench(specs), encoding="utf-8")

    result = compile_and_run(
        [tb_path, *models.model_files()],
        top="tb",
        timeout_s=timeout_s,
        work_dir=work_dir,
    )
    if not result.compiled:
        raise CellTableError(f"cell probe failed to compile:\n{result.compile_stderr}")
    if "PROBE DONE" not in result.run_stdout:
        raise CellTableError(f"cell probe did not finish:\n{result.run_stdout}\n{result.run_stderr}")

    collected: dict[int, dict[int, str]] = {}
    for line in result.run_stdout.splitlines():
        if not line.startswith("ROW "):
            continue
        _, idx_s, pat_s, bits = line.split()
        collected.setdefault(int(idx_s), {})[int(pat_s)] = bits

    tables: dict[str, CellTable] = {}
    for idx, (cell, ins, outs) in enumerate(specs):
        got = collected.get(idx, {})
        n_pat = 1 << len(ins)
        rows = []
        for pat in range(n_pat):
            row = got.get(pat)
            if row is None:
                raise CellTableError(f"{cell}: pattern {pat} missing from probe output")
            if len(row) != len(outs) or any(c not in "01" for c in row):
                raise CellTableError(
                    f"{cell}: pattern {pat} produced non-Boolean output {row!r} — "
                    "the cell may not be purely combinational"
                )
            rows.append(row)
        tables[cell] = CellTable(cell=cell, inputs=ins, outputs=outs, rows=tuple(rows))
    return tables


# --------------------------------------------------------------------------
# cache
# --------------------------------------------------------------------------


def save_tables(tables: dict[str, CellTable], path: Path, models: ResolvedModels) -> None:
    doc = {
        "schema": SCHEMA,
        "pdk": {
            "variant": models.variant,
            "version": models.version,
            "resolved_via": models.resolved_via,
            "primitives_v": str(models.primitives_v),
            "behavioural_v": str(models.behavioural_v),
        },
        "cells": [tables[c].to_json() for c in sorted(tables)],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def load_tables(path: Path) -> dict[str, CellTable]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise CellTableError(f"{path}: unexpected schema {doc.get('schema')!r}")
    return {c["cell"]: CellTable.from_json(c) for c in doc["cells"]}
