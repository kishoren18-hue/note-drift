"""note-drift command line.

    note-drift NOTE SUMMARY [--html report.html] [--json] [--fail-on high]
    note-drift batch DIR [--csv results.csv] [--html-dir reports/]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .compare import SEVERITY_ORDER, check
from .extract import Vocabulary
from .report import to_html


def _vocab(path):
    return Vocabulary.from_json(path) if path else None


def _fails(rep, level):
    return level != "never" and any(SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[level] for f in rep.findings)


def pair_files(folder: Path, marker: str = ".summary") -> list[tuple[Path, Path]]:
    """Pair every 'X<marker>*.txt' summary with its note 'X.txt'."""
    pairs = []
    for s in sorted(folder.glob(f"*{marker}*.txt")):
        stem = s.name.split(marker)[0]
        note = s.with_name(stem + ".txt")
        if note.exists():
            pairs.append((note, s))
    return pairs


def batch_main(argv) -> int:
    ap = argparse.ArgumentParser(prog="note-drift batch",
                                 description="Check every note/summary pair in a folder and write a CSV summary.")
    ap.add_argument("folder")
    ap.add_argument("--marker", default=".summary",
                    help="summaries are named <note-stem><marker>*.txt (default '.summary')")
    ap.add_argument("--csv", help="write one row per pair here")
    ap.add_argument("--html-dir", help="write an HTML report per pair into this folder")
    ap.add_argument("--lexicon", help="JSON file adding medications, conditions, allergens, body_parts, aliases")
    ap.add_argument("--fail-on", choices=["high", "medium", "low", "never"], default="high")
    a = ap.parse_args(argv)

    vocab = _vocab(a.lexicon)
    pairs = pair_files(Path(a.folder), a.marker)
    if not pairs:
        print(f"no '<name>{a.marker}*.txt' summaries with a matching '<name>.txt' note in {a.folder}", file=sys.stderr)
        return 2
    rows, failed = [], 0
    if a.html_dir:
        Path(a.html_dir).mkdir(parents=True, exist_ok=True)
    for note_p, sum_p in pairs:
        note, summary = note_p.read_text(), sum_p.read_text()
        rep = check(note, summary, vocab)
        c = rep.counts()
        top = next((f for f in rep.findings if f.severity != "info"), None)
        rows.append({"note": note_p.name, "summary": sum_p.name, "worst": rep.worst(),
                     "high": c.get("high", 0), "medium": c.get("medium", 0), "low": c.get("low", 0),
                     "top_finding": top.detail if top else ""})
        failed += _fails(rep, a.fail_on)
        if a.html_dir:
            (Path(a.html_dir) / (sum_p.stem + ".html")).write_text(
                to_html(note, summary, rep, f"note-drift: {sum_p.name}"))
    w = max(len(r["summary"]) for r in rows)
    for r in rows:
        print(f"{r['summary']:<{w}}  {r['worst']:<6}  H{r['high']} M{r['medium']} L{r['low']}  {r['top_finding'][:70]}")
    print(f"\n{len(rows)} pairs, {failed} at or above '{a.fail_on}'")
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    return 1 if failed else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "batch":
        return batch_main(argv[1:])
    ap = argparse.ArgumentParser(prog="note-drift",
                                 description="Flag facts that were dropped, changed or invented in a clinical summary.",
                                 epilog="Check a whole folder with: note-drift batch DIR")
    ap.add_argument("note", help="source note (text file)")
    ap.add_argument("summary", help="summary or handoff to check (text file)")
    ap.add_argument("--json", action="store_true", help="print findings as JSON")
    ap.add_argument("--html", help="write a side-by-side HTML report here")
    ap.add_argument("--show-info", action="store_true", help="also list info-level omissions")
    ap.add_argument("--lexicon", help="JSON file adding medications, conditions, allergens, body_parts, aliases")
    ap.add_argument("--fail-on", choices=["high", "medium", "low", "never"], default="high",
                    help="exit 1 if any finding at or above this severity (default: high)")
    a = ap.parse_args(argv)

    note, summary = Path(a.note).read_text(), Path(a.summary).read_text()
    rep = check(note, summary, _vocab(a.lexicon))
    if a.json:
        print(json.dumps(rep.as_dict(), indent=2))
    else:
        shown = [f for f in rep.findings if a.show_info or f.severity != "info"]
        if not shown:
            print("No findings.")
        for f in shown:
            print(f"[{f.severity.upper():<6}] {f.kind:<11} {f.status:<16} {f.detail}")
    if a.html:
        Path(a.html).write_text(to_html(note, summary, rep, f"note-drift: {Path(a.summary).name}"))
        print(f"\nHTML report: {a.html}", file=sys.stderr)
    return 1 if _fails(rep, a.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
