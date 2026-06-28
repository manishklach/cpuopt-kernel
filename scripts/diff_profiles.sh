#!/usr/bin/env bash
set -euo pipefail

python3 cpuoptctl/cpuoptctl.py profile "${1:?old profile required}" --dry-run --json > /tmp/cpuopt-old.json
python3 cpuoptctl/cpuoptctl.py profile "${2:?new profile required}" --dry-run --json > /tmp/cpuopt-new.json
diff -u /tmp/cpuopt-old.json /tmp/cpuopt-new.json || true
