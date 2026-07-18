# IRC-CMPO validation report

The offline integer formulation and surrogate gates pass. No QCi job was submitted.

- valid: `True`
- variables: `33`
- total_num_levels: `66`
- passed: `True`
- maximum_nonzero: `1654.5914152335074`
- minimum_nonzero: `0.0860225438955136`
- dynamic_range: `19234.39298939171`
- effective_maximum_nonzero: `1676.5914152335074`
- effective_minimum_nonzero: `0.5744215996430293`
- effective_dynamic_range: `2918.747164583321`
- family_statistics: `{'coverage': {'count': 88, 'minimum_nonzero': 2.0, 'maximum_nonzero': 2.0, 'median_nonzero': 2.0}, 'interaction': {'count': 35, 'minimum_nonzero': 1.4255784003569707, 'maximum_nonzero': 277.74755937454086, 'median_nonzero': 11.422395641768334}, 'normalized_cost': {'count': 33, 'minimum_nonzero': 0.0860225438955136, 'maximum_nonzero': 1.1319091750320545, 'median_nonzero': 0.21174037095182077}, 'surrogate': {'count': 34, 'minimum_nonzero': 0.8693848932127689, 'maximum_nonzero': 1654.5914152335074, 'median_nonzero': 58.06670038472183}}`
- degree_distribution: `{0: 12, 1: 99, 2: 66, 3: 13}`
- reasons: `()`
- surrogate_gates_passed: `True`
- qci_jobs_submitted: `0`
- full_experiment_run: `False`
- ready_for_three_job_smoke: `True`
- installed_qci_versions: `{'qci-client': '5.0.0', 'eqc-models': '0.20.2'}`

## Hardware smoke status

After the offline report above was written, the gated toy integer smoke request
was submitted as job `6a5ba9ef08442f441bbb20c2`. QCi accepted the correct
integer problem/device configuration and exact uploaded polynomial, but the job
remained `QUEUED` without a `running_at` timestamp through
`2026-07-18T17:14:08Z`. Tests B and C were not submitted. No sample was
projected, and no full experiment was run. See `smoke/queue_diagnosis.md`.

- toy_native_feasible_rate: `unavailable_pending_response`
- reduced_master_job_id: `not_submitted_strict_stop`
- full_master_smoke_job_id: `not_submitted_strict_stop`
- integer_hardware_path_correctly_configured: `YES_REQUEST_CONFIRMED_RESPONSE_PENDING`
- IRC_CMPO_READY_FOR_FULL_RUN: `NO`
