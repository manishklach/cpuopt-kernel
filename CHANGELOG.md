# Changelog

All notable changes to this project will be documented in this file.

## v0.2.0

- repositioned CPUOpt-Kernel as a safety-first CPU performance policy layer rather than an
  overclocking tool, with updated GitHub description, topics, and README guidance
- expanded packaging metadata for a cleaner install path with `pyproject.toml`-based
  project metadata, console entry point configuration, optional test and dev extras, and
  richer project URLs and classifiers
- added `docs/ARCHITECTURE.md` to document the discovery-to-profile pipeline, sysfs-root
  abstraction, and future backend/plugin direction
- introduced `cpuoptctl doctor` for structured platform health checks across CPUFreq,
  `intel_pstate`, `amd-pstate`, cpuidle, thermal zones, hwmon, and policy safety signals
- introduced `cpuoptctl explain` to describe profile intent and expected policy behavior
  without applying changes
- introduced `cpuoptctl compare` as an early benchmark-oriented comparison surface for
  evaluating profile tradeoffs
- added safe, read-only MSR telemetry commands including `cpuoptctl msr-read --intel
  --safe` and `cpuoptctl intel-hwp`
- added the v0.3 recommendation engine behind `cpuoptctl recommend`, including workload
  presets such as `kernel-build`, `low-latency`, and `llama-inference`
- recommendation output now reports recommended profile, confidence, reasons, warnings,
  suggested dry-run and restore commands, and unsupported features without writing to the
  system
- expanded fake sysfs fixtures and unit coverage for advisory logic, dry-run guarantees,
  apply validation, and Intel recommendation paths
- refreshed demo assets and example flows to showcase doctor, recommend, dry-run diff, and
  monitor-driven workflows
- fixed GitHub Actions workflow failures by cleaning up lint issues and simplifying the CI
  gate to the checks that currently reflect the maintained code path

## v0.1.0

- initial public release of CPUOpt-Kernel
- Intel-first, sysfs-first userspace controller with `status`, `discover`, `profile`,
  `monitor`, `restore`, and `export-json` commands
- safe profile mappings for `performance`, `balanced`, `latency`, `quiet`, and
  `ai-inference`
- discovery coverage for CPUFreq, `intel_pstate`, `amd-pstate`, cpuidle, topology, NUMA,
  thermal zones, cooling devices, and hwmon metadata
- reversible write model with snapshot/restore support for non-dry-run profile application
- dry-run behavior hardened so `--dry-run` performs zero filesystem modifications,
  including no snapshot and no write log generation
- apply-time write revalidation added through `ProposedWrite.valid_values`
- fake sysfs fixtures and unit tests for discovery, profile decisions, dry-run safety, and
  invalid-value rejection
- placeholder kernel module scaffolding for future `/sys/kernel/cpuopt/` integration
- GitHub Actions CI, GPL-2.0-only licensing, contribution guidance, security policy, and
  release metadata added
