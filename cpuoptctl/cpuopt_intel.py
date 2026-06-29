from __future__ import annotations

from collections.abc import Iterable

PROFILE_EPP_ORDER: dict[str, list[str]] = {
    "performance": ["performance"],
    "balanced": ["balance_performance", "balance_power", "default", "performance"],
    "quiet": ["power", "balance_power", "balance_performance"],
    "latency": ["performance"],
    "ai-inference": ["performance", "balance_performance"],
}

PROFILE_GOVERNOR_ORDER: dict[str, list[str]] = {
    "performance": ["performance", "schedutil", "powersave"],
    "balanced": ["schedutil", "powersave", "performance"],
    "quiet": ["powersave", "schedutil"],
    "latency": ["performance", "schedutil"],
    "ai-inference": ["performance", "schedutil"],
}


def choose_preference(available: Iterable[str], preferred: Iterable[str]) -> str | None:
    available_list = [item for item in available if item]
    for candidate in preferred:
        if candidate in available_list:
            return candidate
    return None


def epp_for_profile(profile_name: str, available: Iterable[str]) -> str | None:
    return choose_preference(available, PROFILE_EPP_ORDER.get(profile_name, []))


def governor_for_profile(profile_name: str, available: Iterable[str]) -> str | None:
    return choose_preference(available, PROFILE_GOVERNOR_ORDER.get(profile_name, []))


def epb_for_profile(profile_name: str) -> str | None:
    mapping = {
        "performance": "0",
        "balanced": "6",
        "quiet": "15",
        "latency": "0",
        "ai-inference": "0",
    }
    return mapping.get(profile_name)
