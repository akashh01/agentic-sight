import logging
import sqlite3

from agentic_sight.schema import Event

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    timestamp_sec REAL NOT NULL,
    task TEXT NOT NULL,
    tier_used TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT NOT NULL,
    escalated INTEGER NOT NULL,
    email_sent INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(path: str) -> sqlite3.Connection:
    logger.info("opening events db at %s", path)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def insert_event(conn: sqlite3.Connection, event: Event) -> None:
    logger.info(
        "inserting event: run_id=%s frame=%d tier=%s confidence=%.2f",
        event.run_id, event.frame_index, event.tier_used, event.confidence,
    )
    conn.execute(
        """INSERT INTO events
           (run_id, frame_index, timestamp_sec, task, tier_used, confidence,
            reasoning, escalated, email_sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.run_id, event.frame_index, event.timestamp_sec, event.task,
            event.tier_used, event.confidence, event.reasoning,
            int(event.escalated), int(event.email_sent),
        ),
    )
    conn.commit()


if __name__ == "__main__":
    import argparse
    import uuid

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test: init db + insert a dummy event")
    parser.add_argument("--db-path", default="events_test.db")
    args = parser.parse_args()

    conn = init_db(args.db_path)
    dummy = Event(
        run_id=str(uuid.uuid4())[:8], frame_index=0, timestamp_sec=1.5,
        task="person without a hard hat", tier_used="cheap", confidence=0.82,
        reasoning="No helmet visible on person in frame.", escalated=False, email_sent=False,
    )
    insert_event(conn, dummy)

    rows = conn.execute("SELECT * FROM events").fetchall()
    print(f"Inserted. {len(rows)} row(s) in {args.db_path}:")
    for row in rows:
        print(row)
    conn.close()
