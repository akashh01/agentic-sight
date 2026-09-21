import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ollama models 
AGENT_MODEL = os.getenv("AGENT_MODEL", "llama3.1:8b")
CHEAP_MODEL = os.getenv("CHEAP_MODEL", "moondream")
EXPENSIVE_MODEL = os.getenv("EXPENSIVE_MODEL", "llava:13b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SAMPLE_RATE_FPS = float(os.getenv("SAMPLE_RATE_FPS", "0.5"))  # 0.5 fps = one frame every 2s
ESCALATION_MARGIN = float(os.getenv("ESCALATION_MARGIN", "0.15"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
# How far (in seconds) before/after a candidate hit to check for confirmation
# before trusting it and stopping the scan. Set to 0 to disable and trust
# the first hit immediately (old behavior).
CONFIRMATION_OFFSET_SEC = float(os.getenv("CONFIRMATION_OFFSET_SEC", "1.0"))
# Master switch for tiered escalation. When false, the detector graph never
# escalates to the expensive model, regardless of how ambiguous the cheap
# tier's confidence is — every frame is decided on the cheap tier alone.
ESCALATION_ENABLED = _get_bool("ESCALATION_ENABLED", True)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")

DRY_RUN_EMAIL = _get_bool("DRY_RUN_EMAIL", True)

DB_PATH = os.getenv("DB_PATH", "events.db")

# Observability — local self-hosted Phoenix (run with `phoenix serve`, no
# Docker needed). Setup is skipped automatically if arize-phoenix / the
# collector isn't reachable — see observability.py.
PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
)
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "agentic-sight")
