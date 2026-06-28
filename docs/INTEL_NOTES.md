# Intel Notes

Intel v0.2 focuses on safe Linux interfaces:

- `intel_pstate`
- Hardware P-states (HWP)
- Energy Performance Preference (EPP)
- Energy Performance Bias (EPB)
- `no_turbo`
- CPUFreq policy directories
- cpuidle C-state visibility
- thermal and hwmon metadata

## Intel concepts

- `intel_pstate` can expose policy through `status`, `no_turbo`, and EPP files.
- HWP/EPP typically appears as `energy_performance_preference` under policy directories.
- EPB may appear as `energy_perf_bias`.
- CPUFreq policies expose governors, min/max/current frequency, and related metadata.
- C-states live under `cpu*/cpuidle/state*`.
- Uncore frequency controls may exist on some platforms, but v0.2 reports them only as
  future work.

## Future Intel work

- Intel Speed Select integration
- uncore frequency policy
- Intel SDM Vol. 4 MSR decoder
- read-only MSR telemetry
- model-specific allowlisted MSR writes only after validation
