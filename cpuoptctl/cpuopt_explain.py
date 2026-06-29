from typing import Any

PROFILE_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "performance": {
        "intent": "Maximize CPU responsiveness and sustained boost.",
        "actions": [
            "Prefer EPP=performance when exposed by intel_pstate",
            "Prefer scaling_governor=performance when available",
            "Ensure turbo or boost is enabled where safe",
            "Do not disable thermal protection",
            "Do not write raw MSRs",
        ],
        "tradeoffs": [
            "Higher power draw",
            "Higher temperature",
            "Higher fan activity",
            "Lower battery life",
        ],
        "limits": [
            "No raw MSR writes",
            "No fan writes",
            "No thermal bypass",
            "No overclocking or voltage control",
        ],
        "knobs": [
            "energy_performance_preference",
            "scaling_governor",
            "energy_perf_bias",
            "intel_pstate/no_turbo",
            "cpufreq/boost",
        ],
    },
    "balanced": {
        "intent": "Balance responsiveness and efficiency for general workloads.",
        "actions": [
            "Prefer balance_performance or balance_power EPP values",
            "Prefer schedutil or powersave governors depending on availability",
            "Keep turbo enabled when safe",
        ],
        "tradeoffs": [
            "Moderate power usage",
            "Moderate temperature",
            "Less peak responsiveness than performance mode",
        ],
        "limits": ["No raw MSR writes", "No fan writes", "No thermal bypass"],
        "knobs": [
            "energy_performance_preference",
            "scaling_governor",
            "energy_perf_bias",
            "intel_pstate/no_turbo",
            "cpufreq/boost",
        ],
    },
    "latency": {
        "intent": "Reduce response latency for bursty or latency-sensitive workloads.",
        "actions": [
            "Prefer EPP=performance",
            "Prefer scaling_governor=performance when available",
            "Optionally disable deepest idle states only with --allow-idle-tuning",
            "Keep turbo enabled where safe",
        ],
        "tradeoffs": ["Higher power draw", "Higher temperature", "Less idle efficiency"],
        "limits": [
            "No raw MSR writes",
            "No fan writes",
            "No thermal bypass",
            "No blanket C-state disable by default",
        ],
        "knobs": [
            "energy_performance_preference",
            "scaling_governor",
            "energy_perf_bias",
            "intel_pstate/no_turbo",
            "cpuidle/state*/disable",
        ],
    },
    "quiet": {
        "intent": "Reduce CPU aggressiveness before considering any platform-specific fan action.",
        "actions": [
            "Prefer power-oriented EPP choices",
            "Prefer powersave or schedutil governors",
            "Do not change fan speeds in v0.2",
        ],
        "tradeoffs": [
            "Lower peak performance",
            "Potentially slower burst response",
            "Better acoustic behavior on supported platforms",
        ],
        "limits": [
            "No fan writes",
            "No raw MSR writes",
            "No turbo disable unless explicitly requested",
            "No thermal bypass",
        ],
        "knobs": ["energy_performance_preference", "scaling_governor", "energy_perf_bias"],
    },
    "ai-inference": {
        "intent": "Favor high sustained CPU throughput while preserving safe thermal behavior.",
        "actions": [
            "Prefer performance or balance_performance EPP choices",
            "Prefer performance or schedutil governors",
            "Keep turbo enabled where safe",
            "Report NUMA and uncore-related context without risky writes",
        ],
        "tradeoffs": [
            "Higher package power",
            "Higher sustained temperature",
            "Potentially higher fan activity",
        ],
        "limits": [
            "No raw MSR writes",
            "No uncore writes in v0.2",
            "No fan writes",
            "No thermal bypass",
        ],
        "knobs": [
            "energy_performance_preference",
            "scaling_governor",
            "energy_perf_bias",
            "intel_pstate/no_turbo",
            "cpufreq/boost",
        ],
    },
}


def explain_profile(profile_name: str) -> dict[str, Any]:
    return PROFILE_EXPLANATIONS[profile_name]


def format_profile_explanation(profile_name: str) -> str:
    details = explain_profile(profile_name)
    lines = [f"Profile: {profile_name}", "", "Intent:", f"  {details['intent']}", "", "Actions:"]
    lines.extend(f"  - {item}" for item in details["actions"])
    lines.append("")
    lines.append("Tradeoffs:")
    lines.extend(f"  - {item}" for item in details["tradeoffs"])
    lines.append("")
    lines.append("Safety limits:")
    lines.extend(f"  - {item}" for item in details["limits"])
    lines.append("")
    lines.append("Likely sysfs knobs:")
    lines.extend(f"  - {item}" for item in details["knobs"])
    return "\n".join(lines)
