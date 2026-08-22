const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type MemberListItem = {
  member_id: string;
  first_name: string;
  last_name: string;
  age: number;
  plan_type: string;
  cohorts: string | null;
};

export type MemberDetail = {
  summary: Record<string, unknown>;
  recent_claims: Record<string, unknown>[];
  medications: Record<string, unknown>[];
  recent_encounters: Record<string, unknown>[];
  sdoh: Record<string, unknown> | null;
};

export type TraceEvent = { node: string; detail: string };

export type QueryResponse = {
  trace_id: string;
  answer: string;
  citations: string[];
  groundedness_score: number;
  groundedness_passed: boolean;
  retry_count: number;
  low_confidence: boolean;
  routed_model: string;
  routing_reason: string;
  latency_ms: number;
};

export type TraceResponse = QueryResponse & {
  member_id: string;
  question: string;
  trace: TraceEvent[];
  created_at: string;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export function listMembers(cohort?: string): Promise<MemberListItem[]> {
  const qs = cohort ? `?cohort=${encodeURIComponent(cohort)}&limit=100` : "?limit=100";
  return apiFetch(`/members${qs}`);
}

export function getMember(memberId: string): Promise<MemberDetail> {
  return apiFetch(`/members/${memberId}`);
}

export function postQuery(memberId: string, question: string): Promise<QueryResponse> {
  return apiFetch(`/query`, {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, question }),
  });
}

export function getTrace(traceId: string): Promise<TraceResponse> {
  return apiFetch(`/trace/${traceId}`);
}
