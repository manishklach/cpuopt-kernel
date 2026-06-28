#!/usr/bin/env bash
set -euo pipefail

source_dir="${1:-}"

if command -v stress-ng >/dev/null 2>&1; then
  echo "## stress-ng"
  stress-ng --cpu 1 --timeout 10 --metrics-brief || true
fi

if command -v sysbench >/dev/null 2>&1; then
  echo "## sysbench"
  sysbench cpu --time=10 run || true
fi

if [[ -n "$source_dir" && -d "$source_dir" ]]; then
  echo "## make compile benchmark"
  make -C "$source_dir" -j"$(nproc)" -n >/dev/null 2>&1 || true
fi

if command -v perf >/dev/null 2>&1; then
  echo "## perf stat"
  perf stat -a sleep 3 || true
fi
