from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .cpuopt_apply import apply_writes, restore_from_snapshot, snapshot_existing, state_path
    from .cpuopt_compare import compare_profiles, format_compare_report
    from .cpuopt_discovery import discover
    from .cpuopt_doctor import build_doctor_report, format_doctor_report
    from .cpuopt_explain import format_profile_explanation
    from .cpuopt_msr import decode_intel_msrs, format_msr_report
    from .cpuopt_profiles import ProposedWrite, propose_profile
    from .cpuopt_recommend import format_recommendation, recommend_profile
    from .cpuopt_telemetry import collect_sample, monitor
    from .cpuopt_utils import json_ready, now_utc, read_text, save_json
except ImportError:
    from cpuopt_apply import apply_writes, restore_from_snapshot, snapshot_existing, state_path
    from cpuopt_compare import compare_profiles, format_compare_report
    from cpuopt_discovery import discover
    from cpuopt_doctor import build_doctor_report, format_doctor_report
    from cpuopt_explain import format_profile_explanation
    from cpuopt_msr import decode_intel_msrs, format_msr_report
    from cpuopt_profiles import ProposedWrite, propose_profile
    from cpuopt_recommend import format_recommendation, recommend_profile
    from cpuopt_telemetry import collect_sample, monitor
    from cpuopt_utils import json_ready, now_utc, read_text, save_json


def _resolve_common_args(args: argparse.Namespace) -> None:
    if getattr(args, "sysfs_root_local", None):
        args.sysfs_root = args.sysfs_root_local
    if getattr(args, "state_dir_local", None):
        args.state_dir = args.state_dir_local


def _add_common_local_args(parser: argparse.ArgumentParser, include_state_dir: bool = False) -> None:
    parser.add_argument("--sysfs-root", dest="sysfs_root_local")
    if include_state_dir:
        parser.add_argument("--state-dir", dest="state_dir_local")


def _format_status(data: dict[str, Any]) -> str:
    lines = ["## CPUOpt Status", ""]
    lines.append(f"Vendor: {data.get('vendor')}")
    lines.append(f"Model: {data.get('model_name')}")
    lines.append(f"Kernel: {data.get('kernel')}")
    scaling_driver = next((p.get("scaling_driver") for p in data.get("policies", []) if p.get("scaling_driver")), "unknown")
    lines.append(f"Scaling driver: {scaling_driver}")
    hwp = any(policy.get("energy_performance_preference") for policy in data.get("policies", []))
    lines.append(f"HWP/EPP exposed: {'yes' if hwp else 'no'}")
    turbo_control = "none"
    if data.get("intel_pstate", {}).get("exists"):
        turbo_control = "intel_pstate/no_turbo"
    elif data.get("cpufreq_boost") is not None:
        turbo_control = "cpufreq/boost"
    lines.append(f"Turbo control: {turbo_control}")
    lines.append("Policies:")
    for policy in data.get("policies", []):
        lines.append(
            "  "
            f"{policy['name']} CPUs={policy.get('related_cpus')} governor={policy.get('scaling_governor')} "
            f"min={policy.get('scaling_min_freq')} max={policy.get('scaling_max_freq')} "
            f"epp={policy.get('energy_performance_preference')}"
        )
    lines.append("Thermals:")
    for zone in data.get("thermal", {}).get("thermal_zones", []):
        lines.append(f"  {zone.get('type') or zone.get('name')} temp={zone.get('temp')}")
    lines.append("Warnings:")
    for warning in data.get("warnings", []):
        lines.append(f"  {warning}")
    return "\n".join(lines)


def _format_diff(writes: list[ProposedWrite]) -> str:
    lines = ["Planned CPUOpt changes", "----------------------"]
    for item in writes:
        lines.append(item.path)
        lines.append(f"  current: {item.current}")
        lines.append(f"  new:     {item.value}")
        lines.append("")
    return "\n".join(lines).rstrip()


def cmd_status(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    if args.json:
        print(json.dumps(json_ready(data), indent=2))
    else:
        print(_format_status(data))
    return 0


def cmd_export_json(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    print(json.dumps(json_ready(data), indent=2))
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    proposal = propose_profile(
        data,
        args.profile_name,
        sysfs_root=args.sysfs_root,
        allow_idle_tuning=args.allow_idle_tuning,
        allow_fan_control=args.allow_fan_control,
        experimental_fan_write=args.experimental_fan_write,
        allow_turbo_disable=args.allow_turbo_disable,
    )
    writes = proposal["writes"]
    if args.json:
        print(json.dumps(json_ready(proposal), indent=2))
        return 0

    print(f"## CPUOpt Profile: {args.profile_name}")
    for warning in proposal["warnings"]:
        print(f"Warning: {warning}")
    for recommendation in proposal["recommendations"]:
        print(f"Note: {recommendation}")
    if not writes:
        print("No safe changes proposed.")
        return 0
    if getattr(args, "diff", False):
        print(_format_diff(writes))
    else:
        print("Proposed writes:")
        for item in writes:
            print(f"- {item.path}: {item.current!r} -> {item.value!r} ({item.reason})")
    if not args.dry_run and writes:
        snapshot_existing(writes, args.state_dir)
    results = apply_writes(writes, args.state_dir, args.dry_run)
    if args.dry_run:
        print("Dry-run only; no files were modified.")
    else:
        applied = sum(1 for result in results if result.get("applied"))
        print(f"Applied {applied}/{len(results)} writes.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    findings = build_doctor_report(data, state_dir=args.state_dir, dev_root=args.dev_root)
    print(json.dumps(findings, indent=2) if args.json else format_doctor_report(findings))
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    print(format_profile_explanation(args.profile_name))
    return 0


def cmd_intel_hwp(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    policies = data.get("policies", [])
    epp_values = []
    current_epp = []
    for policy in policies:
        epp_values.extend(policy.get("energy_performance_available_preferences", []))
        if policy.get("energy_performance_preference") is not None:
            current_epp.append(f"{policy.get('name')}={policy.get('energy_performance_preference')}")
    msr_report = decode_intel_msrs(dev_root=args.dev_root, safe=True if args.safe_msr else False)
    lines = [
        "Intel HWP Report",
        "----------------",
        f"HWP exposed via sysfs: {'yes' if any(current_epp) else 'no'}",
    ]
    lines.append(f"EPP available: {' '.join(dict.fromkeys(epp_values)) if epp_values else 'none'}")
    lines.append(f"Current EPP: {', '.join(current_epp) if current_epp else 'none'}")
    lines.append(f"HWP MSR read available: {'yes' if msr_report.get('available') else 'no'}")
    turbo_available = (
        data.get("intel_pstate", {}).get("exists")
        or data.get("cpufreq_boost") is not None
    )
    lines.append(
        f"Turbo control: {'available' if turbo_available else 'unavailable'}"
    )
    lines.append(f"intel_pstate status: {data.get('intel_pstate', {}).get('status')}")
    if msr_report.get("available"):
        caps = msr_report.get("registers", {}).get("IA32_HWP_CAPABILITIES", {}).get("fields", {})
        if caps:
            lines.append("HWP capabilities:")
            lines.append(f"  lowest performance: {caps.get('lowest_performance')}")
            lines.append(f"  highest performance: {caps.get('highest_performance')}")
            lines.append(f"  guaranteed performance: {caps.get('guaranteed_performance')}")
            lines.append(f"  most efficient performance: {caps.get('most_efficient_performance')}")
    print("\n".join(lines))
    return 0


def cmd_msr_read(args: argparse.Namespace) -> int:
    if args.intel is not True:
        print("Only --intel read-only telemetry is implemented in v0.2.")
        return 1
    report = decode_intel_msrs(dev_root=args.dev_root, safe=args.safe)
    print(json.dumps(report, indent=2) if args.json else format_msr_report(report))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    result = compare_profiles(
        profile_a=args.profile_a,
        profile_b=args.profile_b,
        benchmark=args.benchmark,
        duration=args.duration,
        sysfs_root=args.sysfs_root,
    )
    print(json.dumps(result, indent=2) if args.json else format_compare_report(result))
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    data = discover(sysfs_root=args.sysfs_root)
    report = recommend_profile(data, workload=args.workload, workload_dir=args.workload_dir)
    print(json.dumps(report, indent=2) if args.json else format_recommendation(report))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    sp = state_path(args.state_dir)
    if not sp.exists():
        print("No restore snapshot found.")
        return 1
    snapshot = json.loads(sp.read_text(encoding="utf-8"))
    entries = snapshot.get("entries", [])
    if not entries:
        print("No entries in restore snapshot.")
        return 0
    pre_snapshot = {"timestamp": now_utc(), "entries": []}
    for entry in entries:
        current = read_text(Path(entry["path"]))
        pre_snapshot["entries"].append({"path": entry["path"], "value": current})
    try:
        save_json(state_path(args.state_dir).with_suffix(".pre-restore.json"), pre_snapshot)
    except OSError as exc:
        print(f"Warning: could not save pre-restore snapshot ({exc})")
    restored = restore_from_snapshot(snapshot, args.state_dir)
    print(f"Restored {restored} paths.")
    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    if args.once:
        sample = collect_sample(sysfs_root=args.sysfs_root)
        print(json.dumps(sample, indent=2) if args.json else _format_sample(sample))
        return 0
    for sample in monitor(sysfs_root=args.sysfs_root, interval=args.interval):
        print(json.dumps(sample, indent=2) if args.json else _format_sample(sample))
    return 0


def _format_sample(sample: dict[str, Any]) -> str:
    lines = [
        f"timestamp={sample.get('timestamp')}",
        f"avg_current_freq={sample.get('avg_current_freq')}",
        f"min_current_freq={sample.get('min_current_freq')}",
        f"max_current_freq={sample.get('max_current_freq')}",
        f"package_temp={sample.get('package_temp')}",
        f"hottest_zone={sample.get('hottest_zone')}",
        f"turbo_status={sample.get('turbo_status')}",
        f"boost_status={sample.get('boost_status')}",
    ]
    for policy in sample.get("policies", []):
        lines.append(
            f"policy={policy.get('policy')} governor={policy.get('governor')} "
            f"epp={policy.get('epp')} current_freq={policy.get('current_freq')}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPUOpt-Kernel safe CPU policy controller")
    parser.add_argument("--sysfs-root", default="/sys")
    parser.add_argument("--state-dir", default="/var/lib/cpuopt")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("status", "discover", "export-json"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--json", action="store_true")
        _add_common_local_args(sub, include_state_dir=(name == "export-json"))
        sub.set_defaults(func=cmd_export_json if name in {"discover", "export-json"} else cmd_status)

    profile = subparsers.add_parser("profile")
    _add_common_local_args(profile, include_state_dir=True)
    profile.add_argument("profile_name", choices=["performance", "balanced", "latency", "quiet", "ai-inference"])
    profile.add_argument("--dry-run", action="store_true")
    profile.add_argument("--diff", action="store_true")
    profile.add_argument("--json", action="store_true")
    profile.add_argument("--allow-idle-tuning", action="store_true")
    profile.add_argument("--allow-fan-control", action="store_true")
    profile.add_argument("--experimental-fan-write", action="store_true")
    profile.add_argument("--i-understand-fan-risk", action="store_true")
    profile.add_argument("--allow-turbo-disable", action="store_true")
    profile.set_defaults(func=cmd_profile)

    mon = subparsers.add_parser("monitor")
    _add_common_local_args(mon)
    mon.add_argument("--interval", type=int, default=1)
    mon.add_argument("--json", action="store_true")
    mon.add_argument("--once", action="store_true")
    mon.set_defaults(func=cmd_monitor)

    restore = subparsers.add_parser("restore")
    _add_common_local_args(restore, include_state_dir=True)
    restore.set_defaults(func=cmd_restore)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--dev-root", default="/dev")
    _add_common_local_args(doctor, include_state_dir=True)
    doctor.set_defaults(func=cmd_doctor)

    explain = subparsers.add_parser("explain")
    explain.add_argument("profile_name", choices=["performance", "balanced", "latency", "quiet", "ai-inference"])
    explain.set_defaults(func=cmd_explain)

    msr = subparsers.add_parser("msr-read")
    msr.add_argument("--intel", action="store_true")
    msr.add_argument("--safe", action="store_true")
    msr.add_argument("--json", action="store_true")
    msr.add_argument("--dev-root", default="/dev")
    msr.set_defaults(func=cmd_msr_read)

    hwp = subparsers.add_parser("intel-hwp")
    hwp.add_argument("--safe-msr", action="store_true")
    hwp.add_argument("--dev-root", default="/dev")
    _add_common_local_args(hwp)
    hwp.set_defaults(func=cmd_intel_hwp)

    compare = subparsers.add_parser("compare")
    compare.add_argument("profile_a", choices=["performance", "balanced", "latency", "quiet", "ai-inference"])
    compare.add_argument("profile_b", choices=["performance", "balanced", "latency", "quiet", "ai-inference"])
    compare.add_argument("--benchmark", default="stress-ng")
    compare.add_argument("--duration", type=int, default=30)
    compare.add_argument("--json", action="store_true")
    _add_common_local_args(compare)
    compare.set_defaults(func=cmd_compare)

    recommend = subparsers.add_parser("recommend")
    recommend.add_argument("--workload")
    recommend.add_argument("--workload-dir")
    recommend.add_argument("--json", action="store_true")
    _add_common_local_args(recommend)
    recommend.set_defaults(func=cmd_recommend)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "experimental_fan_write", False) and not getattr(args, "i_understand_fan_risk", False):
        parser.error("--experimental-fan-write requires --i-understand-fan-risk")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
