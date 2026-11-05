import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ReportActions } from "@/components/report-actions";
import { Results } from "@/components/results";
import { Badge } from "@/components/ui";
import type { CheckResult } from "@/lib/drift";
import { getServerClient, getUser } from "@/lib/supabase/server";

type Report = {
  id: string;
  user_id: string;
  title: string;
  note: string;
  summary: string;
  summary_source: string;
  model: string | null;
  injected: string[];
  findings: CheckResult["findings"];
  worst: CheckResult["worst"];
  counts: CheckResult["counts"];
  is_public: boolean;
  created_at: string;
};

async function load(id: string): Promise<Report | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  const supabase = await getServerClient();
  if (!supabase) return null;
  const { data } = await supabase.from("nd_reports").select("*").eq("id", id).maybeSingle();
  return data as Report | null;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const r = await load((await params).id);
  return { title: r?.title ?? "Report", robots: { index: false } };
}

const SOURCE: Record<string, string> = {
  pasted: "Pasted summary",
  ai: "Written by AI",
  "ai-challenge": "AI challenge mode",
  claude: "Written by Claude",
  "claude-challenge": "Claude challenge mode",
};

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [report, user] = await Promise.all([load(id), getUser()]);
  if (!report) notFound();
  const isOwner = user?.id === report.user_id;
  const result: CheckResult = {
    worst: report.worst,
    counts: report.counts,
    findings: report.findings,
    identifiers: [],
    n_note_facts: 0,
    n_summary_facts: 0,
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <Link href={isOwner ? "/reports" : "/"} className="text-sm text-muted hover:text-ink">
        ← {isOwner ? "My reports" : "note-drift"}
      </Link>
      <div className="mb-8 mt-3 flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{report.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span>{new Date(report.created_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}</span>
            <Badge>{SOURCE[report.summary_source] ?? report.summary_source}</Badge>
            {report.model && <Badge>{report.model}</Badge>}
            {report.is_public && <Badge tone="accent">Public link</Badge>}
          </p>
        </div>
        {isOwner && <ReportActions id={report.id} isPublic={report.is_public} />}
      </div>
      <Results note={report.note} summary={report.summary} result={result} injected={report.injected} />
    </main>
  );
}
