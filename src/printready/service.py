import hashlib
import json
import shutil
import threading
import time
from datetime import UTC, datetime
from uuid import uuid4

from .cad import generate_geometry
from .knowledge import search_knowledge
from .models import DesignSpec
from .store import job_directory, save_job

CAD_LOCK = threading.Lock()


def generate_part(spec: DesignSpec) -> dict:
    start = time.perf_counter()
    job_id = uuid4().hex
    directory = job_directory(job_id)
    directory.mkdir(parents=True)
    try:
        with CAD_LOCK:
            report = generate_geometry(spec, directory)
        artifacts = {}
        for path in directory.iterdir():
            artifacts[path.name] = {
                "url": f"/api/jobs/{job_id}/files/{path.name}",
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        job = {
            "id": job_id,
            "created_at": datetime.now(UTC).isoformat(),
            "spec": spec.model_dump(),
            "report": report,
            "artifacts": artifacts,
            "duration_ms": round((time.perf_counter() - start) * 1000),
            "evidence": search_knowledge(spec.template + " clearance wall slicer", 3),
            "slicer": {"status": "not_run"},
        }
        (directory / "report.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
        job["artifacts"]["report.json"] = {"url": f"/api/jobs/{job_id}/files/report.json"}
        save_job(job)
        return job
    except Exception:
        shutil.rmtree(directory)
        raise
