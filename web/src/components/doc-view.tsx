"use client";

import { segment, type Finding, spansFor, type Severity } from "@/lib/drift";

import { cx } from "./ui";

const markClass: Record<Severity, string> = {
  high: "bg-danger-soft text-danger ring-1 ring-danger/30",
  medium: "bg-warn-soft text-warn ring-1 ring-warn/30",
  low: "bg-info-soft ring-1 ring-line",
  info: "bg-surface-2",
};

export function DocView({
  title,
  text,
  findings,
  side,
  active,
  onPick,
  showInfo,
}: {
  title: string;
  text: string;
  findings: Finding[];
  side: "note" | "summary";
  active: number | null;
  onPick: (i: number) => void;
  showInfo: boolean;
}) {
  const segs = segment(text, spansFor(findings, side, showInfo));
  return (
    <section aria-label={title} className="flex min-w-0 flex-col">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">{title}</h3>
      <div className="max-h-[32rem] flex-1 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-surface p-4 font-mono text-[13px] leading-6">
        {segs.map((s, i) =>
          s.severity ? (
            <mark
              key={i}
              id={`${side}-f${s.index}`}
              title={s.detail}
              onClick={() => onPick(s.index!)}
              className={cx(
                "cursor-pointer rounded px-0.5 transition",
                markClass[s.severity],
                active === s.index && "outline outline-2 outline-offset-1 outline-ink",
              )}
            >
              {s.text}
            </mark>
          ) : (
            <span key={i}>{s.text}</span>
          ),
        )}
      </div>
    </section>
  );
}
