export interface DetectionTask {
  description: string;
  positive_condition: string;
  violation_when: "absent" | "present";
  confidence_threshold: number;
}

export interface FrameRef {
  index: number;
  timestamp_sec: number;
  image_path: string;
}

export interface FrameResult {
  frame: FrameRef;
  tier_used: "cheap" | "expensive";
  detected: boolean;
  confidence: number;
  reasoning: string;
  escalated: boolean;
}

export interface DetectionEvent {
  run_id: string;
  frame_index: number;
  timestamp_sec: number;
  task: string;
  tier_used: string;
  confidence: number;
  reasoning: string;
  escalated: boolean;
  email_sent: boolean;
}

export interface RunSummary {
  run_id: string;
  task: DetectionTask;
  frames_scanned: number;
  escalation_rate: number;
  frame_results: FrameResult[];
  events: DetectionEvent[];
  emails_sent: number;
}

export interface Defaults {
  recipient_email: string;
  escalation_enabled: boolean;
  agent_model: string;
  cheap_model: string;
  expensive_model: string;
  sample_rate_fps: number;
  dry_run_email: boolean;
}

export interface RunRecord {
  id: string;
  timestamp: string;
  summary: RunSummary;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchDefaults(): Promise<Defaults> {
  const res = await fetch(`${API_BASE}/defaults`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /defaults failed: ${res.status}`);
  return res.json();
}

export async function runPipeline(args: {
  intent: string;
  recipientEmail: string;
  video: File;
}): Promise<RunSummary> {
  const form = new FormData();
  form.set("intent", args.intent);
  form.set("recipient_email", args.recipientEmail);
  form.set("video", args.video);

  const res = await fetch(`${API_BASE}/runs`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST /runs failed: ${res.status} ${text}`);
  }
  return res.json();
}
