# CPUOpt-Kernel

[![tests](https://github.com/manishklach/cpuopt-kernel/actions/workflows/tests.yml/badge.svg)](https://github.com/manishklach/cpuopt-kernel/actions/workflows/tests.yml)
[![license](https://img.shields.io/badge/license-GPL--2.0--only-blue.svg)](https://github.com/manishklach/cpuopt-kernel/blob/main/LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![version](https://img.shields.io/badge/version-v0.1.0-informational.svg)](https://github.com/manishklach/cpuopt-kernel/blob/main/CHANGELOG.md)

CPUOpt-Kernel is not an overclocking tool. It is a safety-first CPU performance policy layer
that discovers platform capabilities and maps them into reversible workload profiles such as
`performance`, `balanced`, `latency`, `quiet`, and `ai-inference`. The project starts with a
sysfs-first Intel MVP and is designed for future AMD `amd-pstate` and ARM
SCMI/heterogeneous-topology backends.

CPUOpt-Kernel translates vendor CPU performance controls into safe Linux policy profiles. It
prefers existing kernel interfaces over raw register writes and treats thermal and fan
control as platform concerns, not as a shortcut for unsafe CPU tuning.

Version `v0.1` is intentionally conservative:

- Intel-first, user-space-first implementation
- No raw MSR writes
- No thermal protection bypass
- No voltage or overclock manipulation
- Reversible sysfs writes with snapshot/restore
- Dry-run support for every profile application

## Why this exists

Linux CPU performance policy is spread across multiple interfaces such as `cpufreq`,
`intel_pstate`, `amd-pstate`, EPP/EPB, cpuidle, thermal zones, cooling devices, and
platform-specific hwmon hooks. CPUOpt-Kernel unifies those surfaces into profile-driven,
workload-aware policy choices without pretending every platform exposes the same knobs.

Fan control is platform-specific and is not treated as a CPU register. Performance mode
optimizes for sustained boost and reduced throttling, not unsafe thermal bypass. Quiet mode
reduces CPU aggressiveness before considering fan changes.

## Intel MVP scope

The first release focuses on safe Intel profile application through sysfs:

- `discover` and `status` report CPUFreq, `intel_pstate`, EPP, EPB, turbo, cpuidle,
  thermal, cooling, hwmon, SMT, topology, and NUMA metadata when present
- `profile` maps high-level policies to existing sysfs knobs
- `monitor` provides lightweight live telemetry
- `restore` replays the last reversible snapshot

AMD and ARM support are scaffolded for future milestones but remain discovery-first.

## Repository layout

```text
cpuopt-kernel/
  cpuoptctl/
  docs/
  examples/
  kernel/
  scripts/
  tests/
```

## Commands

```bash
python3 cpuoptctl/cpuoptctl.py status
python3 cpuoptctl/cpuoptctl.py discover --json
sudo python3 cpuoptctl/cpuoptctl.py profile performance --dry-run
sudo python3 cpuoptctl/cpuoptctl.py profile balanced
sudo python3 cpuoptctl/cpuoptctl.py profile latency --allow-idle-tuning
sudo python3 cpuoptctl/cpuoptctl.py profile quiet
sudo python3 cpuoptctl/cpuoptctl.py profile ai-inference
sudo python3 cpuoptctl/cpuoptctl.py monitor --interval 2
sudo python3 cpuoptctl/cpuoptctl.py restore
python3 cpuoptctl/cpuoptctl.py export-json
```

For fixture-backed tests:

```bash
python3 cpuoptctl/cpuoptctl.py status --sysfs-root tests/fixtures/intel_hwp
python3 cpuoptctl/cpuoptctl.py profile performance --dry-run --sysfs-root tests/fixtures/intel_hwp
python3 -m unittest
```

## Safety model

- CPUOpt prefers existing kernel interfaces over raw register writes.
- Every write validates path existence, writability intent, and candidate value selection.
- Unknown sysfs paths are skipped, not guessed.
- Failed writes are logged and are non-fatal.
- Modified values are snapshotted to `last_state.json` before application.
- v0.1 never writes `/dev/cpu/*/msr`, firmware registers, BIOS settings, or BMC controls.
- Fan writes are intentionally unimplemented in v0.1 even if fan inspection is enabled.

See [docs/SAFETY.md](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\docs\SAFETY.md) for the full model.

## Example status output

```text
## CPUOpt Status

Vendor: GenuineIntel
Model: Intel(R) Core(TM) i7-1280P
Kernel: Linux 6.8.0-test
Scaling driver: intel_pstate
HWP/EPP exposed: yes
Turbo control: intel_pstate/no_turbo
Policies:
  policy0 CPUs=0-7 governor=powersave min=400000 max=4700000 epp=balance_performance
Thermals:
  x86_pkg_temp temp=51000
Warnings:
  Fan control is platform-specific; not directly controlled unless safely exposed.
```

## Roadmap highlights

- AMD `amd-pstate` profile support
- ARM SCMI and heterogeneous topology handling
- Optional kernel module under `/sys/kernel/cpuopt/`
- Read-only MSR decoding with model-aware guardrails
- Model-specific write allowlists only after documentation and fallback validation

## Project metadata

- License: `GPL-2.0-only`
- Current target release: `v0.1.0`
- CI: GitHub Actions runs Python compile checks and `unittest`
