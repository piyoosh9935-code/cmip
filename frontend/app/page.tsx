import Link from "next/link";
import { listMembers } from "@/lib/api";

const COHORTS = ["diabetes", "hypertension", "chf", "copd", "depression"];

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ cohort?: string }>;
}) {
  const { cohort } = await searchParams;
  const members = await listMembers(cohort);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-neutral-900">CMIP — Member 360</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Clinical Member Intelligence Platform · select a member to view their profile and ask the agent a question.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/"
          className={`rounded-full border px-3 py-1 text-sm ${
            !cohort ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 text-neutral-600"
          }`}
        >
          All
        </Link>
        {COHORTS.map((c) => (
          <Link
            key={c}
            href={`/?cohort=${c}`}
            className={`rounded-full border px-3 py-1 text-sm capitalize ${
              cohort === c ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 text-neutral-600"
            }`}
          >
            {c}
          </Link>
        ))}
      </div>

      <ul className="mt-6 divide-y divide-neutral-200 rounded-lg border border-neutral-200">
        {members.map((m) => (
          <li key={m.member_id}>
            <Link
              href={`/members/${m.member_id}`}
              className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50"
            >
              <div>
                <div className="font-medium text-neutral-900">
                  {m.first_name} {m.last_name}{" "}
                  <span className="font-normal text-neutral-400">· {m.member_id}</span>
                </div>
                <div className="text-sm text-neutral-500">
                  age {m.age} · {m.plan_type}
                  {m.cohorts ? ` · ${m.cohorts}` : ""}
                </div>
              </div>
              <span className="text-neutral-400">→</span>
            </Link>
          </li>
        ))}
        {members.length === 0 && (
          <li className="px-4 py-6 text-center text-sm text-neutral-500">No members found.</li>
        )}
      </ul>
    </main>
  );
}
