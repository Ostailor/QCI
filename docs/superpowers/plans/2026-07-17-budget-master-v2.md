# IEEE123 Global Budget Master V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve and accurately audit the invalid metadata-only V1 budget sweep, then build and validate six non-submitting global IEEE123 budget-master Hamiltonians with conservative charge-once cost encoding.

**Architecture:** V1 gets immutable, traceable post-hoc copies and a validator that rejects every metadata-only payload before QCi environment setup or upload. V2 uses one binary on/off pair per deduplicated physical catalog asset, binary budget slack, limited integer policy variables, a quadratic budget equality penalty, and an independently computed penalty-dominance certificate; decoded portfolios are exact-dollar checked before they can enter a shared twelve-patch recourse adapter.

**Tech Stack:** Python 3.11+, pandas, PyYAML, NumPy/SciPy already in the repository, pytest, existing CMPO polynomial/QCi export/full-system modules.

## Global Constraints

- Do not delete or overwrite any existing SC-CMPO, budget-frontier V1, CMPO-V2, direct-QCi, baseline, raw QCi, or AC-validation artifact.
- Do not submit QCi jobs during build or validation.
- Build exactly six global payloads, one for each existing public-catalog-derived budget.
- Use 33 catalog assets at 11 physical anchors; charge each asset once.
- Every master is integer encoded, has at most 132 variables, and degree at most 3.
- Conservative cost rounding must make real-dollar budget overrun impossible.
- No new dependencies.

---

### Task 1: Strict-stop V1 audit

**Files:**
- Create: `scripts/phase3_audit_budget_frontier_v1.py`
- Modify: `src/cmpo/qci_client_adapter.py`
- Test: `tests/test_budget_master_v2.py`
- Generate: `results/phase3/sc_cmpo/budget_frontier/posthoc_filter/*`
- Generate: `results/phase3/sc_cmpo/budget_frontier/failed_v1_audit/*`

**Interfaces:**
- Consumes: existing `qci_budgeted_results.csv`, held-out CSV, trace files, and 72 payloads.
- Produces: `audit_budget_frontier_v1(root: Path) -> dict[str, Any]` and a pre-upload guard in `run_payload_repeats`.

- [ ] **Step 1: Write failing regression tests**

```python
def test_metadata_only_budget_payload_is_rejected_before_qci_client(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter, "_client_from_environment", lambda: pytest.fail("client created"))
    with pytest.raises(ValueError, match="metadata only"):
        adapter.run_payload_repeats(metadata_only_payload, 1, tmp_path, {})

def test_v1_audit_reports_all_72_payloads_as_failed():
    result = audit.audit_budget_frontier_v1(ROOT / "results/phase3/sc_cmpo/budget_frontier")
    assert result["payloads_checked"] == 72
    assert result["payloads_failed"] == 72
```

- [ ] **Step 2: Run tests and confirm the guard/audit do not exist**

Run: `pytest tests/test_budget_master_v2.py -k 'metadata_only or v1_audit' -v`
Expected: FAIL before implementation.

- [ ] **Step 3: Implement immutable copies, trace hashes, validation manifest, exact report text, and the guard**

The guard loads and validates a payload before `validate_qci_environment()` or `_client_from_environment()`. A payload containing `budget_constraint` must have positive polynomial terms tagged with `component == "hard_budget"`; otherwise it raises `ValueError("budget constraint is metadata only; QCi submission refused")`.

- [ ] **Step 4: Run focused tests and the audit script**

Run: `pytest tests/test_budget_master_v2.py -k 'metadata_only or v1_audit' -v`
Expected: PASS; audit reports 72 checked, 72 failed, 0 submitted.

### Task 2: Conservative cost encoding

**Files:**
- Create: `src/cmpo/budget_encoding.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Produces: `choose_currency_unit(costs: Sequence[float], budgets: Sequence[float], *, fixed_variables: int, max_variables: int = 132) -> CurrencyEncoding`.
- Produces: `encode_budget(costs: Mapping[str, float], budget: float, unit: float) -> BudgetEncoding`.
- Produces: `add_squared_equality_terms(terms, weights, rhs, rho, component) -> list[dict[str, Any]]`.
- Produces: `validate_budget_payload(payload: Mapping[str, Any]) -> BudgetPayloadValidation`.

- [ ] **Step 1: Write failing tests for upward cost rounding, downward budget rounding, exact budget, one encoded-unit excess, and actual-dollar excess**

```python
assert encoding.encoded_costs["a"] == math.ceil(costs["a"] / encoding.unit)
assert encoding.encoded_budget == math.floor(budget / encoding.unit)
assert validate_decoded_cost(exact, budget).passed
assert not validate_encoded_cost(encoding.encoded_budget + 1, encoding).passed
assert not validate_decoded_cost(budget + 0.01, budget).passed
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k 'rounding or encoded_unit or actual_dollar' -v`
Expected: FAIL.

- [ ] **Step 3: Implement the smallest cent-denominated unit that fits all variables**

Start at `$0.01`; compute `ceil(log2(encoded_budget + 1))` slack bits for every budget and accept the smallest standard currency unit whose maximum master size is at most 132, whose `1/(largest encoded budget)^2` separation proxy is at least `1e-14`, and which preserves an encoded-feasible anchor-covering portfolio at every budget. The `1e-14` floor remains above double-precision epsilon while allowing the exact minimum-islanding dispatchable portfolio. Report per-asset upward error `< unit` and maximum portfolio conservatism `sum(ceil(cost/unit)*unit - cost)` over all 33 assets.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_budget_master_v2.py -k 'rounding or encoded_unit or actual_dollar' -v`
Expected: PASS.

### Task 3: Penalty dominance certificate

**Files:**
- Create: `src/cmpo/budget_penalty_certificate.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Produces: `nonbudget_variation_bound(terms: Sequence[Mapping[str, Any]]) -> float`.
- Produces: `build_penalty_certificate(terms, *, safety_multiplier: float) -> PenaltyCertificate`.

- [ ] **Step 1: Write a failing certificate test**

```python
certificate = build_penalty_certificate(nonbudget_terms, safety_multiplier=2.0)
assert certificate.rho_budget > certificate.maximum_nonbudget_objective_variation
assert certificate.minimum_violation_penalty > certificate.maximum_nonbudget_objective_variation
assert certificate.passed
```

- [ ] **Step 2: Run it and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k penalty_certificate -v`
Expected: FAIL.

- [ ] **Step 3: Implement an auditable sum-of-absolute-coefficients bound**

For binary variables each nonconstant monomial lies in `[0,1]`, so `sum(abs(coefficient))` is a conservative total-variation bound. Set `required_lower_bound = nextafter(bound, +inf)` and `rho_budget = safety_multiplier * max(bound, 1.0)`.

- [ ] **Step 4: Run the focused test**

Run: `pytest tests/test_budget_master_v2.py -k penalty_certificate -v`
Expected: PASS.

### Task 4: Global master builder

**Files:**
- Create: `configs/phase3_sc_cmpo_ieee123_budget_master_v2.yaml`
- Create: `src/cmpo/global_upgrade_master.py`
- Create: `scripts/phase3_build_budget_master_v2.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Consumes: `load_ieee123_upgrade_catalog`, six `BudgetLevel` records, `BudgetEncoding`, and `PenaltyCertificate`.
- Produces: `build_global_upgrade_master(catalog, budget, config) -> GlobalMasterBuild`.
- Produces: six `cmpo.budget_master.v2` JSON payloads.

- [ ] **Step 1: Write failing structural and toy-optimum tests**

```python
assert len(payloads) == 6
assert all(len(p["variables"]) <= 132 for p in payloads)
assert all(p["max_degree"] <= 3 for p in payloads)
assert all(any(t["component"] == "hard_budget" for t in p["polynomial_terms"]) for p in payloads)
assert brute_force_master(toy).selection == brute_force_hamiltonian(toy_payload).selection
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k 'master_payload or toy_master' -v`
Expected: FAIL.

- [ ] **Step 3: Implement binary on/off pairs and objective components**

Use `upgrade::<asset_key>::selected` and `upgrade::<asset_key>::not_selected` with `(selected + not_selected - 1)^2`. This is a two-state one-hot encoding for each independent physical upgrade and preserves the catalog semantics that PV, BESS, and dispatchable upgrades may coexist at one anchor. Add limited binary islanding, three-level reserve one-hot, policy activation, critical-service target, and eight scenario-response variables; add documented cubic upgrade/preparedness/scenario interactions.

- [ ] **Step 4: Add hard budget terms, certificate, normalize once, and preserve component tags/provenance**

The payload records raw and normalized coefficients, normalization scale, source payload checksums, catalog source rows, six budget derivations, integer unit, slack weights, certificate, and a `qci_submission_performed: false` build assertion.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_budget_master_v2.py -k 'master_payload or toy_master' -v`
Expected: PASS.

### Task 5: Portfolio decoding and diversity

**Files:**
- Create: `src/cmpo/portfolio_decode.py`
- Create: `src/cmpo/portfolio_diversity.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Produces: `decode_master_sample(payload, sample) -> DecodedPortfolio` with exact encoded and dollar checks.
- Produces: `select_unique_feasible_portfolios(portfolios, limit=10) -> list[DecodedPortfolio]`.

- [ ] **Step 1: Write failing charge-once and uniqueness tests**

```python
decoded = decode_master_sample(payload, duplicated_asset_sample)
assert decoded.total_upgrade_cost == expected_single_charge
assert len(select_unique_feasible_portfolios([decoded, decoded], limit=10)) == 1
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k 'duplicate_physical or portfolio_diversity' -v`
Expected: FAIL.

- [ ] **Step 3: Implement strict binary decoding, asset-key deduplication, Hamming diversity, and exact rejection**

Decoded selections are keyed by the catalog `asset_key`; any sample with a broken one-hot pair, invalid slack equality, encoded overrun, or exact-dollar overrun is infeasible regardless of native energy.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_budget_master_v2.py -k 'duplicate_physical or portfolio_diversity' -v`
Expected: PASS.

### Task 6: Shared patch recourse contract

**Files:**
- Create: `src/cmpo/budget_master_recourse.py`
- Create: `scripts/phase3_run_budget_master_recourse.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Produces: `fix_portfolio_across_patches(portfolio, payloads) -> dict[str, dict[str, float]]`.
- Produces: `build_recourse_work_items(portfolios, patches, training_scenarios, heldout_contingencies) -> list[RecourseWorkItem]`.
- Reuses: existing overlap consensus, full-system projection, held-out evaluator, and OpenDSS validation entry points.

- [ ] **Step 1: Write a failing identical-portfolio test**

```python
fixed = fix_portfolio_across_patches(portfolio, twelve_payloads)
assert len(fixed) == 12
assert len({portfolio_signature(values) for values in fixed.values()}) == 1
```

- [ ] **Step 2: Run it and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k fixed_across_patches -v`
Expected: FAIL.

- [ ] **Step 3: Implement deterministic portfolio-to-patch fixing and non-submitting recourse planning**

The runner accepts decoded result files, defaults to the top ten unique feasible portfolios per budget, records GPU-parallel work groups, and refuses to fabricate QCi portfolios when raw results are absent.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_budget_master_v2.py -k fixed_across_patches -v`
Expected: PASS.

### Task 7: Validation and baseline comparison contracts

**Files:**
- Create: `scripts/phase3_validate_budget_master_v2.py`
- Create: `scripts/phase3_compare_budget_masters.py`
- Test: `tests/test_budget_master_v2.py`

**Interfaces:**
- Produces: `validate_budget_master_v2(config_path, output_dir) -> dict[str, Any]`.
- Produces: master-level comparison rows only when every method uses the same `evaluate_portfolio_recourse` contract.

- [ ] **Step 1: Write failing 15-gate validation tests**

Validate exactly six payloads, polynomial budget presence, limits, local low-energy feasibility, conservative rounding, one-hot terms, deduplication, shared recourse, charge once, passing certificates, provenance, V1 exclusion, and zero QCi submissions.

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_budget_master_v2.py -k validation_gates -v`
Expected: FAIL.

- [ ] **Step 3: Implement the validator and comparison input gates**

The comparison script recognizes exact MILP/CP-SAT, SLSQP/IPOPT relaxation, Benders, greedy, GPU random, and QUBO master labels, but it rejects any row lacking the common recourse-evaluator trace. It never calls the QCi client.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_budget_master_v2.py -k validation_gates -v`
Expected: PASS.

### Task 8: Build immutable artifacts and verify

**Files:**
- Generate only under: `results/phase3/sc_cmpo/budget_master_v2/`

**Interfaces:**
- Produces every Part C artifact and exact post-approval QCi commands.

- [ ] **Step 1: Run the builder**

Run: `python scripts/phase3_build_budget_master_v2.py`
Expected: exactly six payloads and `qci_submission_performed=false`.

- [ ] **Step 2: Run the validator**

Run: `python scripts/phase3_validate_budget_master_v2.py`
Expected: all 15 gates pass and `BUDGET_MASTER_V2_READY_FOR_QCI: YES`.

- [ ] **Step 3: Run repository verification**

Run: `pytest -q`
Expected: all tests pass.

Run: `ruff check src/cmpo scripts tests/test_budget_master_v2.py`
Expected: no lint errors.

Run: `python -m compileall -q src scripts`
Expected: exit code 0.

- [ ] **Step 4: Verify no QCi artifacts or existing hashes changed**

Compare source checksums from the manifests, assert no `job_id`, request, or response was created under V2, and inspect `git diff --check`.

- [ ] **Step 5: Commit using the repository Lore protocol and push to `main`**

The commit message records the metadata-only V1 constraint, the global-master rationale, validation evidence, and that paid QCi execution was not tested or performed.
