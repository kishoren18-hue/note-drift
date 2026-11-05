import { Checker } from "@/components/checker";
import { getUser } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function Home() {
  const user = await getUser();
  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <div className="mb-8 max-w-3xl">
        <p className="mb-3 text-sm font-medium text-accent">Open-source safety check for AI clinical summaries</p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Catch the facts that change when a clinical note gets summarized.
        </h1>
        <p className="mt-4 text-lg text-muted">
          A dose that turns 20&nbsp;mg into 200&nbsp;mg. A right ear that becomes a left ear. An allergy that quietly disappears.
          note-drift reads both documents and flags every fact that was dropped, changed or invented, ranked by how much it
          could hurt a patient.
        </p>
      </div>
      <Checker signedIn={Boolean(user)} />
    </main>
  );
}
