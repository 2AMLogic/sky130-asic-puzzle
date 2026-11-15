"""Shared result-tracking and synthetic-shape helpers for this repo's
self-test scripts.

`make_tracker()` builds the common pass/FAIL/skip `record()`/`check()` pair
used identically by `test-pins`, `test-extract`, `test-inventory`, and
`test-klt-extract` (`test-compare` keeps its own `record()` with a
deliberately different per-check print format -- see the comment there).
`_box()`/`_label()` are the KLayout synthetic-cell builders shared by
`test-pins` and `test-extract`.

`make_tracker()` returns a fresh `results` list plus `record`/`check`
functions closed over it, so each caller owns its own tracker instead of
sharing mutable module state -- the scripts stay independently runnable and
their exit-status accounting stays local to each file.

`summarize()` prints the trailing count line all five `tools/test-*` scripts
end with (including `test-compare`, whose documented divergence is the
per-check format, not the summary). `report_checks()` is the same idea for
the `tools/sim/` selftests, which carry their own `(label, ok)` check lists
and a different summary format.

`require_klayout()`/`skip_all_no_klayout()` are the module-level klayout
bootstrap and skip-all guard shared by `test-pins`, `test-extract` and
`test-inventory` (each caller's `main()` keeps its own title print and the
`if not KLAYOUT_OK:` branch). The guard's skip block must print identically
from all three, which one shared copy enforces.

Both summary formats are quoted verbatim as committed evidence
(`evidence/independent-review.md`, `evidence/warmup-regression.md`,
`evidence/warmup-sim.md`, `evidence/puzzle-answer.md`), which CLAUDE.md
§5 treats as the re-runnable record. Their output is therefore
byte-for-byte fixed: re-rendering either one -- even reordering the counts --
silently falsifies those files, so a format change here means re-recording
the evidence in the same commit.
"""

from __future__ import annotations

PASS, FAIL, SKIP = "pass", "FAIL", "skip"

_MARKERS = {"pass": "ok", "FAIL": "FAIL", "skip": "skip"}


def make_tracker():
    """Return `(results, record, check)` for a fresh, independent tracker."""

    results: list[tuple[str, str, str]] = []

    def record(name: str, status: str, detail: str = "") -> None:
        results.append((name, status, detail))
        marker = _MARKERS[status]
        print(f"  {marker:6s} {name}" + (f" -- {detail}" if detail else ""))

    def check(name: str, condition: bool, detail: str = "") -> None:
        record(name, PASS if condition else FAIL, detail)

    return results, record, check


def summarize(results: list[tuple[str, str, str]]) -> int:
    """Print `"{n} passed, {n} failed, {n} skipped"`; return a shell exit code.

    Output is byte-for-byte what the five `tools/test-*` scripts printed
    before this was shared -- see the module docstring on why that matters.
    Callers that want the `"=" * 60` rule above the count print it
    themselves; `test-compare` deliberately does not.
    """

    failed = [r for r in results if r[1] == FAIL]
    skipped = [r for r in results if r[1] == SKIP]
    passed = [r for r in results if r[1] == PASS]
    print(f"{len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped")
    return 1 if failed else 0


def report_checks(checks: list[tuple[str, bool]]) -> int:
    """Print the `tools/sim/` selftest `[PASS]`/`[FAIL]` block; return an exit code.

    `checks` is the `[(label, ok), ...]` list those selftests accumulate.
    Output is byte-for-byte what `selftest_answer.py` / `selftest_portmap.py`
    printed before this was shared, blank lines included.
    """

    print()
    passed = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")
        passed = passed and ok

    print(f"\nSELF-TEST {'PASS' if passed else 'FAIL'} "
          f"({sum(1 for _, ok in checks if ok)}/{len(checks)} checks passed)")
    return 0 if passed else 1


def require_klayout():
    """Resolve and import `klayout.db`; return `(ok, db, reason)`.

    `db` is the imported `klayout.db` module when `ok` is True (else None),
    and `reason` is the stringified failure when it is not. The broad except
    covers `klayout_env.KlayoutResolutionError` or any plain import failure
    -- environment-dependent either way, so callers skip all checks with
    `reason` rather than crash. Must be called with the script's own
    directory on `sys.path` (each harness inserts it before importing
    `testutil`) so that `klayout_env` resolves.
    """

    try:
        import klayout_env

        klayout_env.ensure_klayout()
        from klayout import db

        return True, db, ""
    except Exception as exc:  # noqa: BLE001 - KlayoutResolutionError or import failure, environment-dependent
        return False, None, str(exc)


def skip_all_no_klayout(reason: str) -> int:
    """Print the shared skip-all block; return the shell exit code (0).

    Output is byte-for-byte what `test-pins`, `test-extract` and
    `test-inventory` printed in this state before this was shared -- the
    skip line carrying `reason`, the `"=" * 60` rule, `SKIPPED (no klayout)`.
    """

    print(f"  {SKIP:6s} all checks -- klayout not importable: {reason}")
    print("=" * 60)
    print("SKIPPED (no klayout)")
    return 0


def _box(cell, layout, layer_num, datatype, x0, y0, x1, y1):
    from klayout import db

    li = layout.layer(layer_num, datatype)
    cell.shapes(li).insert(db.Box(x0, y0, x1, y1))


def _label(cell, layout, layer_num, datatype, text, x, y):
    from klayout import db

    li = layout.layer(layer_num, datatype)
    cell.shapes(li).insert(db.Text(text, x, y))
