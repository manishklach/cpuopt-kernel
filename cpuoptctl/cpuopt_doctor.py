from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def build_doctor_report(
    discovery: dict[str, Any],
    state_dir: str,
    dev_root: str = "/dev",
    is_root: bool | None = None,
) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    policies = discovery.get("policies", [])
    intel_pstate = discovery.get("intel_pstate", {})
    if intel_pstate.get("status") == "active":
        findings.append(("OK", "intel_pstate active"))
    elif any(policy.get("scaling_driver") for policy in policies):
        findings.append(("INFO", f"scaling driver detected: {policies[0].get('scaling_driver')}"))
    else:
        findings.append(("WARN", "no scaling driver detected"))

    has_epp = any(policy.get("energy_performance_preference") for policy in policies)
    findings.append(("OK" if has_epp else "WARN", "EPP exposed" if has_epp else "EPP not exposed"))

    turbo_disabled = intel_pstate.get("no_turbo") == "1" or discovery.get("cpufreq_boost") == "0"
    findings.append(("WARN" if turbo_disabled else "OK", "turbo disabled" if turbo_disabled else "turbo enabled"))

    has_perf_governor = any("performance" in policy.get("available_governors", []) for policy in policies)
    findings.append(
        ("OK" if has_perf_governor else "WARN", "performance governor available" if has_perf_governor else "performance governor unavailable")
    )

    zone_count = len(discovery.get("thermal", {}).get("thermal_zones", []))
    findings.append(("INFO", f"{zone_count} thermal zones detected"))

    hwmon = discovery.get("hwmon", [])
    fan_detected = any(
        any(name.startswith("fan") for name in device.get("sensors", {}))
        for device in hwmon
    )
    if fan_detected:
        findings.append(("INFO", "hwmon fan sensors detected, write disabled by policy"))
    else:
        findings.append(("INFO", "no hwmon fan sensors detected"))

    deepest = _deepest_state(discovery)
    if deepest is not None and (deepest.get("latency") or 0) >= 100:
        findings.append(
            (
                "WARN",
                "deepest C-state has high exit latency; latency profile may benefit from --allow-idle-tuning",
            )
        )
    elif deepest is not None:
        findings.append(("INFO", "cpuidle states detected with modest deepest-state latency"))
    else:
        findings.append(("INFO", "no cpuidle states detected"))

    findings.append(
        ("INFO", "restore snapshot available" if (Path(state_dir) / "last_state.json").exists() else "no restore snapshot available")
    )

    root_state = is_root if is_root is not None else (_safe_is_root())
    findings.append(("OK" if root_state else "WARN", "running with root privileges" if root_state else "not running as root; write operations may fail"))

    msr_path = Path(dev_root) / "cpu" / "0" / "msr"
    findings.append(("INFO", "MSR device available for read-only telemetry" if msr_path.exists() else "MSR device not available for read-only telemetry"))

    findings.append(("INFO", "no uncore frequency interface detected"))
    return findings


def format_doctor_report(findings: list[tuple[str, str]]) -> str:
    lines = ["CPUOpt Doctor", "-------------"]
    for level, message in findings:
        lines.append(f"[{level}] {message}")
    return "\n".join(lines)


def _safe_is_root() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def _deepest_state(discovery: dict[str, Any]) -> dict[str, Any] | None:
    states = discovery.get("cpuidle_states", [])
    if not states:
        return None
    return max(states, key=lambda state: state.get("latency") or -1)
