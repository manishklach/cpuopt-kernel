# Contributing

CPUOpt-Kernel is a safety-first Linux systems project. Contributions are welcome, but every
change must preserve the core rules:

- no raw MSR writes in v0.1
- no fan writes in v0.1
- no thermal protection bypass
- no overclocking or voltage control
- all profile writes remain reversible

## Development flow

1. Create a focused branch.
2. Keep changes small and easy to review.
3. Add or update tests for every behavior change.
4. Run the local checks before opening a pull request.

## Required checks

```bash
python -m py_compile cpuoptctl\\*.py
python -m unittest
python cpuoptctl/cpuoptctl.py status --sysfs-root tests/fixtures/intel_hwp
python cpuoptctl/cpuoptctl.py profile performance --dry-run --sysfs-root tests/fixtures/intel_hwp --state-dir .tmp-cpuopt
```

In shells that do not expand globs automatically, compile files with:

```bash
python -c "import pathlib, py_compile; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('cpuoptctl').glob('*.py')]"
```

## Review expectations

- document safety implications explicitly
- avoid platform assumptions when sysfs paths may be missing
- prefer kernel/user-space interfaces over new low-level control paths
- keep docs aligned with code behavior
