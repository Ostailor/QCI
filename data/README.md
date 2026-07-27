# Data Retention

This repo keeps only the public inputs needed to explain and reproduce the final Phase 3 artifact.

Retained canonical public data:

- `data/upstream/arpae-go/` — ARPA-E GO download manifest plus the exact `Network_01O-020` `case.raw`, `case.con`, `case.rop`, and `case.inl` files used by the SC-CMPO benchmark adapter.
- `data/upstream/ieee123/` — the retained IEEE 123 OpenDSS feeder snapshot and manifest used by the public IEEE 123 SC-CMPO and IRC-CMPO studies.
- `data/upstream/pglib-opf/` — the retained PGLib case manifests plus the exact `case14` and `case30` MATPOWER files used in the public benchmark ladder.
- `data/upstream/nrel-atb/` — the retained NREL ATB cost catalog slice and manifest used for upgrade-cost provenance.

The package script copies only the retained canonical public inputs above, not every upstream archive in the workspace.
