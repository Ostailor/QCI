# ARPA-E GO Feasibility Check

## Dataset Checked
- Source family: ARPA-E Grid Optimization (GO) Competition public datasets on OEDI
- Selected resource key: `challenge1_original_dataset_2`
- Selected challenge: Challenge 1
- Selected title: Challenge 1 Original Dataset 2 Scenarios.zip
- OEDI submission: https://data.openei.org/submissions/6153
- DOI: 10.25984/2437761
- Local data directory: data/public_benchmarks/arpae_go

## Download And Local Availability
- Download status: downloaded
- Download URL: https://data.openei.org/files/6153/Challenge_1_Original_Dataset_2_Scenarios.zip
- Local archive: data/public_benchmarks/arpae_go/archives/Challenge_1_Original_Dataset_2_Scenarios.zip
- SHA-256: b438dab6d51492ff501cea1e9acb5ed3591873b188f8b844acaad0ef75749852
- Bytes: 10444056
- Local parseable/archive files found: 298

## Parse Result
- Can be parsed: yes
- Sample parsed: data/public_benchmarks/arpae_go/extracted/Challenge_1_Original_Dataset_2_Scenarios/Original_Dataset_Offline_Edition_2/Network_01O-020/scenario_1/case.raw

```json
{
  "can_parse": true,
  "path": "data/public_benchmarks/arpae_go/extracted/Challenge_1_Original_Dataset_2_Scenarios/Original_Dataset_Offline_Edition_2/Network_01O-020/scenario_1/case.raw",
  "records_or_lines": 1823,
  "section_counts": {
    "area": 1,
    "bus": 500,
    "facts": 0,
    "fixed_shunt": 0,
    "generator": 90,
    "gne": 0,
    "induction": 0,
    "interarea": 0,
    "load": 200,
    "multi_section_line": 0,
    "multi_terminal_dc": 0,
    "non_transformer_branch": 468,
    "owner": 0,
    "switched_shunt": 17,
    "transformer": 524,
    "transformer_impedance": 0,
    "two_terminal_dc": 0,
    "vsc_dc": 0,
    "zone": 0
  },
  "section_markers": [
    "0 / end bus section",
    "0 / end load section",
    "0 / end fixed shunt section",
    "0 / end generator section",
    "0 / end non-transformer branch section",
    "0 / end transformer section",
    "0 / end area section",
    "0 / end two terminal dc section",
    "0 / end vsc dc section",
    "0 / end transformer impedance section",
    "0 / end multi terminal dc section",
    "0 / end multi section line section",
    "0 / end zone section",
    "0 / end interarea section",
    "0 / end owner section",
    "0 / end facts section",
    "0 / end switched shunt section",
    "0 / end gne section",
    "0 / end induction section"
  ],
  "type": "raw"
}
```

## Fields That Map To CMPO
- network buses -> candidate microgrid/PCC nodes
- loads and demand snapshots -> base load profiles and stress multipliers
- generators and dispatch limits -> local generator capacity and operating limits
- generator cost data or ROP records -> generator operating cost approximations
- branches/transformers -> tie-line candidates and PCC availability stress inputs
- contingency files -> outage scenario templates
- renewable or scenario availability fields -> PV/resource stress factors when present

## Fields That Do Not Map Cleanly
- native AC voltage, reactive power, tap, phase-shifter, and shunt controls are outside the CMPO microgrid abstraction
- critical infrastructure labels are not supplied and must be synthesized or joined from another source
- customer counts, outage priority classes, PV, BESS, and islanding policy fields are not first-class GO fields
- full SCOPF feasibility semantics do not map directly to the Phase 3 repair feasibility metric
- multi-period market and unit-commitment details need reduction before CMPO payload export

## Recommendation
Yes, as an ARPA-E GO-derived microgrid stress adapter after synthetic microgrid overlays are generated.

Use this benchmark path only as an ARPA-E GO-derived microgrid stress adapter, not as an AC OPF or SCOPF reproduction.
