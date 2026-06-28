from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cpuopt_profiles import ProposedWrite
from .cpuopt_utils import now_utc, read_text, save_json, write_text


def state_path(state_dir: str) -> Path:
    return Path(state_dir) / "last_state.json"


def write_log_path(state_dir: str) -> Path:
    return Path(state_dir) / "write_log.jsonl"


def log_write(state_dir: str, entry: dict[str, Any]) -> None:
    path = write_log_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def snapshot_existing(writes: list[ProposedWrite], state_dir: str) -> dict[str, Any]:
    if not writes:
        return {"timestamp": now_utc(), "entries": []}
    snapshot_entries = []
    for item in writes:
        current = read_text(Path(item.path))
        snapshot_entries.append({"path": item.path, "value": current})
    snapshot = {"timestamp": now_utc(), "entries": snapshot_entries}
    save_json(state_path(state_dir), snapshot)
    return snapshot


def validate_write(item: ProposedWrite, current_value: str | None) -> str | None:
    path = Path(item.path)
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "not-a-file"
    if current_value is None:
        return "unreadable-current-value"
    if item.valid_values is not None and item.value not in item.valid_values:
        return "invalid-value"
    return None


def apply_writes(writes: list[ProposedWrite], state_dir: str, dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in writes:
        path = Path(item.path)
        current_value = read_text(path)
        result = {
            "path": item.path,
            "current": current_value,
            "value": item.value,
            "reason": item.reason,
            "applied": False,
        }
        validation_error = validate_write(item, current_value)
        if validation_error is not None:
            result["error"] = validation_error
        elif dry_run:
            result["dry_run"] = True
        else:
            try:
                write_text(path, item.value)
                result["applied"] = True
            except OSError as exc:
                result["error"] = str(exc)
        if not dry_run:
            log_write(state_dir, result)
        results.append(result)
    return results


def restore_from_snapshot(snapshot: dict[str, Any], state_dir: str) -> int:
    restored = 0
    for entry in snapshot.get("entries", []):
        path = Path(entry["path"])
        if not path.exists():
            continue
        try:
            if entry["value"] is not None:
                write_text(path, str(entry["value"]))
            restored += 1
            log_write(state_dir, {"path": str(path), "restored": True, "value": entry["value"]})
        except OSError as exc:
            log_write(state_dir, {"path": str(path), "restored": False, "error": str(exc)})
    return restored
