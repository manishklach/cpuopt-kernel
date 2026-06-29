from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from .cpuopt_apply import apply_writes, restore_from_snapshot, snapshot_existing
    from .cpuopt_discovery import discover
    from .cpuopt_profiles import propose_profile
    from .cpuopt_telemetry import collect_sample
except ImportError:
    from cpuopt_apply import apply_writes, restore_from_snapshot, snapshot_existing
    from cpuopt_discovery import discover
    from cpuopt_profiles import propose_profile
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

    tmp_dir = Path(tempfile.mkdtemp(prefix="cpuopt-compare-"))
    try:
        data = discover(sysfs_root=sysfs_root)
        proposal_a = propose_profile(data, profile_a, sysfs_root=sysfs_root)
        proposal_b = propose_profile(data, profile_b, sysfs_root=sysfs_root)

        all_writes = proposal_a["writes"] + proposal_b["writes"]
        if not all_writes:
            return {
                "ok": True,
                "profile_a": profile_a,
                "profile_b": profile_b,
                "benchmark": benchmark,
                "duration": duration,
                "note": "no profile changes to apply; running benchmark on current state",
                "samples": {},
                "benchmark_results": {},
            }

        pre_snapshot = snapshot_existing(all_writes, str(tmp_dir))

        apply_writes(proposal_a["writes"], str(tmp_dir), dry_run=False)
        time.sleep(1)
        sample_a = collect_sample(sysfs_root=sysfs_root)
        result_a = _run_benchmark(benchmark, duration)

        restore_from_snapshot(pre_snapshot, str(tmp_dir))
        apply_writes(proposal_b["writes"], str(tmp_dir), dry_run=False)
        time.sleep(1)
        sample_b = collect_sample(sysfs_root=sysfs_root)
        result_b = _run_benchmark(benchmark, duration)

        restore_from_snapshot(pre_snapshot, str(tmp_dir))

        return {
            "ok": True,
            "profile_a": profile_a,
            "profile_b": profile_b,
            "benchmark": benchmark,
            "duration": duration,
            "samples": {profile_a: sample_a, profile_b: sample_b},
            "benchmark_results": {profile_a: result_a, profile_b: result_b},
        }
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


def format_compare_report(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"Profile comparison unavailable: {result.get('reason')}"

    if not result.get("samples"):
        return "No profile changes to compare (system already in requested state)."

    profile_a = result["profile_a"]
    profile_b = result["profile_b"]
    sample_a = result["samples"].get(profile_a, {})
    sample_b = result["samples"].get(profile_b, {})

    lines = [
        "Profile comparison",
        "------------------",
        f"Workload: {result['benchmark']}",
        f"Duration: {result['duration']}s",
        "",
        f"{'Metric':<24}{profile_a:<14}{profile_b:<14}",
        (
            f"{'Avg frequency':<24}"
            f"{_fmt_freq(sample_a.get('avg_current_freq')):<14}"
            f"{_fmt_freq(sample_b.get('avg_current_freq')):<14}"
        ),
        (
            f"{'Max temperature':<24}"
            f"{_fmt_temp(sample_a.get('package_temp')):<14}"
            f"{_fmt_temp(sample_b.get('package_temp')):<14}"
        ),
        f"{'Thermal throttling':<24}{'unknown':<14}{'unknown':<14}",
    ]

    result_a = result.get("benchmark_results", {}).get(profile_a, {})
    result_b = result.get("benchmark_results", {}).get(profile_b, {})
    ra_rc = result_a.get("returncode")
    rb_rc = result_b.get("returncode")
    lines.append(f"{'Benchmark exit code':<24}{str(ra_rc):<14}{str(rb_rc):<14}")
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
