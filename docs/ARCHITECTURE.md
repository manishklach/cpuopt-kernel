# CPUOpt-Kernel Architecture

This document describes the internal design of CPUOpt-Kernel, the layered pipeline, key
abstractions, and the principles that govern how new backends should be added.

---

## Design goals

1. Never surprise the user. Every write is previewed, logged, and reversible.
2. Degrade gracefully. A missing sysfs path is a skip, not a crash.
3. No platform assumptions. The capability map is built from what the running kernel
   actually exposes.
4. Testable without root. The `--sysfs-root` abstraction lets sysfs-touching code paths run
   against fixture trees in CI with zero privileges.

---

## Pipeline

```text
┌────────────────────────────────────────────────────────────────────┐
│                         cpuoptctl CLI                              │
│  (argparse layer — routes to command handlers)                     │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Platform Discovery                            │
│                                                                    │
│  Reads /sys/devices/system/cpu/cpufreq/policy*/                    │
│       /sys/devices/system/cpu/intel_pstate/                        │
│       /sys/class/thermal/thermal_zone*/                            │
│       /sys/class/hwmon/hwmon*/                                     │
│       /sys/devices/system/cpu/cpu*/cpuidle/state*/                 │
│       /sys/devices/system/cpu/smt/                                 │
│                                                                    │
│  Produces a capability map describing the running platform         │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Profile Engine                               │
│                                                                    │
│  Maps profile name → list[ProposedWrite]                           │
│                                                                    │
│  ProposedWrite:                                                    │
│    path: str           (sysfs path)                                │
│    value: str          (value to write)                            │
│    valid_values: set   (allowlist)                                 │
│    reason: str         (human-readable explanation)                │
│    reversible: bool    (always true in v0.x)                       │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                        Validation                                  │
│                                                                    │
│  For each ProposedWrite:                                           │
│    1. Does the path exist?                                         │
│    2. Is the value in valid_values?                                │
│    3. Is the path writable?                                        │
└────────────────────────┬───────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         --dry-run              apply mode
              │                     │
              ▼                     ▼
     Print proposed          Read current value
     writes, exit            → last_state.json
                                    │
                                    ▼
                             Write new value
                             Log result
```

---

## The `--sysfs-root` abstraction

Every path read or write is prefixed with a configurable root. Passing
`--sysfs-root tests/fixtures/intel_hwp` redirects sysfs access to a static fixture tree,
making discovery and profile code paths testable without root and without real hardware.

---

## Adding a new backend

Recommended direction for AMD and ARM backend growth:

1. Add a backend module that probes whether its platform interface is active.
2. Add fixture trees under `tests/fixtures/<platform>/`.
3. Add unit tests for discovery, profile mappings, and at least one negative case.
4. Keep the core flow unchanged: discover → propose → validate → apply/restore.

The current codebase is still partially monolithic, but the design target is a cleanly
layered core with backend-specific policy logic isolated from the CLI surface.

---

## Snapshot / restore

Before any apply run, the current value of every path that will be written is saved to
`last_state.json`. `restore` replays those values. CPUOpt-Kernel never guesses a restore
path and never performs hidden out-of-band rollback.

---

## Module responsibilities

| Module | Responsibility |
|---|---|
| `cpuoptctl.py` | CLI, subcommand dispatch, output formatting |
| `cpuopt_discovery.py` | sysfs traversal and capability discovery |
| `cpuopt_profiles.py` | profile-to-write mapping |
| `cpuopt_apply.py` | apply-time validation, logging, snapshot, restore |
| `cpuopt_doctor.py` | heuristic checks and warning generation |
| `cpuopt_recommend.py` | workload hint to profile recommendation |
| `cpuopt_telemetry.py` | monitor sampling |
| `cpuopt_msr.py` | read-only MSR telemetry decoder |

---

## Non-goals in v0.x

- No raw MSR writes
- No fan-control writes
- No thermal protection bypass
- No voltage or frequency overclocking
- No BIOS, BMC, or firmware writes
- No automatic dependency installation

These are part of the design philosophy, not temporary omissions.
