import { describe, expect, it } from "vitest";

import { segment, spansFor, type Finding } from "./drift";

const f = (over: Partial<Finding>): Finding => ({
  kind: "medication",
  key: "x",
  status: "changed",
  detail: "d",
  severity: "high",
  note_text: null,
  note_span: null,
  summary_text: null,
  summary_span: null,
  ...over,
});

describe("segment", () => {
  it("splits text around spans and keeps every character", () => {
    const text = "take aspirin 81 mg daily";
    const segs = segment(text, [{ span: [5, 12], severity: "high", detail: "d", index: 0 }]);
    expect(segs.map((s) => s.text).join("")).toBe(text);
    expect(segs[1]).toMatchObject({ text: "aspirin", severity: "high", index: 0 });
  });

  it("keeps the more severe of two overlapping spans", () => {
    const segs = segment("abcdefghij", [
      { span: [0, 5], severity: "low", detail: "low", index: 0 },
      { span: [3, 8], severity: "high", detail: "high", index: 1 },
    ]);
    const marked = segs.filter((s) => s.severity);
    expect(marked).toHaveLength(1);
    expect(marked[0].severity).toBe("high");
  });

  it("ignores spans outside the text", () => {
    const segs = segment("short", [{ span: [3, 99], severity: "high", detail: "d", index: 0 }]);
    expect(segs).toEqual([{ text: "short" }]);
  });
});

describe("spansFor", () => {
  it("hides info findings unless asked", () => {
    const findings = [f({ severity: "info", note_span: [0, 2] }), f({ severity: "high", note_span: [3, 5] })];
    expect(spansFor(findings, "note")).toHaveLength(1);
    expect(spansFor(findings, "note", true)).toHaveLength(2);
    expect(spansFor(findings, "summary")).toHaveLength(0);
  });
});
