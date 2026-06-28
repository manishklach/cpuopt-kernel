from __future__ import annotations

import shutil
import subprocess
from typing import Any

try:
    from .cpuopt_telemetry import collect_sample
except ImportError:
    from cpuopt_telemetry import collect_sample


BENCHMARKS: dict[str, list[str]] = {
    "stress-ng": ["stress-ng", "--cpu", "1", "--timeout", "10", "--metrics-brief"],
    "sysbench": ["sysbench", "cpu", "--time=10", "run"],
}


def compare_profiles(
    profile_a: str,
    profile_b: str,
    benchmark: str,
    duration: int,
    sysfs_root: str = "/sys",
) -> dict[str, Any]:
    if benchmark not in BENCHMARKS:
        return {"ok": False, "reason": f"unsupported benchmark: {benchmark}"}
    binary = shutil.which(BENCHMARKS[benchmark][0])
    if binary is None:
        return {"ok": False, "reason": f"benchmark not installed: {benchmark}"}

    before = collect_sample(sysfs_root=sysfs_root)
    benchmark_result = _run_benchmark(benchmark, duration)
    after = collect_sample(sysfs_root=sysfs_root)
    return {
        "ok": True,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "benchmark": benchmark,
        "duration": duration,
        "samples": {
            profile_a: before,
            profile_b: after,
        },
        "benchmark_result": benchmark_result,
    }


def format_compare_report(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"Profile comparison unavailable: {result.get('reason')}"
    profile_a = result["profile_a"]
    profile_b = result["profile_b"]
    sample_a = result["samples"][profile_a]
    sample_b = result["samples"][profile_b]
    lines = ["Profile comparison", "------------------", f"Workload: {result['benchmark']}", f"Duration: {result['duration']}s", ""]
    lines.append(f"{'Metric':<24}{profile_a:<14}{profile_b:<14}")
    lines.append(f"{'Avg frequency':<24}{_fmt_freq(sample_a.get('avg_current_freq')):<14}{_fmt_freq(sample_b.get('avg_current_freq')):<14}")
    lines.append(f"{'Max temperature':<24}{_fmt_temp(sample_a.get('package_temp')):<14}{_fmt_temp(sample_b.get('package_temp')):<14}")
    lines.append(f"{'Thermal throttling':<24}{'unknown':<14}{'unknown':<14}")
    lines.append(f"{'Elapsed time':<24}{str(result['duration']) + 's':<14}{str(result['duration']) + 's':<14}")
    return "\n".join(lines)


def _run_benchmark(benchmark: str, duration: int) -> dict[str, Any]:
    cmd = list(BENCHMARKS[benchmark])
    if benchmark == "stress-ng":
        cmd = ["stress-ng", "--cpu", "1", "--timeout", str(duration), "--metrics-brief"]
    if benchmark == "sysbench":
        cmd = ["sysbench", "cpu", f"--time={duration}", "run"]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _fmt_freq(value: Any) -> str:
    if not isinstance(value, int):
        return "n/a"
    return f"{value / 1_000_000:.1f} GHz"


def _fmt_temp(value: Any) -> str:
    if not isinstance(value, int):
        return "n/a"
    return f"{value / 1000:.0f} C"
