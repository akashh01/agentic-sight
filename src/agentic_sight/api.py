import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from agentic_sight import config
from agentic_sight.logging_config import setup_logging
from agentic_sight.observability import setup_observability
from agentic_sight.pipeline import run_pipeline
from agentic_sight.schema import RunSummary

setup_logging()
logger = logging.getLogger(__name__)

setup_observability(config.PHOENIX_PROJECT_NAME, config.PHOENIX_COLLECTOR_ENDPOINT)

app = FastAPI(title="agentic-sight")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/defaults")
def defaults() -> dict:
    return {
        "recipient_email": config.RECIPIENT_EMAIL,
        "escalation_enabled": config.ESCALATION_ENABLED,
        "agent_model": config.AGENT_MODEL,
        "cheap_model": config.CHEAP_MODEL,
        "expensive_model": config.EXPENSIVE_MODEL,
        "sample_rate_fps": config.SAMPLE_RATE_FPS,
        "dry_run_email": config.DRY_RUN_EMAIL,
    }


@app.post("/runs", response_model=RunSummary)
def create_run(
    intent: str = Form(...),
    recipient_email: str = Form(...),
    video: UploadFile = File(...),
) -> RunSummary:
    logger.info("POST /runs intent=%r video_filename=%s", intent, video.filename)

    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        return run_pipeline(intent, tmp_path, recipient_email)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


    # uv run uvicorn agentic_sight.api:app --reload
    # curl -X POST localhost:8000/runs \
    #      -F intent="flag anyone without a hard hat in the marked zone" \
    #      -F recipient_email=safety@example.com \
    #      -F video=@videos/test.mp4