import numpy as np

from app.services.audio_features import combined_distance, extract_features, feature_distance_breakdown
from app.services.optimizer import optimize_chain_greedy, optimize_stage
from app.services.plugin_defs import default_params
from app.services.plugin_host import ChainStage, SimulatedPluginHost

SR = 11025  # keep it small: faster STFTs => faster CMA-ES iterations in tests


def _noise(seed=0, seconds=0.5):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(int(SR * seconds)) * 0.3).astype(np.float32)


def _distance(a, b):
    fa, fb = extract_features(a, SR), extract_features(b, SR)
    return combined_distance(feature_distance_breakdown(fa, fb, a, b, SR))


def test_single_stage_optimizer_converges_towards_known_target():
    host = SimulatedPluginHost()
    input_audio = _noise(seed=1)

    target_params = default_params("eq3")
    target_params["band3_gain_db"] = 9.0
    target_params["band3_freq"] = 5000
    reference = host.render([ChainStage("eq3", target_params)], input_audio, SR)

    baseline_distance = _distance(reference, input_audio)

    result = optimize_stage(
        host, "eq3", prefix=[], suffix=[], input_audio=input_audio, sr=SR,
        ref_audio=reference, max_generations=20, popsize=12,
    )

    assert result.distance < baseline_distance * 0.5


def test_greedy_chain_optimizer_improves_over_defaults():
    host = SimulatedPluginHost()
    input_audio = _noise(seed=2)

    target_eq = default_params("eq3")
    target_eq["band1_gain_db"] = -6.0
    target_comp = default_params("compressor")
    target_comp["ratio"] = 6.0
    target_comp["threshold_db"] = -22.0
    reference = host.render(
        [ChainStage("eq3", target_eq), ChainStage("compressor", target_comp)], input_audio, SR
    )

    baseline_distance = _distance(reference, input_audio)

    match = optimize_chain_greedy(
        host, ["eq3", "compressor"], input_audio, SR, reference,
        max_generations_per_stage=15, refine_generations=10,
    )

    assert match.final_distance < baseline_distance * 0.5
    assert len(match.chain) == 2


def test_optimizer_never_returns_worse_than_doing_nothing():
    """If a requested stage isn't actually needed to approach the reference
    (e.g. asking for a compressor when the reference has no dynamics change),
    greedy per-stage search can converge to a locally-stuck combo worse than
    the untouched input. The pipeline must fall back to identity rather than
    hand back a chain that makes things worse."""
    host = SimulatedPluginHost()
    input_audio = _noise(seed=4)
    # reference IS the input, unprocessed: no eq/compressor combo should beat identity
    reference = input_audio.copy()
    baseline_distance = _distance(reference, input_audio)
    assert baseline_distance < 1e-6

    match = optimize_chain_greedy(
        host, ["eq3", "compressor"], input_audio, SR, reference,
        max_generations_per_stage=8, refine_generations=5,
    )

    assert match.final_distance <= baseline_distance + 1e-6
    assert match.used_identity_fallback
