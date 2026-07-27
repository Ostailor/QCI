# Results Retention

`results/` now serves one purpose: preserve the final Phase 3 judge/paper artifact and the provenance required to audit it.

Retention rules:

- Final tables, figures, and summary markdown live under `results/phase3/*/final/`.
- Reproducibility inputs, payload manifests, and benchmark provenance stay under the corresponding `irc_cmpo/` and `sc_cmpo/` trees.
- Raw QCi request/response evidence remains immutable in the `qci/` trees and is never rewritten by derived reporting.

Derived CSV, Markdown, and PNG outputs may be regenerated from the retained manifests, but the retained raw QCi evidence should be treated as append-never, edit-never provenance.
