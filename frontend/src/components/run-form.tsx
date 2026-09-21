"use client";

import { useState } from "react";
import { Loader2, Play, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { DetectionTask } from "@/lib/api";

interface RunFormProps {
  loading: boolean;
  error: string | null;
  defaultRecipient: string;
  lastTask: DetectionTask | null;
  onSubmit: (args: { intent: string; recipientEmail: string; video: File }) => void;
}

export function RunForm({ loading, error, defaultRecipient, lastTask, onSubmit }: RunFormProps) {
  const [intent, setIntent] = useState("flag anyone without a hard hat in the marked zone");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [video, setVideo] = useState<File | null>(null);

  const recipient = recipientEmail || defaultRecipient;
  const canSubmit = intent.trim().length > 0 && !!video && recipient.trim().length > 0 && !loading;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run pipeline</CardTitle>
        <CardDescription>Upload a video and describe what to look for.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="video">Video</Label>
          <label
            htmlFor="video"
            className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-input px-3 py-6 text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground"
          >
            <Upload className="h-4 w-4" />
            {video ? video.name : "Click to choose a video file"}
          </label>
          <Input
            id="video"
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="intent">Intent</Label>
          <Textarea
            id="intent"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. flag anyone without a hard hat in the marked zone"
            rows={3}
          />
        </div>

        {lastTask && (
          <div className="rounded-md border border-primary/25 bg-primary/5 px-3 py-2">
            <p className="text-xs font-medium text-primary">Query optimizer agent understood this as</p>
            <p className="mt-1 text-sm">{lastTask.description}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              checks: &ldquo;{lastTask.positive_condition}&rdquo; — violation when{" "}
              {lastTask.violation_when === "absent" ? "this is NOT true" : "this IS true"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              confidence threshold: {lastTask.confidence_threshold.toFixed(2)}
            </p>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="recipient">Alert recipient</Label>
          <Input
            id="recipient"
            type="email"
            placeholder={defaultRecipient || "safety@example.com"}
            value={recipientEmail}
            onChange={(e) => setRecipientEmail(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        <Button
          disabled={!canSubmit}
          onClick={() => video && onSubmit({ intent, recipientEmail: recipient, video })}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {loading ? "Running…" : "Run pipeline"}
        </Button>
      </CardContent>
    </Card>
  );
}
