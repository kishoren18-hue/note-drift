"""note-drift NOTE SUMMARY [--json] [--html report.html] [--fail-on high]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compare import SEVERITY_ORDER, check
from .report import to_html


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="note-drift",
                                 description="Flag facts that were dropped, changed or invented in a clinical summary.")
    ap.add_argument("note", help="source note (text file)")
    ap.add_argument("summary", help="summary or handoff to check (text file)")
    ap.add_argument("--json", action="store_true", help="print findings as JSON")
    ap.add_argument("--html", help="write a side-by-side HTML report here")
    ap.add_argument("--show-info", action="store_true", help="also list info-level omissions")
    ap.add_argument("--fail-on", choices=["high", "medium", "low", "never"], default="high",
                    help="exit 1 if any finding at or above this severity (default: high)")
    a = ap.parse_args(argv)

    note, summary = Path(a.note).read_text(), Path(a.summary).read_text()
    rep = check(note, summary)
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
    if a.fail_on != "never" and any(SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[a.fail_on] for f in rep.findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
