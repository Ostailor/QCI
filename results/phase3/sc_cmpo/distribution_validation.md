# IEEE 123-Bus Distribution Validation

**Status:** PASS

This is a pre-optimization gate. No SC-CMPO payload is considered validated unless the published OpenDSS feeder compiles, converges, and agrees with the repository parser on the checks below.

## Source

- Benchmark: `ieee123_opendss`
- Version: DSS-Extensions filtered OpenDSS archive commit 3b208397160213cae4a9e2d0a7d1aa3528ce26e1
- URL: https://github.com/dss-extensions/electricdss-tst/tree/3b208397160213cae4a9e2d0a7d1aa3528ce26e1/Version8/Distrib/IEEETestCases/123Bus
- Master file: `data/upstream/ieee123/opendss/IEEE123Master.dss`
- Master SHA-256: `c92a69d9b218b1b2646ec7911783826229309038e72f16b848304c0457c0a54d`
- Engine: OpenDSSDirect.py 0.9.1
- Backend: DSS-Python 0.15.7

## Electrical Solve

- Converged: `True`
- Solver iterations: `19`
- Minimum bus voltage: `0.979211032` pu
- Maximum bus voltage: `1.04996093` pu
- Published load represented: `3490` kW / `1920` kvar
- Source power: `-3615.2419` kW / `-1311.51028` kvar
- Active loss: `95.9767073` kW
- Reactive loss: `192.499357` kvar

## Parser/Engine Checks

| Check | Observed | Expected | Pass |
|---|---:|---:|:---:|
| compile_succeeded |  |  | yes |
| solver_converged | True | True | yes |
| bus_count_matches | 132 | 132 | yes |
| line_count_matches | 126 | 126 | yes |
| load_count_matches | 91 | 91 | yes |
| transformer_count_matches | 8 | 8 | yes |
| regulator_count_matches | 7 | 7 | yes |
| capacitor_count_matches | 4 | 4 | yes |
| total_load_kw_matches | 3490 | 3490 | yes |
| total_load_kvar_matches | 1920 | 1920 | yes |
| bus_name_set_matches | 132 exact values | 132 exact values | yes |
| line_name_set_matches | 126 exact values | 126 exact values | yes |
| load_name_set_matches | 91 exact values | 91 exact values | yes |
| transformer_name_set_matches | 8 exact values | 8 exact values | yes |
| regulator_name_set_matches | 7 exact values | 7 exact values | yes |
| capacitor_name_set_matches | 4 exact values | 4 exact values | yes |
| minimum_voltage_within_bounds | 0.979211032 | 0.9 | yes |
| maximum_voltage_within_bounds | 1.04996093 | 1.1 | yes |

## Scope

The validation uses the published unbalanced feeder, phase connections, line-code impedances, loads, transformers, regulator controls, and capacitors. Published line codes contain no ampacity values, so optimization artifacts preserve line ratings as unavailable instead of substituting OpenDSS defaults. PV and BESS are introduced only later as upgrade choices priced from the pinned NREL ATB catalog.
