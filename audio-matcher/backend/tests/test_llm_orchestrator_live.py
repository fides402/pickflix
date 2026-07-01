"""Live integration test: real call against the OpenRouter API using the free
model list. Skipped automatically if no API key is configured. Not part of the
default fast unit-test loop (network + free-tier rate limits), run explicitly:
    PYTHONPATH=. pytest tests/test_llm_orchestrator_live.py -q -m live
"""
import os

import pytest

from app.services.audio_features import AudioFeatures
from app.services.llm_orchestrator import VALID_PLUGIN_TYPES, propose_topology
from app.services.openrouter_client import OpenRouterClient

pytestmark = pytest.mark.live

requires_key = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)


@requires_key
@pytest.mark.asyncio
async def test_propose_topology_returns_valid_stage_list():
    client = OpenRouterClient()
    fake_reference = AudioFeatures(
        log_mel_mean=[0.0], mfcc_mean=[0.0], spectral_centroid=4200.0,
        spectral_bandwidth=1800.0, spectral_flux=0.4, rms=0.08, crest_factor=6.0,
    )
    topology, reasoning, model_used = await propose_topology(
        client, fake_reference, goal_text="make a dry drum loop punchier and warmer, like the reference"
    )
    assert len(topology) > 0
    assert all(t in VALID_PLUGIN_TYPES for t in topology)
    assert model_used
    print(f"\nmodel_used={model_used}\ntopology={topology}\nreasoning={reasoning}")
