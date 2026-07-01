import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

SR = 11025


def _wav_bytes(y: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV")
    buf.seek(0)
    return buf.read()


def test_job_lifecycle_with_forced_topology(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.matching_pipeline.get_settings", lambda: type(
        "S", (), {"jobs_data_dir": str(tmp_path)}
    )())

    rng = np.random.default_rng(7)
    dry = (rng.standard_normal(SR) * 0.2).astype(np.float32)
    reference = dry * 0.8  # trivially close target, cheap to optimize in a test

    with TestClient(app) as client:
        resp = client.post(
            "/jobs",
            files={
                "reference": ("reference.wav", _wav_bytes(reference), "audio/wav"),
                "sample": ("dry.wav", _wav_bytes(dry), "audio/wav"),
            },
            data={"goal_text": "match reference", "topology": "eq3"},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        status_resp = client.get(f"/jobs/{job_id}")
        assert status_resp.status_code == 200
        body = status_resp.json()
        assert body["status"] in {"done", "optimizing", "summarizing", "failed"}
        assert body["topology"] == ["eq3"]
