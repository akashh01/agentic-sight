import logging
import tempfile
import uuid

from agentic_sight import config
from agentic_sight.graphs.agent_graph import intent_to_task
from agentic_sight.graphs.detector_graph import run_detection
from agentic_sight.notifier import send_alert_email
from agentic_sight.schema import DetectionTask, Event, FrameResult, RunSummary
from agentic_sight.store import init_db, insert_event
from agentic_sight.video_input import extract_frame_at, extract_frames

logger = logging.getLogger(__name__)


def _confirm_with_adjacent_frames(
    video_path: str, candidate: FrameResult, task: DetectionTask, tmp_dir: str
) -> bool:
    """Check the frames just before/after a candidate hit before trusting it.

    Returns True (confirmed) if at least one checked neighbor also detects
    the violation, or if there were no neighbors to check (e.g. the hit is
    at the very start/end of the video — nothing to compare against, so we
    trust the original result rather than discard it).
    """
    offset = config.CONFIRMATION_OFFSET_SEC
    if offset <= 0:
        return True  # confirmation disabled — trust the first hit, old behavior

    checked = 0
    confirmations = 0
    for sign, label in ((-1, "before"), (1, "after")):
        t = candidate.frame.timestamp_sec + sign * offset
        if t < 0:
            continue
        try:
            neighbor = extract_frame_at(
                video_path, t, tmp_dir, tag=f"{candidate.frame.index}_{label}"
            )
        except (FileNotFoundError, ValueError) as exc:
            logger.debug("could not grab %s-neighbor for confirmation: %s", label, exc)
            continue

        checked += 1
        neighbor_result = run_detection(
            task, neighbor, config.CHEAP_MODEL, config.EXPENSIVE_MODEL, config.ESCALATION_MARGIN
        )
        logger.info(
            "confirmation check (%s, t=%.2fs): detected=%s confidence=%.2f",
            label, neighbor.timestamp_sec, neighbor_result.detected, neighbor_result.confidence,
        )
        if neighbor_result.detected:
            confirmations += 1

    if checked == 0:
        logger.info("no neighboring frames available to check — trusting the original hit")
        return True
    return confirmations >= 1


def run_pipeline(intent: str, video_path: str, recipient_email: str) -> RunSummary:
    run_id = str(uuid.uuid4())[:8]
    logger.info("run %s starting: intent=%r video=%s", run_id, intent, video_path)

    task = intent_to_task(intent, config.AGENT_MODEL)
    conn = init_db(config.DB_PATH)

    events = []
    frame_results = []
    frames_scanned = 0
    escalated_count = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        for frame in extract_frames(video_path, config.SAMPLE_RATE_FPS, out_dir=tmp_dir):
            frames_scanned += 1
            result = run_detection(
                task, frame, config.CHEAP_MODEL, config.EXPENSIVE_MODEL, config.ESCALATION_MARGIN
            )
            frame_results.append(result)
            if result.escalated:
                escalated_count += 1
                logger.info("run %s: frame %d escalated to expensive tier", run_id, frame.index)

            if not result.detected:
                continue

            logger.info(
                "run %s: candidate detection at frame %d — checking adjacent frames before confirming",
                run_id, frame.index,
            )
            if not _confirm_with_adjacent_frames(video_path, result, task, tmp_dir):
                logger.info(
                    "run %s: frame %d not backed up by neighbors — treating as a false positive, "
                    "continuing scan", run_id, frame.index,
                )
                continue

            logger.info("run %s: confirmed detection at frame %d", run_id, frame.index)
            event = Event(
                run_id=run_id, frame_index=frame.index, timestamp_sec=frame.timestamp_sec,
                task=task.description, tier_used=result.tier_used, confidence=result.confidence,
                reasoning=result.reasoning, escalated=result.escalated, email_sent=False,
            )
            sent = send_alert_email(event, recipient_email, config.DRY_RUN_EMAIL)
            event.email_sent = sent
            insert_event(conn, event)
            events.append(event)
            break  # confirmed — stop scanning the rest of the video

    conn.close()
    summary = RunSummary(
        run_id=run_id,
        task=task,
        frames_scanned=frames_scanned,
        escalation_rate=(escalated_count / frames_scanned) if frames_scanned else 0.0,
        frame_results=frame_results,
        events=events,
        emails_sent=sum(e.email_sent for e in events),
    )
    logger.info(
        "run %s finished: frames=%d escalation_rate=%.2f emails_sent=%d",
        run_id, summary.frames_scanned, summary.escalation_rate, summary.emails_sent,
    )
    return summary
