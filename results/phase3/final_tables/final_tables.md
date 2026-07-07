# Phase 3 Final Tables

## table1_qci_vs_best_baselines

| dataset | qci_method | qci_risk_adjusted_cost | best_baseline_method | best_baseline_risk_adjusted_cost | qci_minus_best_baseline | qci_on_pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | CMPO + QCi Dirac-3 | 30167.7 | Piecewise-linear MILP baseline | 15539.8 | 14627.9 | False |
| pglib_case30_adapted | CMPO + QCi Dirac-3 | 28423.2 | Piecewise-linear MILP baseline | 13101.4 | 15321.9 | False |
| pglib_case57_adapted |  | nan | Piecewise-linear MILP baseline | 3344.14 | nan | False |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 69918.4 | Piecewise-linear MILP baseline | 77693.5 | -7775.12 | False |
| qci_small_synthetic |  | nan | Piecewise-linear MILP baseline | 16458.1 | nan | False |
| synthetic_smoke |  | nan | Piecewise-linear MILP baseline | 508.446 | nan | False |

## table2_public_benchmark_ladder

| benchmark | family | full_payload_count | full_payload_max_variables | full_payload_status | license | local_path | only_classical_baselines_were_run | output_dir | outputs_present | qci_execution_payload_type | qci_execution_was_run | qci_fit_manifest | qci_fit_max_degree | qci_fit_max_variables | qci_fit_payload_count | qci_fit_status | qci_not_executed_reason | required_outputs | sha256_checksum | source_name | status | transformation_notes | upstream_url | version_or_commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case5_pjm | pglib | 8 | 132 | qci_executable_full_payloads | Creative Commons Attribution 4.0 International | results/phase3/public_benchmarks/pglib_case5_pjm | False | results/phase3/public_benchmarks/pglib_case5_pjm | 8 | full | True | nan | 0 | 0 | 0 | missing | nan | 8 | sha256:cadf7501a15c2d508820493cef6acc85757274197e74c40bcec4fc4ecf619e6f | PGLib-OPF pglib_opf_case5_pjm | available | Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction. | https://github.com/power-grid-lib/pglib-opf | v23.07 |
| pglib_case14_ieee | pglib | 12 | 198 | classical_reference_and_qci_fit_source | Creative Commons Attribution 4.0 International | results/phase3/public_benchmarks/pglib_case14_ieee | False | results/phase3/public_benchmarks/pglib_case14_ieee | 8 | qci_fit | True | results/phase3/public_benchmarks/pglib_case14_ieee/qci_fit_payload_manifest.csv | 3 | 132 | 60 | available | nan | 8 | sha256:bd5c568621de65e4b0922317010868bc7fa94173807faa10ea8fdbbe77c28106 | PGLib-OPF pglib_opf_case14_ieee | available | Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction. | https://github.com/power-grid-lib/pglib-opf | v23.07 |
| pglib_case30_ieee | pglib | 18 | 198 | classical_reference_and_qci_fit_source | Creative Commons Attribution 4.0 International | results/phase3/public_benchmarks/pglib_case30_ieee | False | results/phase3/public_benchmarks/pglib_case30_ieee | 8 | nan | True | results/phase3/public_benchmarks/pglib_case30_ieee/qci_fit_payload_manifest.csv | 3 | 132 | 66 | available | nan | 8 | sha256:cae3290639d989731d32428aacf30c0b918bc91db73bc54791f3aa62d3f76c70 | PGLib-OPF pglib_opf_case30_ieee | available | Public-benchmark-derived microgrid resilience adapter; not an AC OPF reproduction. | https://github.com/power-grid-lib/pglib-opf | v23.07 |
| pglib_case57_ieee | pglib | 8 | 198 | classical_reference_and_qci_fit_source | Creative Commons Attribution 4.0 International | results/phase3/public_benchmarks/pglib_case57_ieee | True | results/phase3/public_benchmarks/pglib_case57_ieee | 8 | nan | False | results/phase3/public_benchmarks/pglib_case57_ieee/qci_fit_payload_manifest.csv | 3 | 132 | 40 | available | QCi Dirac-3 rejected/limits degree-3 public payloads above 135 variables; largest full payload has 198 variables. Use qci_fit_payloads for hardware execution. | 8 | sha256:aa3b48f7cbaade2afd69cb3790ef72be981db8494dcef9277bee460f754bdb22 | PGLib-OPF pglib_opf_case57_ieee | available | Public-benchmark-derived microgrid resilience adapter; QCi may be infeasible if payloads exceed limits. | https://github.com/power-grid-lib/pglib-opf | v23.07 |
| arpae_go | arpae_go | nan | nan | nan | See OEDI dataset terms | data/public_benchmarks/arpae_go/extracted/Challenge_1_Original_Dataset_2_Scenarios/Original_Dataset_Offline_Edition_2/Network_01O-020/scenario_1/case.raw | True | results/phase3/public_benchmarks/arpae_go | 2 | nan | False | nan | 0 | 0 | 0 | missing | nan | nan | b438dab6d51492ff501cea1e9acb5ed3591873b188f8b844acaad0ef75749852 | ARPA-E Grid Optimization Challenge public data | available | ARPA-E GO-derived microgrid stress adapter feasibility path. | https://data.openei.org/submissions/6153 | OEDI public submission 6153/6197/5997 resource snapshot |
| ieee_distribution | ieee_distribution | nan | nan | nan | nan | results/phase3/public_benchmarks/ieee_distribution | True | results/phase3/public_benchmarks/ieee_distribution | 1 | nan | False | nan | 0 | 0 | 0 | missing | nan | nan | nan | IEEE 13/34/123-bus distribution feeder public data | benchmark_missing | Benchmark missing report is explicit; this path is not silently skipped. | https://github.com/tshort/OpenDSS | nan |

## table3_scenario_stress

| dataset | scenario | method_name | expected_operating_cost | risk_adjusted_cost | critical_load_served_fraction | critical_energy_not_served_kwh | energy_not_served_kwh | max_fraction_customers_unserved_per_hour | total_critical_infrastructure_unserved_hours_proxy | runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | demand_surge | Piecewise-linear MILP baseline | 113.419 | 113.419 | 1 | 0 | 0 | 0 | 0 | 0.041971 |
| pglib_case14_adapted | demand_surge | Stress-only reserve heuristic baseline | 138.834 | 138.834 | 1 | 0 | 295.712 | 0.190352 | 0 | 0.000102521 |
| pglib_case14_adapted | demand_surge | CMPO + QCi Dirac-3 | 134.098 | 155.507 | 0 | 64.6667 | 155.823 | 0.100305 | 6 | 32 |
| pglib_case14_adapted | demand_surge | IPOPT/Pyomo nonlinear baseline | 182.679 | 182.688 | 0.999938 | 0.0358453 | 3.93554 | 0.00253334 | 3 | 0.539326 |
| pglib_case14_adapted | demand_surge | SLSQPDispatchOptimizer | 182.679 | 182.688 | 0.999938 | 0.0358453 | 3.93554 | 0.00253334 | 3 | 0.503971 |
| pglib_case14_adapted | demand_surge | QUBO/quadratized local search baseline | 183.537 | 183.537 | 1 | 0 | 3.90147 | 0.0025114 | 0 | 5.18882 |
| pglib_case14_adapted | demand_surge | CMPO-local polynomial search | 183.569 | 183.569 | 1 | 0 | 3.90147 | 0.0025114 | 0 | 1.29512 |
| pglib_case14_adapted | demand_surge | GPU-parallel random restart baseline | 183.569 | 183.569 | 1 | 0 | 3.90147 | 0.0025114 | 0 | 0.00401092 |
| pglib_case14_adapted | demand_surge | GreedyCriticalLoadFirst | 183.569 | 183.569 | 1 | 0 | 3.90147 | 0.0025114 | 0 | 0 |
| pglib_case14_adapted | demand_surge | DifferentialEvolutionOptimizer | 156.556 | 200.059 | 0.585279 | 122.936 | 319.076 | 0.205392 | 6 | 0.161828 |
| pglib_case14_adapted | local_generator_failure | Piecewise-linear MILP baseline | 93.5676 | 93.5676 | 1 | 0 | 0 | 0 | 0 | 0.041643 |
| pglib_case14_adapted | local_generator_failure | Stress-only reserve heuristic baseline | 124.433 | 124.433 | 1 | 0 | 229.122 | 0.173188 | 0 | 9.29795e-05 |
| pglib_case14_adapted | local_generator_failure | CMPO + QCi Dirac-3 | 126.443 | 139.167 | 0 | 55.0704 | 132.7 | 0.100305 | 6 | 31.5 |
| pglib_case14_adapted | local_generator_failure | IPOPT/Pyomo nonlinear baseline | 155.377 | 155.377 | 1 | 0 | 0 | 0 | 0 | 0.386308 |
| pglib_case14_adapted | local_generator_failure | SLSQPDispatchOptimizer | 155.377 | 155.377 | 1 | 0 | 0 | 0 | 0 | 0.383172 |
| pglib_case14_adapted | local_generator_failure | CMPO-local polynomial search | 156.361 | 156.361 | 1 | 0 | 0 | 0 | 0 | 1.3278 |
| pglib_case14_adapted | local_generator_failure | GPU-parallel random restart baseline | 156.361 | 156.361 | 1 | 0 | 0 | 0 | 0 | 0.00365698 |
| pglib_case14_adapted | local_generator_failure | GreedyCriticalLoadFirst | 156.361 | 156.361 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case14_adapted | local_generator_failure | QUBO/quadratized local search baseline | 158.418 | 158.418 | 1 | 0 | 0 | 0 | 0 | 5.247 |
| pglib_case14_adapted | local_generator_failure | DifferentialEvolutionOptimizer | 151.459 | 184.883 | 0.591345 | 97.6115 | 293.891 | 0.222145 | 6 | 0.157686 |
| pglib_case14_adapted | normal | Piecewise-linear MILP baseline | 88.0667 | 88.0667 | 1 | 0 | 0 | 0 | 0 | 0.0397932 |
| pglib_case14_adapted | normal | Stress-only reserve heuristic baseline | 124.082 | 124.082 | 1 | 0 | 212.201 | 0.166813 | 0 | 9.3708e-05 |
| pglib_case14_adapted | normal | CMPO + QCi Dirac-3 | 135.214 | 153.321 | 0 | 52.9523 | 127.596 | 0.100305 | 6 | 32 |
| pglib_case14_adapted | normal | IPOPT/Pyomo nonlinear baseline | 155.382 | 155.382 | 1 | 0 | 0 | 0 | 0 | 0.515552 |
| pglib_case14_adapted | normal | SLSQPDispatchOptimizer | 155.382 | 155.382 | 1 | 0 | 0 | 0 | 0 | 0.510156 |
| pglib_case14_adapted | normal | CMPO-local polynomial search | 156.243 | 156.243 | 1 | 0 | 0 | 0 | 0 | 1.35832 |
| pglib_case14_adapted | normal | GPU-parallel random restart baseline | 156.243 | 156.243 | 1 | 0 | 0 | 0 | 0 | 0.00366169 |
| pglib_case14_adapted | normal | GreedyCriticalLoadFirst | 156.243 | 156.243 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case14_adapted | normal | QUBO/quadratized local search baseline | 157.084 | 157.084 | 1 | 0 | 0 | 0 | 0 | 4.87615 |
| pglib_case14_adapted | normal | DifferentialEvolutionOptimizer | 153.879 | 187.276 | 0.592916 | 91.4205 | 269.627 | 0.211957 | 6 | 0.185072 |
| pglib_case14_adapted | pcc_failure | Piecewise-linear MILP baseline | 94.691 | 94.691 | 1 | 0 | 0 | 0 | 0 | 0.0383667 |
| pglib_case14_adapted | pcc_failure | Stress-only reserve heuristic baseline | 126.672 | 126.672 | 1 | 0 | 248.691 | 0.186189 | 0 | 0.000106437 |
| pglib_case14_adapted | pcc_failure | CMPO + QCi Dirac-3 | 126.453 | 145.189 | 0 | 55.6 | 133.976 | 0.100305 | 6 | 32 |
| pglib_case14_adapted | pcc_failure | DifferentialEvolutionOptimizer | 128.313 | 161.785 | 0.607093 | 94.6502 | 285.985 | 0.214111 | 6 | 0.15536 |
| pglib_case14_adapted | pcc_failure | CMPO-local polynomial search | 163.155 | 163.155 | 1 | 0 | 0 | 0 | 0 | 1.26313 |
| pglib_case14_adapted | pcc_failure | GPU-parallel random restart baseline | 163.155 | 163.155 | 1 | 0 | 0 | 0 | 0 | 0.0041156 |
| pglib_case14_adapted | pcc_failure | GreedyCriticalLoadFirst | 163.155 | 163.155 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case14_adapted | pcc_failure | IPOPT/Pyomo nonlinear baseline | 163.155 | 163.155 | 1 | 0 | 0 | 0 | 0 | 0.22112 |
| pglib_case14_adapted | pcc_failure | SLSQPDispatchOptimizer | 163.155 | 163.155 | 1 | 0 | 0 | 0 | 0 | 0.216175 |
| pglib_case14_adapted | pcc_failure | QUBO/quadratized local search baseline | 164.821 | 164.821 | 1 | 0 | 0 | 0 | 0 | 5.14825 |
| pglib_case14_adapted | renewable_shortfall | Piecewise-linear MILP baseline | 96.1417 | 96.1417 | 1 | 0 | 0 | 0 | 0 | 0.0396167 |
| pglib_case14_adapted | renewable_shortfall | Stress-only reserve heuristic baseline | 130.265 | 130.265 | 1 | 0 | 229.874 | 0.177164 | 0 | 9.42295e-05 |
| pglib_case14_adapted | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 150.859 | 150.859 | 1 | 0 | 0 | 0 | 0 | 0.630502 |
| pglib_case14_adapted | renewable_shortfall | SLSQPDispatchOptimizer | 150.859 | 150.859 | 1 | 0 | 0 | 0 | 0 | 0.618822 |
| pglib_case14_adapted | renewable_shortfall | CMPO + QCi Dirac-3 | 133.276 | 153.575 | 0 | 54.0114 | 130.148 | 0.100305 | 6 | 32 |
| pglib_case14_adapted | renewable_shortfall | CMPO-local polynomial search | 164.686 | 164.686 | 1 | 0 | 0 | 0 | 0 | 1.28569 |
| pglib_case14_adapted | renewable_shortfall | GPU-parallel random restart baseline | 164.686 | 164.686 | 1 | 0 | 0 | 0 | 0 | 0.00359906 |
| pglib_case14_adapted | renewable_shortfall | GreedyCriticalLoadFirst | 164.686 | 164.686 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case14_adapted | renewable_shortfall | QUBO/quadratized local search baseline | 165.609 | 165.609 | 1 | 0 | 0 | 0 | 0 | 4.86643 |
| pglib_case14_adapted | renewable_shortfall | DifferentialEvolutionOptimizer | 157.229 | 188.279 | 0.578981 | 90.3234 | 265.547 | 0.204657 | 6 | 0.163774 |
| pglib_case14_adapted | storm_forced_islanding | CMPO + QCi Dirac-3 | 13.5957 | 53.6701 | 0 | 62.4838 | 204.683 | 0.136359 | 6 | 33.5 |
| pglib_case14_adapted | storm_forced_islanding | Stress-only reserve heuristic baseline | 78.6723 | 107.591 | 0.793957 | 115.674 | 514.706 | 0.342895 | 3 | 9.7021e-05 |
| pglib_case14_adapted | storm_forced_islanding | DifferentialEvolutionOptimizer | 82.3116 | 125.335 | 0.477463 | 184.246 | 485.464 | 0.323414 | 6 | 0.136365 |
| pglib_case14_adapted | storm_forced_islanding | GPU-parallel random restart baseline | 88.6324 | 130.032 | 0.79368 | 115.83 | 372.542 | 0.248186 | 3 | 0.00387852 |
| pglib_case14_adapted | storm_forced_islanding | QUBO/quadratized local search baseline | 99.8951 | 132.631 | 0.79368 | 115.83 | 380.929 | 0.253773 | 3 | 4.40673 |
| pglib_case14_adapted | storm_forced_islanding | CMPO-local polynomial search | 91.9639 | 132.765 | 0.79368 | 115.83 | 372.542 | 0.248186 | 3 | 1.10314 |
| pglib_case14_adapted | storm_forced_islanding | Piecewise-linear MILP baseline | 103.876 | 132.795 | 0.793957 | 115.674 | 372.542 | 0.248186 | 3 | 0.0595888 |
| pglib_case14_adapted | storm_forced_islanding | IPOPT/Pyomo nonlinear baseline | 115.259 | 144.221 | 0.793645 | 115.849 | 377.039 | 0.251182 | 3 | 0.505685 |
| pglib_case14_adapted | storm_forced_islanding | SLSQPDispatchOptimizer | 115.259 | 144.221 | 0.793645 | 115.849 | 377.039 | 0.251182 | 3 | 0.464545 |
| pglib_case14_adapted | storm_forced_islanding | GreedyCriticalLoadFirst | 116.415 | 145.373 | 0.79368 | 115.83 | 372.542 | 0.248186 | 3 | 0 |
| pglib_case30_adapted | demand_surge | Piecewise-linear MILP baseline | 29.1378 | 29.1378 | 1 | 0 | 0 | 0 | 0 | 0.0477908 |
| pglib_case30_adapted | demand_surge | IPOPT/Pyomo nonlinear baseline | 115.949 | 115.949 | 1 | 0 | 0 | 0 | 0 | 0.495699 |
| pglib_case30_adapted | demand_surge | SLSQPDispatchOptimizer | 115.949 | 115.949 | 1 | 0 | 0 | 0 | 0 | 0.532949 |
| pglib_case30_adapted | demand_surge | CMPO-local polynomial search | 118.439 | 118.439 | 1 | 0 | 0 | 0 | 0 | 1.93005 |
| pglib_case30_adapted | demand_surge | GPU-parallel random restart baseline | 118.439 | 118.439 | 1 | 0 | 0 | 0 | 0 | 0.00407871 |
| pglib_case30_adapted | demand_surge | GreedyCriticalLoadFirst | 118.439 | 118.439 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | demand_surge | QUBO/quadratized local search baseline | 118.439 | 118.439 | 1 | 0 | 0 | 0 | 0 | 7.4196 |
| pglib_case30_adapted | demand_surge | Stress-only reserve heuristic baseline | 118.439 | 118.439 | 1 | 0 | 0 | 0 | 0 | 0.000105042 |
| pglib_case30_adapted | demand_surge | DifferentialEvolutionOptimizer | 165.709 | 183.546 | 0.676864 | 40.7837 | 115.881 | 0.0758622 | 6 | 0.202892 |
| pglib_case30_adapted | demand_surge | CMPO + QCi Dirac-3 | 123.607 | 191.929 | 0 | 64.6667 | 155.823 | 0.102011 | 6 | 21 |
| pglib_case30_adapted | local_generator_failure | Piecewise-linear MILP baseline | 22.7426 | 22.7426 | 1 | 0 | 0 | 0 | 0 | 0.0453522 |
| pglib_case30_adapted | local_generator_failure | IPOPT/Pyomo nonlinear baseline | 64.2667 | 64.2667 | 1 | 0 | 0 | 0 | 0 | 0.289852 |
| pglib_case30_adapted | local_generator_failure | SLSQPDispatchOptimizer | 64.2667 | 64.2667 | 1 | 0 | 0 | 0 | 0 | 0.297996 |
| pglib_case30_adapted | local_generator_failure | CMPO-local polynomial search | 64.4904 | 64.4904 | 1 | 0 | 0 | 0 | 0 | 1.90145 |
| pglib_case30_adapted | local_generator_failure | GPU-parallel random restart baseline | 64.4904 | 64.4904 | 1 | 0 | 0 | 0 | 0 | 0.00433442 |
| pglib_case30_adapted | local_generator_failure | GreedyCriticalLoadFirst | 64.4904 | 64.4904 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | local_generator_failure | QUBO/quadratized local search baseline | 65.5596 | 65.5596 | 1 | 0 | 0 | 0 | 0 | 7.09426 |
| pglib_case30_adapted | local_generator_failure | Stress-only reserve heuristic baseline | 69.6846 | 69.6846 | 1 | 0 | 0 | 0 | 0 | 0.000106667 |
| pglib_case30_adapted | local_generator_failure | DifferentialEvolutionOptimizer | 106.432 | 122.085 | 0.625678 | 39.4846 | 112.803 | 0.0867153 | 6 | 0.201754 |
| pglib_case30_adapted | local_generator_failure | CMPO + QCi Dirac-3 | 134.93 | 159.584 | 0 | 55.0704 | 132.7 | 0.102011 | 6 | 21 |
| pglib_case30_adapted | normal | Piecewise-linear MILP baseline | 21.0041 | 21.0041 | 1 | 0 | 0 | 0 | 0 | 0.0454554 |
| pglib_case30_adapted | normal | IPOPT/Pyomo nonlinear baseline | 87.7824 | 87.7824 | 1 | 0 | 0 | 0 | 0 | 0.226707 |
| pglib_case30_adapted | normal | SLSQPDispatchOptimizer | 87.7824 | 87.7824 | 1 | 0 | 0 | 0 | 0 | 0.185056 |
| pglib_case30_adapted | normal | CMPO-local polynomial search | 94.2355 | 94.2355 | 1 | 0 | 0 | 0 | 0 | 1.91124 |
| pglib_case30_adapted | normal | GPU-parallel random restart baseline | 94.2355 | 94.2355 | 1 | 0 | 0 | 0 | 0 | 0.00407527 |
| pglib_case30_adapted | normal | GreedyCriticalLoadFirst | 94.2355 | 94.2355 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | normal | QUBO/quadratized local search baseline | 94.2355 | 94.2355 | 1 | 0 | 0 | 0 | 0 | 7.32436 |
| pglib_case30_adapted | normal | Stress-only reserve heuristic baseline | 94.2355 | 94.2355 | 1 | 0 | 0 | 0 | 0 | 0.000107771 |
| pglib_case30_adapted | normal | DifferentialEvolutionOptimizer | 153.476 | 167.042 | 0.660561 | 35.1112 | 97.9489 | 0.0783082 | 6 | 0.206326 |
| pglib_case30_adapted | normal | CMPO + QCi Dirac-3 | 131.403 | 172.656 | 0 | 52.9523 | 127.596 | 0.102011 | 6 | 21 |
| pglib_case30_adapted | pcc_failure | Piecewise-linear MILP baseline | 23.2916 | 23.2916 | 1 | 0 | 0 | 0 | 0 | 0.0468854 |
| pglib_case30_adapted | pcc_failure | Stress-only reserve heuristic baseline | 97.035 | 97.035 | 1 | 0 | 18.0796 | 0.013766 | 0 | 0.000105584 |
| pglib_case30_adapted | pcc_failure | IPOPT/Pyomo nonlinear baseline | 98.0991 | 98.0991 | 1 | 0 | 0 | 0 | 0 | 0.392578 |
| pglib_case30_adapted | pcc_failure | SLSQPDispatchOptimizer | 98.0991 | 98.0991 | 1 | 0 | 0 | 0 | 0 | 0.413515 |
| pglib_case30_adapted | pcc_failure | CMPO-local polynomial search | 100.476 | 100.476 | 1 | 0 | 0 | 0 | 0 | 1.80771 |
| pglib_case30_adapted | pcc_failure | GPU-parallel random restart baseline | 100.476 | 100.476 | 1 | 0 | 0 | 0 | 0 | 0.00406642 |
| pglib_case30_adapted | pcc_failure | GreedyCriticalLoadFirst | 100.476 | 100.476 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | pcc_failure | QUBO/quadratized local search baseline | 100.476 | 100.476 | 1 | 0 | 0 | 0 | 0 | 7.20638 |
| pglib_case30_adapted | pcc_failure | DifferentialEvolutionOptimizer | 138.383 | 151.683 | 0.658525 | 35.9249 | 100.406 | 0.0764499 | 6 | 0.20513 |
| pglib_case30_adapted | pcc_failure | CMPO + QCi Dirac-3 | 141.281 | 180.395 | 0 | 55.6 | 133.976 | 0.102011 | 6 | 22 |
| pglib_case30_adapted | renewable_shortfall | Piecewise-linear MILP baseline | 23.4864 | 23.4864 | 1 | 0 | 0 | 0 | 0 | 0.0457579 |
| pglib_case30_adapted | renewable_shortfall | CMPO-local polynomial search | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 1.75554 |
| pglib_case30_adapted | renewable_shortfall | GPU-parallel random restart baseline | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 0.00408377 |
| pglib_case30_adapted | renewable_shortfall | GreedyCriticalLoadFirst | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 0.303222 |
| pglib_case30_adapted | renewable_shortfall | QUBO/quadratized local search baseline | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 7.46513 |
| pglib_case30_adapted | renewable_shortfall | SLSQPDispatchOptimizer | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 0.335667 |
| pglib_case30_adapted | renewable_shortfall | Stress-only reserve heuristic baseline | 101.654 | 101.654 | 1 | 0 | 0 | 0 | 0 | 0.000106479 |
| pglib_case30_adapted | renewable_shortfall | DifferentialEvolutionOptimizer | 158.58 | 174.474 | 0.64822 | 35.8134 | 101.183 | 0.0793077 | 6 | 0.215984 |
| pglib_case30_adapted | renewable_shortfall | CMPO + QCi Dirac-3 | 129 | 184.602 | 0 | 54.0114 | 130.148 | 0.102011 | 6 | 22 |
| pglib_case30_adapted | storm_forced_islanding | CMPO + QCi Dirac-3 | 15.6182 | 32.7834 | 0 | 62.4838 | 150.563 | 0.102011 | 6 | 22 |
| pglib_case30_adapted | storm_forced_islanding | Stress-only reserve heuristic baseline | 44.6444 | 44.6444 | 1 | 0 | 151.423 | 0.102593 | 0 | 9.6938e-05 |
| pglib_case30_adapted | storm_forced_islanding | Piecewise-linear MILP baseline | 80.9575 | 80.9575 | 1 | 0 | 0 | 0 | 0 | 0.0501115 |
| pglib_case30_adapted | storm_forced_islanding | DifferentialEvolutionOptimizer | 82.3172 | 99.5495 | 0.627779 | 39.254 | 113.777 | 0.077087 | 6 | 0.171746 |
| pglib_case30_adapted | storm_forced_islanding | CMPO-local polynomial search | 106.423 | 117.66 | 1 | 0 | 0 | 0 | 0 | 1.55904 |
| pglib_case30_adapted | storm_forced_islanding | GPU-parallel random restart baseline | 90.5024 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.00414031 |
| pglib_case30_adapted | storm_forced_islanding | GreedyCriticalLoadFirst | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | storm_forced_islanding | IPOPT/Pyomo nonlinear baseline | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.137411 |
| pglib_case30_adapted | storm_forced_islanding | QUBO/quadratized local search baseline | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 6.11043 |
| pglib_case30_adapted | storm_forced_islanding | SLSQPDispatchOptimizer | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.139409 |
| pglib_case57_adapted | demand_surge | Piecewise-linear MILP baseline | 460.417 | 460.417 | 1 | 0 | 0 | 0 | 0 | 0.0224499 |
| pglib_case57_adapted | demand_surge | DifferentialEvolutionOptimizer | 814.127 | 928.495 | 0.67785 | 446.689 | 1155.26 | 0.167428 | 6 | 0.0902412 |
| pglib_case57_adapted | demand_surge | Stress-only reserve heuristic baseline | 1775.24 | 1775.24 | 1 | 0 | 492.067 | 0.0713137 | 0 | 5.53129e-05 |
| pglib_case57_adapted | demand_surge | IPOPT/Pyomo nonlinear baseline | 1852.23 | 1852.23 | 1 | 0 | 0 | 0 | 0 | 0.13616 |
| pglib_case57_adapted | demand_surge | SLSQPDispatchOptimizer | 1852.23 | 1852.23 | 1 | 0 | 0 | 0 | 0 | 0.132865 |
| pglib_case57_adapted | demand_surge | CMPO-local polynomial search | 1853.14 | 1853.14 | 1 | 0 | 0 | 0 | 0 | 0.241068 |
| pglib_case57_adapted | demand_surge | GPU-parallel random restart baseline | 1853.14 | 1853.14 | 1 | 0 | 0 | 0 | 0 | 0.00201315 |
| pglib_case57_adapted | demand_surge | GreedyCriticalLoadFirst | 1853.14 | 1853.14 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case57_adapted | demand_surge | QUBO/quadratized local search baseline | 1854.11 | 1854.11 | 1 | 0 | 0 | 0 | 0 | 2.91418 |
| pglib_case57_adapted | normal | Piecewise-linear MILP baseline | 363.794 | 363.794 | 1 | 0 | 0 | 0 | 0 | 0.0233401 |
| pglib_case57_adapted | normal | DifferentialEvolutionOptimizer | 816.728 | 894.881 | 0.628007 | 431.539 | 1042.91 | 0.184582 | 6 | 0.0910841 |
| pglib_case57_adapted | normal | IPOPT/Pyomo nonlinear baseline | 1177 | 1177 | 1 | 0 | 0 | 0 | 0 | 0.204625 |
| pglib_case57_adapted | normal | SLSQPDispatchOptimizer | 1177 | 1177 | 1 | 0 | 0 | 0 | 0 | 0.209855 |
| pglib_case57_adapted | normal | Stress-only reserve heuristic baseline | 1205.43 | 1205.43 | 1 | 0 | 371.139 | 0.0656873 | 0 | 5.5458e-05 |
| pglib_case57_adapted | normal | CMPO-local polynomial search | 1261.56 | 1261.56 | 1 | 0 | 0 | 0 | 0 | 0.239502 |
| pglib_case57_adapted | normal | GPU-parallel random restart baseline | 1261.56 | 1261.56 | 1 | 0 | 0 | 0 | 0 | 0.00221444 |
| pglib_case57_adapted | normal | GreedyCriticalLoadFirst | 1261.56 | 1261.56 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case57_adapted | normal | QUBO/quadratized local search baseline | 1266.54 | 1266.54 | 1 | 0 | 0 | 0 | 0 | 2.89686 |
| pglib_case57_adapted | pcc_failure | Piecewise-linear MILP baseline | 389.232 | 389.232 | 1 | 0 | 0 | 0 | 0 | 0.0242549 |
| pglib_case57_adapted | pcc_failure | DifferentialEvolutionOptimizer | 869.701 | 952.082 | 0.650757 | 418.429 | 1054.92 | 0.177818 | 6 | 0.0905223 |
| pglib_case57_adapted | pcc_failure | Stress-only reserve heuristic baseline | 1341.65 | 1341.65 | 1 | 0 | 400.315 | 0.0674772 | 0 | 5.5396e-05 |
| pglib_case57_adapted | pcc_failure | IPOPT/Pyomo nonlinear baseline | 1398.27 | 1398.27 | 1 | 0.000237988 | 0.000254626 | 4.29199e-08 | 3 | 0.154834 |
| pglib_case57_adapted | pcc_failure | SLSQPDispatchOptimizer | 1398.27 | 1398.27 | 1 | 0.000237988 | 0.000254626 | 4.29199e-08 | 3 | 0.155566 |
| pglib_case57_adapted | pcc_failure | CMPO-local polynomial search | 1403.03 | 1403.03 | 1 | 0 | 0 | 0 | 0 | 0.239907 |
| pglib_case57_adapted | pcc_failure | GPU-parallel random restart baseline | 1403.03 | 1403.03 | 1 | 0 | 0 | 0 | 0 | 0.0020539 |
| pglib_case57_adapted | pcc_failure | GreedyCriticalLoadFirst | 1403.03 | 1403.03 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case57_adapted | pcc_failure | QUBO/quadratized local search baseline | 1407.25 | 1407.25 | 1 | 0 | 0 | 0 | 0 | 2.89882 |
| pglib_case57_adapted | renewable_shortfall | Piecewise-linear MILP baseline | 395.883 | 395.883 | 1 | 0 | 0 | 0 | 0 | 0.0234522 |
| pglib_case57_adapted | renewable_shortfall | DifferentialEvolutionOptimizer | 848.073 | 957.127 | 0.677824 | 381.029 | 989.846 | 0.171756 | 6 | 0.0891443 |
| pglib_case57_adapted | renewable_shortfall | Stress-only reserve heuristic baseline | 1390.46 | 1390.46 | 1 | 0 | 394.037 | 0.0683724 | 0 | 5.725e-05 |
| pglib_case57_adapted | renewable_shortfall | CMPO-local polynomial search | 1450.71 | 1450.71 | 1 | 0 | 0 | 0 | 0 | 0.237977 |
| pglib_case57_adapted | renewable_shortfall | GPU-parallel random restart baseline | 1450.71 | 1450.71 | 1 | 0 | 0 | 0 | 0 | 0.00224473 |
| pglib_case57_adapted | renewable_shortfall | GreedyCriticalLoadFirst | 1450.71 | 1450.71 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case57_adapted | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 1450.72 | 1450.72 | 1 | 0 | 0 | 0 | 0 | 0.0986136 |
| pglib_case57_adapted | renewable_shortfall | SLSQPDispatchOptimizer | 1450.72 | 1450.72 | 1 | 0 | 0 | 0 | 0 | 0.0908461 |
| pglib_case57_adapted | renewable_shortfall | QUBO/quadratized local search baseline | 1452.24 | 1452.24 | 1 | 0 | 0 | 0 | 0 | 2.90236 |
| pglib_case5_pjm_adapted | demand_surge | Piecewise-linear MILP baseline | 716.705 | 716.705 | 1 | 0 | 17.2878 | 0.00195203 | 0 | 0.0301229 |
| pglib_case5_pjm_adapted | demand_surge | DifferentialEvolutionOptimizer | 788.304 | 898.899 | 0.715737 | 503.777 | 1788.2 | 0.201912 | 6 | 0.0709438 |
| pglib_case5_pjm_adapted | demand_surge | CMPO + QCi Dirac-3 | 918.007 | 1043.75 | 0.775443 | 272.244 | 967.905 | 0.10929 | 6 | 15 |
| pglib_case5_pjm_adapted | demand_surge | Stress-only reserve heuristic baseline | 1433.94 | 1433.94 | 1 | 0 | 1360.48 | 0.153617 | 0 | 5.7562e-05 |
| pglib_case5_pjm_adapted | demand_surge | IPOPT/Pyomo nonlinear baseline | 1645.22 | 1645.22 | 0.999995 | 0.00645788 | 61.0007 | 0.00688781 | 3 | 0.198121 |
| pglib_case5_pjm_adapted | demand_surge | SLSQPDispatchOptimizer | 1645.22 | 1645.22 | 0.999995 | 0.00645788 | 61.0007 | 0.00688781 | 3 | 0.208854 |
| pglib_case5_pjm_adapted | demand_surge | CMPO-local polynomial search | 1650.24 | 1650.24 | 1 | 0 | 66.267 | 0.00748245 | 0 | 0.572155 |
| pglib_case5_pjm_adapted | demand_surge | GPU-parallel random restart baseline | 1650.24 | 1650.24 | 1 | 0 | 66.267 | 0.00748245 | 0 | 0.0021849 |
| pglib_case5_pjm_adapted | demand_surge | GreedyCriticalLoadFirst | 1650.24 | 1650.24 | 1 | 0 | 66.267 | 0.00748245 | 0 | 0 |
| pglib_case5_pjm_adapted | demand_surge | QUBO/quadratized local search baseline | 1655.76 | 1655.76 | 1 | 0 | 79.5994 | 0.00898787 | 0 | 2.36778 |
| pglib_case5_pjm_adapted | normal | Piecewise-linear MILP baseline | 512.911 | 512.911 | 1 | 0 | 0 | 0 | 0 | 0.0322998 |
| pglib_case5_pjm_adapted | normal | DifferentialEvolutionOptimizer | 627.83 | 741.335 | 0.710562 | 395.359 | 1407.88 | 0.194136 | 6 | 0.069685 |
| pglib_case5_pjm_adapted | normal | CMPO + QCi Dirac-3 | 688.569 | 813.194 | 0.83296 | 165.827 | 672.902 | 0.0927885 | 6 | 15 |
| pglib_case5_pjm_adapted | normal | Stress-only reserve heuristic baseline | 1105.67 | 1105.67 | 1 | 0 | 1002.02 | 0.138172 | 0 | 6.02499e-05 |
| pglib_case5_pjm_adapted | normal | QUBO/quadratized local search baseline | 1259.92 | 1259.92 | 1 | 0 | 0 | 0 | 0 | 2.36087 |
| pglib_case5_pjm_adapted | normal | CMPO-local polynomial search | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.567565 |
| pglib_case5_pjm_adapted | normal | GPU-parallel random restart baseline | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0023376 |
| pglib_case5_pjm_adapted | normal | GreedyCriticalLoadFirst | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case5_pjm_adapted | normal | IPOPT/Pyomo nonlinear baseline | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0894795 |
| pglib_case5_pjm_adapted | normal | SLSQPDispatchOptimizer | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0916891 |
| pglib_case5_pjm_adapted | pcc_failure | Piecewise-linear MILP baseline | 577.235 | 577.235 | 1 | 0 | 0 | 0 | 0 | 0.026846 |
| pglib_case5_pjm_adapted | pcc_failure | DifferentialEvolutionOptimizer | 647.384 | 752.954 | 0.714404 | 425.13 | 1538.48 | 0.202044 | 6 | 0.0681624 |
| pglib_case5_pjm_adapted | pcc_failure | CMPO + QCi Dirac-3 | 661.124 | 771.124 | 0.847179 | 159.297 | 666.565 | 0.0875378 | 6 | 15 |
| pglib_case5_pjm_adapted | pcc_failure | Stress-only reserve heuristic baseline | 1111.26 | 1111.26 | 1 | 0 | 1318.91 | 0.173208 | 0 | 5.87085e-05 |
| pglib_case5_pjm_adapted | pcc_failure | QUBO/quadratized local search baseline | 1309.51 | 1309.51 | 1 | 0 | 0 | 0 | 0 | 2.25021 |
| pglib_case5_pjm_adapted | pcc_failure | IPOPT/Pyomo nonlinear baseline | 1364.59 | 1364.59 | 1 | 0 | 0 | 0 | 0 | 0.0920178 |
| pglib_case5_pjm_adapted | pcc_failure | SLSQPDispatchOptimizer | 1364.59 | 1364.59 | 1 | 0 | 0 | 0 | 0 | 0.074665 |
| pglib_case5_pjm_adapted | pcc_failure | CMPO-local polynomial search | 1364.78 | 1364.78 | 1 | 0 | 0 | 0 | 0 | 0.541661 |
| pglib_case5_pjm_adapted | pcc_failure | GPU-parallel random restart baseline | 1364.78 | 1364.78 | 1 | 0 | 0 | 0 | 0 | 0.00237158 |
| pglib_case5_pjm_adapted | pcc_failure | GreedyCriticalLoadFirst | 1364.78 | 1364.78 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case5_pjm_adapted | renewable_shortfall | Piecewise-linear MILP baseline | 554.568 | 554.568 | 1 | 0 | 0 | 0 | 0 | 0.0287779 |
| pglib_case5_pjm_adapted | renewable_shortfall | DifferentialEvolutionOptimizer | 730.153 | 837.5 | 0.707067 | 418.586 | 1468.37 | 0.198507 | 6 | 0.069227 |
| pglib_case5_pjm_adapted | renewable_shortfall | CMPO + QCi Dirac-3 | 788.353 | 905.853 | 0.738224 | 265.073 | 801.735 | 0.108386 | 6 | 15 |
| pglib_case5_pjm_adapted | renewable_shortfall | Stress-only reserve heuristic baseline | 1213 | 1213 | 1 | 0 | 1088.03 | 0.14709 | 0 | 5.77705e-05 |
| pglib_case5_pjm_adapted | renewable_shortfall | QUBO/quadratized local search baseline | 1343.92 | 1343.92 | 1 | 0 | 0 | 0 | 0 | 2.37526 |
| pglib_case5_pjm_adapted | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 1389.01 | 1389.01 | 1 | 8.81137e-05 | 9.42782e-05 | 1.27454e-08 | 3 | 0.161147 |
| pglib_case5_pjm_adapted | renewable_shortfall | SLSQPDispatchOptimizer | 1389.01 | 1389.01 | 1 | 8.81137e-05 | 9.42782e-05 | 1.27454e-08 | 3 | 0.162403 |
| pglib_case5_pjm_adapted | renewable_shortfall | CMPO-local polynomial search | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0.568032 |
| pglib_case5_pjm_adapted | renewable_shortfall | GPU-parallel random restart baseline | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0.00234604 |
| pglib_case5_pjm_adapted | renewable_shortfall | GreedyCriticalLoadFirst | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0 |
| qci_small_synthetic | combined_high_stress | DifferentialEvolutionOptimizer | 10756.2 | 11433.7 | 0.600506 | 2709.91 | 7373.13 | 0.559146 | 4 | 0.0327911 |
| qci_small_synthetic | combined_high_stress | Piecewise-linear MILP baseline | 13887.6 | 14029.9 | 0.916037 | 569.554 | 5544.27 | 0.420453 | 4 | 0.0215135 |
| qci_small_synthetic | combined_high_stress | QUBO/quadratized local search baseline | 15056.9 | 15412.5 | 0.790294 | 1422.51 | 6442.81 | 0.488594 | 4 | 1.00821 |
| qci_small_synthetic | combined_high_stress | Stress-only reserve heuristic baseline | 15474.3 | 15657.9 | 0.8917 | 734.635 | 6997.94 | 0.530693 | 4 | 3.9583e-05 |
| qci_small_synthetic | combined_high_stress | IPOPT/Pyomo nonlinear baseline | 16545.8 | 16851.5 | 0.819733 | 1222.81 | 5975.71 | 0.453172 | 4 | 0.085015 |
| qci_small_synthetic | combined_high_stress | SLSQPDispatchOptimizer | 16545.8 | 16851.5 | 0.819733 | 1222.81 | 5975.71 | 0.453172 | 4 | 0.0829217 |
| qci_small_synthetic | combined_high_stress | CMPO-local polynomial search | 16915.5 | 17221.2 | 0.819733 | 1222.81 | 5955.71 | 0.451655 | 4 | 0.26227 |
| qci_small_synthetic | combined_high_stress | GPU-parallel random restart baseline | 16915.5 | 17221.2 | 0.819733 | 1222.81 | 5955.71 | 0.451655 | 4 | 2.1184 |
| qci_small_synthetic | combined_high_stress | GreedyCriticalLoadFirst | 16915.5 | 17221.2 | 0.819733 | 1222.81 | 5955.71 | 0.451655 | 4 | 0 |
| qci_small_synthetic | combined_high_stress | qBraid GPU-parallel random restart baseline | 16915.5 | 17221.2 | 0.819733 | 1222.81 | 5955.71 | 0.451655 | 4 | 0.00750956 |
| qci_small_synthetic | demand_surge | Piecewise-linear MILP baseline | 1724.09 | 1724.09 | 1 | 0 | 0 | 0 | 0 | 0.0160661 |
| qci_small_synthetic | demand_surge | DifferentialEvolutionOptimizer | 10115.5 | 10563.4 | 0.718509 | 1791.56 | 4505.41 | 0.364152 | 4 | 0.0389033 |
| qci_small_synthetic | demand_surge | IPOPT/Pyomo nonlinear baseline | 17070.5 | 17070.5 | 0.999999 | 0.00585492 | 36.7334 | 0.00296899 | 4 | 0.0995613 |
| qci_small_synthetic | demand_surge | SLSQPDispatchOptimizer | 17070.5 | 17070.5 | 0.999999 | 0.00585492 | 36.7334 | 0.00296899 | 4 | 0.0995963 |
| qci_small_synthetic | demand_surge | Stress-only reserve heuristic baseline | 22339.3 | 22339.3 | 1 | 0 | 3243.51 | 0.262158 | 0 | 3.6334e-05 |
| qci_small_synthetic | demand_surge | CMPO-local polynomial search | 22739.7 | 22739.7 | 1 | 0 | 0 | 0 | 0 | 0.353377 |
| qci_small_synthetic | demand_surge | GPU-parallel random restart baseline | 22739.7 | 22739.7 | 1 | 0 | 0 | 0 | 0 | 2.67791 |
| qci_small_synthetic | demand_surge | GreedyCriticalLoadFirst | 22739.7 | 22739.7 | 1 | 0 | 0 | 0 | 0 | 0 |
| qci_small_synthetic | demand_surge | qBraid GPU-parallel random restart baseline | 22739.7 | 22739.7 | 1 | 0 | 0 | 0 | 0 | 0.00727021 |
| qci_small_synthetic | demand_surge | QUBO/quadratized local search baseline | 22743.5 | 22743.5 | 1 | 0 | 0 | 0 | 0 | 1.24241 |
| qci_small_synthetic | local_generator_failure | Piecewise-linear MILP baseline | 1213.1 | 1213.1 | 1 | 0 | 0 | 0 | 0 | 0.0167353 |
| qci_small_synthetic | local_generator_failure | DifferentialEvolutionOptimizer | 6020.72 | 6387.88 | 0.728835 | 1468.66 | 4001.7 | 0.380054 | 4 | 0.0380156 |
| qci_small_synthetic | local_generator_failure | IPOPT/Pyomo nonlinear baseline | 14769.6 | 14769.6 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 0.0973785 |
| qci_small_synthetic | local_generator_failure | SLSQPDispatchOptimizer | 14769.6 | 14769.6 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 0.0973718 |
| qci_small_synthetic | local_generator_failure | Stress-only reserve heuristic baseline | 15186.4 | 15186.4 | 1 | 0 | 1379.14 | 0.130981 | 0 | 3.34795e-05 |
| qci_small_synthetic | local_generator_failure | CMPO-local polynomial search | 15242.7 | 15242.7 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 0.303869 |
| qci_small_synthetic | local_generator_failure | GPU-parallel random restart baseline | 15242.7 | 15242.7 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 2.44823 |
| qci_small_synthetic | local_generator_failure | GreedyCriticalLoadFirst | 15242.7 | 15242.7 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 0 |
| qci_small_synthetic | local_generator_failure | qBraid GPU-parallel random restart baseline | 15242.7 | 15242.7 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 0.00877542 |
| qci_small_synthetic | local_generator_failure | QUBO/quadratized local search baseline | 15263 | 15263 | 1 | 0 | 46.6636 | 0.00443178 | 0 | 1.1679 |
| qci_small_synthetic | normal | Piecewise-linear MILP baseline | 1084.8 | 1084.8 | 1 | 0 | 0 | 0 | 0 | 0.0242228 |
| qci_small_synthetic | normal | DifferentialEvolutionOptimizer | 8354.51 | 8692.48 | 0.740413 | 1351.87 | 3880.53 | 0.383287 | 4 | 0.0401849 |
| qci_small_synthetic | normal | IPOPT/Pyomo nonlinear baseline | 16122.3 | 16122.3 | 0.999998 | 0.0104195 | 0.0111418 | 1.1005e-06 | 4 | 0.100147 |
| qci_small_synthetic | normal | SLSQPDispatchOptimizer | 16122.3 | 16122.3 | 0.999998 | 0.0104195 | 0.0111418 | 1.1005e-06 | 4 | 0.10178 |
| qci_small_synthetic | normal | Stress-only reserve heuristic baseline | 21602.5 | 21602.5 | 1 | 0 | 928.921 | 0.0917512 | 0 | 4.0854e-05 |
| qci_small_synthetic | normal | CMPO-local polynomial search | 21634.9 | 21634.9 | 1 | 0 | 0 | 0 | 0 | 0.314497 |
| qci_small_synthetic | normal | GPU-parallel random restart baseline | 21634.9 | 21634.9 | 1 | 0 | 0 | 0 | 0 | 2.98183 |
| qci_small_synthetic | normal | GreedyCriticalLoadFirst | 21634.9 | 21634.9 | 1 | 0 | 0 | 0 | 0 | 0 |
| qci_small_synthetic | normal | qBraid GPU-parallel random restart baseline | 21634.9 | 21634.9 | 1 | 0 | 0 | 0 | 0 | 0.00815482 |
| qci_small_synthetic | normal | QUBO/quadratized local search baseline | 21640.1 | 21640.1 | 1 | 0 | 0 | 0 | 0 | 1.19589 |
| qci_small_synthetic | pcc_failure | Piecewise-linear MILP baseline | 8192.88 | 8192.88 | 1 | 0 | 74.1586 | 0.00697598 | 0 | 0.0160739 |
| qci_small_synthetic | pcc_failure | DifferentialEvolutionOptimizer | 9934 | 10280.9 | 0.746255 | 1387.52 | 4113.02 | 0.386905 | 4 | 0.0365929 |
| qci_small_synthetic | pcc_failure | Stress-only reserve heuristic baseline | 15626.4 | 15626.4 | 1 | 0 | 3312.69 | 0.311619 | 0 | 3.4791e-05 |
| qci_small_synthetic | pcc_failure | IPOPT/Pyomo nonlinear baseline | 21777.5 | 21777.5 | 0.999994 | 0.0303059 | 96.3234 | 0.00906099 | 4 | 0.0976387 |
| qci_small_synthetic | pcc_failure | SLSQPDispatchOptimizer | 21777.5 | 21777.5 | 0.999994 | 0.0303059 | 96.3234 | 0.00906099 | 4 | 0.0951075 |
| qci_small_synthetic | pcc_failure | CMPO-local polynomial search | 22440.5 | 22440.5 | 1 | 0 | 74.1586 | 0.00697598 | 0 | 0.295217 |
| qci_small_synthetic | pcc_failure | GPU-parallel random restart baseline | 22440.5 | 22440.5 | 1 | 0 | 74.1586 | 0.00697598 | 0 | 2.43945 |
| qci_small_synthetic | pcc_failure | GreedyCriticalLoadFirst | 22440.5 | 22440.5 | 1 | 0 | 74.1586 | 0.00697598 | 0 | 0 |
| qci_small_synthetic | pcc_failure | qBraid GPU-parallel random restart baseline | 22440.5 | 22440.5 | 1 | 0 | 74.1586 | 0.00697598 | 0 | 0.00802607 |
| qci_small_synthetic | pcc_failure | QUBO/quadratized local search baseline | 22449.5 | 22449.5 | 1 | 0 | 119.647 | 0.011255 | 0 | 1.19757 |
| qci_small_synthetic | renewable_shortfall | Piecewise-linear MILP baseline | 1537.18 | 1537.18 | 1 | 0 | 0 | 0 | 0 | 0.0160486 |
| qci_small_synthetic | renewable_shortfall | DifferentialEvolutionOptimizer | 8979.62 | 9289.94 | 0.766325 | 1241.27 | 3892.15 | 0.376897 | 4 | 0.04518 |
| qci_small_synthetic | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 19620.2 | 19620.2 | 0.999997 | 0.015693 | 0.0167824 | 1.62513e-06 | 4 | 0.100394 |
| qci_small_synthetic | renewable_shortfall | SLSQPDispatchOptimizer | 19620.2 | 19620.2 | 0.999997 | 0.015693 | 0.0167824 | 1.62513e-06 | 4 | 0.0999154 |
| qci_small_synthetic | renewable_shortfall | Stress-only reserve heuristic baseline | 22339.3 | 22339.3 | 1 | 0 | 2829.48 | 0.273993 | 0 | 3.2146e-05 |
| qci_small_synthetic | renewable_shortfall | CMPO-local polynomial search | 22665.2 | 22665.2 | 1 | 0 | 0 | 0 | 0 | 0.332998 |
| qci_small_synthetic | renewable_shortfall | GPU-parallel random restart baseline | 22665.2 | 22665.2 | 1 | 0 | 0 | 0 | 0 | 2.59616 |
| qci_small_synthetic | renewable_shortfall | GreedyCriticalLoadFirst | 22665.2 | 22665.2 | 1 | 0 | 0 | 0 | 0 | 0 |
| qci_small_synthetic | renewable_shortfall | qBraid GPU-parallel random restart baseline | 22665.2 | 22665.2 | 1 | 0 | 0 | 0 | 0 | 0.00782911 |
| qci_small_synthetic | renewable_shortfall | QUBO/quadratized local search baseline | 22672.3 | 22672.3 | 1 | 0 | 0 | 0 | 0 | 1.21961 |
| qci_small_synthetic | restoration | DifferentialEvolutionOptimizer | 7180.44 | 7543.65 | 0.717778 | 1452.84 | 3363.4 | 0.33612 | 4 | 0.0344158 |
| qci_small_synthetic | restoration | Stress-only reserve heuristic baseline | 9506.06 | 9506.06 | 1 | 0 | 3723.35 | 0.372092 | 0 | 3.21461e-05 |
| qci_small_synthetic | restoration | Piecewise-linear MILP baseline | 14135.9 | 14135.9 | 1 | 0 | 18.7044 | 0.00186922 | 0 | 0.0249548 |
| qci_small_synthetic | restoration | IPOPT/Pyomo nonlinear baseline | 22085.4 | 22085.4 | 1 | 0.000990525 | 45.193 | 0.00451634 | 4 | 0.0873615 |
| qci_small_synthetic | restoration | SLSQPDispatchOptimizer | 22085.4 | 22085.4 | 1 | 0.000990525 | 45.193 | 0.00451634 | 4 | 0.0885074 |
| qci_small_synthetic | restoration | CMPO-local polynomial search | 22409 | 22409 | 1 | 0 | 18.7044 | 0.00186922 | 0 | 0.276346 |
| qci_small_synthetic | restoration | GPU-parallel random restart baseline | 22409 | 22409 | 1 | 0 | 18.7044 | 0.00186922 | 0 | 2.22837 |
| qci_small_synthetic | restoration | GreedyCriticalLoadFirst | 22409 | 22409 | 1 | 0 | 18.7044 | 0.00186922 | 0 | 0 |
| qci_small_synthetic | restoration | qBraid GPU-parallel random restart baseline | 22409 | 22409 | 1 | 0 | 18.7044 | 0.00186922 | 0 | 0.00818644 |
| qci_small_synthetic | restoration | QUBO/quadratized local search baseline | 22423 | 22423 | 1 | 0 | 75.9241 | 0.00758744 | 0 | 1.06627 |
| qci_small_synthetic | storm_forced_islanding | Stress-only reserve heuristic baseline | 11363.7 | 11363.7 | 1 | 0 | 5801.53 | 0.485617 | 0 | 3.07295e-05 |
| qci_small_synthetic | storm_forced_islanding | DifferentialEvolutionOptimizer | 15475.1 | 15899.3 | 0.723866 | 1696.9 | 4821.33 | 0.403569 | 4 | 0.0322585 |
| qci_small_synthetic | storm_forced_islanding | QUBO/quadratized local search baseline | 20995.1 | 20996.7 | 0.998954 | 6.42873 | 3336.35 | 0.279269 | 4 | 1.00536 |
| qci_small_synthetic | storm_forced_islanding | Piecewise-linear MILP baseline | 22356 | 22356 | 1 | 0 | 2937.13 | 0.245852 | 0 | 0.0155404 |
| qci_small_synthetic | storm_forced_islanding | IPOPT/Pyomo nonlinear baseline | 22356 | 22357.6 | 0.998951 | 6.44344 | 2940.89 | 0.246167 | 4 | 0.0843736 |
| qci_small_synthetic | storm_forced_islanding | SLSQPDispatchOptimizer | 22356 | 22357.6 | 0.998951 | 6.44344 | 2940.89 | 0.246167 | 4 | 0.0837552 |
| qci_small_synthetic | storm_forced_islanding | CMPO-local polynomial search | 22356 | 22357.6 | 0.998954 | 6.42873 | 2937.13 | 0.245852 | 4 | 0.260785 |
| qci_small_synthetic | storm_forced_islanding | GPU-parallel random restart baseline | 22356 | 22357.6 | 0.998954 | 6.42873 | 2937.13 | 0.245852 | 4 | 2.10513 |
| qci_small_synthetic | storm_forced_islanding | GreedyCriticalLoadFirst | 22356 | 22357.6 | 0.998954 | 6.42873 | 2937.13 | 0.245852 | 4 | 0 |
| qci_small_synthetic | storm_forced_islanding | qBraid GPU-parallel random restart baseline | 22356 | 22357.6 | 0.998954 | 6.42873 | 2937.13 | 0.245852 | 4 | 0.00789553 |
| synthetic_smoke | normal | Piecewise-linear MILP baseline | 353.51 | 353.51 | 1 | 0 | 0 | 0 | 0 | 0.0100886 |
| synthetic_smoke | normal | DifferentialEvolutionOptimizer | 2623.87 | 2681.56 | 0.841513 | 230.766 | 934.136 | 0.0922663 | 4 | 0.00551571 |
| synthetic_smoke | normal | IPOPT/Pyomo nonlinear baseline | 6253.25 | 6253.25 | 1 | 0 | 0 | 0 | 0 | 0.00951954 |
| synthetic_smoke | normal | SLSQPDispatchOptimizer | 6253.25 | 6253.25 | 1 | 0 | 0 | 0 | 0 | 0.00935104 |
| synthetic_smoke | normal | Stress-only reserve heuristic baseline | 7088.71 | 7088.71 | 1 | 0 | 220.382 | 0.0217675 | 0 | 1.93125e-05 |
| synthetic_smoke | normal | CMPO-local polynomial search | 7091.42 | 7091.42 | 1 | 0 | 0 | 0 | 0 | 0.0117354 |
| synthetic_smoke | normal | GPU-parallel random restart baseline | 7092.01 | 7092.01 | 1 | 0 | 0 | 0 | 0 | 0.461736 |
| synthetic_smoke | normal | GreedyCriticalLoadFirst | 7092.01 | 7092.01 | 1 | 0 | 0 | 0 | 0 | 0 |
| synthetic_smoke | normal | QUBO/quadratized local search baseline | 7092.21 | 7092.21 | 1 | 0 | 0 | 0 | 0 | 0.152619 |
| synthetic_smoke | renewable_shortfall | Piecewise-linear MILP baseline | 486.627 | 486.627 | 1 | 0 | 0 | 0 | 0 | 0.00956308 |
| synthetic_smoke | renewable_shortfall | DifferentialEvolutionOptimizer | 2303.26 | 2337.94 | 0.906606 | 138.706 | 926.646 | 0.0897319 | 4 | 0.00506492 |
| synthetic_smoke | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 6918.82 | 6918.82 | 1 | 0 | 0 | 0 | 0 | 0.00924908 |
| synthetic_smoke | renewable_shortfall | SLSQPDispatchOptimizer | 6918.82 | 6918.82 | 1 | 0 | 0 | 0 | 0 | 0.00928773 |
| synthetic_smoke | renewable_shortfall | Stress-only reserve heuristic baseline | 7361.26 | 7361.26 | 1 | 0 | 919.848 | 0.0890736 | 0 | 2.45206e-05 |
| synthetic_smoke | renewable_shortfall | CMPO-local polynomial search | 7461.53 | 7461.53 | 1 | 0 | 0 | 0 | 0 | 0.0116977 |
| synthetic_smoke | renewable_shortfall | GPU-parallel random restart baseline | 7461.53 | 7461.53 | 1 | 0 | 0 | 0 | 0 | 0.0945786 |
| synthetic_smoke | renewable_shortfall | GreedyCriticalLoadFirst | 7461.53 | 7461.53 | 1 | 0 | 0 | 0 | 0 | 0 |
| synthetic_smoke | renewable_shortfall | QUBO/quadratized local search baseline | 7463.72 | 7463.72 | 1 | 0 | 0 | 0 | 0 | 0.142454 |

## table4_native_cubic_vs_qubo

| dataset | payload_count | native_cubic_variable_count_median | native_cubic_term_count_median | native_max_degree | qubo_auxiliary_variable_count_median | qubo_variable_blowup_median | qubo_approximation_error_median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14 | 12 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case14_adapted | nan | nan | nan | nan | 72 | 2.36364 | 7629.09 |
| pglib_case14_ieee | 12 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case30 | 18 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case30_adapted | nan | nan | nan | nan | 72 | 2.36364 | 2726.29 |
| pglib_case30_ieee | 18 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case5 | 8 | 132 | 816 | 3 | nan | nan | nan |
| pglib_case57 | 8 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case57_adapted | nan | nan | nan | nan | 72 | 2.36364 | 322722 |
| pglib_case57_ieee | 8 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case5_pjm | 8 | 132 | 816 | 3 | nan | nan | nan |
| pglib_case5_pjm_adapted | nan | nan | nan | nan | 48 | 2.36364 | 51231.2 |
| phase3_qci_small | 8 | 132 | 821.5 | 3 | nan | nan | nan |
| phase3_qci_small_qbraid_gpu | 8 | 132 | 821.5 | 3 | nan | nan | nan |
| phase3_smoke | 2 | 44 | 272 | 3 | nan | nan | nan |
| qci_small_synthetic | nan | nan | nan | nan | 48 | 2.36364 | 181879 |
| synthetic_smoke | nan | nan | nan | nan | 16 | 2.36364 | 35892.2 |

## table5_resource_usage

| dataset | method_name | runtime_seconds_total | wall_clock_runtime_seconds | repeat_count |
| --- | --- | --- | --- | --- |
| pglib_case14_adapted | CMPO + QCi Dirac-3 | 346410 | 346410 | 1 |
| pglib_case14_adapted | CMPO-local polynomial search | 2530.15 | 2530.15 | 50 |
| pglib_case14_adapted | DifferentialEvolutionOptimizer | 310.935 | 310.935 | 50 |
| pglib_case14_adapted | GPU-parallel random restart baseline | 16.2607 | 16.2607 | 50 |
| pglib_case14_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 721.708 | 721.708 | 50 |
| pglib_case14_adapted | Piecewise-linear MILP baseline | 89.096 | 89.096 | 50 |
| pglib_case14_adapted | QUBO/quadratized local search baseline | 9702.72 | 9702.72 | 50 |
| pglib_case14_adapted | SLSQPDispatchOptimizer | 712.571 | 712.571 | 50 |
| pglib_case14_adapted | Stress-only reserve heuristic baseline | 0.186338 | 0.186338 | 50 |
| pglib_case30_adapted | CMPO + QCi Dirac-3 | 156620 | 156620 | 1 |
| pglib_case30_adapted | CMPO-local polynomial search | 2715.61 | 2715.61 | 50 |
| pglib_case30_adapted | DifferentialEvolutionOptimizer | 327.174 | 327.174 | 50 |
| pglib_case30_adapted | GPU-parallel random restart baseline | 39.0812 | 39.0812 | 50 |
| pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 683.689 | 683.689 | 50 |
| pglib_case30_adapted | Piecewise-linear MILP baseline | 95.1288 | 95.1288 | 50 |
| pglib_case30_adapted | QUBO/quadratized local search baseline | 10557.6 | 10557.6 | 50 |
| pglib_case30_adapted | SLSQPDispatchOptimizer | 725.128 | 725.128 | 50 |
| pglib_case30_adapted | Stress-only reserve heuristic baseline | 0.201415 | 0.201415 | 50 |
| pglib_case57_adapted | CMPO-local polynomial search | 11.6088 | 11.6088 | 3 |
| pglib_case57_adapted | DifferentialEvolutionOptimizer | 4.31909 | 4.31909 | 3 |
| pglib_case57_adapted | GPU-parallel random restart baseline | 6.92005 | 6.92005 | 3 |
| pglib_case57_adapted | GreedyCriticalLoadFirst | 0 | 0 | 3 |
| pglib_case57_adapted | IPOPT/Pyomo nonlinear baseline | 7.2028 | 7.2028 | 3 |
| pglib_case57_adapted | Piecewise-linear MILP baseline | 1.12555 | 1.12555 | 3 |
| pglib_case57_adapted | QUBO/quadratized local search baseline | 140.028 | 140.028 | 3 |
| pglib_case57_adapted | SLSQPDispatchOptimizer | 7.06916 | 7.06916 | 3 |
| pglib_case57_adapted | Stress-only reserve heuristic baseline | 0.00272484 | 0.00272484 | 3 |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 6000 | 6000 | 50 |
| pglib_case5_pjm_adapted | CMPO-local polynomial search | 452.814 | 452.814 | 50 |
| pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 56.8838 | 56.8838 | 50 |
| pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 16.09 | 16.09 | 50 |
| pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 117.218 | 117.218 | 50 |
| pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 24.6453 | 24.6453 | 50 |
| pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 1835.15 | 1835.15 | 50 |
| pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 116.169 | 116.169 | 50 |
| pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 0.0487112 | 0.0487112 | 50 |
| qci_small_synthetic | CMPO-local polynomial search | 4.79872 | 4.79872 | 2 |
| qci_small_synthetic | DifferentialEvolutionOptimizer | 0.596684 | 0.596684 | 2 |
| qci_small_synthetic | GPU-parallel random restart baseline | 39.1909 | 39.1909 | 2 |
| qci_small_synthetic | GreedyCriticalLoadFirst | 0 | 0 | 2 |
| qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 1.50374 | 1.50374 | 2 |
| qci_small_synthetic | Piecewise-linear MILP baseline | 0.302311 | 0.302311 | 2 |
| qci_small_synthetic | QUBO/quadratized local search baseline | 18.2064 | 18.2064 | 2 |
| qci_small_synthetic | SLSQPDispatchOptimizer | 1.49791 | 1.49791 | 2 |
| qci_small_synthetic | Stress-only reserve heuristic baseline | 0.000560126 | 0.000560126 | 2 |
| qci_small_synthetic | qBraid GPU-parallel random restart baseline | 4.44598 | 4.44598 | 50 |
| synthetic_smoke | CMPO-local polynomial search | 0.0468662 | 0.0468662 | 2 |
| synthetic_smoke | DifferentialEvolutionOptimizer | 0.0211613 | 0.0211613 | 2 |
| synthetic_smoke | GPU-parallel random restart baseline | 1.11263 | 1.11263 | 2 |
| synthetic_smoke | GreedyCriticalLoadFirst | 0 | 0 | 2 |
| synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 0.0375373 | 0.0375373 | 2 |
| synthetic_smoke | Piecewise-linear MILP baseline | 0.0393034 | 0.0393034 | 2 |
| synthetic_smoke | QUBO/quadratized local search baseline | 0.590145 | 0.590145 | 2 |
| synthetic_smoke | SLSQPDispatchOptimizer | 0.0372775 | 0.0372775 | 2 |
| synthetic_smoke | Stress-only reserve heuristic baseline | 8.76661e-05 | 8.76661e-05 | 2 |

## win_tie_loss_matrix

| method_name | wins | ties | losses |
| --- | --- | --- | --- |
| CMPO + QCi Dirac-3 | 0 | 1 | 2 |
| CMPO-local polynomial search | 0 | 0 | 6 |
| DifferentialEvolutionOptimizer | 0 | 0 | 6 |
| GPU-parallel random restart baseline | 0 | 0 | 6 |
| GreedyCriticalLoadFirst | 0 | 0 | 6 |
| IPOPT/Pyomo nonlinear baseline | 0 | 0 | 6 |
| Piecewise-linear MILP baseline | 0 | 5 | 1 |
| QUBO/quadratized local search baseline | 0 | 0 | 6 |
| SLSQPDispatchOptimizer | 0 | 0 | 6 |
| Stress-only reserve heuristic baseline | 0 | 0 | 6 |
| qBraid GPU-parallel random restart baseline | 0 | 0 | 1 |

## pareto_frontier

| dataset | method_name | expected_operating_cost | best_cost_by_method | median_cost_by_method | risk_adjusted_cost | total_upgrade_cost | max_fraction_customers_unserved_per_hour | total_hours_critical_infrastructure_unserved | critical_load_served_fraction | critical_energy_not_served_kwh | energy_not_served_kwh | feasibility_after_repair | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | scenario_count | pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | Piecewise-linear MILP baseline | 15495.7 | 26.6986 | 103.876 | 15539.8 | 0 | 0.496372 | 600 | 0.965659 | 23134.8 | 74508.4 | 1 | 89.096 | 0.0411088 | 0.0210873 | 50 | 6 | True |
| pglib_case30_adapted | Piecewise-linear MILP baseline | 13067 | 5.44236 | 23.389 | 13101.4 | 0 | 0.405713 | 600 | 0.969315 | 23933.7 | 63459.9 | 1 | 95.1288 | 0.0462898 | 0.0161598 | 50 | 6 | True |
| pglib_case57_adapted | Piecewise-linear MILP baseline | 3213.45 | 315.415 | 405.118 | 3344.14 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1.12555 | 0.0233855 | 0.0213422 | 3 | 4 | True |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 69379.7 | 165.426 | 748.71 | 69918.4 | 0 | 0.277744 | 1638 | 0.746105 | 137738 | 371486 | 1 | 6000 | 15 | 15 | 50 | 4 | True |
| pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 77465.6 | 383.266 | 582.135 | 77693.5 | 0 | 0.00390406 | 0 | 1 | 0 | 3457.56 | 1 | 24.6453 | 0.0289297 | 0.0208893 | 50 | 4 | True |
| qci_small_synthetic | Piecewise-linear MILP baseline | 10869.1 | 1084.8 | 4958.49 | 16458.1 | 0 | 0.420453 | 8 | 0.989505 | 1139.11 | 17148.5 | 1 | 0.302311 | 0.0164094 | 0.0153801 | 2 | 8 | True |
| synthetic_smoke | Piecewise-linear MILP baseline | 386.789 | 353.51 | 420.068 | 508.446 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0.0393034 | 0.00961394 | 0.00953071 | 2 | 2 | True |

## encoding_efficiency

| benchmark | full_payload_count | qci_fit_payload_count | full_max_variables | qci_fit_max_variables | full_max_degree | qci_fit_max_degree | qci_executable | variable_reduction_fraction | benchmark_dataset | qubo_auxiliary_variable_count_median | qubo_variable_blowup_median | qubo_approximation_error_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case14_adapted | 72 | 2.36364 | 7629.09 |
| pglib_case14_ieee | 12 | 60 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case30_adapted | 72 | 2.36364 | 2726.29 |
| pglib_case30_ieee | 18 | 66 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case57_adapted | 72 | 2.36364 | 322722 |
| pglib_case57_ieee | 8 | 40 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| pglib_case5_pjm | 8 | 0 | 132 | nan | 3 | nan | False | nan | nan | nan | nan | nan |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case5_pjm_adapted | 48 | 2.36364 | 51231.2 |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | qci_small_synthetic | 48 | 2.36364 | 181879 |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | synthetic_smoke | 16 | 2.36364 | 35892.2 |

## qci_repeat_distribution

| dataset | scenario | patch | method_name | repeat_count | best_cost | median_cost | p10_cost | p90_cost | std_cost | best_critical_load_served_fraction | median_runtime_seconds | feasibility_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | demand_surge | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.684 | 74.684 | 74.684 | 74.684 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 109.763 | 139.955 | 116.426 | 157.027 | 18.0526 | 1 | 433 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 69.3662 | 81.0957 | 78.017 | 81.5416 | 2.42344 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 114.71 | 174.2 | 131.82 | 221.013 | 34.0112 | 1 | 434 | 1 |
| pglib_case14_adapted | demand_surge | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 127.638 | 142.31 | 133.634 | 146.843 | 5.94472 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 30.378 | 30.378 | 30.378 | 30.378 | 1.03984e-14 | 0 | 32 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 114.146 | 189.596 | 129.28 | 247.527 | 45.305 | 0.999356 | 432 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 123.57 | 143.396 | 136.597 | 154.866 | 8.54378 | 0 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 173.512 | 235.499 | 179.782 | 285.355 | 41.6596 | 1 | 434 | 1 |
| pglib_case14_adapted | demand_surge | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 120.013 | 127.843 | 123.44 | 132.011 | 3.40076 | 0 | 32 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 74.7443 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 97.0561 | 130.434 | 110.904 | 154.448 | 18.0901 | 1 | 432 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 71.359 | 80.8355 | 76.1891 | 81.5988 | 2.71555 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 96.1432 | 148.51 | 112.473 | 188.42 | 30.3529 | 1 | 433 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 102.678 | 114.221 | 107.163 | 121.78 | 5.62472 | 0 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 30.8901 | 30.8901 | 30.8901 | 30.8901 | 1.02967e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 115.75 | 186.38 | 122.591 | 235.199 | 45.0987 | 1 | 433 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 130.849 | 146.027 | 134.067 | 155.307 | 8.82909 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 187.534 | 253.327 | 197.654 | 291.083 | 33.0126 | 1 | 432 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 116.532 | 129.491 | 125.249 | 132.13 | 3.34045 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.6237 | 74.6237 | 74.6237 | 74.6237 | 2.84217e-14 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 112.381 | 137.66 | 122.458 | 151.392 | 13.2259 | 1 | 433 | 1 |
| pglib_case14_adapted | normal | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 65.5629 | 80.753 | 74.419 | 81.4844 | 3.4125 | 0 | 31 | 1 |
| pglib_case14_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 94.1997 | 174.351 | 131.132 | 205.696 | 31.7173 | 1 | 435 | 1 |
| pglib_case14_adapted | normal | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 135.936 | 143.407 | 136.483 | 149.407 | 4.48941 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 27.3236 | 29.866 | 29.866 | 29.866 | 0.462104 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 116.238 | 176.418 | 123.119 | 221.293 | 39.7112 | 1 | 434 | 1 |
| pglib_case14_adapted | normal | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 120.597 | 144.972 | 134.389 | 160.705 | 10.0399 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 167.286 | 249.851 | 186.58 | 293.776 | 39.3602 | 1 | 433 | 1 |
| pglib_case14_adapted | normal | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 121.768 | 129.024 | 125.214 | 131.891 | 2.66389 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 74.7443 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 62.2093 | 83.9951 | 70.4342 | 91.6804 | 8.11497 | 1 | 433 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 3.34452 | 3.34452 | 3.34452 | 3.34452 | 2.81451e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 68.3567 | 133.461 | 91.4309 | 143.497 | 21.3385 | 1 | 435 | 1 |
| pglib_case14_adapted | pcc_failure | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 129.61 | 141.387 | 134.031 | 148.134 | 5.65698 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 29.9255 | 30.8901 | 30.8901 | 30.8901 | 0.200043 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 116.614 | 154.671 | 118.575 | 219.802 | 46.4038 | 1 | 432 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 124.339 | 144.395 | 133.222 | 155.021 | 8.72942 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 169.257 | 255.679 | 191.517 | 291.532 | 39.0621 | 1 | 434 | 1 |
| pglib_case14_adapted | pcc_failure | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 118.445 | 128.916 | 124.906 | 132.13 | 3.18291 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 75.3232 | 75.3232 | 75.3232 | 75.3232 | 2.84217e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 91.656 | 133.06 | 110.764 | 150.614 | 18.002 | 1 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 73.0435 | 81.0544 | 76.7357 | 82.1494 | 2.64645 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 118.009 | 158.962 | 124.091 | 212.794 | 36.6494 | 1 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 130.82 | 140.601 | 132.116 | 148.011 | 5.42644 | 0 | 32 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 28.766 | 35.8055 | 35.8055 | 35.8055 | 1.26364 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 117.962 | 179.488 | 123.656 | 219.426 | 37.9448 | 0.903252 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 135.516 | 147.874 | 141.486 | 156.288 | 6.42178 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 180.455 | 248.935 | 188.359 | 275.976 | 37.9 | 1 | 435 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 116.425 | 131.215 | 126.599 | 133.276 | 3.71399 | 0 | 32 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 13.7069 | 13.7069 | 13.7069 | 13.7069 | 1.77636e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 17.0446 | 61.7938 | 55.884 | 61.7938 | 13.4016 | 1 | 436 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 3.33774 | 3.33774 | 3.33774 | 3.33774 | 2.23078e-15 | 0 | 32 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 10.9493 | 55.0205 | 11.1787 | 55.0205 | 14.9573 | 1 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 7.61159 | 7.61159 | 7.61159 | 7.61159 | 3.55271e-15 | 0 | 34 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 0.469359 | 0.469359 | 0.469359 | 0.469359 | 1.66533e-16 | 0 | 32 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 13.551 | 71.3906 | 71.3906 | 71.3906 | 14.4026 | 0.421391 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 13.4569 | 13.4569 | 13.4569 | 13.4569 | 7.10543e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 27.0526 | 142.781 | 142.781 | 142.781 | 20.7739 | 0.998418 | 436 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 13.5957 | 13.5957 | 13.5957 | 13.5957 | 8.88178e-15 | 0 | 33 | 1 |
| pglib_case30_adapted | demand_surge | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 94.9814 | 95.587 | 95.587 | 95.587 | 0.131996 | 0 | 21 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.189 | 56.189 | 56.189 | 56.189 | 1.02967e-14 | 0 | 22 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 243.145 | 279.271 | 246.921 | 352.472 | 37.0973 | 1 | 290 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 285.681 | 299.448 | 292.747 | 299.448 | 3.61407 | 0 | 20.5 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 211.215 | 281.717 | 219.147 | 362.581 | 50.9576 | 1 | 288 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 193.012 | 255.006 | 214.763 | 343.789 | 50.4397 | 0.886494 | 287 | 1 |
| pglib_case30_adapted | demand_surge | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0147 | 75.0147 | 75.0147 | 75.0147 | 1.42109e-14 | 0 | 20 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 28.6837 | 29.0055 | 29.0055 | 29.0822 | 0.407232 | 0.0139924 | 21 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 94.4032 | 123.607 | 104.921 | 170.507 | 25.6062 | 0.890853 | 291 | 1 |
| pglib_case30_adapted | demand_surge | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 77.9828 | 77.9828 | 77.9828 | 77.9828 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.6479 | 95.6479 | 95.6479 | 95.6479 | 3.09718e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.2192 | 56.2192 | 56.2192 | 56.2192 | 1.9394e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 141.657 | 181.284 | 159.95 | 207.724 | 21.8525 | 1 | 288 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 125.894 | 148.732 | 145.824 | 148.732 | 3.8609 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 158.944 | 188.654 | 164.975 | 220.765 | 21.0035 | 1 | 287 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 134.581 | 191.957 | 149.621 | 226.755 | 31.8925 | 0.909166 | 291 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0576 | 75.0576 | 75.0576 | 75.0576 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 27.8888 | 29.3868 | 29.3868 | 29.3868 | 0.326479 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 105.991 | 141.374 | 107.183 | 172.681 | 26.4134 | 1 | 291 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 78.0988 | 78.0988 | 78.0988 | 78.0988 | 4.49387e-15 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 94.9205 | 95.5262 | 95.5262 | 95.5262 | 0.131996 | 0 | 22 | 1 |
| pglib_case30_adapted | normal | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 55.6468 | 56.1587 | 56.1587 | 56.1587 | 0.111556 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 198.344 | 277.157 | 222.013 | 334.186 | 48.7546 | 1 | 290 | 1 |
| pglib_case30_adapted | normal | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 270.26 | 299.031 | 285.843 | 299.031 | 7.48847 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 211.957 | 281.905 | 235.997 | 353.248 | 49.7579 | 1 | 289 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 184.028 | 272.251 | 210.237 | 353.24 | 54.5445 | 1 | 289 | 1 |
| pglib_case30_adapted | normal | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 74.9718 | 74.9718 | 74.9718 | 74.9718 | 0 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 28.3024 | 28.6242 | 28.6242 | 28.6242 | 0.171003 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 95.721 | 131.403 | 102.619 | 177.098 | 27.8615 | 1 | 287 | 1 |
| pglib_case30_adapted | normal | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 77.8667 | 77.8667 | 77.8667 | 77.8667 | 1.45618e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.0423 | 95.6479 | 95.5874 | 95.6479 | 0.181692 | 0 | 22 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 6.28969 | 6.28969 | 6.28969 | 6.28969 | 4.53754e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 183.243 | 248.167 | 217.44 | 306.028 | 38.4639 | 1 | 290 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 261.9 | 299.865 | 287.516 | 299.865 | 8.24338 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 191.476 | 286.437 | 234.591 | 354.087 | 50.8984 | 1 | 289 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 188.529 | 272.132 | 197.261 | 334.75 | 50.2552 | 1 | 287 | 1 |
| pglib_case30_adapted | pcc_failure | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0576 | 75.0576 | 75.0576 | 75.0576 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 29.3868 | 29.3868 | 29.3868 | 29.3868 | 3.55271e-15 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 101.196 | 141.281 | 104.599 | 177.799 | 28.426 | 1 | 291 | 1 |
| pglib_case30_adapted | pcc_failure | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 78.0988 | 78.0988 | 78.0988 | 78.0988 | 0 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.6267 | 96.2323 | 96.2323 | 96.2323 | 0.131996 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.5103 | 56.5103 | 56.5103 | 56.5103 | 2.22435e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 197.08 | 283.711 | 219.567 | 337.123 | 44.6746 | 1 | 288 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 275.885 | 303.883 | 292.08 | 303.883 | 6.35082 | 0 | 21.5 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 232.922 | 306.026 | 256.031 | 346.09 | 41.6934 | 1 | 290 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 195.34 | 273.504 | 217.046 | 318.282 | 42.8961 | 1 | 288 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.4695 | 75.4695 | 75.4695 | 75.4695 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 33.0473 | 33.0473 | 33.0473 | 33.0473 | 0 | 0 | 22 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 99.8597 | 129 | 103.727 | 179.239 | 31.341 | 1 | 287 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 79.2126 | 79.2126 | 79.2126 | 79.2126 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 13.7059 | 13.7059 | 13.7059 | 13.7059 | 1.77636e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 6.29343 | 6.29343 | 6.29343 | 6.29343 | 2.8917e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 21.9116 | 108.771 | 108.712 | 108.771 | 18.9246 | 1 | 289 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 15.6182 | 15.6182 | 15.6182 | 15.6182 | 3.55271e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 29.3579 | 137.615 | 29.3579 | 137.615 | 38.6546 | 1 | 290 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 15.8367 | 96.1841 | 15.9283 | 96.1842 | 32.0522 | 0.31067 | 290 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 13.7396 | 13.7396 | 13.7396 | 13.7396 | 0 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 0.349528 | 0.349528 | 0.349528 | 0.349528 | 5.55112e-17 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 71.1271 | 71.1471 | 71.1471 | 71.1471 | 0.00435424 | 0.269727 | 291 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 13.6022 | 13.6022 | 13.6022 | 13.6022 | 1.77636e-15 | 0 | 22 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 295.563 | 378.541 | 313.143 | 680.658 | 149.999 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 1058.7 | 2039.31 | 1167.28 | 2320.41 | 450.848 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 201.512 | 434.669 | 241.847 | 587.316 | 142.296 | 0.948592 | 15 | 1 |
| pglib_case5_pjm_adapted | normal | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 744.894 | 1790.64 | 784.279 | 1907.48 | 448.538 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 165.426 | 458.366 | 228.527 | 512.564 | 99.0758 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 762.793 | 1691.77 | 817.335 | 1974.85 | 504.55 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 230.818 | 486.4 | 270.292 | 589.758 | 139.497 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 830.2 | 1782.91 | 908.578 | 1999.96 | 473.214 | 1 | 15 | 1 |

## challenge_score_summary

| score_mode | dataset | method_name | challenge_score | challenge_rank | best_method_by_challenge_score | qci_minus_best_challenge_score | qci_outcome_by_challenge_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic | pglib_case14_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | SLSQPDispatchOptimizer | 4 | 5 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | CMPO-local polynomial search | 6 | 7 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | GPU-parallel random restart baseline | 7 | 8 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case14_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 9 | qci_loss |
| lexicographic | pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 1 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | Stress-only reserve heuristic baseline | 1 | 2 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | Piecewise-linear MILP baseline | 2 | 3 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | SLSQPDispatchOptimizer | 4 | 5 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | QUBO/quadratized local search baseline | 5 | 6 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | CMPO-local polynomial search | 6 | 7 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | GPU-parallel random restart baseline | 7 | 8 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | CMPO + QCi Dirac-3 | 8 | 9 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case30_adapted | DifferentialEvolutionOptimizer | 9 | 10 | GreedyCriticalLoadFirst | 8 | qci_loss |
| lexicographic | pglib_case57_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | QUBO/quadratized local search baseline | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | Stress-only reserve heuristic baseline | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | SLSQPDispatchOptimizer | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case57_adapted | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 4 | 5 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 5 | 6 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 7 | 8 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 8 | 9 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 9 | 10 | Piecewise-linear MILP baseline | 8 | qci_loss |
| lexicographic | qci_small_synthetic | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | GPU-parallel random restart baseline | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | SLSQPDispatchOptimizer | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | QUBO/quadratized local search baseline | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | qci_small_synthetic | qBraid GPU-parallel random restart baseline | 9 | 10 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 1 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | SLSQPDispatchOptimizer | 2 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | GreedyCriticalLoadFirst | 4 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | GPU-parallel random restart baseline | 5 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | QUBO/quadratized local search baseline | 6 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | Stress-only reserve heuristic baseline | 7 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| lexicographic | synthetic_smoke | DifferentialEvolutionOptimizer | 8 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case14_adapted | Piecewise-linear MILP baseline | 0.00070291 | 1 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | GreedyCriticalLoadFirst | 7.54057 | 2 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 102.156 | 3 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | SLSQPDispatchOptimizer | 102.157 | 4 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | QUBO/quadratized local search baseline | 245.55 | 5 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | CMPO-local polynomial search | 306.359 | 6 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | Stress-only reserve heuristic baseline | 317.87 | 7 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | GPU-parallel random restart baseline | 438.568 | 8 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | DifferentialEvolutionOptimizer | 2269.22 | 9 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case14_adapted | CMPO + QCi Dirac-3 | 2598.21 | 10 | Piecewise-linear MILP baseline | 2598.21 | qci_loss |
| weighted | pglib_case30_adapted | Piecewise-linear MILP baseline | 0.00080799 | 1 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | GreedyCriticalLoadFirst | 9.3165 | 2 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 67.8979 | 3 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | SLSQPDispatchOptimizer | 67.898 | 4 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | QUBO/quadratized local search baseline | 244.633 | 5 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | CMPO-local polynomial search | 412.593 | 6 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | Stress-only reserve heuristic baseline | 467.353 | 7 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | GPU-parallel random restart baseline | 509.503 | 8 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | CMPO + QCi Dirac-3 | 1983.21 | 9 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case30_adapted | DifferentialEvolutionOptimizer | 2551 | 10 | Piecewise-linear MILP baseline | 1983.21 | qci_loss |
| weighted | pglib_case57_adapted | Piecewise-linear MILP baseline | 0.00789695 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | GreedyCriticalLoadFirst | 9.95979 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | GPU-parallel random restart baseline | 9.9605 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | CMPO-local polynomial search | 10.0416 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | QUBO/quadratized local search baseline | 11 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | IPOPT/Pyomo nonlinear baseline | 134.564 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | SLSQPDispatchOptimizer | 134.565 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | Stress-only reserve heuristic baseline | 280.848 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case57_adapted | DifferentialEvolutionOptimizer | 2604.03 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0.645188 | 1 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 30.4402 | 2 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 30.4403 | 3 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | CMPO-local polynomial search | 30.4598 | 4 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 66.8298 | 5 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 278.217 | 6 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 278.217 | 7 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 437.863 | 8 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 1244.87 | 9 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 2603.15 | 10 | Piecewise-linear MILP baseline | 1244.22 | qci_loss |
| weighted | qci_small_synthetic | Piecewise-linear MILP baseline | 0.00732689 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | GreedyCriticalLoadFirst | 148.371 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | CMPO-local polynomial search | 148.494 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | GPU-parallel random restart baseline | 149.371 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | SLSQPDispatchOptimizer | 255.573 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | IPOPT/Pyomo nonlinear baseline | 255.574 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | QUBO/quadratized local search baseline | 350.196 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | Stress-only reserve heuristic baseline | 387.779 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | DifferentialEvolutionOptimizer | 1070.99 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | qci_small_synthetic | qBraid GPU-parallel random restart baseline | 2215.58 | 10 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | Piecewise-linear MILP baseline | 0.067091 | 1 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | IPOPT/Pyomo nonlinear baseline | 9.00903 | 2 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | SLSQPDispatchOptimizer | 9.00955 | 3 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | GreedyCriticalLoadFirst | 9.99855 | 4 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | CMPO-local polynomial search | 10.0795 | 5 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | GPU-parallel random restart baseline | 10.6641 | 6 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | QUBO/quadratized local search baseline | 11 | 7 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | Stress-only reserve heuristic baseline | 472.712 | 8 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
| weighted | synthetic_smoke | DifferentialEvolutionOptimizer | 2603.42 | 9 | Piecewise-linear MILP baseline | nan | inconclusive_no_qci |
