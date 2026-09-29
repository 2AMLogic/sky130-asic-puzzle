"""Shared result-tracking and synthetic-shape helpers for the `tools/test-*`
self-test scripts.

`make_tracker()` builds the common pass/FAIL/skip `record()`/`check()` pair
used identically by `test-pins`, `test-extract`, and `test-inventory`
(`test-compare` keeps its own `record()` with a deliberately different print
format -- see the comment there). `_box()`/`_label()` are the KLayout
synthetic-cell builders shared by `test-pins` and `test-extract`.

`make_tracker()` returns a fresh `results` list plus `record`/`check`
functions closed over it, so each caller owns its own tracker instead of
sharing mutable module state -- the scripts stay independently runnable and
their exit-status accounting stays local to each file.
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


def _box(cell, layout, layer_num, datatype, x0, y0, x1, y1):
    from klayout import db

    li = layout.layer(layer_num, datatype)
    cell.shapes(li).insert(db.Box(x0, y0, x1, y1))


def _label(cell, layout, layer_num, datatype, text, x, y):
    from klayout import db

    li = layout.layer(layer_num, datatype)
    cell.shapes(li).insert(db.Text(text, x, y))
