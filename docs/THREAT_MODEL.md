# Threat Model

CPUOpt-Kernel is a privileged systems tool and must treat safety and reversibility as primary
design constraints.

## Threats

1. Unsafe register writes
2. Thermal protection bypass
3. Fan misconfiguration
4. Battery drain
5. Laptop overheating
6. Server instability
7. Sysfs interfaces changing under hotplug
8. Firmware ownership conflicts
9. Bad restore state
10. Unsupported CPU model assumptions

## Mitigations

- dry-run support for profile application
- no raw MSR writes
- snapshot before non-dry-run write
- allowlisted values only
- apply-time validation of paths and values
- no fan writes by default
- no voltage control
- no overclocking
- no thermal protection bypass
- missing sysfs paths never crash the tool

## Residual risk

- sysfs interfaces can still disappear between discovery and apply time
- firmware may override OS policy on some laptops and servers
- benchmark-driven comparisons can perturb thermals and power even when they avoid unsafe writes
