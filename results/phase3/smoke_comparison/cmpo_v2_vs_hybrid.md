# CMPO-V2 vs Hybrid QCi Smoke Comparison

This report compares only completed, decoded smoke samples. Lower challenge score is better. No superiority claim is made when the evidence is mixed or incomplete.

## Verdict

- Better median challenge score: `cmpo_v2`
- Better best challenge score: `cmpo_v2`
- Lower median critical ENS: `cmpo_v2`
- Higher median critical-load served: `cmpo_v2`
- Hybrid projection successful: `true`
- Recommendation: **run full CMPO-V2**

## Results

| dataset | formulation | completed_jobs | failed_jobs | sample_count | feasibility_rate | challenge_score_best | challenge_score_median | challenge_score_mean | challenge_score_std | challenge_score_variance | critical_energy_not_served_best | critical_energy_not_served_median | critical_load_served_fraction_best | critical_load_served_fraction_median | max_customers_unserved_best | max_customers_unserved_median | critical_infrastructure_outage_proxy_best | critical_infrastructure_outage_proxy_median | risk_adjusted_cost_best | risk_adjusted_cost_median | runtime_seconds_median | qci_energy_variance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pglib_case14_ieee | cmpo_v2 | 20 | 0 | 20 | 1 | 9.15815 | 1216.72 | 1216.1 | 1206.34 | 1.45525e+06 | 0 | 131.625 | 1 | 0.710695 | 0 | 0.26386 | 0 | 3 | 137.203 | 194.821 | 15 | 4.55277e+09 |
| pglib_case14_ieee | hybrid | 20 | 0 | 20 | 1 | 1118.4 | 2065.29 | 1896.3 | 613.198 | 376012 | 19.1356 | 202.478 | 0.952734 | 0.537252 | 0.0501674 | 0.383107 | 6 | 6 | 140.681 | 151.278 | 1.00206 | 1.65666e+11 |
| pglib_case30_ieee | cmpo_v2 | 20 | 0 | 20 | 1 | 10.1281 | 1269.78 | 1269.73 | 1258.82 | 1.58463e+06 | 0 | 135.408 | 1 | 0.634864 | 0.0452296 | 0.237136 | 0 | 3 | 138.851 | 170.612 | 15 | 6.81384e+08 |
| pglib_case30_ieee | hybrid | 20 | 0 | 20 | 1 | 1032.96 | 2453.69 | 1931.6 | 645.586 | 416782 | 7.70056 | 256.569 | 0.979936 | 0.308148 | 0.0452296 | 0.413469 | 6 | 6 | 124.917 | 140.847 | 1.00206 | 1.65654e+11 |
| pglib_case5_pjm | cmpo_v2 | 20 | 0 | 20 | 1 | 1 | 2.84026 | 2.92932 | 1.22319 | 1.49619 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1697.57 | 1883.91 | 15 | 1.05927e+12 |
| pglib_case5_pjm | hybrid | 20 | 0 | 20 | 1 | 5.06026 | 10 | 362.337 | 710.162 | 504330 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1896.42 | 2393.52 | 1.00213 | 1266.83 |
| ALL | cmpo_v2 | 60 | 0 | 60 | 1 | 1 | 10.7476 | 829.589 | 1164.24 | 1.35545e+06 | 0 | 0 | 1 | 1 | 0 | 0.0226148 | 0 | 0 | 137.203 | 231.105 | 15 | 8.55202e+12 |
| ALL | hybrid | 60 | 0 | 60 | 1 | 5.06026 | 1290.15 | 1396.74 | 983.658 | 967582 | 0 | 48.7248 | 1 | 0.874384 | 0 | 0.107324 | 0 | 6 | 124.917 | 168.281 | 1.00207 | 1.47252e+11 |
