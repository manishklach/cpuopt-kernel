# Security Policy

## Scope

CPUOpt-Kernel interacts with privileged Linux performance and power-management interfaces.
Even safe sysfs writes can affect latency, power, and thermals, so responsible disclosure is
important.

## Supported versions

- `main`: supported for security reports during the pre-`v0.2.0` phase

## Reporting

Please do not open public issues for suspected security problems. Instead, report:

- affected platform and kernel version
- exact command used
- expected behavior
- observed behavior
- whether the issue requires elevated privileges

Until a dedicated private contact is added, security-sensitive reports should be sent through
GitHub Security Advisories for this repository.

## Safety boundaries

The following are intentional non-features in `v0.2`:

- raw MSR writes
- fan writes
- thermal throttling bypass
- voltage control
- overclocking

Reports asking for those capabilities will be treated as out of scope for `v0.2`.
