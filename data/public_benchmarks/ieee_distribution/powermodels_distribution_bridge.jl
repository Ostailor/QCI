# PowerModelsDistribution bridge placeholder for CMPO Phase 3
#
# Usage after installing Julia + PowerModelsDistribution:
#   julia data/public_benchmarks/ieee_distribution/powermodels_distribution_bridge.jl path/to/Master.dss
#
# This script intentionally stays lightweight in the Python repo. It records the
# expected bridge entrypoint so judges can connect IEEE OpenDSS feeders without
# changing the CMPO benchmark ladder.

using JSON

function main()
    if length(ARGS) < 1
        error("Pass an OpenDSS feeder Master.dss path")
    end
    feeder = ARGS[1]
    out = Dict(
        "source_file" => feeder,
        "bridge" => "PowerModelsDistribution/OpenDSS",
        "cmpo_transformation" => [
            "parse feeder buses/lines/loads/regulators",
            "select candidate microgrid/PCC buses deterministically",
            "add seeded CMPO PV/BESS/critical-load overlays",
            "export CMPO payload input YAML/JSON"
        ]
    )
    println(JSON.json(out))
end

main()
