# QCi Selection Effect

This is a derived offline analysis over existing decoded QCi repeats. No new QCi jobs were run.

## Overall Answers

- Does choosing by challenge_score improve critical ENS versus raw QCi energy? YES: improved on 43/43 payloads, with aggregate critical ENS delta -4.83081e+06 kWh.
- Does choosing by challenge_score reduce max customers unserved? YES: reduced on 43/43 payloads, with aggregate max-unserved delta -43.
- Does QCi look better under the challenge-aligned selector? YES relative to raw-energy selection, but risk-adjusted cost changes by 4.38429e+09; compare against baselines separately.
- Which payloads still fail even under the best selector? 0/43 payloads have at least one positive critical ENS, critical infrastructure outage, positive max-unserved, infeasibility, or not-fully-served critical load condition.

## Dataset Summary

| benchmark | dataset | payload_count | ens_improved_payloads | max_unserved_reduced_payloads | critical_ENS_delta | max_unserved_delta | risk_cost_delta | still_failing_payloads |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| final_public_experiment | arpae_go_network_01o_020 | 8 | 8 | 8 | -2.53496e+06 | -8 | 2.29177e+09 | 0 |
| final_public_experiment | ieee123_opendss | 12 | 12 | 12 | -6255 | -12 | 3.90418e+06 | 0 |
| final_public_experiment | pglib_case14_ieee | 9 | 9 | 9 | -1.335e+06 | -9 | 1.38748e+09 | 0 |
| final_public_experiment | pglib_case30_ieee | 14 | 14 | 14 | -954600 | -14 | 7.01125e+08 | 0 |

## Payloads Still Failing Under Best Challenge Selector

_No payloads fail under the best challenge selector._
