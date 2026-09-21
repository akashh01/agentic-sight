import { Defaults } from "@/lib/api";

interface Step {
  n: number;
  title: string;
  subtitle: string;
}

function buildSteps(defaults: Defaults | null): Step[] {
  return [
    { n: 1, title: "Source", subtitle: "Uploaded video" },
    { n: 2, title: "Query Optimizer Agent", subtitle: `Rephrase intent (${defaults?.agent_model ?? "…"})` },
    { n: 3, title: "Detection Agent — cheap", subtitle: defaults?.cheap_model ?? "…" },
    {
      n: 4,
      title: "Condition",
      subtitle: defaults
        ? defaults.escalation_enabled
          ? "Escalate if ambiguous"
          : "Escalation disabled"
        : "…",
    },
    { n: 5, title: "Detection Agent — expensive", subtitle: defaults?.expensive_model ?? "…" },
    { n: 6, title: "Notify", subtitle: defaults?.dry_run_email ? "Email (dry-run)" : "Email" },
    { n: 7, title: "Store", subtitle: "SQLite events" },
  ];
}

export function PipelineStrip({ defaults }: { defaults: Defaults | null }) {
  const steps = buildSteps(defaults);
  return (
    <div className="flex flex-col gap-0">
      {steps.map((step, i) => (
        <div key={step.n} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[11px] font-medium text-muted-foreground">
              {step.n}
            </div>
            {i < steps.length - 1 && <div className="h-6 w-px bg-border" />}
          </div>
          <div className="pb-4">
            <p className="text-sm font-medium leading-tight">{step.title}</p>
            <p className="text-xs text-muted-foreground">{step.subtitle}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
