from __future__ import annotations

import time
from typing import Any

try:
    from .cpuopt_discovery import discover
    from .cpuopt_utils import now_utc
except ImportError:
    from cpuopt_discovery import discover
    from cpuopt_utils import now_utc


def collect_sample(sysfs_root: str = "/sys") -> dict[str, Any]:
    data = discover(sysfs_root=sysfs_root)
    policy_samples = []
    freqs = []
    for policy in data.get("policies", []):
        cur = policy.get("scaling_cur_freq")
        if isinstance(cur, int):
            freqs.append(cur)
        policy_samples.append(
            {
                "policy": policy.get("name"),
                "governor": policy.get("scaling_governor"),
                "epp": policy.get("energy_performance_preference"),
                "current_freq": cur,
            }
        )

    hottest = None
    zones = data.get("thermal", {}).get("thermal_zones", [])
    if zones:
        hottest = max(zones, key=lambda zone: zone.get("temp") or -1)

    return {
        "timestamp": now_utc(),
        "avg_current_freq": int(sum(freqs) / len(freqs)) if freqs else None,
        "min_current_freq": min(freqs) if freqs else None,
        "max_current_freq": max(freqs) if freqs else None,
        "policies": policy_samples,
        "package_temp": hottest.get("temp") if hottest else None,
        "hottest_zone": hottest.get("type") if hottest else None,
        "turbo_status": data.get("intel_pstate", {}).get("no_turbo"),
        "boost_status": data.get("cpufreq_boost"),
        "cooling_devices": data.get("thermal", {}).get("cooling_devices", []),
    }


def monitor(sysfs_root: str = "/sys", interval: int = 1) -> list[dict[str, Any]]:
    samples = []
    try:
        while True:
            sample = collect_sample(sysfs_root=sysfs_root)
            samples.append(sample)
            yield sample
            time.sleep(interval)
    except KeyboardInterrupt:
        return samples
