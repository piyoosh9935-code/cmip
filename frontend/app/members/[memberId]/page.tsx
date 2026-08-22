import Link from "next/link";
import { getMember } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export default async function MemberPage({
  params,
}: {
  params: Promise<{ memberId: string }>;
}) {
  const { memberId } = await params;
  const member = await getMember(memberId);
  const s = member.summary;

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <Link href="/" className="text-sm text-neutral-500 hover:text-neutral-900">
        ← All members
      </Link>

      <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <section className="rounded-lg border border-neutral-200 p-5">
            <h1 className="text-xl font-semibold text-neutral-900">
              {fmt(s.first_name)} {fmt(s.last_name)}{" "}
              <span className="text-base font-normal text-neutral-400">· {memberId}</span>
            </h1>
            <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-neutral-600 sm:grid-cols-3">
              <Field label="Age" value={fmt(s.age)} />
              <Field label="Gender" value={fmt(s.gender)} />
              <Field label="Plan" value={fmt(s.plan_type)} />
              <Field label="Region" value={fmt(s.region)} />
              <Field label="Cohorts" value={fmt(s.cohorts)} />
              <Field label="Enrolled" value={fmt(s.enrollment_start)} />
            </div>
            <div className="mt-4 border-t border-neutral-200 pt-3 text-sm text-neutral-600">
              <div>
                <span className="font-medium text-neutral-900">{fmt(s.total_claims)}</span> claims ·{" "}
                <span className="font-medium text-neutral-900">${fmt(s.total_paid_amount)}</span> total paid
              </div>
              <div>
                <span className="font-medium text-neutral-900">{fmt(s.total_encounters)}</span> encounters ·{" "}
                <span className="font-medium text-neutral-900">{fmt(s.active_medication_count)}</span> active
                medications · <span className="font-medium text-neutral-900">{fmt(s.total_notes)}</span> notes
              </div>
              {s.active_conditions ? (
                <div className="mt-1">
                  <span className="font-medium text-neutral-900">Active conditions:</span> {fmt(s.active_conditions)}
                </div>
              ) : null}
            </div>
          </section>

          {member.sdoh && (
            <section className="rounded-lg border border-neutral-200 p-5">
              <h2 className="mb-2 font-medium text-neutral-900">Social determinants of health</h2>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-neutral-600">
                <Field label="Housing" value={fmt(member.sdoh.housing_status)} />
                <Field label="Food security" value={fmt(member.sdoh.food_security)} />
                <Field label="Transportation" value={fmt(member.sdoh.transportation_access)} />
                <Field label="Income" value={fmt(member.sdoh.income_bracket)} />
              </div>
            </section>
          )}

          <section className="rounded-lg border border-neutral-200 p-5">
            <h2 className="mb-2 font-medium text-neutral-900">Active medications</h2>
            <RowList
              rows={member.medications}
              render={(m) => `${fmt(m.medication_name)} · started ${fmt(m.start_date)}`}
              empty="No active medications."
            />
          </section>

          <section className="rounded-lg border border-neutral-200 p-5">
            <h2 className="mb-2 font-medium text-neutral-900">Recent claims</h2>
            <RowList
              rows={member.recent_claims}
              render={(c) => `${fmt(c.service_date)} — ${fmt(c.diagnosis_desc)} (${fmt(c.procedure_desc)}) · $${fmt(c.paid_amount)}`}
              empty="No claims on record."
            />
          </section>

          <section className="rounded-lg border border-neutral-200 p-5">
            <h2 className="mb-2 font-medium text-neutral-900">Recent encounters</h2>
            <RowList
              rows={member.recent_encounters}
              render={(e) => `${fmt(e.encounter_date)} — ${fmt(e.encounter_type)} (${fmt(e.reason)})`}
              empty="No encounters on record."
            />
          </section>
        </div>

        <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
          <ChatPanel memberId={memberId} />
        </div>
      </div>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-neutral-400">{label}: </span>
      <span>{value}</span>
    </div>
  );
}

function RowList<T extends Record<string, unknown>>({
  rows,
  render,
  empty,
}: {
  rows: T[];
  render: (row: T) => string;
  empty: string;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-neutral-400">{empty}</p>;
  }
  return (
    <ul className="space-y-1 text-sm text-neutral-600">
      {rows.map((row, i) => (
        <li key={i}>{render(row)}</li>
      ))}
    </ul>
  );
}
