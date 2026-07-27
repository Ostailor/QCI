# SC-CMPO Validation

Overall: **PASS**

- Payloads: 43 across 4 public benchmark families
- Maximum variables: 103 (limit 132)
- Maximum degree: 3 (limit 3)
- Completed QCi provenance rows: 43
- Payload-level checks: 817 passed
- Every payload passed bounds, normalization, public-input-only, no-random-grid, no-undocumented-synthetic-value, source-provenance, and challenge-stage checks.

## Benchmark Summary

| Benchmark | Payloads | Scenarios | Max variables | Max degree |
|---|---:|---:|---:|---:|
| arpae_go_network_01o_020 | 8 | 8 | 103 | 3 |
| ieee123_opendss | 12 | 8 | 103 | 3 |
| pglib_case14_ieee | 9 | 8 | 103 | 3 |
| pglib_case30_ieee | 14 | 8 | 103 | 3 |

## Global Gates

| Check | Result | Detail |
|---|---:|---|
| payload_manifest_nonempty | PASS | payload_count=43 |
| all_payload_files_exist | PASS | all present |
| at_least_three_public_families | PASS | arpae_go_challenge1,ieee123_distribution,pglib_case14_ieee,pglib_case30_ieee |
| manifest_execution_provenance | PASS | completed_execution_rows=43; build-time execution flags must remain false |
| positive_upgrade_case | PASS | at least one robust island requires a nonzero upgrade |
| provenance_complete | PASS | rows=11 |
| local_provenance_checksums | PASS | every local provenance file matches its recorded checksum |
| source_checksums_recorded | PASS | every upstream source checksum is a SHA-256 digest |
| nonzero_stage1_decision_evidence | PASS | robust_lp_present=False; robust_lp_nonzero=False |
