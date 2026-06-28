from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .cpuopt_discovery import discover
    from .cpuopt_profiles import ProposedWrite, propose_profile
    from .cpuopt_telemetry import collect_sample, monitor
    from .cpuopt_utils import json_ready, now_utc, read_text, save_json, write_text
except ImportError:
    from cpuopt_discovery import discover
    from cpuopt_profiles import ProposedWrite, propose_profile
    from cpuopt_telemetry import collect_sample, monitor
    from cpuopt_utils import json_ready, now_utc, read_text, save_json, write_text


def _state_path(state_dir: str) -> Path:
    return Path(state_dir) / "last_state.json"


def _write_log_path(state_dir: str) -> Path:
    return Path(state_dir) / "write_log.jsonl"


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


def _log_write(state_dir: str, entry: dict[str, Any]) -> None:
    path = _write_log_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _snapshot_existing(writes: list[ProposedWrite], state_dir: str) -> dict[str, Any]:
    snapshot_entries = []
    for item in writes:
        current = read_text(Path(item.path))
        snapshot_entries.append({"path": item.path, "value": current})
    snapshot = {"timestamp": now_utc(), "entries": snapshot_entries}
    save_json(_state_path(state_dir), snapshot)
    return snapshot


def _validate_write(item: ProposedWrite, current_value: str | None) -> str | None:
    path = Path(item.path)
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "not-a-file"
    if current_value is None:
        return "unreadable-current-value"
    if item.valid_values is not None and item.value not in item.valid_values:
        return "invalid-value"
    return None


def _apply_writes(writes: list[ProposedWrite], state_dir: str, dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in writes:
        path = Path(item.path)
        current_value = read_text(path)
        result = {
            "path": item.path,
            "current": current_value,
            "value": item.value,
            "reason": item.reason,
            "applied": False,
        }
        validation_error = _validate_write(item, current_value)
        if validation_error is not None:
            result["error"] = validation_error
        elif dry_run:
            result["dry_run"] = True
        else:
            try:
                write_text(path, item.value)
                result["applied"] = True
            except OSError as exc:
                result["error"] = str(exc)
        if not dry_run:
            _log_write(state_dir, result)
        results.append(result)
    return results


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
    print("Proposed writes:")
    for item in writes:
        print(f"- {item.path}: {item.current!r} -> {item.value!r} ({item.reason})")
    if not args.dry_run:
        _snapshot_existing(writes, args.state_dir)
    results = _apply_writes(writes, args.state_dir, args.dry_run)
    if args.dry_run:
        print("Dry-run only; no files were modified.")
    else:
        applied = sum(1 for result in results if result.get("applied"))
        print(f"Applied {applied}/{len(results)} writes.")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    _resolve_common_args(args)
    state_path = _state_path(args.state_dir)
    if not state_path.exists():
        print("No restore snapshot found.")
        return 1
    snapshot = json.loads(state_path.read_text(encoding="utf-8"))
    restored = 0
    for entry in snapshot.get("entries", []):
        path = Path(entry["path"])
        if not path.exists():
            continue
        try:
            if entry["value"] is not None:
                write_text(path, str(entry["value"]))
            restored += 1
            _log_write(args.state_dir, {"path": str(path), "restored": True, "value": entry["value"]})
        except OSError as exc:
            _log_write(args.state_dir, {"path": str(path), "restored": False, "error": str(exc)})
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "experimental_fan_write", False) and not getattr(args, "i_understand_fan_risk", False):
        parser.error("--experimental-fan-write requires --i-understand-fan-risk")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
