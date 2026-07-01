from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROPOSING_TOPOLOGY = "proposing_topology"
    OPTIMIZING = "optimizing"
    SUMMARIZING = "summarizing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class IterationEvent:
    stage: str
    generation: int
    distance: float
    at: float = field(default_factory=time.time)


@dataclass
class JobState:
    id: str
    status: JobStatus = JobStatus.PENDING
    goal_text: str = ""
    topology: list[str] = field(default_factory=list)
    topology_reasoning: str = ""
    llm_model_used: str = ""
    iterations: list[IterationEvent] = field(default_factory=list)
    final_chain: list[dict] | None = None
    final_distance: float | None = None
    baseline_distance: float | None = None
    used_identity_fallback: bool = False
    summary_text: str | None = None
    error: str | None = None


class JobsStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}

    def create(self, goal_text: str) -> JobState:
        job = JobState(id=str(uuid.uuid4()), goal_text=goal_text)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)


jobs_store = JobsStore()
