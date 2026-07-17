# IEEE123 Budget-Sweep Unbalanced AC Validation

This report is generated from `ac_validation_results.csv` and the saved budget system traces.
Every plan is accepted only when all eight training-scenario OpenDSS solves converge and all checkable limits pass.

## Method

- The complete pinned IEEE123 source bundle is copied before each validation run; source artifacts are not edited.
- Saved critical and noncritical served-load totals are mapped proportionally within those public node classes, preserving phase connections and power factors.
- Saved topology/PCC states and aggregate generation/storage dispatch are applied; technology dispatch is allocated pro rata over eligible installed physical assets.
- No grid-forming inverter or island slack model is added because none is published in the upgrade catalog; disconnected served buses therefore fail the voltage check rather than receiving an invented voltage source.
- Voltage limits are 0.95–1.05 pu. Published transformer kVA ratings are enforced at 100% loading.
- Published line ampacity available: False. Missing ratings are unavailable, never replaced by engine defaults.
- Regulator taps, capacitor states, feeder losses, and numerical island/system balance residuals are retained in the scenario table.

## Results

- Scenario solves: 384
- AC-valid QCi system plans: 0
- AC-valid baseline system plans: 0
- AC-valid comparison rows: 0
- All forced-islanding-family cases de-energize served buses under the published controls; this prevents every eight-scenario plan from passing the AC gate.
- QCi strict advantage budgets: []
- Supported conclusion: No strict QCi total-ENS advantage is supported among matched budgets with AC-valid QCi and baseline plans.

## Reproduction

`python scripts/phase3_validate_ieee123_ac_solutions.py`
