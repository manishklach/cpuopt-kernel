from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError):
        return None


def read_int(path: Path) -> int | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def list_dirs(path: Path, pattern: str) -> list[Path]:
    if not path.exists():
        return []
    return sorted([candidate for candidate in path.glob(pattern) if candidate.exists()])


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return {k: json_ready(v) for k, v in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(v) for v in value]
    return value


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def save_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")
