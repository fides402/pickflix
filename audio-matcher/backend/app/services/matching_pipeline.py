"""Wires together: load audio -> LLM proposes topology -> staged CMA-ES
optimization (reporting each iteration back into the job state for the
frontend's live convergence chart) -> LLM writes a human-readable summary.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import librosa
import soundfile as sf

from app.config import get_settings
from app.services.audio_features import combined_distance, extract_features, feature_distance_breakdown
from app.services.jobs_store import IterationEvent, JobState, JobStatus, jobs_store
from app.services.llm_orchestrator import propose_topology, summarize_result
from app.services.openrouter_client import OpenRouterClient
from app.services.optimizer import optimize_chain_greedy
from app.services.plugin_host import SimulatedPluginHost

TARGET_SR = 22050


def _job_dir(job_id: str) -> Path:
    settings = get_settings()
    d = Path(settings.jobs_data_dir) / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _describe_chain(chain) -> str:
    parts = [f"{stage.plugin_type}({stage.params})" for stage in chain]
    return " -> ".join(parts)


async def run_job(job_id: str, reference_path: str, input_path: str, forced_topology: list[str] | None) -> None:
    job = jobs_store.get(job_id)
    assert job is not None
    client = OpenRouterClient()
    try:
        reference_audio, _ = librosa.load(reference_path, sr=TARGET_SR, mono=True)
        input_audio, _ = librosa.load(input_path, sr=TARGET_SR, mono=True)

        ref_features = extract_features(reference_audio, TARGET_SR)
        input_features = extract_features(input_audio, TARGET_SR)
        job.baseline_distance = combined_distance(
            feature_distance_breakdown(ref_features, input_features, reference_audio, input_audio, TARGET_SR)
        )

        if forced_topology:
            job.topology = forced_topology
            job.topology_reasoning = "user-selected topology"
        else:
            job.status = JobStatus.PROPOSING_TOPOLOGY
            topology, reasoning, model_used = await propose_topology(client, ref_features, job.goal_text)
            job.topology = topology
            job.topology_reasoning = reasoning
            job.llm_model_used = model_used

        def on_iteration(stage: str, generation: int, distance: float, params: dict) -> None:
            job.iterations.append(IterationEvent(stage=stage, generation=generation, distance=distance))

        job.status = JobStatus.OPTIMIZING
        host = SimulatedPluginHost()
        match_result = await asyncio.to_thread(
            optimize_chain_greedy,
            host, job.topology, input_audio, TARGET_SR, reference_audio,
            25, 15, on_iteration,
        )

        job.final_chain = [{"plugin_type": s.plugin_type, "params": s.params} for s in match_result.chain]
        job.final_distance = match_result.final_distance
        job.used_identity_fallback = match_result.used_identity_fallback

        job_dir = _job_dir(job_id)
        matched_audio = host.render(match_result.chain, input_audio, TARGET_SR)
        sf.write(str(job_dir / "matched_output.wav"), matched_audio, TARGET_SR)
        manifest = {
            "topology": job.topology,
            "topology_reasoning": job.topology_reasoning,
            "chain": job.final_chain,
            "final_distance": job.final_distance,
            "baseline_distance": job.baseline_distance,
            "used_identity_fallback": job.used_identity_fallback,
            "sample_rate": TARGET_SR,
        }
        (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        job.status = JobStatus.SUMMARIZING
        job.summary_text = await summarize_result(client, _describe_chain(match_result.chain), match_result.final_distance)

        job.status = JobStatus.DONE
    except Exception as exc:  # noqa: BLE001 - surface any failure to the job status for the API/UI
        job.status = JobStatus.FAILED
        job.error = str(exc)
