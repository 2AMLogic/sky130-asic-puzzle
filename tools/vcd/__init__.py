"""Minimal VCD reader/writer used by tools/sim.

See model.py for the data model and reader.py/writer.py docstrings for scope
and limitations. This is intentionally small — the VCD format is small
enough that a dependency is optional here, not required (issue #5).
"""

from .model import ValueChange, VcdDocument, VcdVar
from .reader import normalize_value, read_vcd
from .writer import document_to_vcd, write_vcd

__all__ = [
    "ValueChange",
    "VcdDocument",
    "VcdVar",
    "normalize_value",
    "read_vcd",
    "document_to_vcd",
    "write_vcd",
]
