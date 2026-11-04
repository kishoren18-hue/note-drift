from pathlib import Path

import pytest

from note_drift import check, extract
from note_drift.cli import main
from note_drift.perturb import PERTURBATIONS

NOTES = Path(__file__).resolve().parent.parent / "examples" / "notes"


def kinds(facts, kind):
    return {f.key: f.value for f in facts if f.kind == kind}


def test_extracts_meds_with_dose_and_frequency():
    meds = kinds(extract("Start cefdinir 120 mg twice daily. Ibuprofen 170 mg every 6 hours as needed."), "medication")
    assert meds["cefdinir"]["dose"] == 120 and meds["cefdinir"]["frequency"] == "twice daily"
    assert meds["ibuprofen"]["prn"] is True


def test_unit_normalization():
    a = kinds(extract("acetaminophen 1 g every 6 hours"), "medication")["acetaminophen"]
    b = kinds(extract("acetaminophen 1000 mg every 6 hours"), "medication")["acetaminophen"]
    assert (a["dose"], a["unit"]) == (b["dose"], b["unit"]) == (1000, "mg")


def test_allergy_section_not_read_as_medication():
    facts = extract("Allergies: penicillin (hives), peanuts\nMeds: none")
    assert set(kinds(facts, "allergy")) == {"penicillin", "peanuts"}
    assert "penicillin" not in kinds(facts, "medication")
    assert kinds(facts, "allergy")["penicillin"]["reaction"] == "hives"


def test_negation():
    conds = kinds(extract("Denies chest pain. Reports palpitations. No evidence of pneumonia."), "condition")
    assert conds["chest pain"]["present"] is False
    assert conds["palpitations"]["present"] is True
    assert conds["pneumonia"]["present"] is False


def test_negation_scope_stops_at_but():
    conds = kinds(extract("No fever but reports cough."), "condition")
    assert conds["fever"]["present"] is False and conds["cough"]["present"] is True


def test_vitals_and_temperature_conversion():
    v = kinds(extract("BP 120/80, HR 88, T 100.4 F, SpO2 97%"), "vital")
    assert v["blood pressure"]["value"] == "120/80"
    assert v["temperature"]["value"] == pytest.approx(38.0)
    assert v["oxygen saturation"]["value"] == 97


def test_faithful_summaries_have_no_high_findings():
    for good in NOTES.glob("*.summary_good.txt"):
        note = good.with_name(good.name.replace(".summary_good", ""))
        rep = check(note.read_text(), good.read_text())
        assert rep.worst() in {"none", "low", "info"}, (good.name, [f.detail for f in rep.findings])


def test_bad_summary_findings():
    rep = check((NOTES / "peds_otitis.txt").read_text(), (NOTES / "peds_otitis.summary_bad.txt").read_text())
    details = " | ".join(f.detail for f in rep.findings if f.severity == "high")
    assert "replaced by 'no known allergies'" in details
    assert "right in note -> left" in details
    assert "allergy to amoxicillin" in details  # allergy conflict
    assert "frequency twice daily -> once daily" in details
    assert "pneumonia" in details


def test_stopped_med_and_earlier_dose():
    rep = check((NOTES / "ed_chest_pain.txt").read_text(), (NOTES / "ed_chest_pain.summary_bad.txt").read_text())
    details = " | ".join(f.detail for f in rep.findings)
    assert "metformin: note's latest instruction is 'stopped'" in details
    assert "earlier dose" in details  # lisinopril 20 vs latest 40


@pytest.mark.parametrize("name", list(PERTURBATIONS))
def test_every_perturbation_is_detected(name):
    fn, kind = PERTURBATIONS[name]
    note = (NOTES / "ed_chest_pain.txt").read_text()
    good = (NOTES / "ed_chest_pain.summary_good.txt").read_text()
    bad = fn(good)
    assert bad and bad != good
    base = {(f.kind, f.detail) for f in check(note, good).findings if f.severity in ("high", "medium")}
    new = {(f.kind, f.detail) for f in check(note, bad).findings if f.severity in ("high", "medium")} - base
    assert any(k == kind for k, _ in new), new


def test_cli(tmp_path):
    out = tmp_path / "r.html"
    code = main([str(NOTES / "peds_otitis.txt"), str(NOTES / "peds_otitis.summary_bad.txt"), "--html", str(out)])
    assert code == 1 and "<mark" in out.read_text()
    assert main([str(NOTES / "peds_otitis.txt"), str(NOTES / "peds_otitis.summary_good.txt")]) == 0
