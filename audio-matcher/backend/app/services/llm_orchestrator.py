"""LLM sits at the edges of the pipeline only: proposing a starting chain
topology from a semantic description of the reference, and explaining/
diagnosing stalls between optimizer stages. It never runs inside the CMA-ES
hot loop (too slow, non-deterministic, unnecessary for pure numeric search).
"""
from __future__ import annotations

import json
import re

from app.services.audio_features import AudioFeatures
from app.services.openrouter_client import OpenRouterClient

VALID_PLUGIN_TYPES = ["eq3", "compressor", "saturation", "reverb"]

_TOPOLOGY_SYSTEM_PROMPT = f"""You are an audio engineering assistant helping design an effect chain \
to transform a dry sample so it matches the timbral character of a reference recording.

Available effect-chain stages you may use, in any subset/order: {VALID_PLUGIN_TYPES}.

Given a textual summary of the reference audio's measured features and the user's goal, reply with ONLY \
a JSON object of the form:
{{"topology": ["eq3", "compressor", "saturation"], "reasoning": "one short sentence"}}
Do not include markdown fences or any other text."""


def _feature_summary_text(features: AudioFeatures) -> str:
    return (
        f"spectral_centroid={features.spectral_centroid:.0f}Hz, "
        f"spectral_bandwidth={features.spectral_bandwidth:.0f}Hz, "
        f"spectral_flux={features.spectral_flux:.3f}, "
        f"rms_loudness={features.rms:.4f}, "
        f"crest_factor={features.crest_factor:.2f}"
    )


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text!r}")
    return json.loads(match.group(0))


async def propose_topology(
    client: OpenRouterClient,
    reference_features: AudioFeatures,
    goal_text: str,
    allowed_types: list[str] | None = None,
) -> tuple[list[str], str, str]:
    """Returns (topology, reasoning, model_used). Falls back to a sensible
    default topology if the LLM response can't be parsed."""
    allowed = allowed_types or VALID_PLUGIN_TYPES
    user_prompt = (
        f"Goal: {goal_text}\n"
        f"Reference audio features: {_feature_summary_text(reference_features)}\n"
        f"Allowed stages for this run: {allowed}"
    )
    content, model_used = await client.chat_json(
        messages=[
            {"role": "system", "content": _TOPOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1200,
    )
    try:
        parsed = _extract_json(content)
        topology = [t for t in parsed["topology"] if t in allowed]
        if not topology:
            raise ValueError("empty/invalid topology from LLM")
        return topology, parsed.get("reasoning", ""), model_used
    except (ValueError, KeyError, json.JSONDecodeError):
        return [t for t in ["eq3", "compressor", "saturation", "reverb"] if t in allowed], "fallback: default topology (LLM response unparseable)", model_used


async def diagnose_stall(
    client: OpenRouterClient, stage_name: str, distance_breakdown: dict[str, float]
) -> str:
    worst = max(distance_breakdown, key=distance_breakdown.get)
    prompt = (
        f"Optimization for stage '{stage_name}' has plateaued. Per-feature distance breakdown: "
        f"{distance_breakdown}. The largest residual gap is in '{worst}'. In one short sentence, "
        f"suggest what kind of processing change might close that gap."
    )
    content, _ = await client.chat_json(
        messages=[{"role": "user", "content": prompt}], max_tokens=1000
    )
    return content.strip()


async def summarize_result(client: OpenRouterClient, chain_description: str, final_distance: float) -> str:
    prompt = (
        f"An audio effect chain was tuned to match a reference sound. Final chain: {chain_description}. "
        f"Final residual distance score: {final_distance:.4f} (lower is closer). "
        f"Write a short (2-3 sentence) human-readable preset description for a producer, in plain language."
    )
    content, _ = await client.chat_json(messages=[{"role": "user", "content": prompt}], max_tokens=1000)
    return content.strip()
