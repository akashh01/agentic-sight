"""logging_config.py — one place that configures logging for the whole app.

Every module does `logger = logging.getLogger(__name__)` and logs through
that; nothing calls basicConfig except this function. Call setup_logging()
once, near the top of whichever entrypoint is running (main.py, api.py, or
any module's own `if __name__ == "__main__":` block for standalone testing).

Level is controlled by the LOG_LEVEL env var (default INFO) — set
LOG_LEVEL=DEBUG in .env to see full prompts and raw model responses.
"""

import logging
import os


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
