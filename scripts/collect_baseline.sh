#!/usr/bin/env bash
set -euo pipefail

out_dir="${1:-baseline-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out_dir"

python3 cpuoptctl/cpuoptctl.py export-json > "$out_dir/cpuopt-status.json"
uname -a > "$out_dir/uname.txt"
lscpu > "$out_dir/lscpu.txt"

if command -v cpupower >/dev/null 2>&1; then
  cpupower frequency-info > "$out_dir/cpupower-frequency-info.txt"
fi

if command -v turbostat >/dev/null 2>&1; then
  turbostat --quiet --show Package,Core,CPU,Avg_MHz,Bzy_MHz,TSC_MHz,PkgTmp --num_iterations 1 > "$out_dir/turbostat.txt" || true
fi

if command -v sensors >/dev/null 2>&1; then
  sensors > "$out_dir/sensors.txt"
fi
