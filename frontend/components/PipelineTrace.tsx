import type { QueryResponse, TraceEvent } from "@/lib/api";

const NODE_COLORS: Record<string, string> = {
  query_analysis: "bg-blue-100 text-blue-800",
  retrieval: "bg-purple-100 text-purple-800",
  grading: "bg-amber-100 text-amber-800",
  generation: "bg-emerald-100 text-emerald-800",
  verification: "bg-teal-100 text-teal-800",
  prepare_retry: "bg-orange-100 text-orange-800",
  mark_low_confidence: "bg-red-100 text-red-800",
};

export function PipelineTrace({
  result,
  trace,
}: {
  result: QueryResponse;
  trace: TraceEvent[];
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm">
      <div className="mb-3 flex flex-wrap gap-2">
        <Badge label={`model: ${result.routed_model}`} />
        <Badge label={`retries: ${result.retry_count}`} tone={result.retry_count > 0 ? "warn" : "default"} />
        <Badge
          label={`groundedness: ${result.groundedness_score.toFixed(2)}`}
          tone={result.groundedness_passed ? "good" : "bad"}
        />
        {result.low_confidence && <Badge label="low confidence" tone="bad" />}
      </div>
      <p className="mb-3 text-neutral-500">{result.routing_reason}</p>

      <ol className="space-y-2">
        {trace.map((event, i) => (
          <li key={i} className="flex gap-2">
            <span
              className={`h-fit shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
                NODE_COLORS[event.node] ?? "bg-neutral-200 text-neutral-700"
              }`}
            >
              {event.node}
            </span>
            <span className="text-neutral-700">{event.detail}</span>
          </li>
        ))}
      </ol>

      {result.citations.length > 0 && (
        <div className="mt-3 border-t border-neutral-200 pt-3">
          <div className="mb-1 text-xs font-medium text-neutral-500">citations</div>
          <div className="flex flex-wrap gap-1">
            {result.citations.map((c) => (
              <code key={c} className="rounded bg-neutral-200 px-1.5 py-0.5 text-xs text-neutral-700">
                {c}
              </code>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Badge({ label, tone = "default" }: { label: string; tone?: "default" | "good" | "bad" | "warn" }) {
  const toneClass = {
    default: "bg-neutral-200 text-neutral-700",
    good: "bg-emerald-100 text-emerald-800",
    bad: "bg-red-100 text-red-800",
    warn: "bg-amber-100 text-amber-800",
  }[tone];
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${toneClass}`}>{label}</span>;
}
