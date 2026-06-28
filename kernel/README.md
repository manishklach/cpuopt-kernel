# Future kernel module

This directory contains a conservative placeholder for a future CPUOpt kernel module.

The intended long-term interface is:

- `/sys/kernel/cpuopt/profile`
- `/sys/kernel/cpuopt/status`
- `/sys/kernel/cpuopt/telemetry`
- `/sys/kernel/cpuopt/safe_mode`

v0.1 keeps policy writes in user space and leaves risky functionality out of the kernel.
