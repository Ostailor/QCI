# Phase 3 QCi Smoke-Test Plan

The smoke test uses six paired public-benchmark payloads: two each from PGLib-derived case5, case14, and case30. No literal `combined_high_stress` payload exists, so selections maximize critical-load exposure within the requested PCC-failure, demand-surge, and storm-forced-islanding scenarios. The direct CMPO-V2 payloads have 132 variables and degree 3; matching hybrid payloads have 123 variables and degree 2.

## Stage A: CMPO-V2

```bash
python scripts/phase3_run_qci.py \
  --payload-list results/phase3/cmpo_v2/smoke_payloads.txt \
  --output-dir results/phase3/cmpo_v2_smoke/qci \
  --repeats 10

python scripts/phase3_decode_qci.py \
  --input-dir results/phase3/cmpo_v2_smoke/qci \
  --output-dir results/phase3/cmpo_v2_smoke/decoded
```

## Stage B: Hybrid

```bash
python scripts/phase3_run_qci.py \
  --payload-list results/phase3/hybrid/smoke_payloads.txt \
  --output-dir results/phase3/hybrid_smoke/qci \
  --repeats 10

python scripts/phase3_decode_qci.py \
  --input-dir results/phase3/hybrid_smoke/qci \
  --output-dir results/phase3/hybrid_smoke/decoded

python scripts/phase3_compare_hybrid.py \
  --qci-dir results/phase3/hybrid_smoke/decoded \
  --output-dir results/phase3/hybrid_smoke/comparison
```

## Stage C: Derived Comparison

```bash
python scripts/phase3_compare_smoke.py \
  --cmpo-v2-dir results/phase3/cmpo_v2_smoke/decoded \
  --hybrid-dir results/phase3/hybrid_smoke/comparison \
  --output-dir results/phase3/smoke_comparison
```

Stage C compares critical ENS, critical-load served fraction, maximum customer-unserved fraction, critical-infrastructure outage proxy, repaired feasibility, challenge score, risk-adjusted cost, runtime, and repeat variance. Conclusions are emitted only from completed decoded samples.
