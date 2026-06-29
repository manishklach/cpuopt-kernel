# Roadmap

## Milestone 0

- repo scaffold
- discovery-only foundation

## Milestone 1

- Intel safe profile application

## Milestone 2

- telemetry and benchmark comparison
- doctor and explain surfaces
- recommendation engine and workload-aware advisory output
- dry-run diff visualization
- Intel HWP reporting and read-only MSR telemetry
- workload presets and demo assets

## Milestone 3

- AMD `amd-pstate` support

## Milestone 4

- ARM SCMI and `cpufreq` support

## Milestone 5

- optional kernel module exposing `/sys/kernel/cpuopt/`

## Milestone 6

- guarded MSR read-only decoding

## Milestone 7

- guarded MSR write support for explicitly supported models only

## v0.1.0 release checklist

- Python files pass `py_compile`
- `python -m unittest` passes
- dry-run performs zero filesystem modifications
- Intel fixture-based `status` and `profile --dry-run` commands succeed
- README, SAFETY, and testing docs match implementation behavior
- CI is enabled on GitHub
- license, security, contributing, and changelog files are present
