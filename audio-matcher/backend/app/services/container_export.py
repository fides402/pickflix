"""Builds the chain_manifest.json consumed by container-plugin's
ContainerProcessor::loadChainFromManifest. Only stages that carry a real
plugin_ref (a VST3 bundle path from the scanned catalog, set when the chain
was rendered through DawDreamerPluginHost) can be baked into a real preset --
SimulatedPluginHost stages (used to prove the matching loop in this sandbox)
have no such binary to reference, so they're reported as unresolved instead
of silently producing a broken preset.
"""
from __future__ import annotations


def build_container_manifest(chain: list[dict]) -> dict:
    stages = []
    unresolved_types = []
    for stage in chain:
        plugin_ref = stage.get("plugin_ref")
        if not plugin_ref:
            unresolved_types.append(stage["plugin_type"])
            continue
        stages.append({"bundle_path": plugin_ref, "parameters": stage["params"]})

    return {
        "chain": stages,
        "ready": len(unresolved_types) == 0 and len(stages) > 0,
        "unresolved_simulated_stages": unresolved_types,
    }
