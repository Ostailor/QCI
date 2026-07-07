#!/usr/bin/env bash
set -u
cd /Users/omtailor/QCI
export QCI_SAMPLES_PER_JOB=20
export QCI_PAYLOAD_WORKERS=66
export QCI_MAX_INFLIGHT_JOBS=1
python -u scripts/phase3_run_qci.py \
  --payload-dir results/phase3/public_benchmarks/pglib_case30_ieee/qci_fit_payloads \
  --output-dir results/phase3/public_benchmarks/pglib_case30_ieee/qci \
  --repeats 20
code=$?
echo "case30_qci_exit_code=$code at $(date '+%Y-%m-%d %H:%M:%S %Z')"
exit $code
