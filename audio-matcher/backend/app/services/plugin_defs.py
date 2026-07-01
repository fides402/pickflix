"""Parameter specs for the simulated plugin types used by SimulatedPluginHost.

These stand in for real VST3 categories (EQ / compressor / saturation / reverb)
so the matching loop (feature extraction -> optimizer -> convergence) can be
built and proven end-to-end in an environment with no VST3 plugins installed.
DawDreamerPluginHost (see plugin_host.py) implements the same render() contract
against real plugins and is meant to be swapped in on a machine that has them.
"""
from __future__ import annotations

from dataclasses import dataclass


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


def default_params(plugin_type: str) -> dict[str, float]:
    return {p.name: p.default for p in PLUGIN_PARAM_SPECS[plugin_type]}


def identity_params(plugin_type: str) -> dict[str, float]:
    """True bypass params, distinct from default_params: e.g. the compressor's
    default ratio (3.0) already compresses, so it is NOT a no-op like the
    other plugin types' defaults are."""
    params = default_params(plugin_type)
    if plugin_type == "compressor":
        params["ratio"] = 1.0
        params["makeup_gain_db"] = 0.0
    return params


def bounds(plugin_type: str) -> list[tuple[float, float]]:
    return [(p.low, p.high) for p in PLUGIN_PARAM_SPECS[plugin_type]]


def param_names(plugin_type: str) -> list[str]:
    return [p.name for p in PLUGIN_PARAM_SPECS[plugin_type]]
