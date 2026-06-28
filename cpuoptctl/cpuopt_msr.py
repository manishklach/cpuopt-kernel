from __future__ import annotations

import os
from pathlib import Path
from typing import Any


INTEL_SAFE_MSRS: dict[str, int] = {
    "IA32_ENERGY_PERF_BIAS": 0x1B0,
    "IA32_PACKAGE_THERM_STATUS": 0x1B1,
    "IA32_THERM_STATUS": 0x19C,
    "IA32_HWP_CAPABILITIES": 0x771,
    "IA32_HWP_REQUEST": 0x774,
    "IA32_HWP_STATUS": 0x777,
}


def safe_root_check() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def decode_intel_msrs(
    dev_root: str = "/dev",
    cpu: int = 0,
    safe: bool = False,
    is_root: bool | None = None,
) -> dict[str, Any]:
    if not safe:
        return {"available": False, "reason": "--safe is required for read-only MSR telemetry"}
    root_state = is_root if is_root is not None else safe_root_check()
    if not root_state:
        return {"available": False, "reason": "root privileges are required for read-only MSR telemetry"}

    msr_path = Path(dev_root) / "cpu" / str(cpu) / "msr"
    if not msr_path.exists():
        return {"available": False, "reason": f"MSR device not present at {msr_path}"}

    decoded: dict[str, Any] = {}
    try:
        fd = os.open(msr_path, os.O_RDONLY)
        try:
            for name, offset in INTEL_SAFE_MSRS.items():
                raw = os.pread(fd, 8, offset)
                if len(raw) != 8:
                    decoded[name] = {"error": "short-read"}
                    continue
                value = int.from_bytes(raw, byteorder="little", signed=False)
                decoded[name] = {"offset": hex(offset), "value": hex(value), "fields": _decode_fields(name, value)}
        finally:
            os.close(fd)
    except OSError as exc:
        return {"available": False, "reason": str(exc)}
    return {"available": True, "cpu": cpu, "msr_path": str(msr_path), "registers": decoded, "read_only": True}


def format_msr_report(report: dict[str, Any]) -> str:
    if not report.get("available"):
        return f"Intel MSR telemetry unavailable: {report.get('reason')}"
    lines = ["Intel MSR Telemetry", "-------------------", "Read-only Intel MSR telemetry decoder. No writes. No tuning."]
    lines.append(f"CPU: {report.get('cpu')}")
    lines.append(f"MSR path: {report.get('msr_path')}")
    for name, payload in report.get("registers", {}).items():
        lines.append(f"{name}: {payload.get('value')}")
        fields = payload.get("fields", {})
        for key, value in fields.items():
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def _decode_fields(name: str, value: int) -> dict[str, int]:
    if name == "IA32_ENERGY_PERF_BIAS":
        return {"bias": value & 0xF}
    if name == "IA32_PACKAGE_THERM_STATUS":
        return {"thermal_status": value & 0x1, "digital_readout": (value >> 16) & 0x7F}
    if name == "IA32_THERM_STATUS":
        return {"thermal_status": value & 0x1, "digital_readout": (value >> 16) & 0x7F}
    if name == "IA32_HWP_CAPABILITIES":
        return {
            "highest_performance": value & 0xFF,
            "guaranteed_performance": (value >> 8) & 0xFF,
            "most_efficient_performance": (value >> 16) & 0xFF,
            "lowest_performance": (value >> 24) & 0xFF,
        }
    if name == "IA32_HWP_REQUEST":
        return {
            "minimum_performance": value & 0xFF,
            "maximum_performance": (value >> 8) & 0xFF,
            "desired_performance": (value >> 16) & 0xFF,
            "energy_performance_preference": (value >> 24) & 0xFF,
        }
    if name == "IA32_HWP_STATUS":
        return {"change_to_guaranteed": value & 0x1, "excursion_to_minimum": (value >> 2) & 0x1}
    return {}
