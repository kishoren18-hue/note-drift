"""Compare facts in a source note against facts in its summary."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .extract import Fact, extract

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1, "info": 0}


@dataclass
class Finding:
    kind: str
    key: str
    status: str  # omitted | invented | changed | detail-omitted
    detail: str
    severity: str
    note_fact: Fact | None = None
    summary_fact: Fact | None = None

    def as_dict(self) -> dict:
        return {
            "kind": self.kind, "key": self.key, "status": self.status, "detail": self.detail,
            "severity": self.severity,
            "note_text": self.note_fact.text if self.note_fact else None,
            "note_span": list(self.note_fact.span) if self.note_fact else None,
            "summary_text": self.summary_fact.text if self.summary_fact else None,
            "summary_span": list(self.summary_fact.span) if self.summary_fact else None,
        }


@dataclass
class DriftReport:
    findings: list[Finding]
    note_facts: list[Fact]
    summary_facts: list[Fact]

    def worst(self) -> str:
        if not self.findings:
            return "none"
        return max(self.findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity

    def counts(self) -> dict:
        c = defaultdict(int)
        for f in self.findings:
            c[f.severity] += 1
        return dict(c)

    def as_dict(self) -> dict:
        return {"worst": self.worst(), "counts": self.counts(),
                "findings": [f.as_dict() for f in self.findings]}


# (kind, status) -> severity. Summaries are expected to drop detail, so plain
# omissions are mostly low; changed values and invented facts are what hurt patients.
SEVERITY = {
    ("allergy", "omitted"): "high", ("allergy", "invented"): "medium", ("allergy", "changed"): "high",
    ("medication", "omitted"): "medium", ("medication", "invented"): "high", ("medication", "changed"): "high",
    ("medication", "detail-omitted"): "low",
    ("condition", "changed"): "high", ("condition", "invented"): "medium", ("condition", "omitted"): "low",
    ("laterality", "changed"): "high", ("laterality", "invented"): "medium", ("laterality", "omitted"): "info",
    ("vital", "changed"): "medium", ("vital", "invented"): "medium", ("vital", "omitted"): "info",
    ("lab", "changed"): "medium", ("lab", "invented"): "medium", ("lab", "omitted"): "info",
}


def _group(facts):
    g = defaultdict(list)
    for f in facts:
        g[(f.kind, f.key)].append(f)
    return g


def _fmt_med(v):
    parts = []
    if v["dose"] is not None:
        d = v["dose"]
        parts.append(f"{d:g} {v['unit']}")
    if v["frequency"]:
        parts.append(v["frequency"])
    if v["status"] == "stopped":
        parts.append("stopped")
    return " ".join(parts) or "(no dose given)"


def _same_dose(a, b):
    return a["dose"] is not None and b["dose"] is not None and abs(a["dose"] - b["dose"]) < 1e-9 \
        and a["unit"] == b["unit"]


def _compare_med(key, nf, sf):
    """Compare a drug's latest state in the note (plans usually come last) with the summary.

    Returns (status, detail, note_fact, summary_fact, severity_override).
    """
    out = []
    n_dosed = [f for f in nf if f.value["dose"] is not None]
    s_dosed = [f for f in sf if f.value["dose"] is not None]
    n_last_status, s_last_status = nf[-1].value["status"], sf[-1].value["status"]
    if n_last_status != s_last_status:
        out.append(("changed", f"note's latest instruction is '{n_last_status}', summary says '{s_last_status}'",
                    nf[-1], sf[-1], None))
    if n_dosed and s_dosed:
        n, s = n_dosed[-1], s_dosed[-1]
        nv, sv = n.value, s.value
        if not _same_dose(nv, sv):
            earlier = next((f for f in n_dosed[:-1] if _same_dose(f.value, sv)), None)
            if earlier:
                out.append(("changed", f"summary uses an earlier dose ({_fmt_med(sv)}); note's latest is "
                            f"{_fmt_med(nv)}", n, s, "medium"))
            else:
                out.append(("changed", f"dose {_fmt_med(nv)} -> {_fmt_med(sv)}", n, s, None))
        elif nv["frequency"] and sv["frequency"] and nv["frequency"] != sv["frequency"]:
            out.append(("changed", f"frequency {nv['frequency']} -> {sv['frequency']}", n, s, None))
    elif n_dosed and not s_dosed and s_last_status == "active":
        out.append(("detail-omitted", f"dose {_fmt_med(n_dosed[-1].value)} not stated in summary",
                    n_dosed[-1], sf[-1], None))
    return out


def _generalize_conditions(note_facts, summary_facts):
    """Treat 'type 2 diabetes' and 'diabetes' as the same problem across documents."""
    keys = {f.key for f in note_facts + summary_facts if f.kind == "condition"}
    for f in note_facts + summary_facts:
        if f.kind == "condition":
            general = [k for k in keys if k != f.key and f.key.endswith(" " + k)]
            if general:
                f.key = min(general, key=len)


def compare_facts(note_facts: list[Fact], summary_facts: list[Fact]) -> list[Finding]:
    _generalize_conditions(note_facts, summary_facts)
    ng, sg = _group(note_facts), _group(summary_facts)
    findings = []

    def add(kind, key, status, detail, nf=None, sf=None, severity=None):
        sev = severity or SEVERITY.get((kind, status), "low")
        findings.append(Finding(kind, key, status, detail, sev, nf, sf))

    # a drug the summary gives the patient that the note lists as an allergy
    note_allergens = {k for (kind, k) in ng if kind == "allergy" and k != "__none__"}
    for (kind, key), sf in sg.items():
        if kind == "medication" and any(f.value["status"] == "active" for f in sf):
            hit = next((a for a in note_allergens if a == key or a.rstrip("s") == key or key.startswith(a)), None)
            if hit:
                add("medication", key, "allergy-conflict",
                    f"summary has the patient taking {key}, but the note lists an allergy to {hit}",
                    ng[("allergy", hit)][0], sf[0], "high")

    # "no known allergies" vs a listed allergy is a contradiction, not an omission
    note_none = ("allergy", "__none__") in ng
    summ_none = ("allergy", "__none__") in sg
    for (kind, key) in sorted(set(ng) | set(sg)):
        nf, sf = ng.get((kind, key), []), sg.get((kind, key), [])
        if key == "__none__":
            if nf and not sf and any(k == "allergy" and kk != "__none__" for k, kk in sg):
                add("allergy", "allergy status", "changed", "note says no known allergies; summary lists one",
                    nf[0], None)
            continue
        if nf and not sf:
            if kind == "condition" and not any(f.value["present"] for f in nf):
                continue  # dropping a negative finding is fine
            if kind == "allergy" and summ_none:
                add(kind, key, "changed", f"allergy to {key} replaced by 'no known allergies'", nf[0],
                    sg[("allergy", "__none__")][0])
                continue
            sev = "low" if kind == "medication" and all(f.value["status"] != "active" for f in nf) else None
            add(kind, key, "omitted", f"{kind} '{key}' is in the note but not the summary", nf[0], None, sev)
        elif sf and not nf:
            if kind == "condition" and not any(f.value["present"] for f in sf):
                continue
            if kind == "allergy" and note_none:
                continue  # reported once above
            add(kind, key, "invented", f"{kind} '{key}' appears in the summary but not the note", None, sf[0])
        else:
            if kind == "medication":
                for status, detail, a, b, sev in _compare_med(key, nf, sf):
                    add(kind, key, status, f"{key}: {detail}", a, b, sev)
            elif kind == "condition":
                n_pres = any(f.value["present"] for f in nf)
                s_pres = any(f.value["present"] for f in sf)
                if n_pres != s_pres:
                    add(kind, key, "changed",
                        f"'{key}' is {'present' if n_pres else 'absent/negated'} in the note but "
                        f"{'present' if s_pres else 'absent/negated'} in the summary", nf[0], sf[0])
            elif kind == "laterality":
                ns, ss = {f.value["side"] for f in nf}, {f.value["side"] for f in sf}
                if not ns & ss:
                    add(kind, key, "changed", f"{key}: {'/'.join(sorted(ns))} in note -> {'/'.join(sorted(ss))} "
                        "in summary", nf[0], sf[0])
            elif kind in ("vital", "lab"):
                nv = {f.value["value"] for f in nf}
                sv = {f.value["value"] for f in sf}
                if not nv & sv:
                    add(kind, key, "changed", f"{key}: {', '.join(map(str, sorted(nv, key=str)))} in note -> "
                        f"{', '.join(map(str, sorted(sv, key=str)))} in summary", nf[0], sf[0])
    findings.sort(key=lambda f: (-SEVERITY_ORDER[f.severity], f.kind, f.key))
    return findings


def check(note: str, summary: str, vocab=None) -> DriftReport:
    """Compare a source note with its summary. Pass a Vocabulary to extend the built-in word lists."""
    nf, sf = extract(note, vocab), extract(summary, vocab)
    return DriftReport(compare_facts(nf, sf), nf, sf)
