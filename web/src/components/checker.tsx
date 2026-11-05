"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { CheckResult } from "@/lib/drift";
import { SAMPLES } from "@/lib/samples";
import { getBrowserClient } from "@/lib/supabase/client";

import { Results } from "./results";
import { Alert, Button, Card, cx, Input, Label, Textarea } from "./ui";

type Source = "pasted" | "claude" | "claude-challenge";
type Health = { ai: boolean; accounts: boolean; model: string } | null;

async function api<T>(path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(`/api/py/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Please check the text you entered." : data.detail;
    throw new Error(detail || `Request failed (${res.status}).`);
  }
  return data as T;
}

export function Checker({ signedIn }: { signedIn: boolean }) {
  const router = useRouter();
  const [mode, setMode] = useState<"paste" | "ai">("paste");
  const [challenge, setChallenge] = useState(true);
  const [note, setNote] = useState("");
  const [summary, setSummary] = useState("");
  const [source, setSource] = useState<Source>("pasted");
  const [model, setModel] = useState<string | null>(null);
  const [injected, setInjected] = useState<string[]>([]);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [checked, setChecked] = useState<{ note: string; summary: string } | null>(null);
  const [busy, setBusy] = useState<"" | "check" | "ai" | "save">("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<Health>(null);
  const [title, setTitle] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/py/health")
      .then((r) => (r.ok ? r.json() : null))
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  function loadSample(id: string) {
    const s = SAMPLES.find((x) => x.id === id);
    if (!s) return;
    setNote(s.note);
    setSummary(mode === "paste" ? s.summary : "");
    setSource("pasted");
    setInjected([]);
    setResult(null);
    setTitle(s.label);
  }

  async function runCheck(n = note, s = summary) {
    setBusy("check");
    setError("");
    try {
      const r = await api<CheckResult>("check", { note: n, summary: s });
      setResult(r);
      setChecked({ note: n, summary: s });
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function runAI() {
    setBusy("ai");
    setError("");
    setResult(null);
    try {
      const { data } = (await getBrowserClient()?.auth.getSession()) ?? { data: { session: null } };
      const token = data.session?.access_token;
      if (!token) throw new Error("Sign in to have Claude write a summary.");
      const r = await api<{ summary: string; injected: string[]; model: string }>(
        "summarize",
        { note, mode: challenge ? "challenge" : "faithful" },
        token,
      );
      setSummary(r.summary);
      setInjected(r.injected);
      setModel(r.model);
      setSource(challenge ? "claude-challenge" : "claude");
      await runCheck(note, r.summary);
    } catch (e) {
      setError((e as Error).message);
      setBusy("");
    }
  }

  async function save() {
    if (!result || !checked) return;
    const supabase = getBrowserClient();
    if (!supabase) return;
    setBusy("save");
    setError("");
    const { data, error: err } = await supabase
      .from("nd_reports")
      .insert({
        title: title.trim() || "Untitled report",
        note: checked.note,
        summary: checked.summary,
        summary_source: source,
        model,
        injected,
        findings: result.findings,
        worst: result.worst,
        counts: result.counts,
        is_public: isPublic,
      })
      .select("id")
      .single();
    setBusy("");
    if (err) return setError(`Couldn't save: ${err.message}`);
    router.push(`/r/${data.id}`);
  }

  const identifiers = result?.identifiers ?? [];
  const canCheck = note.trim() && summary.trim() && !busy;

  return (
    <div className="space-y-8">
      <Card className="space-y-5 p-0">
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 pt-4">
          {(
            [
              ["paste", "Paste a summary"],
              ["ai", "Have Claude summarize"],
            ] as const
          ).map(([m, label]) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setResult(null);
                if (m === "ai") setSummary("");
              }}
              className={cx(
                "-mb-px border-b-2 px-3 pb-3 text-sm font-medium",
                mode === m ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink",
              )}
              aria-pressed={mode === m}
            >
              {label}
            </button>
          ))}
          <div className="ml-auto pb-3">
            <label className="sr-only" htmlFor="sample">
              Load a sample
            </label>
            <select
              id="sample"
              defaultValue=""
              onChange={(e) => {
                loadSample(e.target.value);
                e.target.value = "";
              }}
              className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
            >
              <option value="" disabled>
                Load a synthetic sample…
              </option>
              {SAMPLES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className={cx("grid gap-5 px-5 pb-5", mode === "paste" && "lg:grid-cols-2")}>
          <div>
            <Label htmlFor="note">Source note</Label>
            <Textarea
              id="note"
              rows={14}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Paste a synthetic clinical note…"
              maxLength={20000}
            />
          </div>
          {mode === "paste" ? (
            <div>
              <Label htmlFor="summary">Summary to check</Label>
              <Textarea
                id="summary"
                rows={14}
                value={summary}
                onChange={(e) => {
                  setSummary(e.target.value);
                  setSource("pasted");
                  setInjected([]);
                }}
                placeholder="Paste the summary, handoff or discharge note written from it…"
                maxLength={20000}
              />
            </div>
          ) : (
            <div className="space-y-3">
              <fieldset className="flex flex-wrap gap-3 text-sm">
                <legend className="sr-only">Summary type</legend>
                <label className={cx("flex flex-1 cursor-pointer gap-3 rounded-lg border p-3", !challenge ? "border-accent bg-accent-soft" : "border-line")}>
                  <input type="radio" name="kind" checked={!challenge} onChange={() => setChallenge(false)} className="mt-1" />
                  <span>
                    <b>Faithful summary</b>
                    <span className="block text-muted">Claude summarizes as accurately as it can. How close does it get?</span>
                  </span>
                </label>
                <label className={cx("flex flex-1 cursor-pointer gap-3 rounded-lg border p-3", challenge ? "border-accent bg-accent-soft" : "border-line")}>
                  <input type="radio" name="kind" checked={challenge} onChange={() => setChallenge(true)} className="mt-1" />
                  <span>
                    <b>Challenge mode</b>
                    <span className="block text-muted">Claude secretly plants two errors. Can note-drift catch them?</span>
                  </span>
                </label>
              </fieldset>
              {health && !health.ai && (
                <Alert tone="warn">AI summaries aren&apos;t enabled on this deployment yet. Paste mode works.</Alert>
              )}
              {!signedIn && (
                <Alert tone="neutral">
                  <Link href="/login?next=/" className="font-medium text-accent underline">
                    Sign in
                  </Link>{" "}
                  to use Claude (free, 20 summaries a day). Checking a pasted summary needs no account.
                </Alert>
              )}
              {summary && (
                <div>
                  <Label htmlFor="ai-summary">Claude&apos;s summary {model && <span className="font-normal text-muted">({model})</span>}</Label>
                  <Textarea id="ai-summary" rows={6} value={summary} readOnly />
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
          {mode === "paste" ? (
            <Button onClick={() => runCheck()} disabled={!canCheck} loading={busy === "check"}>
              Check summary
            </Button>
          ) : (
            <Button onClick={runAI} disabled={!note.trim() || !signedIn || !!busy || health?.ai === false} loading={busy === "ai" || busy === "check"}>
              {busy === "ai" ? "Claude is writing…" : challenge ? "Generate a summary with hidden errors" : "Generate and check summary"}
            </Button>
          )}
          <span className="text-xs text-muted">Synthetic notes only. Nothing is stored unless you save the report.</span>
        </div>
      </Card>

      {error && (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      )}

      {result && checked && (
        <div ref={resultsRef} className="scroll-mt-20 space-y-6">
          {identifiers.length > 0 && (
            <Alert tone="warn" title="This text may contain real identifiers">
              It looks like it includes {identifiers.join(", ")}. Don&apos;t use real patient information here. Saving is disabled.
            </Alert>
          )}
          <Results note={checked.note} summary={checked.summary} result={result} injected={injected} />
          {signedIn && identifiers.length === 0 && (
            <Card className="flex flex-wrap items-end gap-3">
              <div className="min-w-48 flex-1">
                <Label htmlFor="title">Save this report</Label>
                <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Report title" maxLength={120} />
              </div>
              <label className="flex items-center gap-2 pb-2 text-sm">
                <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
                Anyone with the link can view
              </label>
              <Button onClick={save} loading={busy === "save"}>
                Save report
              </Button>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
