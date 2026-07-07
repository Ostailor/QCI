# ARPA-E GO Public Dataset Setup

This repository can use public ARPA-E Grid Optimization (GO) Challenge data as a bonus Phase 3 benchmark path.
The checker downloads from the Open Energy Data Initiative (OEDI) records rather than vendoring large archives.

Official dataset records:
- Challenge 1: https://data.openei.org/submissions/6153, DOI 10.25984/2437761
- Challenge 2: https://data.openei.org/submissions/6197, DOI 10.25984/2448433
- Challenge 3: https://data.openei.org/submissions/5997, DOI 10.25984/2426334

Default lightweight download:
- Resource key: `challenge1_original_dataset_2`
- Title: Challenge 1 Original Dataset 2 Scenarios.zip
- URL: https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip
- Expected size: 9.96 MB

Run:

```bash
python scripts/phase3_check_arpae_go.py
```

To choose a different public resource:

```bash
python scripts/phase3_check_arpae_go.py --list-resources
python scripts/phase3_check_arpae_go.py --discover-submission 5997
python scripts/phase3_check_arpae_go.py --resource-key challenge3_sandbox0 --max-download-mb 1000
```

Downloaded archives are stored in `data/upstream/arpae-go/archives/`, extracted cases in
`data/upstream/arpae-go/extracted/`, and SHA-256 provenance in `data/upstream/arpae-go/download_manifest.csv`.

For manual downloads, preserve the source archive name and record:
- source URL,
- challenge and dataset title,
- OEDI DOI or version/date,
- license or terms shown on the source page,
- SHA-256 checksum,
- local path,
- transformation notes.

The Phase 3 paper should describe any use of this path as an "ARPA-E GO-derived microgrid stress adapter",
not as a reproduction of the original AC OPF/SCOPF challenge.
