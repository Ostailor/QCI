# Phase 3 Artifact Roles

This directory is the final public Phase 3 artifact boundary.

Artifact roles:

- `irc_cmpo/final/` — final IRC-CMPO paper and judge tables, figures, and summary markdown.
- `irc_cmpo/payloads/` and `irc_cmpo/unquantized_payloads/` — the final checked-in IRC-CMPO Hamiltonian payloads before and after Dirac-3 quantization.
- `irc_cmpo/qci/` — retained IRC-CMPO execution manifests; `requests/`, `responses/`, and `validations/` are immutable raw evidence.
- `sc_cmpo/final/` — final SC-CMPO system-level tables and figures.
- `sc_cmpo/qci_payloads/` — the final checked-in SC-CMPO public payload bundle.
- `sc_cmpo/qci/` — retained SC-CMPO execution manifests plus immutable per-payload request/response snapshots.
- `sc_cmpo/system_summary/` — compressed consensus and system-level trace summaries used by the final paper artifact.

Important distinction:

- `sc_cmpo/build_summary.json` records the payload-build step and intentionally says `qci_was_run=false`.
- Actual retained execution evidence lives under `sc_cmpo/qci/qci_run_manifest.json`, `sc_cmpo/qci/job_status.csv`, and, when included, the immutable `sc_cmpo/qci/*/repeat_000/` request/response snapshots.
- The submitted SC-CMPO payload bytes retain a legacy build-time `phase2_notice` key. Its “not submitted” text describes the build step only; it is not a Phase 2 result and is superseded by the completed execution manifests above. The key is left unchanged so the checked-in payloads remain the exact hardware inputs.

This separation is deliberate: build-time metadata documents payload construction, while execution manifests document what actually ran on QCi hardware.
