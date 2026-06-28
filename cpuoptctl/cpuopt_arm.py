from __future__ import annotations

from typing import Any


def annotate(discovery: dict[str, Any]) -> dict[str, Any]:
    discovery.setdefault("vendor_notes", []).append("ARM policy writes are not implemented in v0.2.")
    return discovery
