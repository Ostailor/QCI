# IEEE123 Global Budget Master V2 Validation

- [x] exactly_six_global_master_payloads
- [x] budget_encoded_in_polynomial_terms
- [x] no_metadata_only_budget
- [x] qci_variable_limit
- [x] qci_degree_limit
- [x] low_energy_local_portfolios_real_budget_feasible
- [x] conservative_rounding_prevents_real_overrun
- [x] upgrade_one_hot_constraints_encoded
- [x] physical_assets_deduplicated_before_costing
- [x] same_portfolio_fixed_across_twelve_patch_recourse
- [x] upgrade_cost_charged_once_per_physical_system
- [x] penalty_dominance_certificate_passes
- [x] public_checksums_and_cost_provenance_preserved
- [x] no_v1_posthoc_rows_in_v2_outputs
- [x] no_qci_submission_during_build_or_validation

Overall valid: **True**

Strict-stop V1 audit: **FAILED_AS_EXPECTED_NO_SUBMISSION** (72/72 payloads failed as required).

Selected cost unit: **$1.00**; maximum full-catalog rounding conservatism: **$7.687503**.

No QCi upload or job submission was performed.

## Exact commands after approval

```bash
python scripts/phase3_validate_budget_master_v2.py
python scripts/phase3_run_qci.py --config configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml --payload-dir results/phase3/sc_cmpo/budget_master_v2/qci_master_payloads --output-dir results/phase3/sc_cmpo/budget_master_v2/actual_qci --repeats 30
```

`BUDGET_MASTER_V2_READY_FOR_QCI: YES`
