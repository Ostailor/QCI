| method_name | expected_operating_cost | risk_adjusted_cost | critical_load_served_fraction | energy_not_served_kwh | feasibility_rate | median_runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| DifferentialEvolutionOptimizer | 1.544e+04 | 1.786e+04 | 0.6507 | 7.968e+04 | 1 | 0.2561 |
| SLSQPDispatchOptimizer | 2.687e+04 | 3.269e+04 | 0.9668 | 1.413e+04 | 0.4375 | 1.183 |
| CMPO-local polynomial search | 4.179e+04 | 4.787e+04 | 0.9773 | 1.601e+04 | 0.4375 | 1.742 |
| GreedyCriticalLoadFirst | 4.18e+04 | 4.787e+04 | 0.9662 | 2.14e+04 | 1 | 0 |