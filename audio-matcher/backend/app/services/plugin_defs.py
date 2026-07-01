"""Parameter specs for both the simulated stage types (SimulatedPluginHost)
and real VST3 plugins selected by the user (DawDreamerPluginHost).

Simulated types stand in for VST3 categories (EQ / compressor / saturation /
reverb) so the matching loop can be built and proven end-to-end without any
VST3 plugins installed. Real plugins are registered dynamically at runtime
(see register_real_plugin): DawDreamer's set_parameter(index, value) always
takes a value normalized to [0, 1] regardless of the plugin's native units
(confirmed against the installed dawdreamer package), so every real
parameter's bounds are simply [0, 1] -- there is no per-plugin unit
conversion to discover, only the parameter count and names.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParamSpec:
    name: str
    low: float
    high: float
    default: float


PLUGIN_PARAM_SPECS: dict[str, list[ParamSpec]] = {
    "eq3": [
        ParamSpec("band1_freq", 60, 400, 120),
        ParamSpec("band1_gain_db", -12, 12, 0),
        ParamSpec("band1_q", 0.3, 3.0, 0.8),
        ParamSpec("band2_freq", 400, 3000, 1000),
        ParamSpec("band2_gain_db", -12, 12, 0),
        ParamSpec("band2_q", 0.3, 3.0, 0.8),
        ParamSpec("band3_freq", 3000, 12000, 6000),
        ParamSpec("band3_gain_db", -12, 12, 0),
        ParamSpec("band3_q", 0.3, 3.0, 0.8),
    ],
    "compressor": [
        ParamSpec("threshold_db", -40, 0, -18),
        ParamSpec("ratio", 1.0, 10.0, 3.0),
        ParamSpec("attack_ms", 0.5, 50.0, 5.0),
        ParamSpec("release_ms", 20.0, 400.0, 80.0),
        ParamSpec("makeup_gain_db", 0.0, 18.0, 0.0),
    ],
    "saturation": [
        ParamSpec("drive", 1.0, 20.0, 1.0),
        ParamSpec("mix", 0.0, 1.0, 0.0),
    ],
    "reverb": [
        ParamSpec("room_size", 0.1, 0.95, 0.3),
        ParamSpec("decay", 0.1, 0.95, 0.5),
        ParamSpec("wet", 0.0, 1.0, 0.0),
    ],
}


@dataclass
class RealPluginRegistration:
    bundle_path: str
    param_specs: list[ParamSpec]  # name == str(dawdreamer parameter index)
    display_names: list[str] = field(default_factory=list)  # same order, human-readable


_REAL_PLUGIN_REGISTRY: dict[str, RealPluginRegistration] = {}


def register_real_plugin(plugin_type: str, bundle_path: str, display_names: list[str]) -> None:
    """Registers a real VST3 plugin (found by the scanner, chosen by the user)
    under a synthetic type string (e.g. "real:<plugin_id>") so the existing
    optimizer/plugin_defs machinery -- built and tested against the four
    simulated types -- can drive it identically, with no separate code path.
    display_names[i] is whatever DawDreamer's get_parameter_name(i) returned;
    the ParamSpec.name stays the string index since that's what
    DawDreamerPluginHost.set_parameter(index, value) actually needs.
    """
    specs = [ParamSpec(name=str(i), low=0.0, high=1.0, default=0.5) for i in range(len(display_names))]
    _REAL_PLUGIN_REGISTRY[plugin_type] = RealPluginRegistration(bundle_path, specs, display_names)


def is_real_plugin(plugin_type: str) -> bool:
    return plugin_type in _REAL_PLUGIN_REGISTRY


def real_plugin_bundle_path(plugin_type: str) -> str:
    return _REAL_PLUGIN_REGISTRY[plugin_type].bundle_path


def real_plugin_display_names(plugin_type: str) -> list[str]:
    return _REAL_PLUGIN_REGISTRY[plugin_type].display_names


def _specs_for(plugin_type: str) -> list[ParamSpec]:
    if plugin_type in PLUGIN_PARAM_SPECS:
        return PLUGIN_PARAM_SPECS[plugin_type]
    if plugin_type in _REAL_PLUGIN_REGISTRY:
        return _REAL_PLUGIN_REGISTRY[plugin_type].param_specs
    raise KeyError(f"Unknown plugin type: {plugin_type!r} (not simulated, not registered as real)")


def default_params(plugin_type: str) -> dict[str, float]:
    return {p.name: p.default for p in _specs_for(plugin_type)}


def identity_params(plugin_type: str) -> dict[str, float]:
    """True bypass params, distinct from default_params: e.g. the compressor's
    default ratio (3.0) already compresses, so it is NOT a no-op like the
    other plugin types' defaults are. For real plugins there is no reliable
    universal bypass state (no generic way to detect a "mix"/"bypass"
    parameter by name), so this just returns the neutral 0.5 default --
    optimize_chain_greedy's fallback also compares against skipping the
    stage/chain entirely, which is the real safety net for real plugins."""
    params = default_params(plugin_type)
    if plugin_type == "compressor":
        params["ratio"] = 1.0
        params["makeup_gain_db"] = 0.0
    return params


def bounds(plugin_type: str) -> list[tuple[float, float]]:
    return [(p.low, p.high) for p in _specs_for(plugin_type)]


def param_names(plugin_type: str) -> list[str]:
    return [p.name for p in _specs_for(plugin_type)]
