# Running Agentic Sight

This covers environment setup, Ollama models, backend, frontend, CLI, email
configuration, and optional tracing. For *why* the system is built this
way, see [POC Requirements & Architecture Evolution](plans/poc-requirements.md).

---

## 1. Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Ollama](https://ollama.com/) running locally
- Node.js 18+ (only needed for the frontend)
- (Optional) an SMTP account if you want real email alerts instead of
  dry-run logging

## 2. Ollama models

Pull the three models the pipeline uses:

```bash
ollama pull llama3.1:8b   # query optimizer agent (text)
ollama pull moondream     # detection agent, cheap tier (vision)
ollama pull llava:13b     # detection agent, expensive tier (vision)
```

You can swap any of these via `.env` (see below) — they just need to be
pulled and running locally under Ollama.

## 3. Backend setup

```bash
uv sync
cp .env.example .env
```

Edit `.env` as needed. Nothing is required to get started — every setting
has a sane default, and `DRY_RUN_EMAIL=true` means you don't need SMTP
credentials to try it end to end. Settings worth knowing about:

| Variable | Default | What it does |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` to see full prompts and raw model responses |
| `AGENT_MODEL` / `CHEAP_MODEL` / `EXPENSIVE_MODEL` | `llama3.1:8b` / `moondream` / `llava:13b` | Which Ollama models each stage uses |
| `SAMPLE_RATE_FPS` | `0.5` | One frame every 2 seconds |
| `CONFIRMATION_OFFSET_SEC` | `1.0` | Seconds before/after a candidate hit to check before trusting it; `0` disables confirmation |
| `ESCALATION_ENABLED` | `true` | `false` = never escalate to the expensive model |
| `ESCALATION_MARGIN` | `0.15` | How close to the confidence threshold counts as "ambiguous" |
| `DRY_RUN_EMAIL` | `true` | `false` sends real email via the `SMTP_*` settings below |
| `PHOENIX_COLLECTOR_ENDPOINT` | `http://localhost:6006/v1/traces` | Where trace spans go if Phoenix is running |

## 4. Running the API

```bash
uv run uvicorn agentic_sight.api:app --reload
```

The backend is now at `http://localhost:8000`:

- `GET /health` — liveness check
- `GET /defaults` — current config (models in use, escalation on/off, etc.) — this is what the UI reads on load
- `POST /runs` — multipart form (`intent`, `recipient_email`, `video`) — runs the full pipeline and returns a `RunSummary`
- `GET /docs` — interactive Swagger UI

## 5. Running the UI

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The UI is now at `http://localhost:3000`. It talks to the backend via CORS
(already enabled on the FastAPI side for this POC — not something you'd
want wide open in production).

**Using it:** upload a video, describe what to flag (e.g. "flag anyone
without a hard hat in the marked zone"), enter an alert recipient, and run
the pipeline. The box below the prompt shows what the Query Optimizer
Agent actually derived — the affirmative condition it will check, which
polarity counts as a violation, and the confidence threshold — so you can
catch a misinterpreted request before it wastes a full video scan. The
Monitor panel on the right lists each run with a Triggered/No-trigger
badge, an escalation banner for any frame the Detection Agent had to
escalate, and a per-frame breakdown of tier/confidence/reasoning.

## 6. CLI usage (no UI needed)

```bash
uv run agentic-sight --intent "flag anyone without a hard hat in the marked zone" \
  --video videos/test.mp4 \
  --recipient you@example.com
```

Prints the resulting `RunSummary` as JSON.

## 7. Testing pieces individually

Every backend module can be run standalone for focused testing instead of
going through the full pipeline — see each module's own
`if __name__ == "__main__":` block, or the version-by-version evolution in
[POC Requirements & Architecture Evolution](plans/poc-requirements.md).
A few examples:

```bash
uv run python -m agentic_sight.video_input --video videos/test.mp4
uv run python -m agentic_sight.llm.ollama_client --mode vision --model moondream \
  --image frames_out/frame_00000.jpg --prompt '...'
uv run python -m agentic_sight.graphs.detector_graph --image frames_out/frame_00000.jpg \
  --condition "the person is wearing a hard hat" --violation-when absent
uv run python -m agentic_sight.graphs.agent_graph --intent "flag anyone without a hard hat"
uv run python -m agentic_sight.store --db-path /tmp/test.db
uv run python -m agentic_sight.notifier --recipient you@example.com
```

## 8. Optional: tracing with Phoenix

```bash
uv run phoenix serve
```

UI at `http://localhost:6006`. No Docker needed — this is a plain local
process. If it isn't running, `observability.py` logs a warning and the
pipeline continues without tracing; it never blocks a run.
