export type Severity = "high" | "medium" | "low" | "info";

export type Finding = {
  kind: string;
  key: string;
  status: string;
  detail: string;
  severity: Severity;
  note_text: string | null;
  note_span: [number, number] | null;
  summary_text: string | null;
  summary_span: [number, number] | null;
};

export type CheckResult = {
  worst: Severity | "none";
  counts: Partial<Record<Severity, number>>;
  findings: Finding[];
  identifiers: string[];
  n_note_facts: number;
  n_summary_facts: number;
};

export type Segment = { text: string; severity?: Severity; detail?: string; index?: number };

const ORDER: Record<Severity, number> = { high: 3, medium: 2, low: 1, info: 0 };

/** Split text into plain and highlighted segments. Overlapping spans keep the most severe finding. */
export function segment(text: string, spans: { span: [number, number]; severity: Severity; detail: string; index: number }[]): Segment[] {
  const valid = spans
    .filter((s) => s.span[0] < s.span[1] && s.span[0] >= 0 && s.span[1] <= text.length)
    .sort((a, b) => a.span[0] - b.span[0] || ORDER[b.severity] - ORDER[a.severity]);
  const kept: typeof valid = [];
  for (const s of valid) {
    const last = kept[kept.length - 1];
    if (last && s.span[0] < last.span[1]) {
      if (ORDER[s.severity] > ORDER[last.severity]) kept[kept.length - 1] = s;
      continue;
    }
    kept.push(s);
  }
  const out: Segment[] = [];
  let pos = 0;
  for (const s of kept) {
    if (s.span[0] > pos) out.push({ text: text.slice(pos, s.span[0]) });
    out.push({ text: text.slice(s.span[0], s.span[1]), severity: s.severity, detail: s.detail, index: s.index });
    pos = s.span[1];
  }
  if (pos < text.length) out.push({ text: text.slice(pos) });
  return out;
}

export function spansFor(findings: Finding[], side: "note" | "summary", showInfo = false) {
  return findings
    .map((f, index) => ({ f, index }))
    .filter(({ f }) => showInfo || f.severity !== "info")
    .flatMap(({ f, index }) => {
      const span = side === "note" ? f.note_span : f.summary_span;
      return span ? [{ span, severity: f.severity, detail: f.detail, index }] : [];
    });
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

export const STATUS_LABEL: Record<string, string> = {
  changed: "Changed",
  invented: "Invented",
  omitted: "Missing",
  "detail-omitted": "Detail missing",
  "allergy-conflict": "Allergy conflict",
};
