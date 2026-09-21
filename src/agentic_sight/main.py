import argparse
import logging

from agentic_sight import config
from agentic_sight.logging_config import setup_logging
from agentic_sight.observability import setup_observability
from agentic_sight.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Run the Agentic Sight detection pipeline end-to-end")
    parser.add_argument("--intent", required=True, help="e.g. 'flag anyone without a hard hat in the marked zone'")
    parser.add_argument("--video", required=True, help="path to a video file")
    parser.add_argument("--recipient", required=True, help="alert email recipient")
    args = parser.parse_args()

    setup_observability(config.PHOENIX_PROJECT_NAME, config.PHOENIX_COLLECTOR_ENDPOINT)

    summary = run_pipeline(args.intent, args.video, args.recipient)
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()


#     uv run python -m agentic_sight.main \
#         --intent "flag anyone without a hard hat in the marked zone" \
#         --video videos/test.mp4 \
#         --recipient safety@example.com


#     uv run agentic-sight --intent "..." --video videos/test.mp4 --recipient safety@example.com