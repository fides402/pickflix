"""PluginHost abstraction so the optimizer never depends on how audio is
actually rendered.

- SimulatedPluginHost: real DSP (dsp_blocks.py), runs anywhere, used to prove
  the whole matching pipeline works without any VST3 plugins installed.
- DawDreamerPluginHost: loads and automates real VST3/AU plugins offline via
  DawDreamer. Requires requirements-native.txt and actual plugin binaries
  installed. Written against dawdreamer 0.8.3's verified API (make_plugin_processor,
  set_parameter(index, normalized_value), load_graph, get_audio(name), save_state) --
  not exercised against a real plugin binary since none were available while
  building this, but the API surface itself was confirmed against the
  installed package rather than guessed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.services.dsp_blocks import DSP_DISPATCH


@dataclass
class ChainStage:
    plugin_type: str
    params: dict[str, float]
    plugin_ref: str | None = None  # real plugin bundle path, set for real (non-simulated) stages


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


def _import_dawdreamer():
    try:
        import dawdreamer as daw
    except ImportError as exc:
        raise DawDreamerUnavailableError(
            "dawdreamer is not installed. Install requirements-native.txt on a "
            "machine with real VST3/AU plugins to use real-plugin matching."
        ) from exc
    return daw


def discover_real_plugin_params(bundle_path: str, sample_rate: int = 44100, block_size: int = 512) -> list[str]:
    """Parameter display names for a real VST3 bundle, in DawDreamer index
    order (index i's name is display_names[i]). Only needs instantiation, not
    a render, so this is cheap enough to call once when a plugin is selected
    in the UI, before any optimization starts."""
    daw = _import_dawdreamer()
    engine = daw.RenderEngine(sample_rate, block_size)
    plugin = engine.make_plugin_processor("probe", bundle_path)
    count = plugin.get_plugin_parameter_size()
    return [plugin.get_parameter_name(i) for i in range(count)]


class DawDreamerPluginHost(PluginHost):
    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        self._daw = _import_dawdreamer()
        self.sample_rate = sample_rate
        self.block_size = block_size

    def _build_graph(self, engine, chain: list[ChainStage], input_audio: np.ndarray):
        engine.make_playback_processor("input", input_audio)
        graph = [("input", [])]
        instances = []
        prev = "input"
        for i, stage in enumerate(chain):
            if not stage.plugin_ref:
                raise ValueError("DawDreamerPluginHost requires plugin_ref (bundle path) per stage")
            name = f"stage_{i}"
            plugin = engine.make_plugin_processor(name, stage.plugin_ref)
            for index_str, value in stage.params.items():
                plugin.set_parameter(int(index_str), float(value))
            instances.append((name, plugin))
            graph.append((name, [prev]))
            prev = name
        return graph, instances, prev

    def render(self, chain: list[ChainStage], audio: np.ndarray, sr: int) -> np.ndarray:
        if not chain:
            return audio
        engine = self._daw.RenderEngine(sr, self.block_size)
        graph, _instances, last_name = self._build_graph(engine, chain, audio)
        engine.load_graph(graph)
        engine.render(len(audio) / sr)
        return engine.get_audio(last_name)

    def save_chain_states(self, chain: list[ChainStage], out_dir: Path) -> list[Path]:
        """Writes each stage's raw plugin state chunk (via DawDreamer's
        save_state, the same binary blob a DAW's getStateInformation would
        produce) to out_dir/stage_<i>.bin, for container_export.py to embed
        in the Container VST3 preset."""
        out_dir.mkdir(parents=True, exist_ok=True)
        engine = self._daw.RenderEngine(self.sample_rate, self.block_size)
        silence = np.zeros(self.block_size, dtype=np.float32)
        graph, instances, _ = self._build_graph(engine, chain, silence)
        engine.load_graph(graph)

        paths = []
        for name, plugin in instances:
            state_path = out_dir / f"{name}.bin"
            plugin.save_state(str(state_path))
            paths.append(state_path)
        return paths
