"""Builds the chain_manifest.json consumed by container-plugin's
ContainerProcessor::loadChainFromManifest.

Prefers each stage's raw state_chunk_base64 (from DawDreamer's save_state,
the same binary blob a DAW's getStateInformation would produce) when present
-- it round-trips through the real plugin's own setStateInformation, so it
also preserves non-parameter state (e.g. a sampler's loaded sample) that a
named-parameter list would drop. Falls back to named parameters when only
those are available. SimulatedPluginHost stages (used to prove the matching
loop works with no VST3 plugins installed) have no plugin_ref at all -- those
are reported as unresolved instead of producing a broken preset.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.plugin_scanner import PluginInfo, audio_module_cid
from app.services.vstpreset_writer import write_vstpreset


class ContainerClassIdUnavailableError(RuntimeError):
    pass


def write_container_vstpreset(container_plugin: PluginInfo, manifest: dict, output_path: str | Path) -> None:
    """Combines the container manifest with the *compiled* Container VST3's
    own class ID (read from its moduleinfo.json via the plugin scanner, once
    the user has built container-plugin/ and pointed PLUGIN_SCAN_PATHS at it)
    into a real, directly-loadable .vstpreset -- no DAW round-trip needed.

    The component-state bytes must match what ContainerProcessor::getStateInformation
    actually writes: JUCE's MemoryOutputStream::writeString() emits UTF-8 bytes
    followed by a single null terminator, which is what's replicated here.
    Experimental: unverified against the compiled plugin/a real DAW, since
    neither was available while building this -- see vstpreset_writer.py's
    module docstring for the fallback if a preset generated this way doesn't
    load.
    """
    cid = audio_module_cid(container_plugin)
    if not cid:
        raise ContainerClassIdUnavailableError(
            f"No VST3 class ID found for {container_plugin.bundle_path} -- "
            "make sure it's the compiled Container VST3 (with a moduleinfo.json)."
        )

    json_bytes = json.dumps(manifest).encode("utf-8") + b"\x00"
    write_vstpreset(output_path, class_id_hex=cid, component_state=json_bytes)


def build_container_manifest(chain: list[dict]) -> dict:
    stages = []
    unresolved_types = []
    for stage in chain:
        plugin_ref = stage.get("plugin_ref")
        if not plugin_ref:
            unresolved_types.append(stage["plugin_type"])
            continue

        entry = {"bundle_path": plugin_ref}
        if stage.get("state_chunk_base64"):
            entry["state_chunk_base64"] = stage["state_chunk_base64"]
        else:
            entry["parameters"] = stage.get("params", {})
        stages.append(entry)

    return {
        "chain": stages,
        "ready": len(unresolved_types) == 0 and len(stages) > 0,
        "unresolved_simulated_stages": unresolved_types,
    }
