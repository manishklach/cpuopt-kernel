# CPUOpt-Kernel Design

## Architecture

CPUOpt-Kernel is split into four user-space layers plus a future kernel-facing interface:

1. Discovery layer
   Reads `/proc`, `sysfs`, topology, cpuidle, thermal, cooling, and hwmon data without
   assuming any interface is present.
2. Profile layer
   Maps profile intent such as `performance` or `quiet` to safe existing kernel knobs.
3. Vendor backend layer
   Encodes vendor-specific policy choices such as Intel EPP preference ordering.
4. Telemetry layer
   Produces lightweight periodic views of policy state and temperature/frequency trends.
5. Future kernel module
   A placeholder in `kernel/` for a later `/sys/kernel/cpuopt/` policy surface.

## Discovery layer

Discovery is deliberately tolerant:

- missing files are recorded as absent, not errors
- all returned data is JSON-serializable
- `--sysfs-root` supports fake fixture trees for tests
- vendor-neutral metadata is gathered first, then vendor-specific enrichments

## Profile layer

Profiles propose writes instead of directly mutating state during decision-making. This
keeps dry-run, testing, and restore behavior simple:

- discover current state
- compute candidate writes
- snapshot original values
- apply writes when not in dry-run mode
- log every attempted change

## Vendor backends

Intel v0.2 supports:

- `intel_pstate` detection
- EPP selection using available preference files
- EPB selection when `energy_perf_bias` is exposed
- safe turbo enable through `no_turbo` or `cpufreq/boost`

AMD and ARM modules currently provide placeholder hooks and future notes, but discovery is
already structured so additional backends can plug into the same policy engine.

## Telemetry

The telemetry path samples:

- per-policy current frequency
- min/max sampled frequency
- governor and EPP
- package or hottest thermal zone
- turbo/boost state
- cooling device state where exposed

The monitor loop is intentionally light and keeps external dependencies optional.

## Future kernel module

The `kernel/` directory sketches a conservative policy module that could eventually expose:

- `/sys/kernel/cpuopt/profile`
- `/sys/kernel/cpuopt/status`
- `/sys/kernel/cpuopt/telemetry`
- `/sys/kernel/cpuopt/safe_mode`

That module should integrate with CPUFreq, thermal, and vendor backends, but v0.2 keeps all
risky logic out of kernel space.

## Future MSR guardrails

MSR support is future work only and must satisfy:

- documented register semantics
- CPU model allowlist
- read-only decode stage before any write stage
- safe fallback to existing kernel interfaces
- explicit user opt-in and comprehensive restore behavior
