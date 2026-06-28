# Changelog

All notable changes to this project will be documented in this file.

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
