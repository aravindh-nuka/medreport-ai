import { cn } from "@/lib/utils";

export type StatusKind = "normal" | "high" | "low" | "critical" | "unknown";

export function statusKind(status: string): StatusKind {
  const s = status.toLowerCase();
  if (s.includes("critical")) return "critical";
  if (s.includes("high")) return "high";
  if (s.includes("low")) return "low";
  if (s.includes("normal")) return "normal";
  return "unknown";
}

const STATUS_STYLES: Record<StatusKind, string> = {
  normal: "bg-verified-50 text-verified-700 border-verified-400/40",
  high: "bg-attention-50 text-attention-700 border-attention-400/40",
  low: "bg-attention-50 text-attention-700 border-attention-400/40",
  critical: "bg-attention-600 text-white border-attention-700",
  unknown: "bg-unknown-50 text-unknown-600 border-unknown-400/40",
};

export function StatusBadge({ status }: { status: string }) {
  const kind = statusKind(status);
  return (
    <span className={cn("inline-flex items-center rounded-pill border px-2.5 py-0.5 text-xs font-medium", STATUS_STYLES[kind])}>
      {status}
    </span>
  );
}

export function SourceTag({ kind }: { kind: "extracted" | "ai" | "offline" }) {
  if (kind === "extracted") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-pill bg-unknown-50 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-unknown-600 dark:bg-white/5">
        <span className="h-1.5 w-1.5 rounded-full bg-unknown-400" /> From your report
      </span>
    );
  }
  if (kind === "offline") {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-pill bg-attention-50 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-attention-700 dark:bg-attention-600/15"
        title="AI providers were unavailable — this is a basic, non-AI explanation"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-attention-600" /> Basic explanation · AI unavailable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-pill bg-ai-50 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-ai-700 dark:bg-ai-600/20 dark:text-ai-400">
      <span className="h-1.5 w-1.5 rounded-full bg-ai-600" /> AI explanation
    </span>
  );
}

/** Maps a backend source_of_truth string ("ai_generated" | "template_fallback")
 * to the SourceTag kind it should render as. */
export function sourceTagKind(sourceOfTruth: string | undefined): "ai" | "offline" {
  return sourceOfTruth === "template_fallback" ? "offline" : "ai";
}
