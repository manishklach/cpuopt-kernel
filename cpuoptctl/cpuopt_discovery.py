from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

try:
    from .cpuopt_amd import annotate as annotate_amd
    from .cpuopt_arm import annotate as annotate_arm
    from .cpuopt_thermal import discover_hwmon, discover_thermal
    from .cpuopt_utils import first_existing, list_dirs, normalize_whitespace, read_int, read_text
except ImportError:
    from cpuopt_amd import annotate as annotate_amd
    from cpuopt_arm import annotate as annotate_arm
    from cpuopt_thermal import discover_hwmon, discover_thermal
    from cpuopt_utils import first_existing, list_dirs, normalize_whitespace, read_int, read_text


def _parse_cpuinfo(cpuinfo_path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    text = read_text(cpuinfo_path)
    if not text:
        return parsed
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in parsed:
            parsed[key] = value.strip()
    return parsed


def _detect_cpuinfo(sysfs_root: Path) -> dict[str, str]:
    return _parse_cpuinfo(
        first_existing(
            [
                sysfs_root / "proc" / "cpuinfo",
                sysfs_root.parent / "proc" / "cpuinfo",
                Path("/proc/cpuinfo"),
            ]
        )
        or Path("/proc/cpuinfo")
    )


def _detect_kernel_release(sysfs_root: Path) -> str:
    value = read_text(
        first_existing(
            [
                sysfs_root / "proc" / "sys" / "kernel" / "osrelease",
                sysfs_root.parent / "proc" / "sys" / "kernel" / "osrelease",
                Path("/proc/sys/kernel/osrelease"),
            ]
        )
        or Path("/proc/sys/kernel/osrelease")
    )
    return value or platform.release()


def _policy_data(policy: Path) -> dict[str, Any]:
    available_governors = (read_text(policy / "scaling_available_governors") or "").split()
    available_freqs = (read_text(policy / "scaling_available_frequencies") or "").split()
    available_epp = (read_text(policy / "energy_performance_available_preferences") or "").split()
    return {
        "name": policy.name,
        "path": str(policy.resolve()),
        "related_cpus": read_text(policy / "related_cpus"),
        "scaling_driver": read_text(policy / "scaling_driver"),
        "scaling_governor": read_text(policy / "scaling_governor"),
        "available_governors": available_governors,
        "available_frequencies": available_freqs,
        "cpuinfo_min_freq": read_int(policy / "cpuinfo_min_freq"),
        "cpuinfo_max_freq": read_int(policy / "cpuinfo_max_freq"),
        "scaling_min_freq": read_int(policy / "scaling_min_freq"),
        "scaling_max_freq": read_int(policy / "scaling_max_freq"),
        "scaling_cur_freq": read_int(policy / "scaling_cur_freq"),
        "energy_performance_preference": read_text(policy / "energy_performance_preference"),
        "energy_performance_available_preferences": available_epp,
        "energy_perf_bias": read_text(policy / "energy_perf_bias"),
    }


def _cpuidle_data(sysfs_root: Path) -> list[dict[str, Any]]:
    cpu_root = sysfs_root / "devices" / "system" / "cpu"
    states: list[dict[str, Any]] = []
    for cpu in list_dirs(cpu_root, "cpu[0-9]*"):
        for state in list_dirs(cpu / "cpuidle", "state*"):
            states.append(
                {
                    "cpu": cpu.name,
                    "state": state.name,
                    "name": read_text(state / "name"),
                    "desc": read_text(state / "desc"),
                    "latency": read_int(state / "latency"),
                    "disable": read_text(state / "disable"),
                }
            )
    return states


def _topology_data(sysfs_root: Path) -> list[dict[str, Any]]:
    cpu_root = sysfs_root / "devices" / "system" / "cpu"
    items: list[dict[str, Any]] = []
    for cpu in list_dirs(cpu_root, "cpu[0-9]*"):
        topo = cpu / "topology"
        items.append(
            {
                "cpu": cpu.name,
                "core_id": read_text(topo / "core_id"),
                "physical_package_id": read_text(topo / "physical_package_id"),
                "thread_siblings_list": read_text(topo / "thread_siblings_list"),
            }
        )
    return items


def _numa_data(sysfs_root: Path) -> list[dict[str, Any]]:
    node_root = sysfs_root / "devices" / "system" / "node"
    items: list[dict[str, Any]] = []
    for node in list_dirs(node_root, "node*"):
        items.append(
            {
                "name": node.name,
                "cpulist": read_text(node / "cpulist"),
                "distance": read_text(node / "distance"),
            }
        )
    return items


def discover(sysfs_root: str = "/sys") -> dict[str, Any]:
    root = Path(sysfs_root)
    cpuinfo = _detect_cpuinfo(root)
    cpu_root = root / "devices" / "system" / "cpu"
    cpufreq_root = cpu_root / "cpufreq"
    intel_pstate_root = cpu_root / "intel_pstate"
    amd_pstate_root = cpu_root / "amd_pstate"

    policies = [_policy_data(policy) for policy in list_dirs(cpufreq_root, "policy*")]
    thermal = discover_thermal(root)
    hwmon = discover_hwmon(root)

    vulnerabilities: dict[str, str] = {}
    vuln_root = cpu_root / "vulnerabilities"
    if vuln_root.exists():
        for candidate in sorted(vuln_root.iterdir()):
            if candidate.is_file():
                value = read_text(candidate)
                if value is not None:
                    vulnerabilities[candidate.name] = value

    data: dict[str, Any] = {
        "sysfs_root": str(root),
        "vendor": cpuinfo.get("vendor_id") or cpuinfo.get("CPU implementer") or platform.machine(),
        "arch": platform.machine(),
        "model_name": normalize_whitespace(cpuinfo.get("model name") or cpuinfo.get("Processor")),
        "family": cpuinfo.get("cpu family"),
        "model": cpuinfo.get("model"),
        "stepping": cpuinfo.get("stepping"),
        "kernel": _detect_kernel_release(root),
        "smt_control": read_text(cpu_root / "smt" / "control"),
        "intel_pstate": {
            "exists": intel_pstate_root.exists(),
            "status": read_text(intel_pstate_root / "status"),
            "no_turbo": read_text(intel_pstate_root / "no_turbo"),
        },
        "amd_pstate": {
            "exists": amd_pstate_root.exists(),
            "status": read_text(amd_pstate_root / "status"),
        },
        "cpufreq_boost": read_text(cpufreq_root / "boost"),
        "policies": policies,
        "cpuidle_states": _cpuidle_data(root),
        "thermal": thermal,
        "hwmon": hwmon,
        "topology": _topology_data(root),
        "numa": _numa_data(root),
        "vulnerabilities": vulnerabilities,
        "warnings": ["Fan control is platform-specific; not directly controlled unless safely exposed."],
        "vendor_notes": [],
    }

    vendor = str(data["vendor"])
    if "AuthenticAMD" in vendor:
        data = annotate_amd(data)
    elif "ARM" in vendor or "aarch64" in vendor or "arm" in str(data["arch"]).lower():
        data = annotate_arm(data)

    return data
