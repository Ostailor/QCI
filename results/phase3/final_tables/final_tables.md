# Phase 3 Final Tables

## table1_qci_vs_best_baselines

| dataset | qci_method | qci_risk_adjusted_cost | best_baseline_method | best_baseline_risk_adjusted_cost | qci_minus_best_baseline | qci_on_pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | CMPO + QCi Dirac-3 | 158.274 | Piecewise-linear MILP baseline | 123.713 | 34.5611 | False |
| pglib_case30_adapted | CMPO + QCi Dirac-3 | 202.487 | Piecewise-linear MILP baseline | 71.9515 | 130.535 | False |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 1432.97 | Piecewise-linear MILP baseline | 742.562 | 690.41 | False |

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
| pglib_case14_adapted | demand_surge | CMPO-V2 + QCi Dirac-3 | 158.435 | 179.339 | 1 | 0 | 7.80293 | 0.0050228 | 0 | 30 |
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
| pglib_case14_adapted | local_generator_failure | CMPO-V2 + QCi Dirac-3 | 147.557 | 164.602 | 1 | 0 | 0 | 0 | 0 | 31.5 |
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
| pglib_case14_adapted | normal | CMPO-V2 + QCi Dirac-3 | 157.809 | 171.512 | 1 | 0 | 0 | 0 | 0 | 31.5 |
| pglib_case14_adapted | normal | DifferentialEvolutionOptimizer | 153.879 | 187.276 | 0.592916 | 91.4205 | 269.627 | 0.211957 | 6 | 0.185072 |
| pglib_case14_adapted | pcc_failure | Piecewise-linear MILP baseline | 94.691 | 94.691 | 1 | 0 | 0 | 0 | 0 | 0.0383667 |
| pglib_case14_adapted | pcc_failure | Stress-only reserve heuristic baseline | 126.672 | 126.672 | 1 | 0 | 248.691 | 0.186189 | 0 | 0.000106437 |
| pglib_case14_adapted | pcc_failure | CMPO + QCi Dirac-3 | 126.453 | 145.189 | 0 | 55.6 | 133.976 | 0.100305 | 6 | 32 |
| pglib_case14_adapted | pcc_failure | CMPO-V2 + QCi Dirac-3 | 144.077 | 160.603 | 1 | 0 | 1e-07 | 7.48677e-11 | 0 | 31 |
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
| pglib_case14_adapted | renewable_shortfall | CMPO-V2 + QCi Dirac-3 | 163.481 | 172.528 | 1 | 0 | 0 | 0 | 0 | 31 |
| pglib_case14_adapted | renewable_shortfall | DifferentialEvolutionOptimizer | 157.229 | 188.279 | 0.578981 | 90.3234 | 265.547 | 0.204657 | 6 | 0.163774 |
| pglib_case14_adapted | storm_forced_islanding | CMPO + QCi Dirac-3 | 13.5957 | 53.6701 | 0 | 62.4838 | 204.683 | 0.136359 | 6 | 33.5 |
| pglib_case14_adapted | storm_forced_islanding | CMPO-V2 + QCi Dirac-3 | 29.9967 | 55.0205 | 0.421391 | 39.5526 | 150.563 | 0.100305 | 6 | 31 |
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
| pglib_case30_adapted | demand_surge | CMPO-V2 + QCi Dirac-3 | 209.77 | 209.77 | 1 | 0 | 69.0892 | 0.0452296 | 0 | 31 |
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
| pglib_case30_adapted | local_generator_failure | CMPO-V2 + QCi Dirac-3 | 148.732 | 162.5 | 1 | 0 | 4.2e-06 | 3.22867e-09 | 0 | 31 |
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
| pglib_case30_adapted | normal | CMPO-V2 + QCi Dirac-3 | 198.889 | 198.889 | 1 | 0 | 3.485e-05 | 2.78619e-08 | 0 | 31 |
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
| pglib_case30_adapted | pcc_failure | CMPO-V2 + QCi Dirac-3 | 203.792 | 203.792 | 1 | 0 | 0.0018932 | 1.4415e-06 | 0 | 31 |
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
| pglib_case30_adapted | renewable_shortfall | CMPO-V2 + QCi Dirac-3 | 204.256 | 204.256 | 1 | 0 | 2.43548 | 0.00190894 | 0 | 32 |
| pglib_case30_adapted | storm_forced_islanding | CMPO + QCi Dirac-3 | 15.6182 | 32.7834 | 0 | 62.4838 | 150.563 | 0.102011 | 6 | 22 |
| pglib_case30_adapted | storm_forced_islanding | Stress-only reserve heuristic baseline | 44.6444 | 44.6444 | 1 | 0 | 151.423 | 0.102593 | 0 | 9.6938e-05 |
| pglib_case30_adapted | storm_forced_islanding | CMPO-V2 + QCi Dirac-3 | 42.5852 | 73.8792 | 0.240564 | 30.522 | 73.547 | 0.04983 | 6 | 32 |
| pglib_case30_adapted | storm_forced_islanding | Piecewise-linear MILP baseline | 80.9575 | 80.9575 | 1 | 0 | 0 | 0 | 0 | 0.0501115 |
| pglib_case30_adapted | storm_forced_islanding | DifferentialEvolutionOptimizer | 82.3172 | 99.5495 | 0.627779 | 39.254 | 113.777 | 0.077087 | 6 | 0.171746 |
| pglib_case30_adapted | storm_forced_islanding | CMPO-local polynomial search | 106.423 | 117.66 | 1 | 0 | 0 | 0 | 0 | 1.55904 |
| pglib_case30_adapted | storm_forced_islanding | GPU-parallel random restart baseline | 90.5024 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.00414031 |
| pglib_case30_adapted | storm_forced_islanding | GreedyCriticalLoadFirst | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case30_adapted | storm_forced_islanding | IPOPT/Pyomo nonlinear baseline | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.137411 |
| pglib_case30_adapted | storm_forced_islanding | QUBO/quadratized local search baseline | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 6.11043 |
| pglib_case30_adapted | storm_forced_islanding | SLSQPDispatchOptimizer | 117.66 | 117.66 | 1 | 0 | 0 | 0 | 0 | 0.139409 |
| pglib_case5_pjm_adapted | demand_surge | Piecewise-linear MILP baseline | 716.705 | 716.705 | 1 | 0 | 17.2878 | 0.00195203 | 0 | 0.0301229 |
| pglib_case5_pjm_adapted | demand_surge | DifferentialEvolutionOptimizer | 788.304 | 898.899 | 0.715737 | 503.777 | 1788.2 | 0.201912 | 6 | 0.0709438 |
| pglib_case5_pjm_adapted | demand_surge | CMPO + QCi Dirac-3 | 918.007 | 1043.75 | 0.775443 | 272.244 | 967.905 | 0.10929 | 6 | 15 |
| pglib_case5_pjm_adapted | demand_surge | CMPO-V2 + QCi Dirac-3 | 1259.59 | 1259.59 | 1 | 0 | 43.5519 | 0.00491761 | 0 | 431.5 |
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
| pglib_case5_pjm_adapted | normal | CMPO-V2 + QCi Dirac-3 | 1140.28 | 1140.28 | 1 | 0 | 0 | 0 | 0 | 433.5 |
| pglib_case5_pjm_adapted | normal | QUBO/quadratized local search baseline | 1259.92 | 1259.92 | 1 | 0 | 0 | 0 | 0 | 2.36087 |
| pglib_case5_pjm_adapted | normal | CMPO-local polynomial search | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.567565 |
| pglib_case5_pjm_adapted | normal | GPU-parallel random restart baseline | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0023376 |
| pglib_case5_pjm_adapted | normal | GreedyCriticalLoadFirst | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0 |
| pglib_case5_pjm_adapted | normal | IPOPT/Pyomo nonlinear baseline | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0894795 |
| pglib_case5_pjm_adapted | normal | SLSQPDispatchOptimizer | 1269.37 | 1269.37 | 1 | 0 | 0 | 0 | 0 | 0.0916891 |
| pglib_case5_pjm_adapted | pcc_failure | Piecewise-linear MILP baseline | 577.235 | 577.235 | 1 | 0 | 0 | 0 | 0 | 0.026846 |
| pglib_case5_pjm_adapted | pcc_failure | DifferentialEvolutionOptimizer | 647.384 | 752.954 | 0.714404 | 425.13 | 1538.48 | 0.202044 | 6 | 0.0681624 |
| pglib_case5_pjm_adapted | pcc_failure | CMPO + QCi Dirac-3 | 661.124 | 771.124 | 0.847179 | 159.297 | 666.565 | 0.0875378 | 6 | 15 |
| pglib_case5_pjm_adapted | pcc_failure | CMPO-V2 + QCi Dirac-3 | 1072.34 | 1072.34 | 1 | 0 | 5e-08 | 6.56633e-12 | 0 | 433 |
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
| pglib_case5_pjm_adapted | renewable_shortfall | CMPO-V2 + QCi Dirac-3 | 1170.97 | 1170.97 | 1 | 0 | 0 | 0 | 0 | 433.5 |
| pglib_case5_pjm_adapted | renewable_shortfall | Stress-only reserve heuristic baseline | 1213 | 1213 | 1 | 0 | 1088.03 | 0.14709 | 0 | 5.77705e-05 |
| pglib_case5_pjm_adapted | renewable_shortfall | QUBO/quadratized local search baseline | 1343.92 | 1343.92 | 1 | 0 | 0 | 0 | 0 | 2.37526 |
| pglib_case5_pjm_adapted | renewable_shortfall | IPOPT/Pyomo nonlinear baseline | 1389.01 | 1389.01 | 1 | 8.81137e-05 | 9.42782e-05 | 1.27454e-08 | 3 | 0.161147 |
| pglib_case5_pjm_adapted | renewable_shortfall | SLSQPDispatchOptimizer | 1389.01 | 1389.01 | 1 | 8.81137e-05 | 9.42782e-05 | 1.27454e-08 | 3 | 0.162403 |
| pglib_case5_pjm_adapted | renewable_shortfall | CMPO-local polynomial search | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0.568032 |
| pglib_case5_pjm_adapted | renewable_shortfall | GPU-parallel random restart baseline | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0.00234604 |
| pglib_case5_pjm_adapted | renewable_shortfall | GreedyCriticalLoadFirst | 1392.18 | 1392.18 | 1 | 0 | 0 | 0 | 0 | 0 |

## table4_native_cubic_vs_qubo

| dataset | payload_count | native_cubic_variable_count_median | native_cubic_term_count_median | native_max_degree | qubo_auxiliary_variable_count_median | qubo_variable_blowup_median | qubo_approximation_error_median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cmpo_v2 | 134 | 66 | 468 | 3 | nan | nan | nan |
| hybrid | 134 | 63 | 206 | 2 | nan | nan | nan |
| pglib_case14 | 12 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case14_adapted | nan | nan | nan | nan | 72 | 2.36364 | 7629.09 |
| pglib_case14_ieee | 12 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case30 | 18 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case30_adapted | nan | nan | nan | nan | 72 | 2.36364 | 2726.29 |
| pglib_case30_ieee | 18 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case5 | 8 | 132 | 816 | 3 | nan | nan | nan |
| pglib_case57 | 8 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case57_ieee | 8 | 198 | 1224 | 3 | nan | nan | nan |
| pglib_case5_pjm | 8 | 132 | 816 | 3 | nan | nan | nan |
| pglib_case5_pjm_adapted | nan | nan | nan | nan | 48 | 2.36364 | 51231.2 |
| phase3_qci_small | 8 | 132 | 821.5 | 3 | nan | nan | nan |
| phase3_qci_small_qbraid_gpu | 8 | 132 | 821.5 | 3 | nan | nan | nan |
| phase3_smoke | 2 | 44 | 272 | 3 | nan | nan | nan |

## table5_resource_usage

| dataset | method_name | runtime_seconds_total | wall_clock_runtime_seconds | repeat_count |
| --- | --- | --- | --- | --- |
| pglib_case14_adapted | CMPO + QCi Dirac-3 | 346410 | 346410 | 1 |
| pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | 344670 | 344670 | 1 |
| pglib_case14_adapted | CMPO-local polynomial search | 1265.07 | 1265.07 | 50 |
| pglib_case14_adapted | DifferentialEvolutionOptimizer | 155.468 | 155.468 | 50 |
| pglib_case14_adapted | GPU-parallel random restart baseline | 8.13036 | 8.13036 | 50 |
| pglib_case14_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 360.854 | 360.854 | 50 |
| pglib_case14_adapted | Piecewise-linear MILP baseline | 44.548 | 44.548 | 50 |
| pglib_case14_adapted | QUBO/quadratized local search baseline | 4851.36 | 4851.36 | 50 |
| pglib_case14_adapted | SLSQPDispatchOptimizer | 356.286 | 356.286 | 50 |
| pglib_case14_adapted | Stress-only reserve heuristic baseline | 0.0931692 | 0.0931692 | 50 |
| pglib_case30_adapted | CMPO + QCi Dirac-3 | 156620 | 156620 | 1 |
| pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | 351510 | 351510 | 1 |
| pglib_case30_adapted | CMPO-local polynomial search | 1357.8 | 1357.8 | 50 |
| pglib_case30_adapted | DifferentialEvolutionOptimizer | 163.587 | 163.587 | 50 |
| pglib_case30_adapted | GPU-parallel random restart baseline | 19.5406 | 19.5406 | 50 |
| pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 341.844 | 341.844 | 50 |
| pglib_case30_adapted | Piecewise-linear MILP baseline | 47.5644 | 47.5644 | 50 |
| pglib_case30_adapted | QUBO/quadratized local search baseline | 5278.82 | 5278.82 | 50 |
| pglib_case30_adapted | SLSQPDispatchOptimizer | 362.564 | 362.564 | 50 |
| pglib_case30_adapted | Stress-only reserve heuristic baseline | 0.100707 | 0.100707 | 50 |
| pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 6000 | 6000 | 50 |
| pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | 103890 | 103890 | 1 |
| pglib_case5_pjm_adapted | CMPO-local polynomial search | 226.407 | 226.407 | 50 |
| pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 28.4419 | 28.4419 | 50 |
| pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 8.045 | 8.045 | 50 |
| pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 0 | 0 | 50 |
| pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 58.609 | 58.609 | 50 |
| pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 12.3226 | 12.3226 | 50 |
| pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 917.575 | 917.575 | 50 |
| pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 58.0844 | 58.0844 | 50 |
| pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 0.0243556 | 0.0243556 | 50 |

## win_tie_loss_matrix

| method_name | wins | ties | losses |
| --- | --- | --- | --- |
| CMPO + QCi Dirac-3 | 0 | 0 | 3 |
| CMPO-V2 + QCi Dirac-3 | 0 | 0 | 3 |
| CMPO-local polynomial search | 0 | 0 | 3 |
| DifferentialEvolutionOptimizer | 0 | 0 | 3 |
| GPU-parallel random restart baseline | 0 | 0 | 3 |
| GreedyCriticalLoadFirst | 0 | 0 | 3 |
| IPOPT/Pyomo nonlinear baseline | 0 | 0 | 3 |
| Piecewise-linear MILP baseline | 0 | 3 | 0 |
| QUBO/quadratized local search baseline | 0 | 0 | 3 |
| SLSQPDispatchOptimizer | 0 | 0 | 3 |
| Stress-only reserve heuristic baseline | 0 | 0 | 3 |

## pareto_frontier

| dataset | method_name | expected_operating_cost | best_cost_by_method | median_cost_by_method | risk_adjusted_cost | total_upgrade_cost | max_fraction_customers_unserved_per_hour | total_hours_critical_infrastructure_unserved | critical_load_served_fraction | critical_energy_not_served_kwh | energy_not_served_kwh | feasibility_after_repair | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | samples_per_payload_median | payload_count | scenario_count | scenario_probability_mass | aggregation | pareto_frontier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | Piecewise-linear MILP baseline | 95.3581 | 26.6986 | 103.876 | 123.713 | 0 | 0.496372 | 0.230769 | 0.984151 | 8.89801 | 28.6571 | 1 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | True |
| pglib_case30_adapted | Piecewise-linear MILP baseline | 53.6081 | 5.44236 | 23.389 | 71.9515 | 0 | 0.405713 | 0.153846 | 0.985838 | 6.13684 | 17.1893 | 1 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | True |
| pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 563.386 | 383.266 | 582.135 | 742.562 | 0 | 0.00390406 | 0 | 1 | 0 | 3.14323 | 1 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | True |

## encoding_efficiency

| benchmark | full_payload_count | qci_fit_payload_count | full_max_variables | qci_fit_max_variables | full_max_degree | qci_fit_max_degree | qci_executable | variable_reduction_fraction | benchmark_dataset | qubo_auxiliary_variable_count_median | qubo_variable_blowup_median | qubo_approximation_error_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case14_adapted | 72 | 2.36364 | 7629.09 |
| pglib_case14_ieee | 12 | 60 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case30_adapted | 72 | 2.36364 | 2726.29 |
| pglib_case30_ieee | 18 | 66 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| pglib_case57_ieee | 8 | 40 | 198 | 132 | 3 | 3 | True | 0.333333 | nan | nan | nan | nan |
| pglib_case5_pjm | 8 | 0 | 132 | nan | 3 | nan | False | nan | nan | nan | nan | nan |
| nan | nan | nan | nan | nan | nan | nan | nan | nan | pglib_case5_pjm_adapted | 48 | 2.36364 | 51231.2 |

## qci_repeat_distribution

| dataset | scenario | patch | method_name | repeat_count | best_cost | median_cost | p10_cost | p90_cost | std_cost | best_critical_load_served_fraction | median_runtime_seconds | feasibility_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | demand_surge | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.684 | 74.684 | 74.684 | 74.684 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.684 | 74.684 | 74.684 | 93.9429 | 9.07874 | 1 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 109.763 | 139.955 | 116.426 | 157.027 | 18.0526 | 1 | 433 | 1 |
| pglib_case14_adapted | demand_surge | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 164.726 | 186.233 | 177.891 | 190.369 | 6.74476 | 1 | 433 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 69.3662 | 81.0957 | 78.017 | 81.5416 | 2.42344 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.9222 | 81.5416 | 77.9073 | 101.381 | 10.5804 | 1 | 29 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 114.71 | 174.2 | 131.82 | 221.013 | 34.0112 | 1 | 434 | 1 |
| pglib_case14_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 219.514 | 248.519 | 236.7 | 260.555 | 9.64096 | 1 | 430 | 1 |
| pglib_case14_adapted | demand_surge | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 127.638 | 142.31 | 133.634 | 146.843 | 5.94472 | 0 | 31 | 1 |
| pglib_case14_adapted | demand_surge | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 134.219 | 148.981 | 135.729 | 179.339 | 17.5518 | 1 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 30.378 | 30.378 | 30.378 | 30.378 | 1.03984e-14 | 0 | 32 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 30.378 | 30.378 | 30.378 | 113.735 | 31.0069 | 1 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 114.146 | 189.596 | 129.28 | 247.527 | 45.305 | 0.999356 | 432 | 1 |
| pglib_case14_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 253.025 | 269.614 | 261.665 | 284.725 | 10.9847 | 1 | 431 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 123.57 | 143.396 | 136.597 | 154.866 | 8.54378 | 0 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 135.816 | 151.744 | 141.259 | 227.356 | 34.0254 | 1 | 30 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 173.512 | 235.499 | 179.782 | 285.355 | 41.6596 | 1 | 434 | 1 |
| pglib_case14_adapted | demand_surge | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 268.757 | 307.937 | 296.582 | 328.878 | 14.1438 | 1 | 433 | 1 |
| pglib_case14_adapted | demand_surge | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 120.013 | 127.843 | 123.44 | 132.011 | 3.40076 | 0 | 32 | 1 |
| pglib_case14_adapted | demand_surge | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 121.026 | 132.011 | 125.983 | 170.141 | 16.4066 | 1 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 74.7443 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 91.1452 | 7.60591 | 1 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 97.0561 | 130.434 | 110.904 | 154.448 | 18.0901 | 1 | 432 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 161.959 | 178.493 | 170.818 | 183.792 | 5.65447 | 1 | 434 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 71.359 | 80.8355 | 76.1891 | 81.5988 | 2.71555 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.0933 | 81.5988 | 79.4231 | 98.4386 | 8.69466 | 1 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 96.1432 | 148.51 | 112.473 | 188.42 | 30.3529 | 1 | 433 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 190.71 | 208.943 | 196.452 | 218.111 | 9.19964 | 1 | 433 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 102.678 | 114.221 | 107.163 | 121.78 | 5.62472 | 0 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 107.384 | 123.545 | 111.111 | 147.557 | 16.2806 | 1 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 30.8901 | 30.8901 | 30.8901 | 30.8901 | 1.02967e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 29.9255 | 30.8901 | 30.8901 | 108.351 | 26.2962 | 1 | 32 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 115.75 | 186.38 | 122.591 | 235.199 | 45.0987 | 1 | 433 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 248.075 | 265.792 | 254.927 | 278.241 | 8.94576 | 1 | 432 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 130.849 | 146.027 | 134.067 | 155.307 | 8.82909 | 0 | 31 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 134.707 | 164.353 | 138.503 | 225.223 | 36.7306 | 1 | 30 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 187.534 | 253.327 | 197.654 | 291.083 | 33.0126 | 1 | 432 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 286.458 | 309.328 | 296.328 | 318.486 | 10.9423 | 1 | 430 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 116.532 | 129.491 | 125.249 | 132.13 | 3.34045 | 0 | 32 | 1 |
| pglib_case14_adapted | local_generator_failure | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 124.407 | 132.13 | 127.541 | 164.602 | 15.1324 | 1 | 30 | 1 |
| pglib_case14_adapted | normal | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.6237 | 74.6237 | 74.6237 | 74.6237 | 2.84217e-14 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.6237 | 74.6237 | 74.6237 | 90.3938 | 7.72577 | 1 | 31 | 1 |
| pglib_case14_adapted | normal | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 112.381 | 137.66 | 122.458 | 151.392 | 13.2259 | 1 | 433 | 1 |
| pglib_case14_adapted | normal | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 151.056 | 175.169 | 169.095 | 180.835 | 6.35364 | 1 | 434 | 1 |
| pglib_case14_adapted | normal | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 65.5629 | 80.753 | 74.419 | 81.4844 | 3.4125 | 0 | 31 | 1 |
| pglib_case14_adapted | normal | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.1413 | 81.5872 | 77.1916 | 97.6438 | 8.76001 | 1 | 31 | 1 |
| pglib_case14_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 94.1997 | 174.351 | 131.132 | 205.696 | 31.7173 | 1 | 435 | 1 |
| pglib_case14_adapted | normal | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 213.228 | 231.8 | 221.261 | 243.471 | 8.41303 | 1 | 434 | 1 |
| pglib_case14_adapted | normal | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 135.936 | 143.407 | 136.483 | 149.407 | 4.48941 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 127.009 | 149.338 | 134.231 | 174.155 | 14.9552 | 1 | 31 | 1 |
| pglib_case14_adapted | normal | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 27.3236 | 29.866 | 29.866 | 29.866 | 0.462104 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 29.866 | 29.866 | 29.866 | 106.68 | 32.0991 | 1 | 32 | 1 |
| pglib_case14_adapted | normal | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 116.238 | 176.418 | 123.119 | 221.293 | 39.7112 | 1 | 434 | 1 |
| pglib_case14_adapted | normal | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 233.753 | 253.04 | 240.282 | 262.207 | 8.65252 | 1 | 434 | 1 |
| pglib_case14_adapted | normal | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 120.597 | 144.972 | 134.389 | 160.705 | 10.0399 | 0 | 32 | 1 |
| pglib_case14_adapted | normal | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 135.523 | 156.017 | 142.114 | 218.789 | 27.8179 | 1 | 31 | 1 |
| pglib_case14_adapted | normal | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 167.286 | 249.851 | 186.58 | 293.776 | 39.3602 | 1 | 433 | 1 |
| pglib_case14_adapted | normal | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 257.043 | 289.829 | 278.066 | 302.76 | 11.1935 | 1 | 433 | 1 |
| pglib_case14_adapted | normal | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 121.768 | 129.024 | 125.214 | 131.891 | 2.66389 | 0 | 31 | 1 |
| pglib_case14_adapted | normal | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 121.695 | 131.891 | 125.689 | 163.114 | 14.9952 | 1 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 74.7443 | 4.26326e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.7443 | 74.7443 | 74.7443 | 91.303 | 7.51035 | 1 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 62.2093 | 83.9951 | 70.4342 | 91.6804 | 8.11497 | 1 | 433 | 1 |
| pglib_case14_adapted | pcc_failure | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 95.3804 | 99.242 | 99.242 | 99.242 | 0.695713 | 1 | 433 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 3.34452 | 3.34452 | 3.34452 | 3.34452 | 2.81451e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 3.34452 | 3.34452 | 3.34452 | 7.93908 | 2.1055 | 1 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 68.3567 | 133.461 | 91.4309 | 143.497 | 21.3385 | 1 | 435 | 1 |
| pglib_case14_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 160.11 | 172.435 | 163.554 | 177.383 | 5.7168 | 1 | 432 | 1 |
| pglib_case14_adapted | pcc_failure | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 129.61 | 141.387 | 134.031 | 148.134 | 5.65698 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 132.232 | 150.948 | 138.496 | 175.509 | 15.775 | 1 | 30 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 29.9255 | 30.8901 | 30.8901 | 30.8901 | 0.200043 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 30.8901 | 30.8901 | 30.8901 | 108.683 | 30.9123 | 1 | 30 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 116.614 | 154.671 | 118.575 | 219.802 | 46.4038 | 1 | 432 | 1 |
| pglib_case14_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 237.31 | 262.089 | 252.826 | 272.728 | 9.46055 | 1 | 431 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 124.339 | 144.395 | 133.222 | 155.021 | 8.72942 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 124.324 | 158.728 | 134.55 | 219.399 | 32.6631 | 1 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 169.257 | 255.679 | 191.517 | 291.532 | 39.0621 | 1 | 434 | 1 |
| pglib_case14_adapted | pcc_failure | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 274.307 | 304.868 | 290.383 | 320.908 | 12.3811 | 1 | 431 | 1 |
| pglib_case14_adapted | pcc_failure | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 118.445 | 128.916 | 124.906 | 132.13 | 3.18291 | 0 | 31 | 1 |
| pglib_case14_adapted | pcc_failure | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 125.269 | 162.986 | 129.173 | 164.914 | 16.5438 | 1 | 30 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 75.3232 | 75.3232 | 75.3232 | 75.3232 | 2.84217e-14 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.3232 | 75.3232 | 75.3232 | 91.4088 | 8.02489 | 1 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 91.656 | 133.06 | 110.764 | 150.614 | 18.002 | 1 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 163.707 | 176.005 | 171.428 | 182.467 | 4.93862 | 1 | 432 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 73.0435 | 81.0544 | 76.7357 | 82.1494 | 2.64645 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.7899 | 82.1494 | 80.9836 | 98.6988 | 8.85543 | 1 | 30 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 118.009 | 158.962 | 124.091 | 212.794 | 36.6494 | 1 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 213.841 | 235.627 | 220.98 | 245.026 | 10.2695 | 1 | 431 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 130.82 | 140.601 | 132.116 | 148.011 | 5.42644 | 0 | 32 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 132.329 | 150.898 | 142.111 | 175.808 | 14.8445 | 1 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 28.766 | 35.8055 | 35.8055 | 35.8055 | 1.26364 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 35.8055 | 35.8863 | 35.8055 | 109.325 | 34.2841 | 1 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 117.962 | 179.488 | 123.656 | 219.426 | 37.9448 | 0.903252 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 241.81 | 260.423 | 246.453 | 267.464 | 8.19402 | 1 | 431 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 135.516 | 147.874 | 141.486 | 156.288 | 6.42178 | 0 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 122.775 | 155.497 | 135.126 | 218.825 | 30.5539 | 1 | 31 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 180.455 | 248.935 | 188.359 | 275.976 | 37.9 | 1 | 435 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 270.779 | 297.432 | 282.094 | 312.149 | 10.7443 | 1 | 434 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 116.425 | 131.215 | 126.599 | 133.276 | 3.71399 | 0 | 32 | 1 |
| pglib_case14_adapted | renewable_shortfall | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 125.141 | 133.276 | 129.965 | 165.124 | 15.3595 | 1 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG | CMPO + QCi Dirac-3 | 30 | 13.7069 | 13.7069 | 13.7069 | 13.7069 | 1.77636e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.7069 | 13.7069 | 13.7069 | 53.0598 | 16.6444 | 1 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG-BUS1_MG | CMPO + QCi Dirac-3 | 30 | 17.0446 | 61.7938 | 55.884 | 61.7938 | 13.4016 | 1 | 436 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS14_MG-BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 61.7938 | 61.7938 | 61.7938 | 61.7938 | 2.36367e-07 | 1 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG | CMPO + QCi Dirac-3 | 30 | 3.33774 | 3.33774 | 3.33774 | 3.33774 | 2.23078e-15 | 0 | 32 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 3.33774 | 3.33774 | 3.33774 | 8.73402 | 2.67405 | 1 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 30 | 10.9493 | 55.0205 | 11.1787 | 55.0205 | 14.9573 | 1 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 55.0205 | 55.0205 | 55.0205 | 55.0205 | 8.48454e-06 | 1 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS2_MG | CMPO + QCi Dirac-3 | 30 | 7.61159 | 7.61159 | 7.61159 | 7.61159 | 3.55271e-15 | 0 | 34 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 7.61159 | 7.61159 | 7.61159 | 46.2865 | 17.7231 | 1 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG | CMPO + QCi Dirac-3 | 30 | 0.469359 | 0.469359 | 0.469359 | 0.469359 | 1.66533e-16 | 0 | 32 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG | CMPO-V2 + QCi Dirac-3 | 30 | 0 | 0.469359 | 0 | 0.469359 | 0.198517 | 0.106388 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 30 | 13.551 | 71.3906 | 71.3906 | 71.3906 | 14.4026 | 0.421391 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 71.3906 | 71.3906 | 71.3906 | 71.3906 | 0.0673146 | 0.421772 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG | CMPO + QCi Dirac-3 | 30 | 13.4569 | 13.4569 | 13.4569 | 13.4569 | 7.10543e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.4569 | 13.4569 | 13.4569 | 71.3906 | 23.1735 | 0.997372 | 31 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG-BUS9_MG | CMPO + QCi Dirac-3 | 30 | 27.0526 | 142.781 | 142.781 | 142.781 | 20.7739 | 0.998418 | 436 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS4_MG-BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 142.781 | 142.781 | 142.781 | 142.781 | 0 | 0.998418 | 435 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS9_MG | CMPO + QCi Dirac-3 | 30 | 13.5957 | 13.5957 | 13.5957 | 13.5957 | 8.88178e-15 | 0 | 33 | 1 |
| pglib_case14_adapted | storm_forced_islanding | BUS9_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.5957 | 13.5957 | 13.5957 | 71.3906 | 25.5579 | 1 | 31 | 1 |
| pglib_case30_adapted | demand_surge | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 94.9814 | 95.587 | 95.587 | 95.587 | 0.131996 | 0 | 21 | 1 |
| pglib_case30_adapted | demand_surge | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 95.587 | 95.587 | 95.587 | 110.064 | 6.7158 | 1 | 31 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.189 | 56.189 | 56.189 | 56.189 | 1.02967e-14 | 0 | 22 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 56.189 | 56.189 | 56.189 | 66.4203 | 4.6886 | 1 | 30 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 243.145 | 279.271 | 246.921 | 352.472 | 37.0973 | 1 | 290 | 1 |
| pglib_case30_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 334.28 | 382.279 | 346.178 | 406.13 | 22.5562 | 1 | 433 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 285.681 | 299.448 | 292.747 | 299.448 | 3.61407 | 0 | 20.5 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 282.289 | 299.448 | 295.097 | 342.341 | 20.8424 | 1 | 31 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 211.215 | 281.717 | 219.147 | 362.581 | 50.9576 | 1 | 288 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 359.753 | 402.489 | 389.243 | 421.749 | 14.8999 | 1 | 434 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 193.012 | 255.006 | 214.763 | 343.789 | 50.4397 | 0.886494 | 287 | 1 |
| pglib_case30_adapted | demand_surge | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 338.374 | 420.974 | 397.533 | 442.878 | 23.6654 | 1 | 433 | 1 |
| pglib_case30_adapted | demand_surge | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0147 | 75.0147 | 75.0147 | 75.0147 | 1.42109e-14 | 0 | 20 | 1 |
| pglib_case30_adapted | demand_surge | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.0147 | 75.0147 | 75.0147 | 88.7157 | 6.54161 | 1 | 31 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 28.6837 | 29.0055 | 29.0055 | 29.0822 | 0.407232 | 0.0139924 | 21 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 29.0055 | 29.0055 | 29.0055 | 102.318 | 29.7573 | 1 | 30 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 94.4032 | 123.607 | 104.921 | 170.507 | 25.6062 | 0.890853 | 291 | 1 |
| pglib_case30_adapted | demand_surge | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 208.371 | 209.77 | 209.498 | 209.77 | 0.347231 | 1 | 433 | 1 |
| pglib_case30_adapted | demand_surge | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 77.9828 | 77.9828 | 77.9828 | 77.9828 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | demand_surge | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 77.9828 | 77.9828 | 77.9828 | 107.453 | 14.3027 | 1 | 31 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.6479 | 95.6479 | 95.6479 | 95.6479 | 3.09718e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 94.4366 | 95.6479 | 95.6479 | 107.976 | 6.07635 | 1 | 31 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.2192 | 56.2192 | 56.2192 | 56.2192 | 1.9394e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 56.2192 | 56.2192 | 56.2192 | 64.9277 | 4.26628 | 1 | 30 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 141.657 | 181.284 | 159.95 | 207.724 | 21.8525 | 1 | 288 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 203.653 | 233.003 | 215.106 | 237.466 | 9.50244 | 1 | 433 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 125.894 | 148.732 | 145.824 | 148.732 | 3.8609 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 139.963 | 173.465 | 148.696 | 173.465 | 12.6202 | 1 | 30 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 158.944 | 188.654 | 164.975 | 220.765 | 21.0035 | 1 | 287 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 230.997 | 254.449 | 245.423 | 260.191 | 7.02096 | 1 | 435 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 134.581 | 191.957 | 149.621 | 226.755 | 31.8925 | 0.909166 | 291 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 236.625 | 268.668 | 260.633 | 272.439 | 8.1351 | 1 | 435 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0576 | 75.0576 | 75.0576 | 75.0576 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.0576 | 75.0576 | 75.0576 | 86.7254 | 4.89551 | 1 | 30 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 27.8888 | 29.3868 | 29.3868 | 29.3868 | 0.326479 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 27.865 | 29.3868 | 29.3868 | 100.567 | 31.5056 | 1 | 30 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 105.991 | 141.374 | 107.183 | 172.681 | 26.4134 | 1 | 291 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 199.739 | 202.915 | 200.661 | 203.658 | 1.06594 | 1 | 432 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 78.0988 | 78.0988 | 78.0988 | 78.0988 | 4.49387e-15 | 0 | 21 | 1 |
| pglib_case30_adapted | local_generator_failure | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 78.0988 | 78.0988 | 78.0988 | 103.196 | 11.7319 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 94.9205 | 95.5262 | 95.5262 | 95.5262 | 0.131996 | 0 | 22 | 1 |
| pglib_case30_adapted | normal | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 93.7205 | 96.2566 | 95.4656 | 107.38 | 5.97671 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 55.6468 | 56.1587 | 56.1587 | 56.1587 | 0.111556 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 56.1587 | 56.1587 | 56.1587 | 64.5233 | 3.33384 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 198.344 | 277.157 | 222.013 | 334.186 | 48.7546 | 1 | 290 | 1 |
| pglib_case30_adapted | normal | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 332.77 | 367.725 | 344.253 | 396.432 | 19.4553 | 1 | 434 | 1 |
| pglib_case30_adapted | normal | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 270.26 | 299.031 | 285.843 | 299.031 | 7.48847 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 280.31 | 299.031 | 290.567 | 337.157 | 19.8762 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 211.957 | 281.905 | 235.997 | 353.248 | 49.7579 | 1 | 289 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 355.455 | 393.601 | 368.324 | 414.59 | 17.1595 | 1 | 435 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 184.028 | 272.251 | 210.237 | 353.24 | 54.5445 | 1 | 289 | 1 |
| pglib_case30_adapted | normal | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 354.4 | 400.152 | 378.336 | 419.829 | 18.3026 | 1 | 436 | 1 |
| pglib_case30_adapted | normal | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 74.9718 | 74.9718 | 74.9718 | 74.9718 | 0 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 74.9718 | 74.9718 | 74.9718 | 86.1908 | 5.55943 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 28.3024 | 28.6242 | 28.6242 | 28.6242 | 0.171003 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 25.1762 | 28.6242 | 28.6242 | 98.9837 | 26.2986 | 1 | 31 | 1 |
| pglib_case30_adapted | normal | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 95.721 | 131.403 | 102.619 | 177.098 | 27.8615 | 1 | 287 | 1 |
| pglib_case30_adapted | normal | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 195.807 | 198.889 | 196.666 | 200.141 | 1.51408 | 1 | 436 | 1 |
| pglib_case30_adapted | normal | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 77.8667 | 77.8667 | 77.8667 | 77.8667 | 1.45618e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | normal | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 77.8667 | 77.8667 | 77.8667 | 101.998 | 11.822 | 1 | 31 | 1 |
| pglib_case30_adapted | pcc_failure | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.0423 | 95.6479 | 95.5874 | 95.6479 | 0.181692 | 0 | 22 | 1 |
| pglib_case30_adapted | pcc_failure | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 95.6479 | 108.095 | 95.6479 | 108.095 | 5.99085 | 1 | 30 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 6.28969 | 6.28969 | 6.28969 | 6.28969 | 4.53754e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 6.28969 | 6.28969 | 6.28969 | 11.7079 | 2.01924 | 1 | 31 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 183.243 | 248.167 | 217.44 | 306.028 | 38.4639 | 1 | 290 | 1 |
| pglib_case30_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 288.951 | 342.351 | 322.099 | 350.218 | 14.7885 | 1 | 435 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 261.9 | 299.865 | 287.516 | 299.865 | 8.24338 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 277.397 | 299.865 | 288.099 | 338.511 | 20.4526 | 1 | 30.5 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 191.476 | 286.437 | 234.591 | 354.087 | 50.8984 | 1 | 289 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 366.506 | 405.736 | 380.945 | 422.535 | 15.4473 | 1 | 435 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 188.529 | 272.132 | 197.261 | 334.75 | 50.2552 | 1 | 287 | 1 |
| pglib_case30_adapted | pcc_failure | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 366.098 | 420.526 | 387.834 | 432.616 | 18.7462 | 1 | 431 | 1 |
| pglib_case30_adapted | pcc_failure | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.0576 | 75.0576 | 75.0576 | 75.0576 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.0576 | 75.0576 | 75.0576 | 86.8376 | 5.66078 | 1 | 31 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 29.3868 | 29.3868 | 29.3868 | 29.3868 | 3.55271e-15 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 29.065 | 29.3868 | 29.3868 | 100.9 | 34.1247 | 1 | 30 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 101.196 | 141.281 | 104.599 | 177.799 | 28.426 | 1 | 291 | 1 |
| pglib_case30_adapted | pcc_failure | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 200.95 | 203.792 | 202.843 | 204.337 | 0.757426 | 1 | 435 | 1 |
| pglib_case30_adapted | pcc_failure | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 78.0988 | 78.0988 | 78.0988 | 78.0988 | 0 | 0 | 21 | 1 |
| pglib_case30_adapted | pcc_failure | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 78.0988 | 78.0988 | 78.0988 | 103.437 | 11.5117 | 1 | 30 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 95.6267 | 96.2323 | 96.2323 | 96.2323 | 0.131996 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 95.6267 | 108.323 | 96.2323 | 108.323 | 5.73151 | 1 | 31 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 56.5103 | 56.5103 | 56.5103 | 56.5103 | 2.22435e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 56.5103 | 56.5103 | 56.5103 | 65.0605 | 4.03062 | 1 | 30 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 197.08 | 283.711 | 219.567 | 337.123 | 44.6746 | 1 | 288 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 309.469 | 373.086 | 348.074 | 395.563 | 20.2194 | 1 | 435 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 275.885 | 303.883 | 292.08 | 303.883 | 6.35082 | 0 | 21.5 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 288.832 | 303.883 | 297.831 | 338.81 | 17.3008 | 1 | 31.5 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 232.922 | 306.026 | 256.031 | 346.09 | 41.6934 | 1 | 290 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 340.167 | 394.092 | 351.945 | 407.324 | 20.6053 | 1 | 434 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 195.34 | 273.504 | 217.046 | 318.282 | 42.8961 | 1 | 288 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 347.19 | 407.672 | 371.254 | 434.038 | 24.0708 | 1 | 434 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 75.4695 | 75.4695 | 75.4695 | 75.4695 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 75.4695 | 86.9129 | 75.4695 | 86.9129 | 5.60611 | 1 | 31 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 33.0473 | 33.0473 | 33.0473 | 33.0473 | 0 | 0 | 22 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 33.0473 | 33.0473 | 33.0473 | 100.977 | 29.8384 | 1 | 31 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 99.8597 | 129 | 103.727 | 179.239 | 31.341 | 1 | 287 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 202.258 | 204.256 | 203.053 | 204.803 | 0.764232 | 1 | 434 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 79.2126 | 79.2126 | 79.2126 | 79.2126 | 1.42109e-14 | 0 | 21 | 1 |
| pglib_case30_adapted | renewable_shortfall | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 79.2126 | 79.2126 | 79.2126 | 103.827 | 10.7399 | 1 | 32 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS12_MG | CMPO + QCi Dirac-3 | 20 | 13.7059 | 13.7059 | 13.7059 | 13.7059 | 1.77636e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS12_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.7059 | 13.7059 | 13.7059 | 42.5852 | 14.3107 | 1 | 32 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG | CMPO + QCi Dirac-3 | 20 | 6.29343 | 6.29343 | 6.29343 | 6.29343 | 2.8917e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG | CMPO-V2 + QCi Dirac-3 | 30 | 6.29343 | 6.29343 | 6.29343 | 12.5872 | 2.9669 | 1 | 32 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 20 | 21.9116 | 108.771 | 108.712 | 108.771 | 18.9246 | 1 | 289 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 104.776 | 108.767 | 108.765 | 108.769 | 0.71634 | 1 | 435 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG | CMPO + QCi Dirac-3 | 40 | 15.6182 | 15.6182 | 15.6182 | 15.6182 | 3.55271e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG | CMPO-V2 + QCi Dirac-3 | 60 | 15.6182 | 15.6182 | 15.6182 | 96.1842 | 39.1711 | 1 | 32 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS30_MG | CMPO + QCi Dirac-3 | 20 | 29.3579 | 137.615 | 29.3579 | 137.615 | 38.6546 | 1 | 290 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 137.56 | 137.615 | 137.615 | 137.615 | 0.00986076 | 1 | 435 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS5_MG | CMPO + QCi Dirac-3 | 20 | 15.8367 | 96.1841 | 15.9283 | 96.1842 | 32.0522 | 0.31067 | 290 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS2_MG-BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 96.1842 | 96.1842 | 96.1842 | 96.1842 | 2.05935e-14 | 0.240564 | 434 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS30_MG | CMPO + QCi Dirac-3 | 20 | 13.7396 | 13.7396 | 13.7396 | 13.7396 | 0 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS30_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.7396 | 13.7396 | 13.7396 | 41.4307 | 13.7219 | 1 | 32 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG | CMPO + QCi Dirac-3 | 20 | 0.349528 | 0.349528 | 0.349528 | 0.349528 | 5.55112e-17 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG | CMPO-V2 + QCi Dirac-3 | 30 | 0 | 0.349528 | 0 | 0.349528 | 0.139811 | 0.079226 | 31 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG-BUS7_MG | CMPO + QCi Dirac-3 | 20 | 71.1271 | 71.1471 | 71.1471 | 71.1471 | 0.00435424 | 0.269727 | 291 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS5_MG-BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 66.0944 | 71.1471 | 71.1471 | 71.1471 | 0.906988 | 0.269727 | 434 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS7_MG | CMPO + QCi Dirac-3 | 20 | 13.6022 | 13.6022 | 13.6022 | 13.6022 | 1.77636e-15 | 0 | 22 | 1 |
| pglib_case30_adapted | storm_forced_islanding | BUS7_MG | CMPO-V2 + QCi Dirac-3 | 30 | 13.6022 | 13.6022 | 13.6022 | 71.1471 | 27.127 | 1 | 31 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 295.563 | 378.541 | 313.143 | 680.658 | 149.999 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 650.962 | 712.815 | 674.87 | 747.923 | 29.0703 | 1 | 433 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 1058.7 | 2039.31 | 1167.28 | 2320.41 | 450.848 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | demand_surge | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 1744.37 | 1957.33 | 1829.81 | 2120.18 | 111.991 | 1 | 430 | 1 |
| pglib_case5_pjm_adapted | normal | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 201.512 | 434.669 | 241.847 | 587.316 | 142.296 | 0.948592 | 15 | 1 |
| pglib_case5_pjm_adapted | normal | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 583.187 | 638.035 | 600.317 | 682.707 | 30.7137 | 1 | 434 | 1 |
| pglib_case5_pjm_adapted | normal | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 744.894 | 1790.64 | 784.279 | 1907.48 | 448.538 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | normal | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 1573.44 | 1705.73 | 1595.4 | 1817.43 | 85.696 | 1 | 433 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 165.426 | 458.366 | 228.527 | 512.564 | 99.0758 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 549.296 | 557.295 | 555.028 | 560.873 | 2.85762 | 1 | 433 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 762.793 | 1691.77 | 817.335 | 1974.85 | 504.55 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | pcc_failure | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 1582.06 | 1767.72 | 1631.67 | 1870.26 | 102.006 | 1 | 433 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO + QCi Dirac-3 | 50 | 230.818 | 486.4 | 270.292 | 589.758 | 139.497 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS1_MG-BUS2_MG | CMPO-V2 + QCi Dirac-3 | 30 | 605.2 | 653.757 | 631.705 | 701.959 | 29.1418 | 1 | 433 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO + QCi Dirac-3 | 50 | 830.2 | 1782.91 | 908.578 | 1999.96 | 473.214 | 1 | 15 | 1 |
| pglib_case5_pjm_adapted | renewable_shortfall | BUS3_MG-BUS4_MG | CMPO-V2 + QCi Dirac-3 | 30 | 1605.86 | 1747.51 | 1654.32 | 1859.24 | 99.1803 | 1 | 434 | 1 |

## challenge_score_summary

| score_mode | dataset | method_name | challenge_score | challenge_rank | best_method_by_challenge_score | qci_minus_best_challenge_score | qci_outcome_by_challenge_score | critical_energy_not_served_kwh | total_hours_critical_infrastructure_unserved | max_fraction_customers_unserved_per_hour | total_energy_not_served | critical_load_served_fraction | feasibility_after_repair | risk_adjusted_cost | expected_operating_cost | runtime | weighted_challenge_score | weighted_challenge_rank | lexicographic_challenge_score | lexicographic_challenge_rank | best_cost_by_method | median_cost_by_method | total_upgrade_cost | energy_not_served_kwh | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | samples_per_payload_median | payload_count | scenario_count | scenario_probability_mass | aggregation | normalized_critical_energy_not_served_kwh | normalized_total_hours_critical_infrastructure_unserved | normalized_max_fraction_customers_unserved_per_hour | normalized_total_energy_not_served | normalized_risk_adjusted_cost | normalized_runtime | infeasibility_penalty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic | pglib_case14_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.89801 | 0.230769 | 0.496372 | 28.6571 | 0.984151 | 1 | 123.713 | 95.3581 | 0.0346349 | nan | nan | 0 | 1 | 26.6986 | 103.876 | 0 | 28.6571 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.89801 | 0.230769 | 0.572846 | 255.146 | 0.984151 | 1 | 158.744 | 124.036 | 9.15419e-05 | nan | nan | 1 | 2 | 39.8837 | 103.403 | 0 | 255.146 | 0.0931692 | 9.75415e-05 | 9.15419e-05 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.90997 | 0.230769 | 0.496372 | 29.2573 | 0.984129 | 1 | 205.115 | 159.223 | 0 | nan | nan | 2 | 3 | 63.4467 | 116.772 | 0 | 29.2573 | 0 | 0 | 0 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | SLSQPDispatchOptimizer | 3 | 4 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.142905 | nan | nan | 3 | 4 | 49.3394 | 115.942 | 0 | 29.6085 | 356.286 | 0.361676 | 0.142905 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 4 | 5 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.157031 | nan | nan | 4 | 5 | 49.3394 | 115.942 | 0 | 29.6085 | 360.854 | 0.351995 | 0.157031 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 8 | qci_loss | 10.014 | 0.230769 | 0.522312 | 30.7549 | 0.982163 | 1 | 205.757 | 159.635 | 4.12812 | nan | nan | 5 | 6 | 64.5159 | 109.147 | 0 | 30.7549 | 4851.36 | 4.8627 | 4.12812 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO-local polynomial search | 6 | 7 | Piecewise-linear MILP baseline | 8 | qci_loss | 11.4178 | 0.230769 | 0.53538 | 31.5094 | 0.979662 | 1 | 204.285 | 158.392 | 1.08133 | nan | nan | 6 | 7 | 63.4467 | 105.973 | 0 | 31.5094 | 1265.07 | 1.29204 | 1.08133 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | GPU-parallel random restart baseline | 7 | 8 | Piecewise-linear MILP baseline | 8 | qci_loss | 13.206 | 0.230769 | 0.573028 | 33.6829 | 0.976477 | 1 | 203.632 | 157.739 | 0.00357137 | nan | nan | 7 | 8 | 63.4467 | 97.4857 | 0 | 33.6829 | 8.13036 | 0.00381432 | 0.00357137 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | 8 | 9 | Piecewise-linear MILP baseline | 8 | qci_loss | 64.2239 | 3.64615 | 0.527719 | 140.955 | 0.404639 | 1 | 189.103 | 148.312 | 29 | nan | nan | 8 | 9 | 0.469359 | 138.029 | 0 | 140.955 | 344670 | 31 | 29 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 8 | qci_loss | 75.9432 | 4.38462 | 0.527719 | 179.8 | 0.367861 | 1 | 158.274 | 124.751 | 30 | nan | nan | 9 | 10 | 0.469359 | 129.962 | 0 | 179.8 | 346410 | 32 | 30 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | DifferentialEvolutionOptimizer | 10 | 11 | Piecewise-linear MILP baseline | 8 | qci_loss | 128.404 | 6 | 0.567061 | 339.118 | 0.580631 | 1 | 196.917 | 153.723 | 0.130723 | nan | nan | 10 | 11 | 60.4848 | 127.051 | 0 | 339.118 | 155.468 | 0.157663 | 0.130723 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 1 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 18.7075 | 0.985838 | 1 | 146.308 | 112.994 | 0 | nan | nan | 0 | 1 | 27.1822 | 101.065 | 0 | 18.7075 | 0 | 0 | 0 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | Stress-only reserve heuristic baseline | 1 | 2 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.520588 | 123.389 | 0.985838 | 1 | 122.268 | 93.1641 | 4.3396e-05 | nan | nan | 1 | 2 | 17.9954 | 81.9601 | 0 | 123.389 | 0.100707 | 0.00010574 | 4.3396e-05 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | Piecewise-linear MILP baseline | 2 | 3 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 17.1893 | 0.985838 | 1 | 71.9515 | 53.6081 | 0.024059 | nan | nan | 2 | 3 | 5.44236 | 23.389 | 0 | 17.1893 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0141961 | nan | nan | 3 | 4 | 25.6382 | 99.8766 | 0 | 18.7078 | 341.844 | 0.296537 | 0.0141961 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | SLSQPDispatchOptimizer | 4 | 5 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0142361 | nan | nan | 4 | 5 | 25.6382 | 99.8766 | 0 | 18.7078 | 362.564 | 0.332888 | 0.0142361 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | QUBO/quadratized local search baseline | 5 | 6 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.5438 | 0.153846 | 0.448658 | 21.6049 | 0.984899 | 1 | 145.077 | 112.07 | 0.782626 | nan | nan | 5 | 6 | 27.1822 | 101.065 | 0 | 21.6049 | 5278.82 | 7.35439 | 0.782626 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO-local polynomial search | 6 | 7 | GreedyCriticalLoadFirst | 8 | qci_loss | 7.37013 | 0.153846 | 0.479241 | 21.4902 | 0.982992 | 1 | 145.193 | 111.88 | 0.175437 | nan | nan | 6 | 7 | 27.1822 | 101.065 | 0 | 21.4902 | 1357.8 | 1.81652 | 0.175437 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | GPU-parallel random restart baseline | 7 | 8 | GreedyCriticalLoadFirst | 8 | qci_loss | 7.77747 | 0.153846 | 0.508286 | 22.5894 | 0.982052 | 1 | 144.785 | 111.472 | 0.00182383 | nan | nan | 7 | 8 | 27.1822 | 97.3558 | 0 | 22.5894 | 19.5406 | 0.00447831 | 0.00182383 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | 8 | 9 | GreedyCriticalLoadFirst | 8 | qci_loss | 47.8945 | 3.58741 | 0.442829 | 110.672 | 0.429245 | 1 | 246.896 | 193.467 | 30 | nan | nan | 8 | 9 | 0.349528 | 108.209 | 0 | 110.672 | 351510 | 31 | 30 | 30 | 30 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | DifferentialEvolutionOptimizer | 9 | 10 | GreedyCriticalLoadFirst | 8 | qci_loss | 67.2514 | 6 | 0.50106 | 191.628 | 0.657384 | 1 | 159.027 | 123.602 | 0.0238047 | nan | nan | 9 | 10 | 27.6043 | 123.714 | 0 | 191.628 | 163.587 | 0.206908 | 0.0238047 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO + QCi Dirac-3 | 10 | 11 | GreedyCriticalLoadFirst | 8 | qci_loss | 72.6759 | 4.99301 | 0.442829 | 166.757 | 0.286621 | 1 | 202.487 | 158.385 | 20 | nan | nan | 10 | 11 | 0.349528 | 96.2082 | 0 | 166.757 | 156620 | 22 | 20 | 20 | 20 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.00390406 | 3.14323 | 1 | 1 | 742.562 | 563.386 | 0.0267492 | nan | nan | 0 | 1 | 383.266 | 582.135 | 0 | 3.14323 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0 | nan | nan | 1 | 2 | 491.074 | 1328.52 | 0 | 12.0485 | 0 | 0 | 0 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.0021564 | nan | nan | 2 | 3 | 491.074 | 1328.52 | 0 | 12.0485 | 8.045 | 0.0023095 | 0.0021564 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.506283 | nan | nan | 3 | 4 | 491.074 | 1328.52 | 0 | 12.0485 | 226.407 | 0.573114 | 0.506283 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | 4 | 5 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0155717 | 12.5371 | 1 | 1 | 1539.7 | 1205.93 | 430 | nan | nan | 4 | 5 | 557.295 | 1209.27 | 0 | 12.5371 | 103890 | 433 | 430 | 30 | 30 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0221664 | 17.8466 | 1 | 1 | 1779.7 | 1368.57 | 2.19171 | nan | nan | 5 | 6 | 491.074 | 1322.78 | 0 | 17.8466 | 917.575 | 2.36803 | 2.19171 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 6 | 7 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.200946 | 1111.64 | 1 | 1 | 1543.86 | 1185.38 | 5.64375e-05 | nan | nan | 6 | 7 | 199.817 | 1156.2 | 0 | 1111.64 | 0.0243556 | 6.00312e-05 | 5.64375e-05 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 7 | 8 | Piecewise-linear MILP baseline | 4 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0520741 | nan | nan | 7 | 8 | 491.074 | 1330.02 | 0 | 11.091 | 58.609 | 0.13214 | 0.0520741 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 8 | 9 | Piecewise-linear MILP baseline | 4 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0565725 | nan | nan | 8 | 9 | 491.074 | 1330.02 | 0 | 11.091 | 58.0844 | 0.132923 | 0.0565725 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 4 | qci_loss | 169.56 | 3 | 0.165217 | 738.799 | 0.840915 | 1 | 1432.97 | 1130.74 | 15 | nan | nan | 9 | 10 | 378.541 | 1089.09 | 0 | 738.799 | 6000 | 15 | 15 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 10 | 11 | Piecewise-linear MILP baseline | 4 | qci_loss | 442.277 | 6 | 0.231811 | 1501.31 | 0.700112 | 1 | 1001.8 | 774.708 | 0.0646265 | nan | nan | 10 | 11 | 249.655 | 753.188 | 0 | 1501.31 | 28.4419 | 0.0698639 | 0.0646265 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| weighted | pglib_case14_adapted | Piecewise-linear MILP baseline | 0.0011545 | 1 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.89801 | 0.230769 | 0.496372 | 28.6571 | 0.984151 | 1 | 123.713 | 95.3581 | 0.0346349 | 0.0011545 | 1 | nan | nan | 26.6986 | 103.876 | 0 | 28.6571 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0 | 0 | 0.0011545 | 0 |
| weighted | pglib_case14_adapted | GreedyCriticalLoadFirst | 10.2152 | 2 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.90997 | 0.230769 | 0.496372 | 29.2573 | 0.984129 | 1 | 205.115 | 159.223 | 0 | 10.2152 | 2 | nan | nan | 63.4467 | 116.772 | 0 | 29.2573 | 0 | 0 | 0 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000100122 | 0 | 0 | 0.00193334 | 0.992178 | 0 | 0 |
| weighted | pglib_case14_adapted | SLSQPDispatchOptimizer | 129.105 | 3 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.142905 | 129.105 | 3 | nan | nan | 49.3394 | 115.942 | 0 | 29.6085 | 356.286 | 0.361676 | 0.142905 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000158801 | 0.08 | 0.0781691 | 0.00306452 | 0.955019 | 0.00476349 | 0 |
| weighted | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 129.105 | 4 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.157031 | 129.105 | 4 | nan | nan | 49.3394 | 115.942 | 0 | 29.6085 | 360.854 | 0.351995 | 0.157031 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000158801 | 0.08 | 0.0781691 | 0.00306452 | 0.955019 | 0.00523437 | 0 |
| weighted | pglib_case14_adapted | QUBO/quadratized local search baseline | 189.351 | 5 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 10.014 | 0.230769 | 0.522312 | 30.7549 | 0.982163 | 1 | 205.757 | 159.635 | 4.12812 | 189.351 | 5 | nan | nan | 64.5159 | 109.147 | 0 | 30.7549 | 4851.36 | 4.8627 | 4.12812 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.00933824 | 0 | 0.338399 | 0.00675719 | 1 | 0.137604 | 0 |
| weighted | pglib_case14_adapted | CMPO-local polynomial search | 286.296 | 6 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 11.4178 | 0.230769 | 0.53538 | 31.5094 | 0.979662 | 1 | 204.285 | 158.392 | 1.08133 | 286.296 | 6 | nan | nan | 63.4467 | 105.973 | 0 | 31.5094 | 1265.07 | 1.29204 | 1.08133 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0210855 | 0 | 0.508871 | 0.00918727 | 0.982053 | 0.0360443 | 0 |
| weighted | pglib_case14_adapted | GPU-parallel random restart baseline | 547.408 | 7 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 13.206 | 0.230769 | 0.573028 | 33.6829 | 0.976477 | 1 | 203.632 | 157.739 | 0.00357137 | 547.408 | 7 | nan | nan | 63.4467 | 97.4857 | 0 | 33.6829 | 8.13036 | 0.00381432 | 0.00357137 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.036048 | 0 | 1 | 0.0161883 | 0.974096 | 0.000119046 | 0 |
| weighted | pglib_case14_adapted | Stress-only reserve heuristic baseline | 576.037 | 8 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.89801 | 0.230769 | 0.572846 | 255.146 | 0.984151 | 1 | 158.744 | 124.036 | 9.15419e-05 | 576.037 | 8 | nan | nan | 39.8837 | 103.403 | 0 | 255.146 | 0.0931692 | 9.75415e-05 | 9.15419e-05 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.997629 | 0.729525 | 0.426986 | 3.0514e-06 | 0 |
| weighted | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | 1304.53 | 9 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 64.2239 | 3.64615 | 0.527719 | 140.955 | 0.404639 | 1 | 189.103 | 148.312 | 29 | 1304.53 | 9 | nan | nan | 0.469359 | 138.029 | 0 | 140.955 | 344670 | 31 | 29 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.462956 | 0.592 | 0.408932 | 0.361713 | 0.797011 | 0.966667 | 0 |
| weighted | pglib_case14_adapted | CMPO + QCi Dirac-3 | 1539.38 | 10 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 75.9432 | 4.38462 | 0.527719 | 179.8 | 0.367861 | 1 | 158.274 | 124.751 | 30 | 1539.38 | 10 | nan | nan | 0.469359 | 129.962 | 0 | 179.8 | 346410 | 32 | 30 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.561021 | 0.72 | 0.408932 | 0.486833 | 0.42125 | 1 | 0 |
| weighted | pglib_case14_adapted | DifferentialEvolutionOptimizer | 2570.01 | 11 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 128.404 | 6 | 0.567061 | 339.118 | 0.580631 | 1 | 196.917 | 153.723 | 0.130723 | 2570.01 | 11 | nan | nan | 60.4848 | 127.051 | 0 | 339.118 | 155.468 | 0.157663 | 0.130723 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 1 | 0.922158 | 1 | 0.89225 | 0.00435742 | 0 |
| weighted | pglib_case30_adapted | Piecewise-linear MILP baseline | 0.000801966 | 1 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 17.1893 | 0.985838 | 1 | 71.9515 | 53.6081 | 0.024059 | 0.000801966 | 1 | nan | nan | 5.44236 | 23.389 | 0 | 17.1893 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1.33482e-17 | 0 | 0 | 0 | 0 | 0.000801966 | 0 |
| weighted | pglib_case30_adapted | GreedyCriticalLoadFirst | 5.12061 | 2 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 18.7075 | 0.985838 | 1 | 146.308 | 112.994 | 0 | 5.12061 | 2 | nan | nan | 27.1822 | 101.065 | 0 | 18.7075 | 0 | 0 | 0 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0.00870344 | 0.425027 | 0 | 0 |
| weighted | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 57.6357 | 3 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0141961 | 57.6357 | 3 | nan | nan | 25.6382 | 99.8766 | 0 | 18.7078 | 341.844 | 0.296537 | 0.0141961 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 5.26444e-06 | 0.0526316 | 5.52575e-05 | 0.00870543 | 0.410025 | 0.000473203 | 0 |
| weighted | pglib_case30_adapted | SLSQPDispatchOptimizer | 57.6357 | 4 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0142361 | 57.6357 | 4 | nan | nan | 25.6382 | 99.8766 | 0 | 18.7078 | 362.564 | 0.332888 | 0.0142361 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 5.26444e-06 | 0.0526316 | 5.52575e-05 | 0.00870543 | 0.410025 | 0.000474536 | 0 |
| weighted | pglib_case30_adapted | QUBO/quadratized local search baseline | 199.773 | 5 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.5438 | 0.153846 | 0.448658 | 21.6049 | 0.984899 | 1 | 145.077 | 112.07 | 0.782626 | 199.773 | 5 | nan | nan | 27.1822 | 101.065 | 0 | 21.6049 | 5278.82 | 7.35439 | 0.782626 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.00611604 | 0 | 0.373839 | 0.0253131 | 0.417995 | 0.0260875 | 0 |
| weighted | pglib_case30_adapted | CMPO-local polynomial search | 345.228 | 6 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 7.37013 | 0.153846 | 0.479241 | 21.4902 | 0.982992 | 1 | 145.193 | 111.88 | 0.175437 | 345.228 | 6 | nan | nan | 27.1822 | 101.065 | 0 | 21.4902 | 1357.8 | 1.81652 | 0.175437 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0185348 | 0 | 0.640069 | 0.0246556 | 0.418658 | 0.00584789 | 0 |
| weighted | pglib_case30_adapted | GPU-parallel random restart baseline | 478.373 | 7 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 7.77747 | 0.153846 | 0.508286 | 22.5894 | 0.982052 | 1 | 144.785 | 111.472 | 0.00182383 | 478.373 | 7 | nan | nan | 27.1822 | 97.3558 | 0 | 22.5894 | 19.5406 | 0.00447831 | 0.00182383 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0246565 | 0 | 0.892915 | 0.0309571 | 0.416324 | 6.07944e-05 | 0 |
| weighted | pglib_case30_adapted | Stress-only reserve heuristic baseline | 563.757 | 8 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.520588 | 123.389 | 0.985838 | 1 | 122.268 | 93.1641 | 4.3396e-05 | 563.757 | 8 | nan | nan | 17.9954 | 81.9601 | 0 | 123.389 | 0.100707 | 0.00010574 | 4.3396e-05 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 1 | 0.608808 | 0.287613 | 1.44653e-06 | 0 |
| weighted | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | 1441.03 | 9 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 47.8945 | 3.58741 | 0.442829 | 110.672 | 0.429245 | 1 | 246.896 | 193.467 | 30 | 1441.03 | 9 | nan | nan | 0.349528 | 108.209 | 0 | 110.672 | 351510 | 31 | 30 | 30 | 30 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.627566 | 0.587321 | 0.323101 | 0.535908 | 1 | 1 | 0 |
| weighted | pglib_case30_adapted | CMPO + QCi Dirac-3 | 2083.17 | 10 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 72.6759 | 4.99301 | 0.442829 | 166.757 | 0.286621 | 1 | 202.487 | 158.385 | 20 | 2083.17 | 10 | nan | nan | 0.349528 | 96.2082 | 0 | 166.757 | 156620 | 22 | 20 | 20 | 20 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 0.827751 | 0.323101 | 0.857424 | 0.746155 | 0.666667 | 0 |
| weighted | pglib_case30_adapted | DifferentialEvolutionOptimizer | 2438.46 | 11 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 67.2514 | 6 | 0.50106 | 191.628 | 0.657384 | 1 | 159.027 | 123.602 | 0.0238047 | 2438.46 | 11 | nan | nan | 27.6043 | 123.714 | 0 | 191.628 | 163.587 | 0.206908 | 0.0238047 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.918477 | 1 | 0.830013 | 1 | 0.49773 | 0.00079349 | 0 |
| weighted | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 6.22075e-05 | 1 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.00390406 | 3.14323 | 1 | 1 | 742.562 | 563.386 | 0.0267492 | 6.22075e-05 | 1 | nan | nan | 383.266 | 582.135 | 0 | 3.14323 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0 | 0 | 6.22075e-05 | 0 |
| weighted | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 34.8606 | 2 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0 | 34.8606 | 2 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 0 | 0 | 0 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 0 | 0 |
| weighted | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 34.8606 | 3 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.0021564 | 34.8606 | 3 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 8.045 | 0.0023095 | 0.0021564 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 5.01487e-06 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO-local polynomial search | 34.8618 | 4 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.506283 | 34.8618 | 4 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 226.407 | 0.573114 | 0.506283 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 0.0011774 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | 34.892 | 5 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0155717 | 12.5371 | 1 | 1 | 1539.7 | 1205.93 | 430 | 34.892 | 5 | nan | nan | 557.295 | 1209.27 | 0 | 12.5371 | 103890 | 433 | 430 | 30 | 30 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0511947 | 0.00627023 | 0.766759 | 1 | 0 |
| weighted | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 51.028 | 6 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0221664 | 17.8466 | 1 | 1 | 1779.7 | 1368.57 | 2.19171 | 51.028 | 6 | nan | nan | 491.074 | 1322.78 | 0 | 17.8466 | 917.575 | 2.36803 | 2.19171 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0801307 | 0.00981425 | 0.997616 | 0.00509699 | 0 |
| weighted | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 213.982 | 7 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0520741 | 213.982 | 7 | nan | nan | 491.074 | 1330.02 | 0 | 11.091 | 58.609 | 0.13214 | 0.0520741 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 2.69103e-06 | 0.181818 | 0.0433141 | 0.00530503 | 0.997345 | 0.000121103 | 0 |
| weighted | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 213.982 | 8 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0565725 | 213.982 | 8 | nan | nan | 491.074 | 1330.02 | 0 | 11.091 | 58.0844 | 0.132923 | 0.0565725 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 2.69103e-06 | 0.181818 | 0.0433141 | 0.00530503 | 0.997345 | 0.000131564 | 0 |
| weighted | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 513.984 | 9 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.200946 | 1111.64 | 1 | 1 | 1543.86 | 1185.38 | 5.64375e-05 | 513.984 | 9 | nan | nan | 199.817 | 1156.2 | 0 | 1111.64 | 0.0243556 | 6.00312e-05 | 5.64375e-05 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.864572 | 0.739903 | 0.770766 | 1.3125e-07 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 1293.06 | 10 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 169.56 | 3 | 0.165217 | 738.799 | 0.840915 | 1 | 1432.97 | 1130.74 | 15 | 1293.06 | 10 | nan | nan | 378.541 | 1089.09 | 0 | 738.799 | 6000 | 15 | 15 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0.383381 | 0.5 | 0.707802 | 0.491038 | 0.664102 | 0.0348837 | 0 |
| weighted | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 2602.49 | 11 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 442.277 | 6 | 0.231811 | 1501.31 | 0.700112 | 1 | 1001.8 | 774.708 | 0.0646265 | 2602.49 | 11 | nan | nan | 249.655 | 753.188 | 0 | 1501.31 | 28.4419 | 0.0698639 | 0.0646265 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 1 | 1 | 1 | 0.249359 | 0.000150294 | 0 |

## final_challenge_score_table

| score_mode | dataset | method_name | challenge_score | challenge_rank | best_method_by_challenge_score | qci_minus_best_challenge_score | qci_outcome_by_challenge_score | critical_energy_not_served_kwh | total_hours_critical_infrastructure_unserved | max_fraction_customers_unserved_per_hour | total_energy_not_served | critical_load_served_fraction | feasibility_after_repair | risk_adjusted_cost | expected_operating_cost | runtime | weighted_challenge_score | weighted_challenge_rank | lexicographic_challenge_score | lexicographic_challenge_rank | best_cost_by_method | median_cost_by_method | total_upgrade_cost | energy_not_served_kwh | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | samples_per_payload_median | payload_count | scenario_count | scenario_probability_mass | aggregation | normalized_critical_energy_not_served_kwh | normalized_total_hours_critical_infrastructure_unserved | normalized_max_fraction_customers_unserved_per_hour | normalized_total_energy_not_served | normalized_risk_adjusted_cost | normalized_runtime | infeasibility_penalty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic | pglib_case14_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.89801 | 0.230769 | 0.496372 | 28.6571 | 0.984151 | 1 | 123.713 | 95.3581 | 0.0346349 | nan | nan | 0 | 1 | 26.6986 | 103.876 | 0 | 28.6571 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | Stress-only reserve heuristic baseline | 1 | 2 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.89801 | 0.230769 | 0.572846 | 255.146 | 0.984151 | 1 | 158.744 | 124.036 | 9.15419e-05 | nan | nan | 1 | 2 | 39.8837 | 103.403 | 0 | 255.146 | 0.0931692 | 9.75415e-05 | 9.15419e-05 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | GreedyCriticalLoadFirst | 2 | 3 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.90997 | 0.230769 | 0.496372 | 29.2573 | 0.984129 | 1 | 205.115 | 159.223 | 0 | nan | nan | 2 | 3 | 63.4467 | 116.772 | 0 | 29.2573 | 0 | 0 | 0 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | SLSQPDispatchOptimizer | 3 | 4 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.142905 | nan | nan | 3 | 4 | 49.3394 | 115.942 | 0 | 29.6085 | 356.286 | 0.361676 | 0.142905 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 4 | 5 | Piecewise-linear MILP baseline | 8 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.157031 | nan | nan | 4 | 5 | 49.3394 | 115.942 | 0 | 29.6085 | 360.854 | 0.351995 | 0.157031 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 8 | qci_loss | 10.014 | 0.230769 | 0.522312 | 30.7549 | 0.982163 | 1 | 205.757 | 159.635 | 4.12812 | nan | nan | 5 | 6 | 64.5159 | 109.147 | 0 | 30.7549 | 4851.36 | 4.8627 | 4.12812 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO-local polynomial search | 6 | 7 | Piecewise-linear MILP baseline | 8 | qci_loss | 11.4178 | 0.230769 | 0.53538 | 31.5094 | 0.979662 | 1 | 204.285 | 158.392 | 1.08133 | nan | nan | 6 | 7 | 63.4467 | 105.973 | 0 | 31.5094 | 1265.07 | 1.29204 | 1.08133 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | GPU-parallel random restart baseline | 7 | 8 | Piecewise-linear MILP baseline | 8 | qci_loss | 13.206 | 0.230769 | 0.573028 | 33.6829 | 0.976477 | 1 | 203.632 | 157.739 | 0.00357137 | nan | nan | 7 | 8 | 63.4467 | 97.4857 | 0 | 33.6829 | 8.13036 | 0.00381432 | 0.00357137 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | 8 | 9 | Piecewise-linear MILP baseline | 8 | qci_loss | 64.2239 | 3.64615 | 0.527719 | 140.955 | 0.404639 | 1 | 189.103 | 148.312 | 29 | nan | nan | 8 | 9 | 0.469359 | 138.029 | 0 | 140.955 | 344670 | 31 | 29 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 8 | qci_loss | 75.9432 | 4.38462 | 0.527719 | 179.8 | 0.367861 | 1 | 158.274 | 124.751 | 30 | nan | nan | 9 | 10 | 0.469359 | 129.962 | 0 | 179.8 | 346410 | 32 | 30 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case14_adapted | DifferentialEvolutionOptimizer | 10 | 11 | Piecewise-linear MILP baseline | 8 | qci_loss | 128.404 | 6 | 0.567061 | 339.118 | 0.580631 | 1 | 196.917 | 153.723 | 0.130723 | nan | nan | 10 | 11 | 60.4848 | 127.051 | 0 | 339.118 | 155.468 | 0.157663 | 0.130723 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | GreedyCriticalLoadFirst | 0 | 1 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 18.7075 | 0.985838 | 1 | 146.308 | 112.994 | 0 | nan | nan | 0 | 1 | 27.1822 | 101.065 | 0 | 18.7075 | 0 | 0 | 0 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | Stress-only reserve heuristic baseline | 1 | 2 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.520588 | 123.389 | 0.985838 | 1 | 122.268 | 93.1641 | 4.3396e-05 | nan | nan | 1 | 2 | 17.9954 | 81.9601 | 0 | 123.389 | 0.100707 | 0.00010574 | 4.3396e-05 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | Piecewise-linear MILP baseline | 2 | 3 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 17.1893 | 0.985838 | 1 | 71.9515 | 53.6081 | 0.024059 | nan | nan | 2 | 3 | 5.44236 | 23.389 | 0 | 17.1893 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 3 | 4 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0141961 | nan | nan | 3 | 4 | 25.6382 | 99.8766 | 0 | 18.7078 | 341.844 | 0.296537 | 0.0141961 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | SLSQPDispatchOptimizer | 4 | 5 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0142361 | nan | nan | 4 | 5 | 25.6382 | 99.8766 | 0 | 18.7078 | 362.564 | 0.332888 | 0.0142361 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | QUBO/quadratized local search baseline | 5 | 6 | GreedyCriticalLoadFirst | 8 | qci_loss | 6.5438 | 0.153846 | 0.448658 | 21.6049 | 0.984899 | 1 | 145.077 | 112.07 | 0.782626 | nan | nan | 5 | 6 | 27.1822 | 101.065 | 0 | 21.6049 | 5278.82 | 7.35439 | 0.782626 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO-local polynomial search | 6 | 7 | GreedyCriticalLoadFirst | 8 | qci_loss | 7.37013 | 0.153846 | 0.479241 | 21.4902 | 0.982992 | 1 | 145.193 | 111.88 | 0.175437 | nan | nan | 6 | 7 | 27.1822 | 101.065 | 0 | 21.4902 | 1357.8 | 1.81652 | 0.175437 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | GPU-parallel random restart baseline | 7 | 8 | GreedyCriticalLoadFirst | 8 | qci_loss | 7.77747 | 0.153846 | 0.508286 | 22.5894 | 0.982052 | 1 | 144.785 | 111.472 | 0.00182383 | nan | nan | 7 | 8 | 27.1822 | 97.3558 | 0 | 22.5894 | 19.5406 | 0.00447831 | 0.00182383 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | 8 | 9 | GreedyCriticalLoadFirst | 8 | qci_loss | 47.8945 | 3.58741 | 0.442829 | 110.672 | 0.429245 | 1 | 246.896 | 193.467 | 30 | nan | nan | 8 | 9 | 0.349528 | 108.209 | 0 | 110.672 | 351510 | 31 | 30 | 30 | 30 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | DifferentialEvolutionOptimizer | 9 | 10 | GreedyCriticalLoadFirst | 8 | qci_loss | 67.2514 | 6 | 0.50106 | 191.628 | 0.657384 | 1 | 159.027 | 123.602 | 0.0238047 | nan | nan | 9 | 10 | 27.6043 | 123.714 | 0 | 191.628 | 163.587 | 0.206908 | 0.0238047 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case30_adapted | CMPO + QCi Dirac-3 | 10 | 11 | GreedyCriticalLoadFirst | 8 | qci_loss | 72.6759 | 4.99301 | 0.442829 | 166.757 | 0.286621 | 1 | 202.487 | 158.385 | 20 | nan | nan | 10 | 11 | 0.349528 | 96.2082 | 0 | 166.757 | 156620 | 22 | 20 | 20 | 20 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 0 | 1 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.00390406 | 3.14323 | 1 | 1 | 742.562 | 563.386 | 0.0267492 | nan | nan | 0 | 1 | 383.266 | 582.135 | 0 | 3.14323 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 1 | 2 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0 | nan | nan | 1 | 2 | 491.074 | 1328.52 | 0 | 12.0485 | 0 | 0 | 0 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 2 | 3 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.0021564 | nan | nan | 2 | 3 | 491.074 | 1328.52 | 0 | 12.0485 | 8.045 | 0.0023095 | 0.0021564 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO-local polynomial search | 3 | 4 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.506283 | nan | nan | 3 | 4 | 491.074 | 1328.52 | 0 | 12.0485 | 226.407 | 0.573114 | 0.506283 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | 4 | 5 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0155717 | 12.5371 | 1 | 1 | 1539.7 | 1205.93 | 430 | nan | nan | 4 | 5 | 557.295 | 1209.27 | 0 | 12.5371 | 103890 | 433 | 430 | 30 | 30 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 5 | 6 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.0221664 | 17.8466 | 1 | 1 | 1779.7 | 1368.57 | 2.19171 | nan | nan | 5 | 6 | 491.074 | 1322.78 | 0 | 17.8466 | 917.575 | 2.36803 | 2.19171 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 6 | 7 | Piecewise-linear MILP baseline | 4 | qci_loss | 0 | 0 | 0.200946 | 1111.64 | 1 | 1 | 1543.86 | 1185.38 | 5.64375e-05 | nan | nan | 6 | 7 | 199.817 | 1156.2 | 0 | 1111.64 | 0.0243556 | 6.00312e-05 | 5.64375e-05 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 7 | 8 | Piecewise-linear MILP baseline | 4 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0520741 | nan | nan | 7 | 8 | 491.074 | 1330.02 | 0 | 11.091 | 58.609 | 0.13214 | 0.0520741 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 8 | 9 | Piecewise-linear MILP baseline | 4 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0565725 | nan | nan | 8 | 9 | 491.074 | 1330.02 | 0 | 11.091 | 58.0844 | 0.132923 | 0.0565725 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 9 | 10 | Piecewise-linear MILP baseline | 4 | qci_loss | 169.56 | 3 | 0.165217 | 738.799 | 0.840915 | 1 | 1432.97 | 1130.74 | 15 | nan | nan | 9 | 10 | 378.541 | 1089.09 | 0 | 738.799 | 6000 | 15 | 15 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| lexicographic | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 10 | 11 | Piecewise-linear MILP baseline | 4 | qci_loss | 442.277 | 6 | 0.231811 | 1501.31 | 0.700112 | 1 | 1001.8 | 774.708 | 0.0646265 | nan | nan | 10 | 11 | 249.655 | 753.188 | 0 | 1501.31 | 28.4419 | 0.0698639 | 0.0646265 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | nan | nan | nan | nan | nan | nan | nan |
| weighted | pglib_case14_adapted | Piecewise-linear MILP baseline | 0.0011545 | 1 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.89801 | 0.230769 | 0.496372 | 28.6571 | 0.984151 | 1 | 123.713 | 95.3581 | 0.0346349 | 0.0011545 | 1 | nan | nan | 26.6986 | 103.876 | 0 | 28.6571 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0 | 0 | 0.0011545 | 0 |
| weighted | pglib_case14_adapted | GreedyCriticalLoadFirst | 10.2152 | 2 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.90997 | 0.230769 | 0.496372 | 29.2573 | 0.984129 | 1 | 205.115 | 159.223 | 0 | 10.2152 | 2 | nan | nan | 63.4467 | 116.772 | 0 | 29.2573 | 0 | 0 | 0 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000100122 | 0 | 0 | 0.00193334 | 0.992178 | 0 | 0 |
| weighted | pglib_case14_adapted | SLSQPDispatchOptimizer | 129.105 | 3 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.142905 | 129.105 | 3 | nan | nan | 49.3394 | 115.942 | 0 | 29.6085 | 356.286 | 0.361676 | 0.142905 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000158801 | 0.08 | 0.0781691 | 0.00306452 | 0.955019 | 0.00476349 | 0 |
| weighted | pglib_case14_adapted | IPOPT/Pyomo nonlinear baseline | 129.105 | 4 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.91698 | 0.692308 | 0.502364 | 29.6085 | 0.984117 | 1 | 202.067 | 156.397 | 0.157031 | 129.105 | 4 | nan | nan | 49.3394 | 115.942 | 0 | 29.6085 | 360.854 | 0.351995 | 0.157031 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.000158801 | 0.08 | 0.0781691 | 0.00306452 | 0.955019 | 0.00523437 | 0 |
| weighted | pglib_case14_adapted | QUBO/quadratized local search baseline | 189.351 | 5 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 10.014 | 0.230769 | 0.522312 | 30.7549 | 0.982163 | 1 | 205.757 | 159.635 | 4.12812 | 189.351 | 5 | nan | nan | 64.5159 | 109.147 | 0 | 30.7549 | 4851.36 | 4.8627 | 4.12812 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.00933824 | 0 | 0.338399 | 0.00675719 | 1 | 0.137604 | 0 |
| weighted | pglib_case14_adapted | CMPO-local polynomial search | 286.296 | 6 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 11.4178 | 0.230769 | 0.53538 | 31.5094 | 0.979662 | 1 | 204.285 | 158.392 | 1.08133 | 286.296 | 6 | nan | nan | 63.4467 | 105.973 | 0 | 31.5094 | 1265.07 | 1.29204 | 1.08133 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0210855 | 0 | 0.508871 | 0.00918727 | 0.982053 | 0.0360443 | 0 |
| weighted | pglib_case14_adapted | GPU-parallel random restart baseline | 547.408 | 7 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 13.206 | 0.230769 | 0.573028 | 33.6829 | 0.976477 | 1 | 203.632 | 157.739 | 0.00357137 | 547.408 | 7 | nan | nan | 63.4467 | 97.4857 | 0 | 33.6829 | 8.13036 | 0.00381432 | 0.00357137 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.036048 | 0 | 1 | 0.0161883 | 0.974096 | 0.000119046 | 0 |
| weighted | pglib_case14_adapted | Stress-only reserve heuristic baseline | 576.037 | 8 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 8.89801 | 0.230769 | 0.572846 | 255.146 | 0.984151 | 1 | 158.744 | 124.036 | 9.15419e-05 | 576.037 | 8 | nan | nan | 39.8837 | 103.403 | 0 | 255.146 | 0.0931692 | 9.75415e-05 | 9.15419e-05 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.997629 | 0.729525 | 0.426986 | 3.0514e-06 | 0 |
| weighted | pglib_case14_adapted | CMPO-V2 + QCi Dirac-3 | 1304.53 | 9 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 64.2239 | 3.64615 | 0.527719 | 140.955 | 0.404639 | 1 | 189.103 | 148.312 | 29 | 1304.53 | 9 | nan | nan | 0.469359 | 138.029 | 0 | 140.955 | 344670 | 31 | 29 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.462956 | 0.592 | 0.408932 | 0.361713 | 0.797011 | 0.966667 | 0 |
| weighted | pglib_case14_adapted | CMPO + QCi Dirac-3 | 1539.38 | 10 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 75.9432 | 4.38462 | 0.527719 | 179.8 | 0.367861 | 1 | 158.274 | 124.751 | 30 | 1539.38 | 10 | nan | nan | 0.469359 | 129.962 | 0 | 179.8 | 346410 | 32 | 30 | 30 | 30 | 60 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.561021 | 0.72 | 0.408932 | 0.486833 | 0.42125 | 1 | 0 |
| weighted | pglib_case14_adapted | DifferentialEvolutionOptimizer | 2570.01 | 11 | Piecewise-linear MILP baseline | 1304.53 | qci_loss | 128.404 | 6 | 0.567061 | 339.118 | 0.580631 | 1 | 196.917 | 153.723 | 0.130723 | 2570.01 | 11 | nan | nan | 60.4848 | 127.051 | 0 | 339.118 | 155.468 | 0.157663 | 0.130723 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 1 | 0.922158 | 1 | 0.89225 | 0.00435742 | 0 |
| weighted | pglib_case30_adapted | Piecewise-linear MILP baseline | 0.000801966 | 1 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 17.1893 | 0.985838 | 1 | 71.9515 | 53.6081 | 0.024059 | 0.000801966 | 1 | nan | nan | 5.44236 | 23.389 | 0 | 17.1893 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1.33482e-17 | 0 | 0 | 0 | 0 | 0.000801966 | 0 |
| weighted | pglib_case30_adapted | GreedyCriticalLoadFirst | 5.12061 | 2 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.405713 | 18.7075 | 0.985838 | 1 | 146.308 | 112.994 | 0 | 5.12061 | 2 | nan | nan | 27.1822 | 101.065 | 0 | 18.7075 | 0 | 0 | 0 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0.00870344 | 0.425027 | 0 | 0 |
| weighted | pglib_case30_adapted | IPOPT/Pyomo nonlinear baseline | 57.6357 | 3 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0141961 | 57.6357 | 3 | nan | nan | 25.6382 | 99.8766 | 0 | 18.7078 | 341.844 | 0.296537 | 0.0141961 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 5.26444e-06 | 0.0526316 | 5.52575e-05 | 0.00870543 | 0.410025 | 0.000473203 | 0 |
| weighted | pglib_case30_adapted | SLSQPDispatchOptimizer | 57.6357 | 4 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13719 | 0.461538 | 0.405719 | 18.7078 | 0.985837 | 1 | 143.683 | 111.041 | 0.0142361 | 57.6357 | 4 | nan | nan | 25.6382 | 99.8766 | 0 | 18.7078 | 362.564 | 0.332888 | 0.0142361 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 5.26444e-06 | 0.0526316 | 5.52575e-05 | 0.00870543 | 0.410025 | 0.000474536 | 0 |
| weighted | pglib_case30_adapted | QUBO/quadratized local search baseline | 199.773 | 5 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.5438 | 0.153846 | 0.448658 | 21.6049 | 0.984899 | 1 | 145.077 | 112.07 | 0.782626 | 199.773 | 5 | nan | nan | 27.1822 | 101.065 | 0 | 21.6049 | 5278.82 | 7.35439 | 0.782626 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.00611604 | 0 | 0.373839 | 0.0253131 | 0.417995 | 0.0260875 | 0 |
| weighted | pglib_case30_adapted | CMPO-local polynomial search | 345.228 | 6 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 7.37013 | 0.153846 | 0.479241 | 21.4902 | 0.982992 | 1 | 145.193 | 111.88 | 0.175437 | 345.228 | 6 | nan | nan | 27.1822 | 101.065 | 0 | 21.4902 | 1357.8 | 1.81652 | 0.175437 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0185348 | 0 | 0.640069 | 0.0246556 | 0.418658 | 0.00584789 | 0 |
| weighted | pglib_case30_adapted | GPU-parallel random restart baseline | 478.373 | 7 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 7.77747 | 0.153846 | 0.508286 | 22.5894 | 0.982052 | 1 | 144.785 | 111.472 | 0.00182383 | 478.373 | 7 | nan | nan | 27.1822 | 97.3558 | 0 | 22.5894 | 19.5406 | 0.00447831 | 0.00182383 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.0246565 | 0 | 0.892915 | 0.0309571 | 0.416324 | 6.07944e-05 | 0 |
| weighted | pglib_case30_adapted | Stress-only reserve heuristic baseline | 563.757 | 8 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 6.13684 | 0.153846 | 0.520588 | 123.389 | 0.985838 | 1 | 122.268 | 93.1641 | 4.3396e-05 | 563.757 | 8 | nan | nan | 17.9954 | 81.9601 | 0 | 123.389 | 0.100707 | 0.00010574 | 4.3396e-05 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 1 | 0.608808 | 0.287613 | 1.44653e-06 | 0 |
| weighted | pglib_case30_adapted | CMPO-V2 + QCi Dirac-3 | 1441.03 | 9 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 47.8945 | 3.58741 | 0.442829 | 110.672 | 0.429245 | 1 | 246.896 | 193.467 | 30 | 1441.03 | 9 | nan | nan | 0.349528 | 108.209 | 0 | 110.672 | 351510 | 31 | 30 | 30 | 30 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.627566 | 0.587321 | 0.323101 | 0.535908 | 1 | 1 | 0 |
| weighted | pglib_case30_adapted | CMPO + QCi Dirac-3 | 2083.17 | 10 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 72.6759 | 4.99301 | 0.442829 | 166.757 | 0.286621 | 1 | 202.487 | 158.385 | 20 | 2083.17 | 10 | nan | nan | 0.349528 | 96.2082 | 0 | 166.757 | 156620 | 22 | 20 | 20 | 20 | 66 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 0.827751 | 0.323101 | 0.857424 | 0.746155 | 0.666667 | 0 |
| weighted | pglib_case30_adapted | DifferentialEvolutionOptimizer | 2438.46 | 11 | Piecewise-linear MILP baseline | 1441.03 | qci_loss | 67.2514 | 6 | 0.50106 | 191.628 | 0.657384 | 1 | 159.027 | 123.602 | 0.0238047 | 2438.46 | 11 | nan | nan | 27.6043 | 123.714 | 0 | 191.628 | 163.587 | 0.206908 | 0.0238047 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | 0.918477 | 1 | 0.830013 | 1 | 0.49773 | 0.00079349 | 0 |
| weighted | pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 6.22075e-05 | 1 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.00390406 | 3.14323 | 1 | 1 | 742.562 | 563.386 | 0.0267492 | 6.22075e-05 | 1 | nan | nan | 383.266 | 582.135 | 0 | 3.14323 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0 | 0 | 0 | 6.22075e-05 | 0 |
| weighted | pglib_case5_pjm_adapted | GreedyCriticalLoadFirst | 34.8606 | 2 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0 | 34.8606 | 2 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 0 | 0 | 0 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 0 | 0 |
| weighted | pglib_case5_pjm_adapted | GPU-parallel random restart baseline | 34.8606 | 3 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.0021564 | 34.8606 | 3 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 8.045 | 0.0023095 | 0.0021564 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 5.01487e-06 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO-local polynomial search | 34.8618 | 4 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0149649 | 12.0485 | 1 | 1 | 1782.18 | 1369.62 | 0.506283 | 34.8618 | 4 | nan | nan | 491.074 | 1328.52 | 0 | 12.0485 | 226.407 | 0.573114 | 0.506283 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0485324 | 0.00594415 | 1 | 0.0011774 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO-V2 + QCi Dirac-3 | 34.892 | 5 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0155717 | 12.5371 | 1 | 1 | 1539.7 | 1205.93 | 430 | 34.892 | 5 | nan | nan | 557.295 | 1209.27 | 0 | 12.5371 | 103890 | 433 | 430 | 30 | 30 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0511947 | 0.00627023 | 0.766759 | 1 | 0 |
| weighted | pglib_case5_pjm_adapted | QUBO/quadratized local search baseline | 51.028 | 6 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.0221664 | 17.8466 | 1 | 1 | 1779.7 | 1368.57 | 2.19171 | 51.028 | 6 | nan | nan | 491.074 | 1322.78 | 0 | 17.8466 | 917.575 | 2.36803 | 2.19171 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.0801307 | 0.00981425 | 0.997616 | 0.00509699 | 0 |
| weighted | pglib_case5_pjm_adapted | IPOPT/Pyomo nonlinear baseline | 213.982 | 7 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0520741 | 213.982 | 7 | nan | nan | 491.074 | 1330.02 | 0 | 11.091 | 58.609 | 0.13214 | 0.0520741 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 2.69103e-06 | 0.181818 | 0.0433141 | 0.00530503 | 0.997345 | 0.000121103 | 0 |
| weighted | pglib_case5_pjm_adapted | SLSQPDispatchOptimizer | 213.982 | 8 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0.00119018 | 1.09091 | 0.0137756 | 11.091 | 0.999999 | 1 | 1779.42 | 1368.11 | 0.0565725 | 213.982 | 8 | nan | nan | 491.074 | 1330.02 | 0 | 11.091 | 58.0844 | 0.132923 | 0.0565725 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 2.69103e-06 | 0.181818 | 0.0433141 | 0.00530503 | 0.997345 | 0.000131564 | 0 |
| weighted | pglib_case5_pjm_adapted | Stress-only reserve heuristic baseline | 513.984 | 9 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 0 | 0 | 0.200946 | 1111.64 | 1 | 1 | 1543.86 | 1185.38 | 5.64375e-05 | 513.984 | 9 | nan | nan | 199.817 | 1156.2 | 0 | 1111.64 | 0.0243556 | 6.00312e-05 | 5.64375e-05 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0 | 0 | 0.864572 | 0.739903 | 0.770766 | 1.3125e-07 | 0 |
| weighted | pglib_case5_pjm_adapted | CMPO + QCi Dirac-3 | 1293.06 | 10 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 169.56 | 3 | 0.165217 | 738.799 | 0.840915 | 1 | 1432.97 | 1130.74 | 15 | 1293.06 | 10 | nan | nan | 378.541 | 1089.09 | 0 | 738.799 | 6000 | 15 | 15 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 0.383381 | 0.5 | 0.707802 | 0.491038 | 0.664102 | 0.0348837 | 0 |
| weighted | pglib_case5_pjm_adapted | DifferentialEvolutionOptimizer | 2602.49 | 11 | Piecewise-linear MILP baseline | 34.8919 | qci_loss | 442.277 | 6 | 0.231811 | 1501.31 | 0.700112 | 1 | 1001.8 | 774.708 | 0.0646265 | 2602.49 | 11 | nan | nan | 249.655 | 753.188 | 0 | 1501.31 | 28.4419 | 0.0698639 | 0.0646265 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | 1 | 1 | 1 | 1 | 0.249359 | 0.000150294 | 0 |

## final_win_tie_loss_by_challenge_score

| score_mode | method_name | wins | ties | losses | datasets_evaluated |
| --- | --- | --- | --- | --- | --- |
| lexicographic | CMPO + QCi Dirac-3 | 0 | 0 | 3 | 3 |
| lexicographic | CMPO-V2 + QCi Dirac-3 | 0 | 0 | 3 | 3 |
| lexicographic | CMPO-local polynomial search | 0 | 0 | 3 | 3 |
| lexicographic | DifferentialEvolutionOptimizer | 0 | 0 | 3 | 3 |
| lexicographic | GPU-parallel random restart baseline | 0 | 0 | 3 | 3 |
| lexicographic | GreedyCriticalLoadFirst | 1 | 0 | 2 | 3 |
| lexicographic | IPOPT/Pyomo nonlinear baseline | 0 | 0 | 3 | 3 |
| lexicographic | Piecewise-linear MILP baseline | 2 | 0 | 1 | 3 |
| lexicographic | QUBO/quadratized local search baseline | 0 | 0 | 3 | 3 |
| lexicographic | SLSQPDispatchOptimizer | 0 | 0 | 3 | 3 |
| lexicographic | Stress-only reserve heuristic baseline | 0 | 0 | 3 | 3 |
| weighted | CMPO + QCi Dirac-3 | 0 | 0 | 3 | 3 |
| weighted | CMPO-V2 + QCi Dirac-3 | 0 | 0 | 3 | 3 |
| weighted | CMPO-local polynomial search | 0 | 0 | 3 | 3 |
| weighted | DifferentialEvolutionOptimizer | 0 | 0 | 3 | 3 |
| weighted | GPU-parallel random restart baseline | 0 | 0 | 3 | 3 |
| weighted | GreedyCriticalLoadFirst | 0 | 0 | 3 | 3 |
| weighted | IPOPT/Pyomo nonlinear baseline | 0 | 0 | 3 | 3 |
| weighted | Piecewise-linear MILP baseline | 3 | 0 | 0 | 3 |
| weighted | QUBO/quadratized local search baseline | 0 | 0 | 3 | 3 |
| weighted | SLSQPDispatchOptimizer | 0 | 0 | 3 | 3 |
| weighted | Stress-only reserve heuristic baseline | 0 | 0 | 3 | 3 |

## final_pareto_frontier_v2

| dataset | method_name | expected_operating_cost | best_cost_by_method | median_cost_by_method | risk_adjusted_cost | total_upgrade_cost | max_fraction_customers_unserved_per_hour | total_hours_critical_infrastructure_unserved | critical_load_served_fraction | critical_energy_not_served_kwh | energy_not_served_kwh | feasibility_after_repair | wall_clock_runtime_seconds | median_runtime_seconds | time_to_good_solution | repeat_count | samples_per_payload_median | payload_count | scenario_count | scenario_probability_mass | aggregation | pareto_frontier | cost_objective | resilience_objective |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_adapted | Piecewise-linear MILP baseline | 95.3581 | 26.6986 | 103.876 | 123.713 | 0 | 0.496372 | 0.230769 | 0.984151 | 8.89801 | 28.6571 | 1 | 44.548 | 0.0392278 | 0.0346349 | 50 | 50 | 12 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | True | risk_adjusted_cost_min | critical_energy_not_served_kwh_min |
| pglib_case30_adapted | Piecewise-linear MILP baseline | 53.6081 | 5.44236 | 23.389 | 71.9515 | 0 | 0.405713 | 0.153846 | 0.985838 | 6.13684 | 17.1893 | 1 | 47.5644 | 0.0466731 | 0.024059 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | True | risk_adjusted_cost_min | critical_energy_not_served_kwh_min |
| pglib_case30_adapted | Stress-only reserve heuristic baseline | 93.1641 | 17.9954 | 81.9601 | 122.268 | 0 | 0.520588 | 0.153846 | 0.985838 | 6.13684 | 123.389 | 1 | 0.100707 | 0.00010574 | 4.3396e-05 | 50 | 50 | 18 | 6 | 0.8125 | median_per_payload_then_probability_weighted_scenario_mean | True | risk_adjusted_cost_min | critical_energy_not_served_kwh_min |
| pglib_case5_pjm_adapted | Piecewise-linear MILP baseline | 563.386 | 383.266 | 582.135 | 742.562 | 0 | 0.00390406 | 0 | 1 | 0 | 3.14323 | 1 | 12.3226 | 0.028794 | 0.0267492 | 50 | 50 | 8 | 4 | 0.6875 | median_per_payload_then_probability_weighted_scenario_mean | True | risk_adjusted_cost_min | critical_energy_not_served_kwh_min |
