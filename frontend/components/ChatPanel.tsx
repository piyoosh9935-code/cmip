"use client";

import { useState } from "react";
import { getTrace, postQuery, type QueryResponse, type TraceEvent } from "@/lib/api";
import { PipelineTrace } from "@/components/PipelineTrace";

const SUGGESTIONS = [
  "What medications is this member currently taking?",
  "Summarize this member's condition using claims and clinical notes.",
  "How is this member's condition trending over time?",
];

type Turn = {
  question: string;
  result: QueryResponse;
  trace: TraceEvent[];
};

export function ChatPanel({ memberId }: { memberId: string }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q: string) {
    if (!q.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await postQuery(memberId, q);
      const full = await getTrace(result.trace_id);
      setTurns((prev) => [...prev, { question: q, result, trace: full.trace }]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-200">
      <div className="border-b border-neutral-200 px-4 py-3">
        <h2 className="font-medium text-neutral-900">Ask the agent</h2>
        <p className="text-xs text-neutral-500">Agentic RAG over this member&apos;s claims, EHR, notes, and SDoH.</p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="rounded-full border border-neutral-300 px-3 py-1 text-xs text-neutral-600 hover:bg-neutral-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <div className="ml-auto w-fit max-w-[85%] rounded-lg bg-neutral-900 px-3 py-2 text-sm text-white">
              {turn.question}
            </div>
            <div className="w-fit max-w-[95%] rounded-lg bg-white px-3 py-2 text-sm text-neutral-900 shadow-sm ring-1 ring-neutral-200">
              {turn.result.answer}
            </div>
            <PipelineTrace result={turn.result} trace={turn.trace} />
          </div>
        ))}

        {loading && <div className="text-sm text-neutral-400">Running the agentic pipeline…</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="flex gap-2 border-t border-neutral-200 p-3"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this member…"
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
