# Compressed Consensus Artifacts

Two complete consensus exports exceed GitHub's 100 MB per-file limit. Their
gzip-compressed copies are committed in this directory; the uncompressed local
files remain untouched and are excluded from Git only.

Restore the original files with:

```bash
gzip -dk consensus_manifest.json.gz
gzip -dk consensus_values.csv.gz
```

Use `compressed_artifact_manifest.csv` to verify compressed and restored file
sizes and SHA-256 checksums.
