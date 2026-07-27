# ARPA-E GO Retained Slice

The final Phase 3 package keeps one public ARPA-E GO benchmark slice:

- Benchmark: `Network_01O-020`
- Files: `case.raw`, `case.con`, `case.rop`, `case.inl`
- Location: `data/upstream/arpae-go/extracted/.../Network_01O-020/`
- Scenario used for the retained public adapter: `scenario_1`

Why this narrow slice is retained:

- It is the exact public source referenced by `configs/phase3_sc_cmpo_arpae.yaml`.
- It is sufficient to audit the published SC-CMPO benchmark transformation.
- It avoids shipping unrelated challenge networks or historical experiments.

The download manifest remains under `data/upstream/arpae-go/download_manifest.csv` for source URL and checksum provenance.

Verify the retained slice and download provenance without writing:

```bash
python scripts/phase3_check_arpae_go.py --dry-run
```

Download the pinned public archive and extract the benchmark slice when it is missing:

```bash
python scripts/phase3_fetch_public_benchmarks.py --family arpae_go
```

The source is the ARPA-E GO Challenge 1 Original Dataset 2 Offline Edition 2 published through OpenEI. The exact URL, checksum, version, and local path are recorded in `download_manifest.csv` and `results/phase3/sc_cmpo/public_benchmark_provenance.csv`.
