"""Synthetic error-injection benchmark.

For every (note, faithful summary) pair in examples/notes, apply each perturbation
and check whether note-drift raises a new medium/high finding of the right kind
that was not already present on the faithful summary.

    python benchmarks/run_benchmark.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from note_drift import check  # noqa: E402
from note_drift.perturb import PERTURBATIONS  # noqa: E402

SERIOUS = {"high", "medium"}


def serious(report):
    return {(f.kind, f.key, f.status, f.detail) for f in report.findings if f.severity in SERIOUS}


def main():
    notes = ROOT / "examples" / "notes"
    pairs = [(p, p.with_name(p.stem + ".summary_good.txt")) for p in sorted(notes.glob("*.txt"))
             if ".summary" not in p.name]
    pairs = [(n, s) for n, s in pairs if s.exists()]
    results, false_pos = {}, 0
    for note_path, good_path in pairs:
        note, good = note_path.read_text(), good_path.read_text()
        base = serious(check(note, good))
        false_pos += len(base)
        for name, (fn, kind) in PERTURBATIONS.items():
            bad = fn(good)
            if bad is None or bad == good:
                continue
            new = serious(check(note, bad)) - base
            hit = any(k == kind or (kind == "medication" and k == "medication") for k, *_ in new)
            r = results.setdefault(name, {"applied": 0, "detected": 0})
            r["applied"] += 1
            r["detected"] += int(hit)
    total_a = sum(r["applied"] for r in results.values())
    total_d = sum(r["detected"] for r in results.values())
    print(f"{len(pairs)} note/summary pairs\n")
    print(f"{'perturbation':<18}{'applied':>8}{'detected':>10}")
    for name, r in results.items():
        print(f"{name:<18}{r['applied']:>8}{r['detected']:>10}")
    print(f"{'total':<18}{total_a:>8}{total_d:>10}   recall {total_d / total_a:.0%}")
    print(f"\nmedium/high findings on faithful summaries (false alarms): {false_pos}")
    (ROOT / "benchmarks" / "results.json").write_text(
        json.dumps({"pairs": len(pairs), "results": results, "false_alarms": false_pos}, indent=2))


if __name__ == "__main__":
    main()
