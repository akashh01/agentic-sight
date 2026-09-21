"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight, Mail, MailX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { RunRecord } from "@/lib/api";
import { cn } from "@/lib/utils";

function RunEntry({ record }: { record: RunRecord }) {
  const [open, setOpen] = useState(true);
  const [showRaw, setShowRaw] = useState(false);
  const { summary } = record;
  const triggered = summary.events.length > 0;
  const escalations = summary.frame_results.filter((f) => f.escalated);

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-accent/50"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <div>
            <p className="text-sm font-medium">
              {new Date(record.timestamp).toLocaleTimeString()} · run {summary.run_id}
            </p>
            <p className="text-xs text-muted-foreground">
              {summary.frames_scanned} frame(s) scanned · escalation rate{" "}
              {(summary.escalation_rate * 100).toFixed(0)}%
            </p>
          </div>
        </div>
        <Badge variant={triggered ? "destructive" : "success"}>
          {triggered ? "Triggered" : "No trigger"}
        </Badge>
      </button>

      {open && (
        <div className="flex flex-col gap-2 px-4 pb-4">
          {escalations.length > 0 && (
            <div className="flex flex-col gap-1.5">
              {escalations.map((f) => (
                <div
                  key={`esc-${f.frame.index}`}
                  className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning"
                >
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    Escalated to expensive model on frame {f.frame.index} (t=
                    {f.frame.timestamp_sec.toFixed(1)}s) — cheap tier was ambiguous, final
                    confidence {(f.confidence * 100).toFixed(0)}%.
                  </span>
                </div>
              ))}
            </div>
          )}

          {summary.frame_results.map((f) => (
            <div
              key={f.frame.index}
              className={cn(
                "rounded-md border px-3 py-2 text-xs",
                f.detected ? "border-destructive/30 bg-destructive/5" : "border-border bg-muted/40"
              )}
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">frame {f.frame.index}</span>
                <span className="text-muted-foreground">t={f.frame.timestamp_sec.toFixed(1)}s</span>
                <Badge variant={f.tier_used === "expensive" ? "warning" : "default"}>
                  {f.tier_used}
                </Badge>
                {f.escalated && <Badge variant="warning">escalated</Badge>}
                <Badge variant={f.detected ? "destructive" : "success"}>
                  {f.detected ? "detected" : "clear"}
                </Badge>
                <span className="ml-auto text-muted-foreground">
                  confidence {(f.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-1 text-muted-foreground">{f.reasoning}</p>
            </div>
          ))}

          {summary.events.map((e) => (
            <div
              key={`event-${e.frame_index}`}
              className="flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs"
            >
              {e.email_sent ? (
                <Mail className="h-3.5 w-3.5 text-success" />
              ) : (
                <MailX className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              <span>
                {e.email_sent ? "Alert email sent" : "Alert email not sent"} for confirmed
                detection at frame {e.frame_index}
              </span>
            </div>
          ))}

          <button
            className="self-start text-xs text-primary hover:underline"
            onClick={() => setShowRaw((s) => !s)}
          >
            {showRaw ? "Hide full result" : "Full result →"}
          </button>
          {showRaw && (
            <pre className="max-h-64 overflow-auto rounded-md bg-muted/60 p-2 text-[11px] leading-snug">
              {JSON.stringify(summary, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export function MonitorPanel({ runs }: { runs: RunRecord[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Monitor</CardTitle>
        <CardDescription>Test runs. Results stay here for this session.</CardDescription>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 overflow-auto p-0">
        {runs.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">No runs yet — run the pipeline to see results here.</p>
        ) : (
          runs.map((r) => <RunEntry key={r.id} record={r} />)
        )}
      </CardContent>
    </Card>
  );
}
