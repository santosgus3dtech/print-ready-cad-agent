import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .knowledge import search_knowledge
from .models import PROFILES, BriefRequest, DesignSpec
from .planner import plan_brief
from .service import generate_part
from .store import ROOT, get_job, job_directory, recent_jobs

load_dotenv(ROOT / ".env", override=False)
app = FastAPI(title="PrintReady CAD Agent", version=__version__)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])


@app.middleware("http")
async def same_origin_writes(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin writes are disabled."}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__, "physical_controls": False}


@app.get("/api/catalog")
def catalog():
    return {
        "printers": PROFILES,
        "templates": ["enclosure", "bracket", "adapter"],
        "default_spec": DesignSpec().model_dump(),
    }


@app.get("/api/knowledge")
def knowledge(q: str = "enclosure clearance", limit: int = 3):
    return search_knowledge(q[:1500], min(max(limit, 1), 7))


@app.post("/api/plan")
def plan(request: BriefRequest):
    try:
        return plan_brief(request)
    except ValidationError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/jobs", status_code=201)
def create_job(spec: DesignSpec):
    return generate_part(spec)


@app.get("/api/jobs")
def list_jobs():
    return recent_jobs()


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    try:
        job = get_job(job_id)
    except ValueError as error:
        raise HTTPException(404, "Job not found.") from error
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/api/jobs/{job_id}/files/{filename}")
def download(job_id: str, filename: str):
    job = job_detail(job_id)
    if filename not in job["artifacts"] or Path(filename).name != filename:
        raise HTTPException(404, "Artifact not found.")
    path = job_directory(job_id) / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact not found.")
    return FileResponse(
        path, filename=filename, media_type="model/gltf-binary" if filename.endswith(".glb") else None
    )


@app.get("/api/slicer")
def slicer_status():
    from .slicer import capabilities

    return capabilities()


@app.post("/api/jobs/{job_id}/slice")
def slice_job(job_id: str):
    from .slicer import slice_model

    return slice_model(job_detail(job_id))


frontend = ROOT / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")


def main():
    import uvicorn

    uvicorn.run(
        "printready.api:app",
        host=os.getenv("PRINTREADY_HOST", "127.0.0.1"),
        port=int(os.getenv("PRINTREADY_PORT", "8012")),
    )
