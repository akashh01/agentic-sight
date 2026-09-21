"""agent_graph.py — Query Optimizer Agent: natural-language intent -> DetectionTask.

Single node today (v1: one task, not a multi-step plan) but it's a real
compiled LangGraph graph, not a bare function call — v2 can add nodes
(clarifying questions, multi-task planning) without changing callers,
since callers only see intent_to_task().

Deliberately produces a POSITIVE, literal condition (positive_condition)
plus a violation_when flag rather than a negatively-phrased description.
Small vision models are unreliable at judging negated conditions ("not
wearing a hard hat") even when they correctly perceive the scene — they
can describe "wearing a helmet" accurately in their reasoning and still
get the true/false flag backwards. Asking a positive question ("is the
person wearing a hard hat?") and inverting the boolean in code
(detector_graph.py) sidesteps that failure mode entirely.

Standalone:
    uv run python -m agentic_sight.graphs.agent_graph \
        --intent "flag anyone without a hard hat in the marked zone"
"""

import logging
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from agentic_sight.llm.ollama_client import call_text_json
from agentic_sight.schema import DetectionTask

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You convert a plain-language safety instruction into a structured detection \
task for a computer-vision model. You do not see any camera feed yourself — you only rephrase text.

Rules:
- Do NOT add any equipment, location, person count, or condition the user did not mention or clearly imply. If they said "hard hat", do not also mention vests, boots, or gloves.
- "positive_condition" must always be phrased AFFIRMATIVELY — as something the vision model can literally see and answer yes/no to. NEVER put "not", "without", "no", or any other negation word in positive_condition. If the user's instruction is negative (e.g. "without a hard hat"), positive_condition is the OPPOSITE, affirmative thing to check for (e.g. "the person is wearing a hard hat"), and "violation_when" is set to "absent" to record that the violation is the ABSENCE of that condition.
- "violation_when" is "absent" when the user is asking to be flagged when something is MISSING/NOT happening (no hard hat, no vest, nobody present). "violation_when" is "present" when the user is asking to be flagged when something IS happening (someone smoking, someone running, a person in a restricted zone).
- "description" is a short human-readable summary of the violation itself (for display only, not sent to the vision model) — this one CAN be phrased negatively since a human reads it, e.g. "a person not wearing a hard hat".
- "confidence_threshold" is how confident the vision model must be before an alert fires. Use 0.6 unless the user explicitly asks to be stricter (e.g. "only if you're very sure" -> higher, like 0.8) or looser (e.g. "flag anything even slightly suspicious" -> lower, like 0.4).

Examples:
Input: flag anyone without a hard hat in the marked zone
Output: {"description": "a person in the marked zone not wearing a hard hat", "positive_condition": "the person in the marked zone is wearing a hard hat", "violation_when": "absent", "confidence_threshold": 0.6}

Input: only alert me if you're really sure someone doesn't have safety goggles on
Output: {"description": "a person not wearing safety goggles", "positive_condition": "the person is wearing safety goggles", "violation_when": "absent", "confidence_threshold": 0.85}

Input: alert if someone is smoking near the loading dock
Output: {"description": "a person smoking near the loading dock", "positive_condition": "a person is smoking near the loading dock", "violation_when": "present", "confidence_threshold": 0.6}

Respond with ONLY a single valid JSON object — no markdown, no extra text before or after it — in exactly this shape:
{"description": "<short human-readable violation summary, may be negative>", "positive_condition": "<literal AFFIRMATIVE yes/no condition, never negated>", "violation_when": "absent" or "present", "confidence_threshold": <float 0-1>}
"""


class AgentState(TypedDict):
    intent: str
    model: str
    task: Optional[DetectionTask]


def extract_task_node(state: AgentState) -> AgentState:
    logger.info("extracting detection task from intent=%r (model=%s)", state["intent"], state["model"])
    try:
        data = call_text_json(state["model"], SYSTEM_PROMPT, state["intent"])
        violation_when = data.get("violation_when", "absent")
        if violation_when not in ("absent", "present"):
            logger.warning("agent returned invalid violation_when=%r, defaulting to 'absent'", violation_when)
            violation_when = "absent"
        task = DetectionTask(
            description=data.get("description", state["intent"]),
            positive_condition=data.get("positive_condition", state["intent"]),
            violation_when=violation_when,
            confidence_threshold=float(data.get("confidence_threshold", 0.6)),
        )
    except Exception as exc:
        logger.error(
            "agent model failed to return parseable JSON (%s) — falling back to the raw intent, "
            "treated as an affirmative condition (violation_when=present)", exc,
        )
        task = DetectionTask(
            description=state["intent"], positive_condition=state["intent"],
            violation_when="present", confidence_threshold=0.6,
        )
    logger.info("extracted task: %s", task)
    return {**state, "task": task}


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        builder = StateGraph(AgentState)
        builder.add_node("extract_task", extract_task_node)
        builder.set_entry_point("extract_task")
        builder.add_edge("extract_task", END)
        _graph = builder.compile()
        logger.debug("agent graph compiled")
    return _graph


def intent_to_task(intent: str, model: str) -> DetectionTask:
    result = _get_graph().invoke({"intent": intent, "model": model, "task": None})
    return result["task"]


if __name__ == "__main__":
    import argparse

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test: intent -> DetectionTask via LangGraph")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--model", default="llama3.1:8b")
    args = parser.parse_args()

    task = intent_to_task(args.intent, args.model)
    print(task.model_dump_json(indent=2))
