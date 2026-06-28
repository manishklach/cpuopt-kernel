from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .cpuopt_intel import epb_for_profile, epp_for_profile, governor_for_profile
except ImportError:
    from cpuopt_intel import epb_for_profile, epp_for_profile, governor_for_profile


@dataclass
class ProposedWrite:
    path: str
    current: str | None
    value: str
    reason: str
    valid_values: tuple[str, ...] | None = None


def _maybe_add_write(
    writes: list[ProposedWrite],
    path: Path,
    current: str | None,
    value: str | None,
    reason: str,
    valid_values: list[str] | None = None,
) -> None:
    if value is None or current == value:
        return
    if valid_values is not None and value not in valid_values:
        return
    writes.append(
        ProposedWrite(
            path=str(path),
            current=current,
            value=value,
            reason=reason,
            valid_values=tuple(valid_values) if valid_values is not None else None,
        )
    )


def propose_profile(
    discovery: dict[str, Any],
    profile_name: str,
    sysfs_root: str,
    allow_idle_tuning: bool = False,
    allow_fan_control: bool = False,
    experimental_fan_write: bool = False,
    allow_turbo_disable: bool = False,
) -> dict[str, Any]:
    root = Path(sysfs_root).resolve()
    writes: list[ProposedWrite] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    for policy in discovery.get("policies", []):
        policy_path = Path(policy["path"])
        if not policy_path.is_absolute():
            policy_path = root / Path(policy["path"])
        selected_epp = epp_for_profile(
            profile_name, policy.get("energy_performance_available_preferences", [])
        )
        _maybe_add_write(
            writes,
            policy_path / "energy_performance_preference",
            policy.get("energy_performance_preference"),
            selected_epp,
            f"Set EPP for {profile_name}",
            policy.get("energy_performance_available_preferences", []),
        )
        selected_governor = governor_for_profile(profile_name, policy.get("available_governors", []))
        _maybe_add_write(
            writes,
            policy_path / "scaling_governor",
            policy.get("scaling_governor"),
            selected_governor,
            f"Set governor for {profile_name}",
            policy.get("available_governors", []),
        )
        _maybe_add_write(
            writes,
            policy_path / "energy_perf_bias",
            policy.get("energy_perf_bias"),
            epb_for_profile(profile_name),
            f"Set EPB for {profile_name}",
        )

    intel_pstate = discovery.get("intel_pstate", {})
    no_turbo_path = root / "devices" / "system" / "cpu" / "intel_pstate" / "no_turbo"
    if intel_pstate.get("exists") and no_turbo_path.exists():
        current = intel_pstate.get("no_turbo")
        if profile_name in {"performance", "latency", "ai-inference", "balanced"}:
            _maybe_add_write(writes, no_turbo_path, current, "0", "Enable turbo safely via intel_pstate")
        elif profile_name == "quiet" and allow_turbo_disable:
            _maybe_add_write(writes, no_turbo_path, current, "1", "Optionally reduce turbo for quiet mode")

    boost_path = root / "devices" / "system" / "cpu" / "cpufreq" / "boost"
    if boost_path.exists():
        current_boost = discovery.get("cpufreq_boost")
        if profile_name in {"performance", "latency", "ai-inference", "balanced"}:
            _maybe_add_write(writes, boost_path, current_boost, "1", "Enable boost if supported")
        elif profile_name == "quiet" and allow_turbo_disable:
            _maybe_add_write(writes, boost_path, current_boost, "0", "Optionally reduce boost for quiet mode")

    if profile_name == "latency":
        warnings.append("Latency mode may increase power and temperature.")
        if allow_idle_tuning:
            deepest = _deepest_idle_states(discovery)
            for state in deepest:
                if state["disable"] != "1":
                    writes.append(
                        ProposedWrite(
                            path=state["disable_path"],
                            current=state["disable"],
                            value="1",
                            reason="Disable deepest idle state for latency mode",
                            valid_values=("0", "1"),
                        )
                    )

    if profile_name == "quiet":
        warnings.append("Lower fan speed can reduce sustained performance.")
        if allow_fan_control and experimental_fan_write:
            warnings.append("Fan writes remain intentionally unimplemented.")

    if profile_name == "ai-inference":
        recommendations.extend(
            [
                "Consider pinning worker threads to locality-aware CPU sets.",
                "Review NUMA node placement before large inference runs.",
                "Inspect uncore controls manually; v0.1 reports them only.",
            ]
        )

    return {
        "profile": profile_name,
        "writes": writes,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def _deepest_idle_states(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for state in discovery.get("cpuidle_states", []):
        cpu = state.get("cpu")
        latency_raw = state.get("latency")
        latency = latency_raw if latency_raw is not None else -1
        disable_path = (
            f"{discovery['sysfs_root']}/devices/system/cpu/{cpu}/cpuidle/{state['state']}/disable"
        )
        candidate = dict(state)
        candidate["disable_path"] = disable_path
        existing_latency_raw = grouped[cpu].get("latency") if cpu in grouped else None
        existing_latency = existing_latency_raw if existing_latency_raw is not None else -1
        if cpu not in grouped or latency > existing_latency:
            grouped[cpu] = candidate
    return list(grouped.values())
