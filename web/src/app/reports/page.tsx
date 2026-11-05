import Link from "next/link";
import { redirect } from "next/navigation";

import { Badge, ButtonLink } from "@/components/ui";
import { supabaseConfigured } from "@/lib/supabase/env";
import { getServerClient, getUser } from "@/lib/supabase/server";

export const metadata = { title: "My reports" };

type Row = { id: string; title: string; worst: string; counts: Record<string, number>; summary_source: string; is_public: boolean; created_at: string };

const tone = { high: "danger", medium: "warn", low: "neutral", info: "neutral", none: "ok" } as const;

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  if (!supabaseConfigured) redirect("/login");
  const user = await getUser();
  if (!user) redirect("/login?next=/reports");
  const supabase = (await getServerClient())!;
  const { data, error } = await supabase
    .from("nd_reports")
    .select("id,title,worst,counts,summary_source,is_public,created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(100);
  const rows = (data ?? []) as Row[];

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">My reports</h1>
        <ButtonLink href="/">New check</ButtonLink>
      </div>
      {error && <p className="text-sm text-danger">Couldn&apos;t load reports: {error.message}</p>}
      {rows.length === 0 && !error ? (
        <div className="rounded-xl border border-dashed border-line p-10 text-center text-muted">
          <p>No saved reports yet.</p>
          <p className="mt-1 text-sm">Run a check, then use &quot;Save report&quot; under the results.</p>
        </div>
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {rows.map((r) => (
            <li key={r.id}>
              <Link href={`/r/${r.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-surface-2">
                <span className="min-w-0 flex-1 truncate font-medium">{r.title}</span>
                {r.is_public && <Badge tone="accent">Public</Badge>}
                <Badge tone={tone[r.worst as keyof typeof tone] ?? "neutral"}>
                  {r.worst === "none" ? "Clean" : `${(r.counts.high ?? 0) + (r.counts.medium ?? 0)} problems`}
                </Badge>
                <span className="w-28 text-right text-xs text-muted">
                  {new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
