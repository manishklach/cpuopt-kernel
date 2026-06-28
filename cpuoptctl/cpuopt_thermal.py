from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .cpuopt_utils import list_dirs, read_int, read_text
except ImportError:
    from cpuopt_utils import list_dirs, read_int, read_text


def discover_thermal(sysfs_root: Path) -> dict[str, Any]:
    thermal_root = sysfs_root / "class" / "thermal"
    zones: list[dict[str, Any]] = []
    cooling: list[dict[str, Any]] = []

    for zone in list_dirs(thermal_root, "thermal_zone*"):
        zones.append(
            {
                "name": zone.name,
                "type": read_text(zone / "type"),
                "temp": read_int(zone / "temp"),
                "mode": read_text(zone / "mode"),
            }
        )

    for device in list_dirs(thermal_root, "cooling_device*"):
        cooling.append(
            {
                "name": device.name,
                "type": read_text(device / "type"),
                "cur_state": read_int(device / "cur_state"),
                "max_state": read_int(device / "max_state"),
            }
        )

    return {"thermal_zones": zones, "cooling_devices": cooling}


def discover_hwmon(sysfs_root: Path) -> list[dict[str, Any]]:
    hwmon_root = sysfs_root / "class" / "hwmon"
    devices: list[dict[str, Any]] = []
    for device in list_dirs(hwmon_root, "hwmon*"):
        item: dict[str, Any] = {"name": read_text(device / "name") or device.name, "path": str(device)}
        sensors: dict[str, Any] = {}
        for candidate in sorted(device.iterdir()) if device.exists() else []:
            if candidate.is_file() and any(token in candidate.name for token in ("temp", "fan", "pwm")):
                sensors[candidate.name] = read_text(candidate)
        item["sensors"] = sensors
        devices.append(item)
    return devices
