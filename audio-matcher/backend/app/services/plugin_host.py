"""PluginHost abstraction so the optimizer never depends on how audio is
actually rendered.

- SimulatedPluginHost: real DSP (dsp_blocks.py), runs anywhere, used to prove
  the whole matching pipeline works in this sandbox (no VST3 plugins here).
- DawDreamerPluginHost: loads and automates real VST3/AU plugins offline via
  DawDreamer. Requires requirements-native.txt and actual plugin binaries
  installed -- meant to run on the user's own machine, not this container.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from app.services.dsp_blocks import DSP_DISPATCH


@dataclass
class ChainStage:
    plugin_type: str
    params: dict[str, float]
    plugin_ref: str | None = None  # real plugin id from the scanned catalog, if applicable


class PluginHost(ABC):
    @abstractmethod
    def render(self, chain: list[ChainStage], audio: np.ndarray, sr: int) -> np.ndarray: ...


class SimulatedPluginHost(PluginHost):
    def render(self, chain: list[ChainStage], audio: np.ndarray, sr: int) -> np.ndarray:
        out = audio
        for stage in chain:
            fn = DSP_DISPATCH.get(stage.plugin_type)
            if fn is None:
                raise ValueError(f"Unknown simulated plugin type: {stage.plugin_type}")
            out = fn(out, sr, stage.params)
        return out


class DawDreamerUnavailableError(RuntimeError):
    pass


class DawDreamerPluginHost(PluginHost):
    """Real VST3/AU offline host. Not exercised in this sandbox (no plugins,
    no dawdreamer install) -- install requirements-native.txt and point
    bundle_paths at real plugins on a machine that has them."""

    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        try:
            import dawdreamer as daw  # noqa: F401
        except ImportError as exc:
            raise DawDreamerUnavailableError(
                "dawdreamer is not installed. Install requirements-native.txt on a "
                "machine with real VST3/AU plugins to use DawDreamerPluginHost."
            ) from exc
        self._daw = daw
        self._sample_rate = sample_rate
        self._block_size = block_size

    def render(self, chain: list[ChainStage], audio: np.ndarray, sr: int) -> np.ndarray:
        engine = self._daw.RenderEngine(sr, self._block_size)
        processors = []
        prev_name = "input"
        playback = engine.make_playback_processor(prev_name, audio)
        engine.load_graph([(prev_name, [])])
        graph = [(prev_name, [])]

        for i, stage in enumerate(chain):
            if not stage.plugin_ref:
                raise ValueError("DawDreamerPluginHost requires plugin_ref (bundle path) per stage")
            name = f"plugin_{i}"
            plugin = engine.make_plugin_processor(name, stage.plugin_ref)
            for param_name, value in stage.params.items():
                plugin.set_parameter(param_name, value)
            processors.append(plugin)
            graph.append((name, [prev_name]))
            prev_name = name

        engine.load_graph(graph)
        engine.render(len(audio) / sr)
        return engine.get_audio()

    def get_state_chunk(self, engine, plugin_name: str) -> bytes:
        return engine.get_plugin(plugin_name).get_state()
