# CPUOpt-Kernel Safety Model

CPUOpt-Kernel is designed as a serious systems policy tool, not an overclocking utility.

## Core rules

- No raw MSR writes in v0.1
- No thermal protection bypass
- No unsafe fan forcing
- No overclocking
- No voltage manipulation
- No BIOS, UEFI, EC, or BMC reconfiguration
- All writes are reversible
- Dry-run is a first-class workflow
- Missing interfaces never justify guessing

## Why sysfs first

Modern Linux kernels already expose vendor and platform policy through interfaces such as
`cpufreq`, `intel_pstate`, `amd-pstate`, cpuidle, thermal, hwmon, and cooling devices.
Those interfaces carry kernel-side validation, platform integration, and better stability
than ad hoc register pokes.

## Reversible writes

Before applying a profile, CPUOpt stores original values for every targeted path in
`last_state.json`. Restore replays those values and skips paths that are no longer writable
or present.

## Dry-run

`--dry-run` computes and prints the exact intended changes without touching the system. It is
mandatory support and is the recommended first step before any real profile change.

## Idle tuning

Latency-sensitive cpuidle tuning is opt-in only:

- disabled by default
- only attempted with `--allow-idle-tuning`
- limited to the deepest exposed idle states
- fully reversible through snapshot restore

CPUOpt does not disable all C-states by default.

## Fan handling

Fan control is platform-specific and often owned by firmware, ACPI, an embedded controller,
or a BMC. v0.2 can inspect hwmon PWM-related files when explicitly requested but does not
perform fan writes. Reducing fan speed is not treated as CPU optimization.

## Platform-specific limitations

- Some systems expose no EPP or EPB controls.
- Some `cpufreq` drivers ignore governor writes.
- Thermal zone labels differ significantly across platforms.
- Fan and PWM paths vary widely and may be firmware-owned.
- Heterogeneous systems may expose multiple policies with different core types.

## Future advanced work

Any future register-level support must start with:

- documented sources such as Intel SDM Vol. 4 or AMD PPR
- model-specific validation
- read-only decoding before writes
- explicit safe-mode behavior
- fallback to supported kernel interfaces
