import { Card } from "@/components/ui";

export const metadata = { title: "How it works" };

const steps = [
  {
    title: "1. Extract checkable facts",
    body: "Transparent rules pull allergies (with reactions), medications (dose, unit, frequency, as-needed, stopped), vitals, labs, conditions with negation, and left/right from both documents. Every fact keeps the exact characters it came from, so every flag can be traced.",
  },
  {
    title: "2. Compare them",
    body: "Facts are matched by type and name. Brand names map to generics (Tylenol matches acetaminophen). For medications, the note's latest instruction wins, since plans come after the home medication list.",
  },
  {
    title: "3. Rank by harm",
    body: "Summaries are supposed to drop detail, so plain omissions of vitals are informational. Changed doses, swapped sides, flipped negations, invented drugs and dropped allergies are high severity. A drug the patient is allergic to appearing as active is always flagged.",
  },
];

export default function HowItWorks() {
  return (
    <main className="mx-auto max-w-4xl space-y-10 px-4 py-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">How it works</h1>
        <p className="mt-3 text-lg text-muted">
          No model judges another model here. The checker is deterministic, open source and runs in milliseconds, so it can sit
          in front of any AI summarizer as a safety gate.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {steps.map((s) => (
          <Card key={s.title}>
            <h2 className="font-semibold">{s.title}</h2>
            <p className="mt-2 text-sm text-muted">{s.body}</p>
          </Card>
        ))}
      </div>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Architecture</h2>
        <Card className="overflow-x-auto font-mono text-[13px] leading-6">
          <pre>{`Browser (Next.js 15, React 19, TypeScript, Tailwind)
   │  POST /api/py/check ────────────► FastAPI (Python) ─► note_drift library
   │  POST /api/py/summarize ─────────► FastAPI ─► Claude API
   │                                      └─► Supabase RPC: per-user daily quota
   └─ save / list / share reports ────► Supabase Postgres (row-level security)
                                         Supabase Auth (email magic link)`}</pre>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Safety and privacy</h2>
        <ul className="list-disc space-y-2 pl-5 text-muted">
          <li>Use synthetic notes only. Text that looks like it contains real identifiers (SSNs, phone numbers, record numbers, dates of birth, addresses) is never sent to the AI, and saving is disabled.</li>
          <li>Checking a summary stores nothing. Reports are saved only when you choose to, visible only to you unless you make the link public, and deleted with one click.</li>
          <li>AI summaries need an account and are limited per day, so the hosted demo can&apos;t be abused.</li>
          <li>This is a screening aid. It can miss errors and flag non-errors, and it is not a medical device.</li>
        </ul>
      </section>
    </main>
  );
}
