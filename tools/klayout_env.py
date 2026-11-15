"""Resolve an importable `klayout` Python module and open GDS streams.

Every CLI in this repo that reads a GDS stream does both through this
module: `ensure_klayout()` makes `import klayout.db` succeed, and
`open_layout()` performs the whole resolve -> existence-check -> read
preamble on top of it, so the GDS-open error wording lives in exactly one
place and a new GDS-reading CLI inherits it instead of re-rolling the
block. Nothing in this repo vendors that package -- `klt` (the
`klayout-tools` CLI under test) already depends on it, so the interpreter
`klt` itself runs under is the one reliable place to find it without asking a
contributor to `pip install` anything extra.

Resolution order:

  1. Already importable in the running interpreter (fast path once a
     contributor has `pip install klayout`d it themselves, or is already
     running under an interpreter that has it).
  2. `$KLAYOUT_PYTHON` -- an explicit override naming an interpreter path.
  3. The interpreter named in `klt`'s own shebang line. `klt` (from
     `klayout-tools`) is installed as a self-contained tool (e.g. via
     `uv tool install klayout-tools`), so the interpreter next to it on disk
     is the one with `klayout` on its `sys.path`.

If (2) or (3) resolves to an interpreter that is not the one already running,
this process re-execs itself under that interpreter (`os.execv`) so
`import klayout.db` succeeds transparently for the rest of the CLI. Failure
is one actionable message and a non-zero exit -- never a silent stub.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import klayout.db

# Guards against relaunch loops: once we've re-exec'd once, a second failure
# to import means the resolved interpreter didn't actually have klayout
# either, and retrying forever would just spin.
_RELAUNCHED_ENV = "_TOOLS_KLAYOUT_RELAUNCHED"

INSTALL_HINT = (
    "No importable `klayout` Python module found (looked in the running "
    "interpreter, $KLAYOUT_PYTHON, and the interpreter behind `klt` on "
    "PATH). Install one with `pip install klayout`, or install "
    "klayout-tools (`uv tool install klayout-tools`), which depends on it, "
    "or point $KLAYOUT_PYTHON at an interpreter that already has it, then "
    "re-run."
)


class KlayoutResolutionError(RuntimeError):
    """Raised when no interpreter with an importable `klayout` can be found.

    Always carries `INSTALL_HINT` as the message -- a missing `klayout`
    module is one actionable install instruction, never a silent skip.
    """


class LayoutReadError(RuntimeError):
    """Raised when the file at `path` cannot be opened as a GDS layout.

    Covers both failure branches of the GDS-open preamble, with the exact
    wording the CLIs reported inline before the block was centralised:
    `no such file: <path>` when the path does not exist, and
    `could not read <path!r>: <reason>` when KLayout refuses the stream.
    The message carries no program prefix -- the caller adds `f"{prog}: "`,
    as it already does for `KlayoutResolutionError`.
    """


def _is_importable() -> bool:
    try:
        import klayout.db  # noqa: F401
    except ImportError:
        return False
    return True


def _klt_interpreter() -> str | None:
    """Read the interpreter path out of `klt`'s own shebang line, if found."""
    klt = shutil.which("klt")
    if klt is None:
        return None
    try:
        with open(klt, "r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline()
    except OSError:
        return None
    if not first_line.startswith("#!"):
        return None
    interp = first_line[2:].strip()
    return interp if interp and os.path.isfile(interp) else None


def ensure_klayout() -> None:
    """Make `import klayout.db` succeed in this process, or raise loudly.

    Call this before importing `klayout.db` at the top of a CLI entry point.
    If klayout is not importable under the running interpreter, this
    re-execs the current invocation under a resolved interpreter that has
    it. Never falls back to a stub/mocked module -- either the real
    `klayout.db` becomes importable, or this raises `KlayoutResolutionError`.
    """
    if _is_importable():
        return

    if os.environ.get(_RELAUNCHED_ENV):
        # Already relaunched once under a resolved interpreter and klayout
        # still isn't importable there either -- stop, don't loop.
        raise KlayoutResolutionError(INSTALL_HINT)

    candidates: list[str] = []
    override = os.environ.get("KLAYOUT_PYTHON")
    if override:
        candidates.append(override)
    klt_interp = _klt_interpreter()
    if klt_interp:
        candidates.append(klt_interp)

    for interp in candidates:
        if not os.path.isfile(interp):
            continue
        if os.path.abspath(interp) == os.path.abspath(sys.executable):
            continue
        os.environ[_RELAUNCHED_ENV] = "1"
        os.execv(interp, [interp] + sys.argv)  # never returns on success

    raise KlayoutResolutionError(INSTALL_HINT)


def open_layout(path: str) -> klayout.db.Layout:
    """Resolve klayout, then read the GDS stream at `path` into a `db.Layout`.

    The whole GDS-open preamble of a top-level CLI in one call: resolution
    (`ensure_klayout()`, which may re-exec this process), the existence
    check, and the `db.Layout().read()` itself. Raises
    `KlayoutResolutionError` when no importable `klayout` can be resolved
    and `LayoutReadError` for either read failure. Never prints and never
    exits -- that is the caller's job, adding its own prog prefix and exit
    status when it catches either error.
    """
    ensure_klayout()

    from klayout import db

    if not os.path.isfile(path):
        raise LayoutReadError(f"no such file: {path}")

    layout = db.Layout()
    try:
        layout.read(path)
    except Exception as exc:  # klayout raises its own RuntimeError subclasses
        raise LayoutReadError(f"could not read {path!r}: {exc}") from exc
    return layout
