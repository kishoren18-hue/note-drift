"""Rule-based extraction of checkable clinical facts from free text.

Extracted fact kinds: allergy, medication, vital, lab, condition (with negation),
laterality. Rules are deliberately transparent: every fact keeps the character
span it came from, so a reviewer can see exactly why something was flagged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import lexicon as L

__all__ = ["Fact", "Vocabulary", "extract", "default_vocabulary"]


@dataclass
class Fact:
    kind: str
    key: str
    value: dict
    span: tuple[int, int]
    text: str = field(default="", repr=False)


_NUM = r"(\d+(?:\.\d+)?)"
_DOSE = re.compile(_NUM + r"\s*(mg/kg|mg|mcg|g|ml|mL|units?|puffs?|tablets?|tabs?|capsules?|drops?)\b", re.I)
_SENT_END = re.compile(r"[.\n;]")


def _sentence_bounds(text: str, pos: int) -> tuple[int, int]:
    start = max(text.rfind(".", 0, pos), text.rfind("\n", 0, pos), text.rfind(";", 0, pos)) + 1
    m = _SENT_END.search(text, pos)
    end = m.start() if m else len(text)
    return start, end


def _word_re(words) -> re.Pattern:
    alts = sorted((re.escape(w) for w in words), key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(alts) + r")(?![\w-])", re.I)


_FREQ = [(norm, re.compile(r"\b(?:" + "|".join(pats) + r")(?!\w)", re.I)) for norm, pats in L.FREQUENCIES.items()]
_PRE_NEG = re.compile(r"\b(?:" + "|".join(re.escape(c) for c in L.NEGATION_CUES) + r")\b", re.I)
_POST_NEG = re.compile(r"^\W*(?:\w+\W+){0,2}?(?:resolved|ruled out|is absent|was absent|negative)\b", re.I)
_DONE = re.compile(r"\b(?:treated with|received|was given|were given|completed|transitioned from)\b", re.I)
_STOP = re.compile(r"\b(?:stop(?:ped)?|discontinu(?:e|ed)|hold|held|d/c)\b", re.I)


class Vocabulary:
    """Words the extractor recognizes. Extend it for your specialty or institution.

    aliases map alternative names (brand names, abbreviations) to one canonical
    name, so "Tylenol" in a summary matches "acetaminophen" in the note.
    """

    def __init__(self, medications=(), conditions=(), allergens=(), body_parts=(), aliases=None):
        self.aliases = {k.lower(): v.lower() for k, v in (aliases or {}).items()}
        self.medications = {m.lower() for m in medications} | {
            a for a, v in self.aliases.items() if v in {m.lower() for m in medications}}
        self.conditions = {c.lower() for c in conditions}
        self.allergens = {a.lower() for a in allergens}
        self.body_parts = {b.lower() for b in body_parts}
        self.med_re = _word_re(self.medications)
        self.cond_re = _word_re(self.conditions)
        self.lateral_re = re.compile(r"\b(left|right|bilateral|l|r)\s+(" + "|".join(
            sorted(map(re.escape, self.body_parts), key=len, reverse=True)) + r")\b", re.I)

    def canonical(self, name: str) -> str:
        n = name.lower()
        return self.aliases.get(n, n)

    def extended(self, medications=(), conditions=(), allergens=(), body_parts=(), aliases=None) -> "Vocabulary":
        return Vocabulary(self.medications | set(medications), self.conditions | set(conditions),
                          self.allergens | set(allergens), self.body_parts | set(body_parts),
                          {**self.aliases, **(aliases or {})})

    @classmethod
    def from_json(cls, path, base: "Vocabulary | None" = None) -> "Vocabulary":
        import json
        from pathlib import Path

        d = json.loads(Path(path).read_text())
        unknown = set(d) - {"medications", "conditions", "allergens", "body_parts", "aliases"}
        if unknown:
            raise ValueError(f"unknown vocabulary keys: {sorted(unknown)}")
        base = base or default_vocabulary()
        return base.extended(d.get("medications", ()), d.get("conditions", ()), d.get("allergens", ()),
                             d.get("body_parts", ()), d.get("aliases"))


_DEFAULT_VOCAB = None


def default_vocabulary() -> Vocabulary:
    global _DEFAULT_VOCAB
    if _DEFAULT_VOCAB is None:
        _DEFAULT_VOCAB = Vocabulary(L.MEDICATIONS, L.CONDITIONS, L.ALLERGENS, L.BODY_PARTS, L.BRAND_NAMES)
    return _DEFAULT_VOCAB

_VITALS = {
    "blood pressure": re.compile(r"\b(?:BP|blood pressure)\s*(?:of|:|was|is)?\s*(\d{2,3})\s*/\s*(\d{2,3})", re.I),
    "heart rate": re.compile(r"\b(?:HR|heart rate|pulse)\s*(?:of|:|was|is)?\s*(\d{2,3})\b", re.I),
    "respiratory rate": re.compile(r"\b(?:RR|resp(?:iratory)? rate)\s*(?:of|:|was|is)?\s*(\d{1,2})\b", re.I),
    "temperature": re.compile(r"\b(?:T|temp|temperature|Tmax)\s*(?:of|:|was|is)?\s*(\d{2,3}(?:\.\d)?)\s*°?\s*([CF])?\b",
                              re.I),
    "oxygen saturation": re.compile(r"\b(?:SpO2|O2 sat(?:uration)?|oxygen saturation|sats?)\s*(?:of|:|was|is)?\s*"
                                    r"(\d{2,3})\s*%", re.I),
    "weight": re.compile(r"\b(?:weight|wt)\s*(?:of|:|was|is)?\s*" + _NUM + r"\s*(kg|lb|lbs)\b", re.I),
}


def _norm_dose(num: str, unit: str) -> tuple[float, str]:
    v, u = float(num), unit.lower().rstrip("s")
    u = {"tab": "tablet", "capsule": "capsule", "ml": "ml"}.get(u, u)
    if u == "g":
        return v * 1000, "mg"
    if u == "mcg":
        return v / 1000, "mg"
    return v, u


def _overlaps(span, taken) -> bool:
    return any(span[0] < b and a < span[1] for a, b in taken)


def _allergies(text: str):
    facts, spans = [], []
    if re.search(r"\b(?:NKDA|NKA|no known (?:drug )?allergies)\b", text, re.I):
        m = re.search(r"\b(?:NKDA|NKA|no known (?:drug )?allergies)\b", text, re.I)
        facts.append(Fact("allergy", "__none__", {"status": "no known allergies"}, m.span(), m.group(0)))
        spans.append(m.span())
    patterns = [re.compile(r"\ballerg(?:ies|y)\s*:\s*([^\n.]+)", re.I),
                re.compile(r"\ballergic to\s+([^\n.;]+)", re.I)]
    for pat in patterns:
        for m in pat.finditer(text):
            body = m.group(1)
            if re.match(r"\s*(?:NKDA|none|no known)", body, re.I):
                continue
            spans.append(m.span())
            offset = m.start(1)
            for part in re.finditer(r"[^,]+", re.sub(r"\band\b", ",", body)):
                raw = part.group(0)
                reaction = re.search(r"\(([^)]*)\)", raw)
                name = re.sub(r"\([^)]*\)", "", raw).strip(" -:").lower()
                name = re.sub(r"\s*-\s*\w+$", "", name).strip()
                if not name or len(name) > 40:
                    continue
                s = offset + part.start()
                facts.append(Fact("allergy", name, {"reaction": reaction.group(1).strip() if reaction else None},
                                  (s, s + len(raw)), raw.strip()))
    return facts, spans


def _medications(text: str, blocked, vocab: "Vocabulary"):
    facts, seen_spans = [], []
    candidates = [(vocab.canonical(m.group(1)), m.span()) for m in vocab.med_re.finditer(text)]
    # unknown drugs written as "<word> <dose>" (e.g. "Zyrtec 10 mg")
    for m in re.finditer(r"\b([A-Za-z][A-Za-z-]{3,})\s+" + _DOSE.pattern, text, re.I):
        name = m.group(1).lower()
        if name in vocab.medications or name in L.LAB_NAMES or name in {"dose", "given", "take", "daily", "total"}:
            continue
        candidates.append((name, (m.start(1), m.end(1))))
    for name, span in sorted(candidates, key=lambda c: c[1]):
        if _overlaps(span, blocked) or _overlaps(span, seen_spans):
            continue
        # "the amoxicillin allergy", "allergic to penicillin": an allergen, not an order
        if re.search(r"allerg(?:ic|y|ies)\s+to\s*$", text[max(0, span[0] - 20):span[0]], re.I) or \
                re.match(r"\s*(?:allerg|intolerance)", text[span[1]:span[1] + 15], re.I):
            continue
        s_start, s_end = _sentence_bounds(text, span[0])
        window_end = min(s_end, span[1] + 80)
        tail = text[span[1]:window_end]
        nxt = vocab.med_re.search(tail)  # don't steal the next drug's dose
        if nxt:
            tail = tail[:nxt.start()]
        dose = _DOSE.search(tail)
        freq = None
        for norm, pat in _FREQ:
            if pat.search(tail):
                freq = norm if freq is None or norm != "as needed" else freq
        prn = bool(re.search(r"\b(?:as needed|p\.?r\.?n\.?)\b", tail, re.I))
        head = text[s_start:span[0]]
        if _STOP.search(head[-40:]) or _STOP.search(tail[:25]):
            status = "stopped"
        elif _DONE.search(head):
            status = "completed"  # given in the past, e.g. "treated with X, transitioned to Y"
        else:
            status = "active"
        val = {"dose": None, "unit": None, "frequency": freq, "prn": prn, "status": status}
        if dose:
            val["dose"], val["unit"] = _norm_dose(dose.group(1), dose.group(2))
        end = span[1] + (len(tail) if (dose or freq) else 0)
        facts.append(Fact("medication", name, val, (span[0], end), text[span[0]:end].strip()))
        seen_spans.append(span)
    return facts


def _vitals(text: str):
    facts = []
    for key, pat in _VITALS.items():
        for m in pat.finditer(text):
            if key == "blood pressure":
                val = {"value": f"{m.group(1)}/{m.group(2)}"}
            elif key == "temperature":
                t = float(m.group(1))
                unit = (m.group(2) or ("F" if t > 50 else "C")).upper()
                if not (30 <= t <= 45 or 86 <= t <= 113):
                    continue
                c = round((t - 32) * 5 / 9, 1) if unit == "F" else t
                val = {"value": c, "unit": "C"}
            elif key == "weight":
                w = float(m.group(1))
                kg = round(w * 0.4536, 1) if m.group(2).lower().startswith("lb") else w
                val = {"value": kg, "unit": "kg"}
            else:
                val = {"value": float(m.group(1))}
            facts.append(Fact("vital", key, val, m.span(), m.group(0)))
    return facts


def _labs(text: str, blocked):
    facts = []
    for raw, norm in L.LAB_NAMES.items():
        # short symbols (K, Na, Cr) are matched case-sensitively to avoid false hits
        name_pat, flags = (raw.capitalize(), 0) if len(raw) <= 2 else (raw, re.I)
        pat = re.compile(r"\b" + re.escape(name_pat) + r"\b\s*(?:of|:|was|is|=)?\s*(-?\d+(?:\.\d+)?)", flags)
        for m in pat.finditer(text):
            if _overlaps(m.span(), blocked):
                continue
            facts.append(Fact("lab", norm, {"value": float(m.group(1))}, m.span(), m.group(0)))
    return facts


def _conditions(text: str, vocab: "Vocabulary", blocked=()):
    facts = []
    for m in vocab.cond_re.finditer(text):
        if _overlaps(m.span(), blocked):
            continue  # e.g. "rash" as an allergy reaction
        s_start, s_end = _sentence_bounds(text, m.start())
        before = text[s_start:m.start()]
        # NegEx-style scope: cue within the 6 words before, not interrupted by "but"/"however"
        scope = " ".join(re.split(r"\b(?:but|however|although)\b", before, flags=re.I)[-1].split()[-6:])
        negated = bool(_PRE_NEG.search(scope)) or bool(_POST_NEG.search(text[m.end():s_end]))
        facts.append(Fact("condition", m.group(1).lower(), {"present": not negated}, m.span(), m.group(0)))
    return facts


def _laterality(text: str, vocab: "Vocabulary"):
    side_map = {"l": "left", "r": "right"}
    facts = []
    for m in vocab.lateral_re.finditer(text):
        side = side_map.get(m.group(1).lower(), m.group(1).lower())
        facts.append(Fact("laterality", m.group(2).lower(), {"side": side}, m.span(), m.group(0)))
    return facts


def extract(text: str, vocab: Vocabulary | None = None) -> list[Fact]:
    vocab = vocab or default_vocabulary()
    allergies, allergy_spans = _allergies(text)
    for a in allergies:
        if a.key != "__none__":
            a.key = vocab.canonical(a.key)
    meds = _medications(text, allergy_spans, vocab)
    vitals = _vitals(text)
    labs = _labs(text, [f.span for f in vitals])
    return allergies + meds + vitals + labs + _conditions(text, vocab, allergy_spans) + _laterality(text, vocab)
