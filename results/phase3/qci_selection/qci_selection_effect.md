# QCi Selection Effect

This is a derived offline analysis over existing decoded QCi repeats. No new QCi jobs were run.

## Overall Answers

- Does choosing by challenge_score improve critical ENS versus raw QCi energy? YES: improved on 56/135 payloads, with aggregate critical ENS delta -14505.2 kWh.
- Does choosing by challenge_score reduce max customers unserved? YES: reduced on 58/135 payloads, with aggregate max-unserved delta -14.4789.
- Does QCi look better under the challenge-aligned selector? YES relative to raw-energy selection, but risk-adjusted cost changes by 3889.96; compare against baselines separately.
- Which payloads still fail even under the best selector? 113/135 payloads have at least one positive critical ENS, critical infrastructure outage, positive max-unserved, infeasibility, or not-fully-served critical load condition.

## Dataset Summary

| benchmark | dataset | payload_count | ens_improved_payloads | max_unserved_reduced_payloads | critical_ENS_delta | max_unserved_delta | risk_cost_delta | still_failing_payloads |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_ieee | pglib_case14_adapted | 60 | 24 | 25 | -4495.96 | -6.49994 | 206.235 | 52 |
| pglib_case30_ieee | pglib_case30_adapted | 66 | 24 | 25 | -3851.47 | -6.35865 | -115.223 | 54 |
| pglib_case5_pjm | pglib_case5_pjm_adapted | 8 | 8 | 8 | -6157.81 | -1.62035 | 3798.95 | 6 |
| qci_env_smoke | qci_small_synthetic | 1 | 0 | 0 | 0 | 0 | 0 | 1 |

## Payloads Still Failing Under Best Challenge Selector

| benchmark | dataset | payload_name | challenge_selector_critical_ENS | challenge_selector_max_customers_unserved | challenge_selector_infra_hours | challenge_selector_critical_load_served | best_selector_failure_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_ieee | pglib_case14_adapted | demand_surge_BUS3_MG__from__demand_surge_BUS3_MG-BUS4_MG-BUS9_MG.json | 304.394 | 0.435424 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | demand_surge_BUS5_MG__from__demand_surge_BUS2_MG-BUS5_MG-BUS7_MG.json | 300.135 | 0.440041 | 6 | 0.0139924 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | storm_forced_islanding_BUS5_MG__from__storm_forced_islanding_BUS2_MG-BUS5_MG-BUS7_MG.json | 294.119 | 0.442829 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | storm_forced_islanding_BUS3_MG__from__storm_forced_islanding_BUS3_MG-BUS4_MG-BUS9_MG.json | 294.119 | 0.435424 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | storm_forced_islanding_BUS5_MG-BUS7_MG__from__storm_forced_islanding_BUS2_MG-BUS5_MG-BUS7_MG.json | 270.817 | 0.429043 | 6 | 0.269727 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | storm_forced_islanding_BUS3_MG-BUS4_MG__from__storm_forced_islanding_BUS3_MG-BUS4_MG-BUS9_MG.json | 263.251 | 0.527719 | 6 | 0.421391 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | pcc_failure_BUS5_MG__from__pcc_failure_BUS2_MG-BUS5_MG-BUS7_MG.json | 261.716 | 0.442829 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | pcc_failure_BUS3_MG__from__pcc_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 261.716 | 0.435424 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | local_generator_failure_BUS5_MG__from__local_generator_failure_BUS2_MG-BUS5_MG-BUS7_MG.json | 259.223 | 0.442829 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | local_generator_failure_BUS3_MG__from__local_generator_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 259.223 | 0.435424 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | renewable_shortfall_BUS5_MG__from__renewable_shortfall_BUS2_MG-BUS5_MG-BUS7_MG.json | 254.238 | 0.442829 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | renewable_shortfall_BUS3_MG__from__renewable_shortfall_BUS3_MG-BUS4_MG-BUS9_MG.json | 254.238 | 0.435424 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | normal_BUS5_MG__from__normal_BUS2_MG-BUS5_MG-BUS7_MG.json | 249.253 | 0.439725 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | normal_BUS3_MG__from__normal_BUS3_MG-BUS4_MG-BUS9_MG.json | 249.253 | 0.434001 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case30_ieee | pglib_case30_adapted | storm_forced_islanding_BUS2_MG-BUS5_MG__from__storm_forced_islanding_BUS2_MG-BUS5_MG-BUS7_MG.json | 245.817 | 0.410103 | 6 | 0.31067 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | demand_surge_BUS4_MG__from__demand_surge_BUS3_MG-BUS4_MG-BUS9_MG.json | 166.472 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | storm_forced_islanding_BUS4_MG__from__storm_forced_islanding_BUS3_MG-BUS4_MG-BUS9_MG.json | 160.853 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | pcc_failure_BUS4_MG__from__pcc_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 143.132 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | local_generator_failure_BUS4_MG__from__local_generator_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 141.769 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | renewable_shortfall_BUS4_MG__from__renewable_shortfall_BUS3_MG-BUS4_MG-BUS9_MG.json | 139.042 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | normal_BUS4_MG__from__normal_BUS3_MG-BUS4_MG-BUS9_MG.json | 136.316 | 0.220947 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | demand_surge_BUS9_MG__from__demand_surge_BUS3_MG-BUS4_MG-BUS9_MG.json | 110.153 | 0.136359 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | storm_forced_islanding_BUS9_MG__from__storm_forced_islanding_BUS3_MG-BUS4_MG-BUS9_MG.json | 106.435 | 0.136359 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | pcc_failure_BUS9_MG__from__pcc_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 94.7092 | 0.136359 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
| pglib_case14_ieee | pglib_case14_adapted | local_generator_failure_BUS9_MG__from__local_generator_failure_BUS3_MG-BUS4_MG-BUS9_MG.json | 93.8072 | 0.136359 | 6 | 0 | critical_ENS_positive\|critical_infra_unserved_hours_positive\|max_customers_unserved_positive\|critical_load_not_fully_served |
