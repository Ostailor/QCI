#!/usr/bin/env bash
set -u
cd /Users/omtailor/QCI
echo "public_baselines_remaining_start=$(date '+%Y-%m-%d %H:%M:%S %Z')"
python -u scripts/phase3_run_gpu_baselines.py \
  --benchmarks pglib_case14_ieee pglib_case30_ieee \
  --repeats 50 \
  --budget-hours 50
code=$?
echo "public_baselines_remaining_exit_code=$code at $(date '+%Y-%m-%d %H:%M:%S %Z')"
exit $code
