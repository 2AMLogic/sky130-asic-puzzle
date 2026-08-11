"""Resolve sky130_fd_sc_hd's behavioural Verilog models.

Simulating a `sky130_fd_sc_hd` gate-level netlist needs the standard-cell
library's behavioural Verilog (`sky130_fd_sc_hd.v`) plus its UDP primitives
(`primitives.v`). Neither is vendored in this repo (they are Apache-2.0 and
fetchable, so vendoring would be permissible, but `CLAUDE.md` §3's fetch
rather than vendor habit is the right default here too — a resolver keeps the
repo small and the models stay pinned to whatever PDK install is actually on
the machine, not a copy that can drift from it).

Resolution order:
  1. `klt pdk find --pdk sky130A --format json` (klayout-tools' own resolver,
     if `klt` is on PATH) — this is the toolkit's documented search order
     (env `$PDK`/`$PDK_ROOT`, then well-known install roots including
     `~/.volare`), so deferring to it means one resolution order for the
     whole fleet instead of a second, possibly-diverging one here.
  2. `$PDK_ROOT/sky130A/...` directly, if `klt` is unavailable or fails.
  3. `~/.volare/sky130A/...` directly, as a last-resort fallback matching
     volare's own default install location.

Every evidence record produced by this repo must state which of these
resolved, and the exact paths used — a simulation whose model provenance is
unstated is not re-runnable (CLAUDE.md §5, issue #5).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PDK_VARIANT = "sky130A"
CELL_LIBRARY = "sky130_fd_sc_hd"

INSTALL_HINT = (
    "No resolvable sky130 PDK found (looked for sky130_fd_sc_hd's behavioural "
    "Verilog via `klt pdk find --pdk sky130A`, $PDK_ROOT, and ~/.volare). "
    "Install one with volare: `pip install volare && volare enable "
    "$(volare ls-remote sky130 --limit 1 -f '{version}')`, or point $PDK_ROOT "
    "at an existing open_pdks sky130A install, then re-run."
)


class PdkResolutionError(RuntimeError):
    """Raised when no sky130_fd_sc_hd behavioural Verilog can be found.

    Always carries `INSTALL_HINT` (or a more specific variant of it) as the
    message, per issue #5's requirement that a missing model produces one
    actionable install instruction, never a silent skip.
    """


@dataclass(frozen=True)
class ResolvedModels:
    """Provenance + file paths for the resolved sky130_fd_sc_hd Verilog models.

    Record every field of this in evidence output — that is what makes a
    simulation re-runnable by someone else (CLAUDE.md §5).
    """

    variant: str
    version: str
    resolved_via: str
    libs_ref: Path
    primitives_v: Path
    behavioural_v: Path

    def model_files(self) -> list[Path]:
        return [self.primitives_v, self.behavioural_v]

    def describe(self) -> str:
        return (
            f"PDK variant: {self.variant}\n"
            f"PDK version: {self.version}\n"
            f"Resolved via: {self.resolved_via}\n"
            f"Model files:\n  {self.primitives_v}\n  {self.behavioural_v}"
        )


def _models_under_libs_ref(libs_ref: Path) -> tuple[Path, Path] | None:
    verilog_dir = libs_ref / CELL_LIBRARY / "verilog"
    primitives = verilog_dir / "primitives.v"
    behavioural = verilog_dir / f"{CELL_LIBRARY}.v"
    if primitives.is_file() and behavioural.is_file():
        return primitives, behavioural
    return None


def _try_klt() -> ResolvedModels | None:
    klt = shutil.which("klt")
    if klt is None:
        return None
    try:
        proc = subprocess.run(
            [klt, "pdk", "find", "--pdk", PDK_VARIANT, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    libs_ref = data.get("assets", {}).get("libs_ref")
    if not libs_ref:
        return None
    models = _models_under_libs_ref(Path(libs_ref))
    if models is None:
        return None
    primitives, behavioural = models
    return ResolvedModels(
        variant=data.get("variant", PDK_VARIANT),
        version=str(data.get("version", "unknown")),
        resolved_via=f"klt pdk find --pdk {PDK_VARIANT} (root: {data.get('root', '?')})",
        libs_ref=Path(libs_ref),
        primitives_v=primitives,
        behavioural_v=behavioural,
    )


def _try_root(root: Path, resolved_via: str) -> ResolvedModels | None:
    libs_ref = root / PDK_VARIANT / "libs.ref"
    models = _models_under_libs_ref(libs_ref)
    if models is None:
        return None
    primitives, behavioural = models
    return ResolvedModels(
        variant=PDK_VARIANT,
        version="unknown (resolved by direct path search, not klt)",
        resolved_via=resolved_via,
        libs_ref=libs_ref,
        primitives_v=primitives,
        behavioural_v=behavioural,
    )


def resolve_sky130_models() -> ResolvedModels:
    """Resolve sky130_fd_sc_hd's behavioural Verilog, or raise PdkResolutionError.

    Never returns a partial/empty result — either both `primitives.v` and
    `sky130_fd_sc_hd.v` are found together, or resolution fails outright with
    `INSTALL_HINT`.
    """
    resolved = _try_klt()
    if resolved is not None:
        return resolved

    pdk_root = os.environ.get("PDK_ROOT")
    if pdk_root:
        resolved = _try_root(Path(pdk_root).expanduser(), f"$PDK_ROOT ({pdk_root})")
        if resolved is not None:
            return resolved

    volare_root = Path.home() / ".volare"
    resolved = _try_root(volare_root, f"~/.volare ({volare_root})")
    if resolved is not None:
        return resolved

    raise PdkResolutionError(INSTALL_HINT)
