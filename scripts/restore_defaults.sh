#!/usr/bin/env bash
set -euo pipefail

python3 cpuoptctl/cpuoptctl.py restore "$@"
