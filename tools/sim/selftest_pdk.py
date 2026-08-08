"""Self-test `tools/sim/pdk.py`'s resolution order — above all its failure path.

`resolve_sky130_models()` is the one part of the harness whose *failure*
behaviour is an acceptance criterion in its own right (issue #5: a missing
model set must produce one actionable install instruction and a non-zero
exit, never a silent skip or a green run against no models). That path
cannot be exercised on a workstation that has a PDK installed — which this
one now does — so it is exercised here by pinning all three sources in the
documented search order (`klt` on `PATH`, `$PDK_ROOT`, `~/.volare`) to
point at controlled temporary directories.

This is deliberately a committed, re-runnable check rather than a manual
one: CLAUDE.md §5 asks for claims backed by something a reader can re-run,
and "the resolver fails loudly when no PDK exists" is exactly such a claim.

Run it with:

    python3 -m tools.sim.selftest_pdk

No PDK, no `klt`, and no simulator are required — every external source is
mocked, so this runs identically on a machine with a PDK and on one
without (which is the whole point).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest import mock

from tools.sim import pdk
from tools.sim.pdk import INSTALL_HINT, PdkResolutionError, resolve_sky130_models

FAKE_KLT_PATH = "/nonexistent/bin/klt"


def _make_install(root: Path, *, primitives: bool = True, behavioural: bool = True) -> Path:
    """Create a fake open_pdks-shaped install under `root`; return its libs.ref.

    `primitives=False` / `behavioural=False` build a *partial* install — the
    case the non-empty-or-fail contract exists for.
    """
    libs_ref = root / pdk.PDK_VARIANT / "libs.ref"
    verilog_dir = libs_ref / pdk.CELL_LIBRARY / "verilog"
    verilog_dir.mkdir(parents=True, exist_ok=True)
    if primitives:
        (verilog_dir / "primitives.v").write_text("// fake primitives.v (self-test fixture)\n")
    if behavioural:
        (verilog_dir / f"{pdk.CELL_LIBRARY}.v").write_text(f"// fake {pdk.CELL_LIBRARY}.v (self-test fixture)\n")
    return libs_ref


@contextmanager
def _search_order(
    *,
    home: Path,
    klt_result: subprocess.CompletedProcess | None = None,
    pdk_root: Path | None = None,
) -> Iterator[None]:
    """Pin every source `resolve_sky130_models()` consults.

    `klt_result=None` means `klt` is not on `PATH` at all; otherwise `klt`
    resolves and `subprocess.run` returns exactly the given result. `home`
    is always redirected at a temporary directory so a real `~/.volare`
    install on the machine running this can never leak into a result.
    """
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PDK_ROOT", None)
        if pdk_root is not None:
            os.environ["PDK_ROOT"] = str(pdk_root)

        def fake_which(name: str) -> str | None:
            return FAKE_KLT_PATH if (name == "klt" and klt_result is not None) else None

        def fake_run(*_args, **_kwargs) -> subprocess.CompletedProcess:
            if klt_result is None:  # pragma: no cover - guards a mocking mistake
                raise AssertionError("subprocess.run called with klt absent from PATH")
            return klt_result

        with (
            mock.patch.object(pdk.shutil, "which", fake_which),
            mock.patch.object(pdk.subprocess, "run", fake_run),
            mock.patch.object(Path, "home", lambda: home),
        ):
            yield


def _klt_ok(libs_ref: Path, *, version: str = "0.0.0-selftest") -> subprocess.CompletedProcess:
    payload = {
        "variant": pdk.PDK_VARIANT,
        "version": version,
        "root": str(libs_ref.parent.parent),
        "assets": {"libs_ref": str(libs_ref)},
    }
    return subprocess.CompletedProcess(args=[FAKE_KLT_PATH], returncode=0, stdout=json.dumps(payload), stderr="")


def _klt_failed() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[FAKE_KLT_PATH], returncode=1, stdout="", stderr="no sky130A install found\n"
    )


# --- checks -----------------------------------------------------------------
# Each returns (passed, detail). The failure-path checks are the ones issue #5
# requires; the two positive controls exist so a check like "raises when there
# is no PDK" cannot pass vacuously (i.e. by the harness never finding anything).


def check_no_pdk_anywhere(tmp: Path) -> tuple[bool, str]:
    """The criterion: nothing on any of the three sources -> loud, actionable failure."""
    home = tmp / "empty-home"
    home.mkdir()
    with _search_order(home=home):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            message = str(exc)
            ok = (
                message == INSTALL_HINT
                and "volare" in message
                and "$PDK_ROOT" in message
                and "klt pdk find" in message
            )
            return ok, f"raised PdkResolutionError; message is INSTALL_HINT with install instructions: {ok}"
        return False, f"NO exception raised — silently returned {resolved.resolved_via!r} (this is the silent skip #5 forbids)"


def check_klt_present_but_fails(tmp: Path) -> tuple[bool, str]:
    """`klt` on PATH but exiting non-zero must fall through, not crash or resolve."""
    home = tmp / "empty-home-klt-fail"
    home.mkdir()
    with _search_order(home=home, klt_result=_klt_failed()):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return str(exc) == INSTALL_HINT, "klt failure fell through to PdkResolutionError"
        return False, f"resolved anyway via {resolved.resolved_via!r} despite klt failing"


def check_klt_returns_garbage(tmp: Path) -> tuple[bool, str]:
    """Non-JSON on klt's stdout must not propagate a JSONDecodeError to the caller."""
    home = tmp / "empty-home-klt-garbage"
    home.mkdir()
    garbage = subprocess.CompletedProcess(args=[FAKE_KLT_PATH], returncode=0, stdout="not json at all", stderr="")
    with _search_order(home=home, klt_result=garbage):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return str(exc) == INSTALL_HINT, "unparseable klt output fell through to PdkResolutionError"
        except json.JSONDecodeError as exc:  # pragma: no cover - regression guard
            return False, f"leaked a JSONDecodeError to the caller: {exc}"
        return False, f"resolved anyway via {resolved.resolved_via!r} on unparseable klt output"


def check_partial_install_is_not_accepted(tmp: Path) -> tuple[bool, str]:
    """Half an install (primitives.v but no sky130_fd_sc_hd.v) must fail, not half-resolve."""
    root = tmp / "partial-root"
    _make_install(root, primitives=True, behavioural=False)
    home = tmp / "empty-home-partial"
    home.mkdir()
    with _search_order(home=home, pdk_root=root):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return str(exc) == INSTALL_HINT, "partial install rejected; PdkResolutionError raised"
        return False, f"accepted a partial install via {resolved.resolved_via!r} (non-empty-or-fail contract broken)"


def check_pdk_root_resolves(tmp: Path) -> tuple[bool, str]:
    """Positive control for source 2 — proves the failure checks aren't vacuous."""
    root = tmp / "pdk-root"
    libs_ref = _make_install(root)
    home = tmp / "empty-home-pdk-root"
    home.mkdir()
    with _search_order(home=home, pdk_root=root):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return False, f"failed on a complete $PDK_ROOT install: {exc}"
    ok = (
        resolved.libs_ref == libs_ref
        and resolved.primitives_v.is_file()
        and resolved.behavioural_v.is_file()
        and "$PDK_ROOT" in resolved.resolved_via
    )
    return ok, f"resolved via {resolved.resolved_via!r}"


def check_volare_fallback_resolves(tmp: Path) -> tuple[bool, str]:
    """Positive control for source 3 (`~/.volare`) with klt absent and $PDK_ROOT unset."""
    home = tmp / "volare-home"
    libs_ref = _make_install(home / ".volare")
    with _search_order(home=home):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return False, f"failed on a complete ~/.volare install: {exc}"
    ok = resolved.libs_ref == libs_ref and "~/.volare" in resolved.resolved_via
    return ok, f"resolved via {resolved.resolved_via!r}"


def check_klt_resolves(tmp: Path) -> tuple[bool, str]:
    """Positive control for source 1 — klt's JSON is preferred over the direct paths."""
    klt_root = tmp / "klt-root"
    libs_ref = _make_install(klt_root)
    other_root = tmp / "shadowed-pdk-root"
    _make_install(other_root)
    home = tmp / "empty-home-klt-ok"
    home.mkdir()
    with _search_order(home=home, klt_result=_klt_ok(libs_ref), pdk_root=other_root):
        try:
            resolved = resolve_sky130_models()
        except PdkResolutionError as exc:
            return False, f"failed on a complete klt-reported install: {exc}"
    ok = resolved.libs_ref == libs_ref and "klt pdk find" in resolved.resolved_via and resolved.version == "0.0.0-selftest"
    return ok, f"resolved via {resolved.resolved_via!r} (version {resolved.version})"


CHECKS = [
    ("no PDK anywhere -> PdkResolutionError carrying the install hint", check_no_pdk_anywhere),
    ("klt present but exits non-zero -> falls through, still fails loudly", check_klt_present_but_fails),
    ("klt emits unparseable JSON -> falls through, no leaked JSONDecodeError", check_klt_returns_garbage),
    ("partial install (no sky130_fd_sc_hd.v) -> rejected, not half-resolved", check_partial_install_is_not_accepted),
    ("[control] complete $PDK_ROOT install -> resolves via $PDK_ROOT", check_pdk_root_resolves),
    ("[control] complete ~/.volare install -> resolves via ~/.volare", check_volare_fallback_resolves),
    ("[control] klt-reported install -> resolves via klt, ahead of $PDK_ROOT", check_klt_resolves),
]


def main() -> int:
    print("== tools/sim/pdk.py resolution-order self-test (all three sources mocked) ==")
    failures = 0
    for name, check in CHECKS:
        with tempfile.TemporaryDirectory(prefix="pdk-selftest-") as tmpdir:
            try:
                passed, detail = check(Path(tmpdir))
            except Exception as exc:  # noqa: BLE001 - an unexpected raise is a failure, not a crash
                passed, detail = False, f"unexpected {type(exc).__name__}: {exc}"
        print(f"[{'PASS' if passed else 'FAIL'}] {name}\n         {detail}")
        if not passed:
            failures += 1

    print(f"\nSELF-TEST {'PASS' if failures == 0 else 'FAIL'} ({len(CHECKS) - failures}/{len(CHECKS)} checks passed)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
