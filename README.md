# CPUOpt-Kernel

> Safe, workload-aware CPU performance profiles for Linux — no overclocking, no register
> hacks, no guessing.

[![tests](https://github.com/manishklach/cpuopt-kernel/actions/workflows/tests.yml/badge.svg)](https://github.com/manishklach/cpuopt-kernel/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-GPL--2.0--only-blue.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-v0.2.0-informational.svg)](https://github.com/manishklach/cpuopt-kernel/blob/main/CHANGELOG.md)

---

<!-- INSERT: animated terminal GIF here — record with vhs or asciinema -->
<!-- Suggested flow: doctor → recommend --workload llama-inference → profile ai-inference --dry-run --diff → monitor → restore -->

---

Linux CPU performance policy is **shattered across six kernel interfaces**:

```text
cpufreq  ·  intel_pstate  ·  amd-pstate  ·  EPP/EPB  ·  cpuidle  ·  thermal zones
```

Every tool speaks one dialect. CPUOpt-Kernel speaks all of them — and exposes a single
profile-driven API that is **safe by default**, **reversible on demand**, and
**workload-aware**.

---

## Quick Start

```bash
# Install (requires Python 3.10+)
pipx install .
# or: pip install .

# No root needed to inspect
cpuoptctl doctor
cpuoptctl recommend
cpuoptctl explain performance

# Root needed to apply
sudo cpuoptctl profile balanced
sudo cpuoptctl profile ai-inference --dry-run --diff
sudo cpuoptctl restore
```

That is the intended flow: inspect first, preview second, apply only when comfortable.

---

## Why Not Just Use X?

| | CPUOpt-Kernel | cpupower | tuned | TLP | powertop |
|---|---|---|---|---|---|
| Workload-aware profiles | yes | no | partial | no | no |
| Dry-run + diff preview | yes | no | no | no | no |
| Snapshot/restore | yes | no | no | no | no |
| No raw MSR writes | yes | partial | partial | yes | partial |
| Unified Intel/AMD/ARM roadmap | yes | partial | partial | partial | partial |
| Advisory mode with no writes | yes | no | no | no | partial |
| Fixture-backed tests | yes | no | no | no | no |
| JSON output | yes | limited | no | no | no |

---

## How It Works

```text
                    ┌─────────────────────────────────────────┐
                    │           CPUOpt-Kernel                  │
                    │                                          │
  sysfs ──────────▶│  Discover ──▶ CapabilityMap ──▶ Profile  │
  /sys/devices/    │                                   │       │
  /sys/class/      │             ProposedWrite ◀───────┘       │
  /dev/cpu/*/msr   │             (read-only check)             │
  (read-only)      │                    │                      │
                   │            Validate ──▶ Snapshot          │
                   │                    │                      │
                   │             Apply (or Dry-run)            │
                   └─────────────────────────────────────────┘
                            │                    │
                       last_state.json     zero writes
                       (before state)      (--dry-run)
```

Every sysfs path is validated for existence and writability before a single byte changes.
Unknown paths are skipped, not guessed. The snapshot taken before `apply` is what `restore`
replays.

---

## Commands

### Discovery & inspection

```bash
cpuoptctl status
cpuoptctl discover --json
cpuoptctl doctor
cpuoptctl intel-hwp
cpuoptctl msr-read --intel --safe
```

### Advisory

```bash
cpuoptctl recommend
cpuoptctl recommend --workload kernel-build
cpuoptctl recommend --workload llama-inference
cpuoptctl recommend --workload low-latency
cpuoptctl explain performance
```

### Apply & restore

```bash
sudo cpuoptctl profile performance
sudo cpuoptctl profile balanced
sudo cpuoptctl profile latency --allow-idle-tuning
sudo cpuoptctl profile quiet
sudo cpuoptctl profile ai-inference
sudo cpuoptctl profile performance --dry-run --diff
sudo cpuoptctl restore
```

### Observe

```bash
sudo cpuoptctl monitor --interval 2
cpuoptctl compare balanced performance --benchmark stress-ng --duration 30
cpuoptctl export-json
```

---

## Example Output

```text
## CPUOpt Status

Vendor:         GenuineIntel
Model:          Intel(R) Core(TM) i7-1280P
Kernel:         Linux 6.8.0
Scaling driver: intel_pstate
HWP/EPP:        exposed
Turbo:          intel_pstate/no_turbo = 0 (turbo enabled)

Policies:
  policy0  CPUs=0-7   governor=powersave  epp=balance_performance

Thermals:
  x86_pkg_temp  51 C
```

---

## Safety Model

CPUOpt-Kernel is **not** an overclocking tool. Every design decision biases toward
reversibility and kernel-interface compliance:

- Prefers existing kernel interfaces over raw register writes
- Every sysfs write validates path existence and candidate value before touching the file
- `--dry-run` performs **zero filesystem modifications**
- Unknown sysfs paths are skipped, not guessed
- Failed writes are logged and non-fatal
- Modified values are snapshotted to `last_state.json` before any `apply` run
- `msr-read` is read-only telemetry only
- Fan writes are intentionally unimplemented in v0.x
- No thermal protection bypass, no voltage manipulation, no BIOS or BMC writes

See [docs/SAFETY.md](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\docs\SAFETY.md) for the full model.

---

## Architecture

See [docs/ARCHITECTURE.md](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\docs\ARCHITECTURE.md) for the layered pipeline design, the
`--sysfs-root` abstraction, and the planned backend/plugin direction.

---

## Demo

```bash
cpuoptctl doctor
cpuoptctl recommend --workload llama-inference
cpuoptctl profile performance --dry-run --diff
cpuoptctl monitor
```

Demo assets:

- [assets/cpuopt-status-demo.txt](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\assets\cpuopt-status-demo.txt)
- [assets/cpuopt-doctor-demo.txt](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\assets\cpuopt-doctor-demo.txt)
- [assets/cpuopt-dry-run-demo.txt](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\assets\cpuopt-dry-run-demo.txt)
- [assets/cpuopt-monitor-demo.txt](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\assets\cpuopt-monitor-demo.txt)
- [assets/cpuopt-recommend-demo.txt](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\assets\cpuopt-recommend-demo.txt)

---

## Testing Without Root

All discovery and profile-decision paths can be exercised against fake sysfs fixtures:

```bash
python cpuoptctl/cpuoptctl.py status --sysfs-root tests/fixtures/intel_hwp
python cpuoptctl/cpuoptctl.py profile performance --dry-run --sysfs-root tests/fixtures/intel_hwp
python -m unittest
```

If you install the optional test extras from `pyproject.toml`, you can also run:

```bash
pytest
```

---

## Repository Layout

```text
cpuopt-kernel/
├── cpuoptctl/
├── docs/
├── examples/
├── kernel/
├── scripts/
├── tests/
├── assets/
├── pyproject.toml
└── CHANGELOG.md
```

---

## Roadmap

| Milestone | Target |
|---|---|
| v0.1.0 | Intel MVP foundation |
| v0.2.0 | Doctor, recommend, explain, read-only MSR telemetry |
| v0.3.0 | AMD `amd-pstate` backend depth |
| v0.4.0 | ARM SCMI and heterogeneous-topology handling |
| v1.0.0 | Multi-backend plugin protocol and optional kernel module |

---

## Contributing

CPUOpt-Kernel is a safety-first project. See [CONTRIBUTING.md](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\CONTRIBUTING.md) for the
development flow, required checks, and expectations for backend/profile changes.

---

## License

GPL-2.0-only — see [LICENSE](C:\Users\ManishKL\Documents\Playground\cpuopt-kernel\LICENSE).
