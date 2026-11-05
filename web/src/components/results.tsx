"use client";

import { useState } from "react";

import { type CheckResult, SEVERITY_LABEL, type Severity, STATUS_LABEL } from "@/lib/drift";

import { DocView } from "./doc-view";
import { Alert, Badge, cx } from "./ui";

const tone: Record<Severity, "danger" | "warn" | "neutral" | "accent"> = {
  high: "danger",
  medium: "warn",
  low: "neutral",
  info: "neutral",
};

export function Results({
  note,
  summary,
  result,
  injected = [],
}: {
  note: string;
  summary: string;
  result: CheckResult;
  injected?: string[];
}) {
  const [active, setActive] = useState<number | null>(null);
  const [showLow, setShowLow] = useState(false);
  const [revealed, setRevealed] = useState(false);

  const visible = result.findings
    .map((f, i) => ({ f, i }))
    .filter(({ f }) => f.severity === "high" || f.severity === "medium" || (showLow && f.severity !== "info"));
  const hiddenCount = result.findings.filter((f) => f.severity === "low").length;

  function pick(i: number) {
    setActive(i);
    for (const side of ["note", "summary"]) {
      document.getElementById(`${side}-f${i}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  const high = result.counts.high ?? 0;
  const medium = result.counts.medium ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold tracking-tight">
          {high + medium === 0 ? "No serious problems found" : `${high + medium} problem${high + medium === 1 ? "" : "s"} found`}
        </h2>
        <Badge tone="danger">{high} high</Badge>
        <Badge tone="warn">{medium} medium</Badge>
        <Badge>{result.counts.low ?? 0} low</Badge>
        <span className="text-xs text-muted">
          {result.n_note_facts} facts read in the note, {result.n_summary_facts} in the summary
        </span>
      </div>

      {injected.length > 0 && (
        <Alert tone="neutral" title="Challenge mode: Claude hid errors in this summary">
          {revealed ? (
            <ul className="mt-1 list-disc pl-5">
              {injected.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          ) : (
            <p>
              See whether the findings below caught them, then{" "}
              <button className="font-medium text-accent underline" onClick={() => setRevealed(true)}>
                reveal what Claude changed
              </button>
              .
            </p>
          )}
        </Alert>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <DocView title="Source note" text={note} findings={result.findings} side="note" active={active} onPick={pick} showInfo={false} />
        <DocView title="Summary" text={summary} findings={result.findings} side="summary" active={active} onPick={pick} showInfo={false} />
      </div>

      <section aria-labelledby="findings-h">
        <div className="mb-3 flex items-center justify-between">
          <h3 id="findings-h" className="font-semibold">
            Findings
          </h3>
          {hiddenCount > 0 && (
            <label className="flex items-center gap-2 text-sm text-muted">
              <input type="checkbox" checked={showLow} onChange={(e) => setShowLow(e.target.checked)} />
              Show {hiddenCount} low-severity omission{hiddenCount === 1 ? "" : "s"}
            </label>
          )}
        </div>
        {visible.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line p-6 text-center text-sm text-muted">
            Nothing at medium or high severity. Summaries are expected to leave some details out.
          </p>
        ) : (
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {visible.map(({ f, i }) => (
              <li key={i}>
                <button
                  onClick={() => pick(i)}
                  className={cx(
                    "flex w-full flex-wrap items-start gap-x-3 gap-y-1 px-4 py-3 text-left text-sm hover:bg-surface-2",
                    active === i && "bg-surface-2",
                  )}
                >
                  <Badge tone={tone[f.severity]} className="mt-0.5 w-16 justify-center">
                    {SEVERITY_LABEL[f.severity]}
                  </Badge>
                  <span className="mt-0.5 w-28 shrink-0 text-xs uppercase tracking-wide text-muted">
                    {STATUS_LABEL[f.status] ?? f.status} · {f.kind}
                  </span>
                  <span className="min-w-0 flex-1">{f.detail}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
