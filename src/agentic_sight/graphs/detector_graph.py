"""detector_graph.py — Detection Agent: tiered cheap/expensive frame detection.

Graph shape:

    cheap_detect --(confidence within margin of threshold?)--> expensive_detect --> END
                 --(clear-cut result)-------------------------------------------> END

The conditional edge (should_escalate) is what used to be an if-statement
in a plain function — now it's a real LangGraph branch, so the escalation
policy is visible in the graph structure itself.

The vision model is always asked task.positive_condition — a literal,
AFFIRMATIVE yes/no question (never a negated one) — and answers with
"condition_met": true/false. The actual violation ("detected") is then
derived in code from task.violation_when:
  - violation_when="absent"  -> detected = NOT condition_met
  - violation_when="present" -> detected = condition_met
This is deliberate: small vision models reliably answer straightforward
positive questions ("is the person wearing a hard hat?") but are prone to
getting negated ones ("is the person NOT wearing a hard hat?") backwards
even when their own reasoning correctly describes the scene. Handling the
negation in Python removes that failure mode entirely.

Standalone:
    uv run python -m agentic_sight.graphs.detector_graph \
        --image videos/frame_00003.jpg --condition "the person is wearing a hard hat" \
        --violation-when absent
"""

import logging
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from agentic_sight import config
from agentic_sight.llm.ollama_client import call_vision_json
from agentic_sight.observability import traced_call
from agentic_sight.schema import DetectionTask, Frame, FrameResult

logger = logging.getLogger(__name__)

# moondream (cheap tier) is a small (~1.6B) model — long rule-lists confuse
# it more than they help. Keep this short, plain, and single-purpose. Note
# this always asks the AFFIRMATIVE condition, never a negated one.
CHEAP_DETECTION_PROMPT_TEMPLATE = """Look at the image. Question: is this true — {positive_condition}?

Only answer yes if you clearly see it. If not sure, answer no with low confidence.

Reply with ONLY this JSON, nothing else:
{{"condition_met": true or false, "confidence": <0 to 1>, "reasoning": "<short sentence, what you saw>"}}
"""

# llava (expensive tier) is larger and follows more detailed instructions
# reliably — worth spelling out edge cases here since it's only called on
# frames the cheap tier was already unsure about.
EXPENSIVE_DETECTION_PROMPT_TEMPLATE = """You are a workplace safety inspector reviewing a single frame \
captured from a security camera.

Condition to check (answer literally, based only on what is visible): {positive_condition}

Instructions:
- Examine every person visible in the frame, including ones partially visible, distant, or at the edge of the frame.
- Only answer "condition_met": true if you can clearly see that the condition holds. Do not guess based on context, typical workplace practice, or what is "probably" happening off-frame.
- If the frame is blurry, too dark, too far away, or the relevant body part/area is not visible, treat the condition as NOT confirmed and reflect that uncertainty in a lower confidence score.
- "confidence" is how certain you are about your "condition_met" answer, not how important it is. 1.0 = completely certain, 0.5 = genuinely unsure, 0.0 = completely certain the condition does NOT hold.
- "reasoning" must describe specifically what you observed in this frame (who/what/where) in one sentence. Do not just repeat the condition back.

Respond with ONLY a single valid JSON object — no markdown, no code fences, no text before or after it — in exactly this shape:
{{"condition_met": true or false, "confidence": <float between 0 and 1>, "reasoning": "<one sentence describing what you actually saw>"}}
"""


class DetectorState(TypedDict):
    task: DetectionTask
    frame: Frame
    cheap_model: str
    expensive_model: str
    margin: float
    cheap_confidence: float
    result: Optional[FrameResult]


def _safe_detect_call(fn, *args, tier: str, model: str, frame_index: int) -> dict:
    """Run a traced model call; on failure (e.g. the model never returned
    parseable JSON, or a connection error), log it and degrade to
    "condition not met" instead of letting the exception crash the whole
    run — one bad frame shouldn't stop the scan or 500 the API."""
    try:
        return traced_call(fn, *args, tier=tier, model=model)
    except Exception as exc:
        logger.error(
            "model call failed on frame %d (tier=%s, model=%s): %s — treating condition as not met",
            frame_index, tier, model, exc,
        )
        return {"condition_met": False, "confidence": 0.0, "reasoning": f"model call failed: {exc}"}


def _to_frame_result(
    frame: Frame, task: DetectionTask, data: dict, tier: str, escalated: bool
) -> FrameResult:
    condition_met = bool(data.get("condition_met", False))
    detected = (not condition_met) if task.violation_when == "absent" else condition_met
    return FrameResult(
        frame=frame, tier_used=tier, detected=detected,
        confidence=float(data.get("confidence", 0.0)), reasoning=data.get("reasoning", ""),
        escalated=escalated,
    )


def cheap_detect_node(state: DetectorState) -> DetectorState:
    logger.info("cheap tier on frame %d", state["frame"].index)
    prompt = CHEAP_DETECTION_PROMPT_TEMPLATE.format(positive_condition=state["task"].positive_condition)
    data = _safe_detect_call(
        call_vision_json, state["cheap_model"], state["frame"].image_path, prompt,
        tier="cheap", model=state["cheap_model"], frame_index=state["frame"].index,
    )
    confidence = float(data.get("confidence", 0.0))
    result = _to_frame_result(state["frame"], state["task"], data, tier="cheap", escalated=False)
    logger.info(
        "cheap tier result: condition_met=%s -> detected=%s confidence=%.2f",
        data.get("condition_met"), result.detected, confidence,
    )
    return {**state, "cheap_confidence": confidence, "result": result}


def should_escalate(state: DetectorState) -> str:
    if not config.ESCALATION_ENABLED:
        logger.info(
            "ESCALATION_ENABLED=false — staying on cheap tier for frame %d (no escalation check performed)",
            state["frame"].index,
        )
        return END

    threshold = state["task"].confidence_threshold
    if abs(state["cheap_confidence"] - threshold) <= state["margin"]:
        logger.info(
            "escalating frame %d (cheap confidence=%.2f is within margin=%.2f of threshold=%.2f)",
            state["frame"].index, state["cheap_confidence"], state["margin"], threshold,
        )
        return "expensive_detect"
    logger.info("frame %d resolved at cheap tier, no escalation needed", state["frame"].index)
    return END


def expensive_detect_node(state: DetectorState) -> DetectorState:
    logger.info("expensive tier on frame %d", state["frame"].index)
    prompt = EXPENSIVE_DETECTION_PROMPT_TEMPLATE.format(positive_condition=state["task"].positive_condition)
    data = _safe_detect_call(
        call_vision_json, state["expensive_model"], state["frame"].image_path, prompt,
        tier="expensive", model=state["expensive_model"], frame_index=state["frame"].index,
    )
    result = _to_frame_result(state["frame"], state["task"], data, tier="expensive", escalated=True)
    logger.info(
        "expensive tier result: condition_met=%s -> detected=%s confidence=%.2f",
        data.get("condition_met"), result.detected, result.confidence,
    )
    return {**state, "result": result}


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        builder = StateGraph(DetectorState)
        builder.add_node("cheap_detect", cheap_detect_node)
        builder.add_node("expensive_detect", expensive_detect_node)
        builder.set_entry_point("cheap_detect")
        builder.add_conditional_edges(
            "cheap_detect", should_escalate, {"expensive_detect": "expensive_detect", END: END}
        )
        builder.add_edge("expensive_detect", END)
        _graph = builder.compile()
        logger.debug("detector graph compiled")
    return _graph


def run_detection(
    task: DetectionTask, frame: Frame, cheap_model: str, expensive_model: str, margin: float
) -> FrameResult:
    state = _get_graph().invoke(
        {
            "task": task, "frame": frame, "cheap_model": cheap_model,
            "expensive_model": expensive_model, "margin": margin,
            "cheap_confidence": 0.0, "result": None,
        }
    )
    return state["result"]


if __name__ == "__main__":
    import argparse

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test: run the detector graph on a single image")
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--condition", required=True,
        help="AFFIRMATIVE condition, e.g. 'the person is wearing a hard hat' (never negated)",
    )
    parser.add_argument("--violation-when", choices=["absent", "present"], default="absent")
    parser.add_argument("--description", default=None, help="optional human-readable label")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--cheap-model", default="moondream")
    parser.add_argument("--expensive-model", default="llava:13b")
    parser.add_argument("--margin", type=float, default=0.15)
    args = parser.parse_args()

    task = DetectionTask(
        description=args.description or args.condition,
        positive_condition=args.condition,
        violation_when=args.violation_when,
        confidence_threshold=args.threshold,
    )
    frame = Frame(index=0, timestamp_sec=0.0, image_path=args.image)

    result = run_detection(task, frame, args.cheap_model, args.expensive_model, args.margin)
    print(result.model_dump_json(indent=2))
