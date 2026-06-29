from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def recommend_profile(
    discovery: dict[str, Any],
    workload: str | None = None,
    workload_dir: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_workload(workload)
    preset = _load_workload_preset(normalized, workload_dir) if normalized else None

    vendor = str(discovery.get("vendor", ""))
    policies = discovery.get("policies", [])
    has_thermal = bool(discovery.get("thermal", {}).get("thermal_zones"))
    has_epp = any(policy.get("energy_performance_preference") for policy in policies)
    current_epp = [policy.get("energy_performance_preference") for policy in policies if policy.get("energy_performance_preference")]
    turbo_disabled = discovery.get("intel_pstate", {}).get("no_turbo") == "1" or discovery.get("cpufreq_boost") == "0"
    deepest_latency = max((state.get("latency") or 0) for state in discovery.get("cpuidle_states", [])) if discovery.get("cpuidle_states") else None
    package_temp = _package_temp(discovery)
    laptop_like = _is_laptop_like(discovery)

    reasons: list[str] = []
    warnings: list[str] = []
    unsupported: list[str] = []
    confidence = "high"

    if not has_thermal:
        confidence = _lower_confidence(confidence)
        warnings.append("Thermal zones are missing; recommendation confidence is reduced.")

    profile = "balanced"
    if "AuthenticAMD" in vendor:
        profile = _recommend_for_amd(normalized)
        reasons.append("AMD platform detected; using generic cpufreq and amd-pstate-safe guidance.")
        unsupported.append("Intel-specific HWP/EPP recommendations are suppressed on AMD.")
        if not discovery.get("amd_pstate", {}).get("exists"):
            warnings.append("amd-pstate is not exposed; recommendations stay conservative.")
    elif "arm" in str(discovery.get("arch", "")).lower() or "ARM" in vendor or "aarch64" in str(discovery.get("arch", "")):
        profile = _recommend_for_arm(normalized)
        reasons.append("ARM-style platform detected; using cpufreq/SCMI-style guidance.")
        unsupported.append("Intel-specific EPP and HWP recommendations are suppressed on ARM.")
    else:
        profile = _recommend_for_intel(normalized, has_epp)
        if has_epp:
            reasons.append("Intel platform with EPP exposure allows profile-aligned policy recommendations.")
        else:
            warnings.append("EPP is not exposed; recommendations rely more on governors and boost state.")

    if normalized in {"llama-inference", "ai-inference"}:
        profile = "ai-inference"
        reasons.append("AI inference workload maps directly to the ai-inference profile.")
    elif normalized == "latency" and "GenuineIntel" in vendor and has_epp:
        profile = "latency"
        reasons.append("Intel platform with EPP available and latency workload favors the latency profile.")
    elif normalized and preset is not None:
        preset_profile = preset.get("recommended_profile")
        if preset_profile in {"performance", "balanced", "latency", "quiet", "ai-inference"}:
            profile = preset_profile
            reasons.append(f"Workload preset '{preset.get('name')}' recommends the {preset_profile} profile.")

    if laptop_like:
        warnings.append("Laptop-like thermal and fan characteristics detected; quiet or balanced may be safer for sustained use.")
        if profile in {"performance", "latency", "ai-inference"}:
            warnings.append("Aggressive profiles on laptop-like systems may reduce thermal headroom.")

    if turbo_disabled and profile in {"performance", "latency", "ai-inference"}:
        warnings.append("Turbo or boost is currently disabled; recommended profile may underperform until it is re-enabled.")

    if deepest_latency is not None and deepest_latency >= 100 and profile == "latency":
        reasons.append("Deepest C-state latency is high enough that optional idle tuning may help latency-sensitive workloads.")

    if package_temp is not None and package_temp >= 80000:
        confidence = _lower_confidence(confidence)
        warnings.append("Thermal headroom appears limited; sustained high-performance profiles may not hold.")
    elif package_temp is not None:
        reasons.append(f"Observed package temperature is about {package_temp / 1000:.0f} C, suggesting current thermal headroom is acceptable.")

    optimal_epp = _optimal_epp_for_profile(profile)
    if has_epp and current_epp and all(value == optimal_epp for value in current_epp if optimal_epp is not None):
        reasons.append("Current EPP already matches the recommended profile intent; no changes may be needed.")

    if normalized is None:
        reasons.append("No workload preset was specified; recommendation is based on current platform capabilities and safety posture.")

    return {
        "recommended_profile": profile,
        "confidence": confidence,
        "reasons": reasons,
        "warnings": warnings,
        "suggested_dry_run_command": f"python cpuoptctl/cpuoptctl.py profile {profile} --dry-run --diff",
        "suggested_restore_command": "python cpuoptctl/cpuoptctl.py restore",
        "unsupported_features": unsupported,
        "workload": normalized,
    }


def format_recommendation(report: dict[str, Any]) -> str:
    lines = ["CPUOpt Recommendation", "---------------------"]
    lines.append(f"Recommended profile: {report.get('recommended_profile')}")
    lines.append(f"Confidence: {report.get('confidence')}")
    if report.get("workload"):
        lines.append(f"Workload: {report.get('workload')}")
    lines.append("")
    lines.append("Reasons:")
    for reason in report.get("reasons", []):
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("Warnings:")
    for warning in report.get("warnings", []):
        lines.append(f"- {warning}")
    if not report.get("warnings"):
        lines.append("- none")
    lines.append("")
    lines.append(f"Suggested dry-run command: {report.get('suggested_dry_run_command')}")
    lines.append(f"Suggested restore command: {report.get('suggested_restore_command')}")
    lines.append("")
    lines.append("Unsupported features:")
    for item in report.get("unsupported_features", []):
        lines.append(f"- {item}")
    if not report.get("unsupported_features"):
        lines.append("- none")
    return "\n".join(lines)


def _normalize_workload(workload: str | None) -> str | None:
    if not workload:
        return None
    value = workload.strip().lower()
    aliases = {
        "low-latency": "latency",
        "low-latency-trading": "low-latency-trading",
        "llama-inference": "llama-inference",
        "ai-inference": "ai-inference",
        "kernel-build": "kernel-build",
        "low-latency": "latency",
    }
    return aliases.get(value, value)


def _load_workload_preset(workload: str, workload_dir: str | None) -> dict[str, Any] | None:
    if workload_dir is None:
        workload_dir = str(Path(__file__).resolve().parents[1] / "examples" / "workloads")
    candidate = Path(workload_dir) / f"{workload}.json"
    if not candidate.exists():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _recommend_for_intel(workload: str | None, has_epp: bool) -> str:
    if workload == "kernel-build":
        return "performance"
    if workload in {"latency", "low-latency-trading"}:
        return "latency" if has_epp else "performance"
    if workload in {"llama-inference", "ai-inference"}:
        return "ai-inference"
    if workload == "laptop-quiet":
        return "quiet"
    return "balanced"


def _recommend_for_amd(workload: str | None) -> str:
    if workload in {"llama-inference", "ai-inference", "kernel-build"}:
        return "balanced"
    if workload in {"latency", "low-latency-trading"}:
        return "latency"
    if workload == "laptop-quiet":
        return "quiet"
    return "balanced"


def _recommend_for_arm(workload: str | None) -> str:
    if workload in {"llama-inference", "ai-inference"}:
        return "balanced"
    if workload in {"latency", "low-latency-trading"}:
        return "latency"
    if workload == "laptop-quiet":
        return "quiet"
    return "balanced"


def _lower_confidence(confidence: str) -> str:
    order = ["low", "medium", "high"]
    index = order.index(confidence)
    return order[max(0, index - 1)]


def _package_temp(discovery: dict[str, Any]) -> int | None:
    zones = discovery.get("thermal", {}).get("thermal_zones", [])
    if not zones:
        return None
    hottest = max(zones, key=lambda zone: zone.get("temp") or -1)
    return hottest.get("temp")


def _is_laptop_like(discovery: dict[str, Any]) -> bool:
    model = str(discovery.get("model_name") or "").lower()
    fan_present = any(
        any(name.startswith("fan") for name in device.get("sensors", {}))
        for device in discovery.get("hwmon", [])
    )
    return fan_present and any(token in model for token in ("core(tm)", "ultra", "mobile", "laptop"))


def _optimal_epp_for_profile(profile: str) -> str | None:
    mapping = {
        "performance": "performance",
        "balanced": "balance_performance",
        "latency": "performance",
        "quiet": "power",
        "ai-inference": "performance",
    }
    return mapping.get(profile)
