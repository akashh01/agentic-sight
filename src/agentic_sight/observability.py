import logging

from opentelemetry import trace

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("agentic-sight")


def setup_observability(project_name: str, endpoint: str) -> None:
    """Call once at process start (main.py / api.py) to wire spans to Phoenix."""
    try:
        from phoenix.otel import register

        register(project_name=project_name, endpoint=endpoint)
        logger.info("Phoenix tracing enabled: project=%s endpoint=%s", project_name, endpoint)
    except Exception:
        logger.warning(
            "Phoenix not reachable at %s — continuing without tracing "
            "(run `phoenix serve` to enable it)", endpoint, exc_info=True,
        )


def traced_call(fn, *args, tier: str, model: str, **kwargs):
    with tracer.start_as_current_span(f"{tier}_model_call") as span:
        span.set_attribute("model", model)
        span.set_attribute("tier", tier)
        result = fn(*args, **kwargs)
        span.set_attribute("detected", result.get("detected"))
        span.set_attribute("confidence", result.get("confidence", 0.0))
        return result
