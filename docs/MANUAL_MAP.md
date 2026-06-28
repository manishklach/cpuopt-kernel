# Manual-to-Code Map

This document maps vendor architectural manuals and Linux kernel interfaces to CPUOpt-Kernel
implementation areas.

| Area | Intel | AMD | ARM | Linux Interface |
|---|---|---|---|---|
| Core performance policy | HWP/EPP | CPPC/EPP | SCMI perf | `cpufreq` |
| Energy bias | EPB/EPP | CPPC EPP | platform-specific | sysfs |
| Idle latency | C-states | C-states | PSCI idle | `cpuidle` |
| Thermal telemetry | DTS/package temp | Tctl/Tdie | thermal zones | `thermal` / `hwmon` |
| Fan control | platform EC/BMC | platform EC/BMC | platform-specific | `hwmon` / `thermal` |
| Uncore/interconnect | uncore freq | data fabric/UMC | interconnect | platform-specific |

## Implementation notes

- v0.2 still prefers documented kernel and sysfs interfaces over register writes.
- Read-only Intel MSR decoding is telemetry-only and does not tune the platform.
- AMD and ARM remain backend roadmap areas until their Linux interfaces are implemented with
  the same safety constraints as the Intel MVP.
