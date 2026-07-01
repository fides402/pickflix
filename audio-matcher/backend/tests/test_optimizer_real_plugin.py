"""Verifies the real-plugin wiring (plugin_ref threading through _make_stage,
dynamic [0,1]-bounded params from plugin_defs.register_real_plugin) without
needing an actual VST3 binary: a stub PluginHost stands in for
DawDreamerPluginHost and asserts every stage for a registered real plugin type
carries its bundle path, exactly like the real host requires.
"""
import numpy as np
import pytest

from app.services import plugin_defs
from app.services.optimizer import optimize_chain_greedy
from app.services.plugin_host import ChainStage, PluginHost

SR = 11025


class StubRealPluginHost(PluginHost):
    """Pretends param '0' is a simple linear gain knob in [0, 1]."""

    def render(self, chain: list[ChainStage], audio: np.ndarray, sr: int) -> np.ndarray:
        out = audio
        for stage in chain:
            if plugin_defs.is_real_plugin(stage.plugin_type):
                assert stage.plugin_ref, f"real stage {stage.plugin_type} missing plugin_ref"
            out = out * stage.params["0"]
        return out


@pytest.fixture
def fake_real_plugin():
    plugin_defs.register_real_plugin("real:fakegain", "/fake/path/FakeGain.vst3", ["Gain"])
    yield "real:fakegain"
    del plugin_defs._REAL_PLUGIN_REGISTRY["real:fakegain"]


def _noise(seed=0, seconds=0.5):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(int(SR * seconds)) * 0.3).astype(np.float32)


def test_real_plugin_stage_carries_bundle_path_and_converges(fake_real_plugin):
    host = StubRealPluginHost()
    input_audio = _noise(seed=9)
    reference = input_audio * 0.35  # the "true" gain the fake plugin should converge to

    match = optimize_chain_greedy(
        host, [fake_real_plugin], input_audio, SR, reference,
        max_generations_per_stage=15, refine_generations=8,
    )

    assert len(match.chain) == 1
    assert match.chain[0].plugin_ref == "/fake/path/FakeGain.vst3"
    assert abs(match.chain[0].params["0"] - 0.35) < 0.05
