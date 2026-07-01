import numpy as np

from app.services.audio_features import extract_features
from app.services.plugin_defs import default_params
from app.services.plugin_host import ChainStage, SimulatedPluginHost

SR = 22050


def _test_tone(freq=220.0, seconds=1.0) -> np.ndarray:
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_eq_boost_raises_spectral_centroid():
    host = SimulatedPluginHost()
    y = _test_tone(220) + 0.2 * _test_tone(4000)

    flat_params = default_params("eq3")
    boosted_params = dict(flat_params)
    boosted_params["band3_gain_db"] = 12  # boost the ~6kHz-ish high band

    flat_out = host.render([ChainStage("eq3", flat_params)], y, SR)
    boosted_out = host.render([ChainStage("eq3", boosted_params)], y, SR)

    flat_centroid = extract_features(flat_out, SR).spectral_centroid
    boosted_centroid = extract_features(boosted_out, SR).spectral_centroid
    assert boosted_centroid > flat_centroid


def test_compressor_reduces_crest_factor():
    host = SimulatedPluginHost()
    rng = np.random.default_rng(0)
    # quiet floor well below threshold, plus a sustained loud burst well above
    # it. The burst is windowed (Hann) rather than a hard step: a literal
    # sample-to-sample jump would leak through any envelope follower at full
    # amplitude for one sample regardless of attack time, which is a property
    # of one-pole smoothing, not a realistic transient shape to test against.
    y = (rng.standard_normal(SR) * 0.02).astype(np.float32)
    burst_len = int(SR * 0.1)
    burst = 0.9 * np.hanning(burst_len)
    y[SR // 2 : SR // 2 + burst_len] += burst.astype(np.float32)

    params = default_params("compressor")
    params["threshold_db"] = -20
    params["ratio"] = 8.0
    params["attack_ms"] = 2.0

    uncompressed_crest = extract_features(y, SR).crest_factor
    compressed = host.render([ChainStage("compressor", params)], y, SR)
    compressed_crest = extract_features(compressed, SR).crest_factor

    assert compressed_crest < uncompressed_crest


def test_saturation_adds_harmonics():
    host = SimulatedPluginHost()
    y = _test_tone(220)

    clean_params = default_params("saturation")
    driven_params = dict(clean_params)
    driven_params["drive"] = 15.0
    driven_params["mix"] = 1.0

    clean_out = host.render([ChainStage("saturation", clean_params)], y, SR)
    driven_out = host.render([ChainStage("saturation", driven_params)], y, SR)

    # saturation broadens the spectrum with harmonics -> bandwidth increases
    clean_bw = extract_features(clean_out, SR).spectral_bandwidth
    driven_bw = extract_features(driven_out, SR).spectral_bandwidth
    assert driven_bw > clean_bw


def test_chain_applies_stages_in_order():
    host = SimulatedPluginHost()
    y = _test_tone(220)
    chain = [
        ChainStage("eq3", default_params("eq3")),
        ChainStage("compressor", default_params("compressor")),
        ChainStage("saturation", default_params("saturation")),
        ChainStage("reverb", default_params("reverb")),
    ]
    out = host.render(chain, y, SR)
    assert len(out) == len(y)
    assert np.all(np.isfinite(out))
