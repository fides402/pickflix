import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.container_export import build_container_manifest
from app.services.jobs_store import jobs_store
from app.services.matching_pipeline import _job_dir, run_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("")
async def create_job(
    background_tasks: BackgroundTasks,
    reference: UploadFile = File(...),
    sample: UploadFile = File(...),
    goal_text: str = Form(""),
    topology: str = Form(""),  # comma-separated plugin types, or empty to let the LLM propose one
):
    job = jobs_store.create(goal_text=goal_text)
    job_dir = _job_dir(job.id)

    reference_path = job_dir / "reference_upload"
    input_path = job_dir / "input_upload"
    reference_path.write_bytes(await reference.read())
    input_path.write_bytes(await sample.read())

    forced_topology = [t.strip() for t in topology.split(",") if t.strip()] or None

    background_tasks.add_task(run_job, job.id, str(reference_path), str(input_path), forced_topology)
    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = jobs_store.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "goal_text": job.goal_text,
        "topology": job.topology,
        "topology_reasoning": job.topology_reasoning,
        "llm_model_used": job.llm_model_used,
        "baseline_distance": job.baseline_distance,
        "final_distance": job.final_distance,
        "used_identity_fallback": job.used_identity_fallback,
        "summary_text": job.summary_text,
        "error": job.error,
        "iterations": [
            {"stage": e.stage, "generation": e.generation, "distance": e.distance} for e in job.iterations
        ],
    }


@router.get("/{job_id}/manifest")
async def get_manifest(job_id: str):
    job_dir = _job_dir(job_id)
    manifest_path = job_dir / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(404, "manifest not ready yet")
    return json.loads(manifest_path.read_text())


@router.get("/{job_id}/container-manifest")
async def get_container_manifest(job_id: str):
    job = jobs_store.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.final_chain is None:
        raise HTTPException(404, "chain not ready yet")
    return build_container_manifest(job.final_chain)


@router.get("/{job_id}/audio")
async def get_matched_audio(job_id: str):
    job_dir = _job_dir(job_id)
    audio_path = job_dir / "matched_output.wav"
    if not audio_path.is_file():
        raise HTTPException(404, "matched audio not ready yet")
    return FileResponse(str(audio_path), media_type="audio/wav", filename="matched_output.wav")
