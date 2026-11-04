"""Self-contained HTML report with highlighted spans in both documents."""

from __future__ import annotations

import html

from .compare import DriftReport

COLORS = {"high": "#f6c1c1", "medium": "#fbe3b0", "low": "#dbe8f7", "info": "#ececec"}


def _highlight(text: str, spans: list[tuple[int, int, str, str]]) -> str:
    spans = sorted(s for s in spans if s[0] < s[1])
    out, pos = [], 0
    for start, end, sev, tip in spans:
        if start < pos:
            continue  # skip overlaps; the first (earliest) highlight wins
        out.append(html.escape(text[pos:start]))
        out.append(f'<mark class="{sev}" title="{html.escape(tip)}">{html.escape(text[start:end])}</mark>')
        pos = end
    out.append(html.escape(text[pos:]))
    return "".join(out)


def to_html(note: str, summary: str, report: DriftReport, title: str = "note-drift report") -> str:
    shown = [f for f in report.findings if f.severity != "info"]
    note_spans = [(*f.note_fact.span, f.severity, f.detail) for f in shown if f.note_fact]
    summ_spans = [(*f.summary_fact.span, f.severity, f.detail) for f in shown if f.summary_fact]
    rows = "\n".join(
        f'<tr><td><span class="pill {f.severity}">{f.severity}</span></td><td>{html.escape(f.kind)}</td>'
        f"<td>{html.escape(f.status)}</td><td>{html.escape(f.detail)}</td></tr>" for f in shown)
    counts = report.counts()
    badge = " · ".join(f"{counts.get(s, 0)} {s}" for s in ("high", "medium", "low"))
    css = "".join(f"mark.{k},.pill.{k}{{background:{v}}}" for k, v in COLORS.items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:24px 16px;color:#1d2330;background:#fff}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#5b6475;margin-bottom:20px}}
.docs{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:760px){{.docs{{grid-template-columns:1fr}}}}
pre{{white-space:pre-wrap;background:#f7f8fa;border:1px solid #e3e6eb;border-radius:8px;padding:12px;font:13px/1.55 ui-monospace,monospace}}
mark{{border-radius:3px;padding:0 2px}} {css}
table{{border-collapse:collapse;width:100%;margin-top:20px}} td,th{{border-bottom:1px solid #e3e6eb;padding:8px;text-align:left;vertical-align:top}}
.pill{{border-radius:10px;padding:1px 8px;font-size:12px}}
.note{{color:#5b6475;font-size:13px;margin-top:24px}}
</style></head><body>
<h1>{html.escape(title)}</h1><div class="sub">{badge}</div>
<div class="docs"><div><h3>Source note</h3><pre>{_highlight(note, note_spans)}</pre></div>
<div><h3>Summary</h3><pre>{_highlight(summary, summ_spans)}</pre></div></div>
<table><thead><tr><th>severity</th><th>kind</th><th>status</th><th>detail</th></tr></thead><tbody>
{rows or '<tr><td colspan="4">No medium or high findings.</td></tr>'}</tbody></table>
<p class="note">Rule-based screening aid. It can miss errors and flag non-errors; a clinician must review every summary.</p>
</body></html>"""
