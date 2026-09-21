from typing import Literal

from pydantic import BaseModel, Field


class DetectionTask(BaseModel):
    description: str
    positive_condition: str
    # "absent"  -> violation is TRUE when positive_condition is NOT met
    #              (e.g. "flag anyone without a hard hat")
    # "present" -> violation is TRUE when positive_condition IS met
    #              (e.g. "flag anyone smoking")
    violation_when: Literal["absent", "present"]
    confidence_threshold: float


class Frame(BaseModel):
    index: int
    timestamp_sec: float
    image_path: str


class FrameResult(BaseModel):
    frame: Frame
    tier_used: Literal["cheap", "expensive"]
    detected: bool
    confidence: float
    reasoning: str
    escalated: bool


class Event(BaseModel):
    run_id: str
    frame_index: int
    timestamp_sec: float
    task: str
    tier_used: str
    confidence: float
    reasoning: str
    escalated: bool
    email_sent: bool


class RunSummary(BaseModel):
    run_id: str
    task: DetectionTask
    frames_scanned: int
    escalation_rate: float
    frame_results: list[FrameResult] = Field(default_factory=list)
    events: list[Event]
    emails_sent: int
