"use client";

import { useEffect, useState } from "react";

import { PipelineStrip } from "@/components/pipeline-strip";
import { RunForm } from "@/components/run-form";
import { MonitorPanel } from "@/components/monitor-panel";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Defaults, DetectionTask, RunRecord, fetchDefaults, runPipeline } from "@/lib/api";

export default function Home() {
  const [defaults, setDefaults] = useState<Defaults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [lastTask, setLastTask] = useState<DetectionTask | null>(null);

  useEffect(() => {
    fetchDefaults()
      .then(setDefaults)
      .catch(() => setDefaults(null));
  }, []);

  async function handleSubmit(args: { intent: string; recipientEmail: string; video: File }) {
    setLoading(true);
    setError(null);
    try {
      const summary = await runPipeline(args);
      setLastTask(summary.task);
      setRuns((prev) => [
        { id: summary.run_id, timestamp: new Date().toISOString(), summary },
        ...prev,
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground">Console / Agentic Sight</p>
          <h1 className="text-lg font-semibold">Agentic Sight — Video Safety Detection</h1>
        </div>
        {defaults && (
          <Badge variant={defaults.escalation_enabled ? "primary" : "default"}>
            escalation: {defaults.escalation_enabled ? "on" : "off"}
          </Badge>
        )}
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr_380px]">
        <Card className="hidden lg:block">
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>Fixed for this POC</CardDescription>
          </CardHeader>
          <CardContent>
            <PipelineStrip defaults={defaults} />
          </CardContent>
        </Card>

        <RunForm
          loading={loading}
          error={error}
          defaultRecipient={defaults?.recipient_email ?? ""}
          lastTask={lastTask}
          onSubmit={handleSubmit}
        />

        <MonitorPanel runs={runs} />
      </div>
    </main>
  );
}
