#!/usr/bin/env bash
set -u
cd /Users/omtailor/QCI
export QCI_SAMPLES_PER_JOB=30
export QCI_PAYLOAD_WORKERS=60
export QCI_MAX_INFLIGHT_JOBS=1
python -u scripts/phase3_run_qci.py \
  --payload-dir results/phase3/public_benchmarks/pglib_case14_ieee/qci_fit_payloads \
  --output-dir results/phase3/public_benchmarks/pglib_case14_ieee/qci \
  --repeats 30
code=$?
echo "case14_qci_exit_code=$code at $(date '+%Y-%m-%d %H:%M:%S %Z')"
exit $code
