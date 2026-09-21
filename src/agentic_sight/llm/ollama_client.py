"""ollama_client.py — thin LangChain(ChatOllama) helpers, JSON-mode.

This is the ONLY place that talks to Ollama directly. The actual
orchestration — intent parsing, tiered cheap/expensive detection — lives
in graphs/agent_graph.py and graphs/detector_graph.py as compiled
LangGraph StateGraphs; those graphs call the two functions below as
their node logic instead of hitting Ollama's HTTP API themselves.

Kept here (rather than inlined in the graph nodes) so each function stays
independently testable from the command line without building a graph:

    uv run python -m agentic_sight.llm.ollama_client --mode text \
        --model llama3.1:8b --prompt "flag anyone without a hard hat"

    uv run python -m agentic_sight.llm.ollama_client --mode vision \
        --model moondream --image frame_00001.jpg \
        --prompt 'Respond as JSON: {"detected": bool, "confidence": float, "reasoning": str}. Missing a hard hat?'
"""

import base64
import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from agentic_sight import config

logger = logging.getLogger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

# Small vision models (moondream especially) sometimes ignore format="json"
# and wrap the object in prose or markdown fences, or emit truncated/invalid
# JSON. This does a best-effort recovery before giving up.
def _extract_json(raw: str) -> dict:
    text = raw.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = _FENCE_RE.sub("", text).strip()
    if fenced != text:
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass

    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"model did not return parseable JSON: {raw!r}")


def _invoke_json(llm: ChatOllama, messages: list, model: str, retries: int = 1) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        response = llm.invoke(messages)
        raw = response.content
        logger.debug("raw response (attempt %d/%d): %s", attempt + 1, retries + 1, raw)
        try:
            return _extract_json(raw)
        except ValueError as exc:
            last_error = exc
            logger.warning(
                "model=%s returned malformed JSON on attempt %d/%d, retrying: %r",
                model, attempt + 1, retries + 1, raw,
            )
    logger.error("model=%s failed to return parseable JSON after %d attempt(s)", model, retries + 1)
    raise last_error


def call_text_json(model: str, system: str, prompt: str) -> dict:
    logger.debug("call_text_json model=%s prompt=%r", model, prompt)
    llm = ChatOllama(
        model=model, base_url=config.OLLAMA_BASE_URL, format="json", temperature=0,
        num_predict=300, repeat_penalty=1.3,
    )
    messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
    return _invoke_json(llm, messages, model)


def call_vision_json(model: str, image_path: str, prompt: str) -> dict:
    logger.debug("call_vision_json model=%s image=%s", model, image_path)
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    # num_predict caps how many tokens the model can generate — without it,
    # small vision models (moondream especially) can fall into a repetition
    # loop (e.g. repeating '"0.99": 0.89, ' forever) and never emit a
    # closing brace, which previously meant the JSON parse never succeeded
    # and the call effectively hung generating garbage. repeat_penalty
    # discourages the loop from starting in the first place.
    llm = ChatOllama(
        model=model, base_url=config.OLLAMA_BASE_URL, format="json", temperature=0,
        num_predict=200, repeat_penalty=1.3,
    )
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"},
        ]
    )
    return _invoke_json(llm, [message], model)


if __name__ == "__main__":
    import argparse

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test for the Ollama client helpers")
    parser.add_argument("--mode", choices=["text", "vision"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image", help="required for --mode vision")
    parser.add_argument("--system", default="Respond only with valid JSON.")
    args = parser.parse_args()

    if args.mode == "text":
        result = call_text_json(args.model, args.system, args.prompt)
    else:
        if not args.image:
            parser.error("--image is required for --mode vision")
        result = call_vision_json(args.model, args.image, args.prompt)

    print(json.dumps(result, indent=2))
