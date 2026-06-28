# Testing

CPUOpt-Kernel uses fake sysfs fixtures so policy logic can be validated without mutating a
real host.

## Run tests

```bash
python3 -m unittest
```

## Run CLI against fixtures

```bash
python3 cpuoptctl/cpuoptctl.py status --sysfs-root tests/fixtures/intel_hwp
python3 cpuoptctl/cpuoptctl.py profile performance --dry-run --sysfs-root tests/fixtures/intel_hwp
```

## Test focus

- Intel EPP discovery
- profile write proposal correctness
- dry-run non-mutation
- snapshot creation
- missing path tolerance
- invalid value rejection
- no fan writes in quiet mode without explicit opt-in
