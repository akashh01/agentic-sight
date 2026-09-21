import logging
import smtplib
from email.message import EmailMessage

from agentic_sight import config
from agentic_sight.schema import Event

logger = logging.getLogger(__name__)


def send_alert_email(event: Event, recipient: str, dry_run: bool) -> bool:
    subject = f"[Agentic Sight] Detection confirmed — run {event.run_id}"
    body = (
        f"Task: {event.task}\n"
        f"Frame: {event.frame_index} (t={event.timestamp_sec:.2f}s)\n"
        f"Tier: {event.tier_used} (escalated={event.escalated})\n"
        f"Confidence: {event.confidence:.2f}\n"
        f"Reasoning: {event.reasoning}\n"
    )

    if dry_run:
        logger.info("DRY_RUN_EMAIL=true — not actually sending, printing instead")
        print("[DRY RUN] Would send email:")
        print(f"To: {recipient}\nSubject: {subject}\n\n{body}")
        return True

    logger.info("sending alert email to %s via %s:%d", recipient, config.SMTP_HOST, config.SMTP_PORT)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.FROM_EMAIL
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASS)
        smtp.send_message(msg)
    logger.info("email sent")
    return True


if __name__ == "__main__":
    import argparse
    import uuid

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test: send (or dry-run) an alert email")
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--live", action="store_true", help="actually send via SMTP instead of dry-run")
    args = parser.parse_args()

    dummy = Event(
        run_id=str(uuid.uuid4())[:8], frame_index=3, timestamp_sec=3.0,
        task="person without a hard hat", tier_used="expensive", confidence=0.91,
        reasoning="Bare head clearly visible in restricted zone.", escalated=True, email_sent=False,
    )
    ok = send_alert_email(dummy, args.recipient, dry_run=not args.live)
    print("sent" if ok else "failed")
