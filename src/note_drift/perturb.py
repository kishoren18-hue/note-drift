"""Inject known errors into faithful summaries to measure what note-drift catches.

Each perturbation returns the corrupted text (or None if it doesn't apply) and
the fact kind a detector should flag. This gives a reproducible, synthetic
benchmark: it measures recall on error types we can inject, not real-world
accuracy on AI-written summaries.
"""

from __future__ import annotations

import re
from typing import Callable

from .lexicon import NEGATION_CUES

_FREQ_SWAP = {"twice daily": "once daily", "once daily": "twice daily", "every 4 hours": "every 12 hours",
              "at bedtime": "twice daily", "three times daily": "once daily"}


def dose_change(t: str):
    m = re.search(r"(\d+(?:\.\d+)?)(\s*(?:mg|mcg|puffs?))\b", t)
    if not m:
        return None
    v = float(m.group(1))
    new = f"{v * 10:g}"
    return t[:m.start(1)] + new + t[m.end(1):]


def frequency_change(t: str):
    for a, b in _FREQ_SWAP.items():
        m = re.search(r"\d+\s*(?:mg|puffs?)\s+" + re.escape(a), t)
        if m:
            i = m.end() - len(a)
            return t[:i] + b + t[m.end():]
    return None


def laterality_flip(t: str):
    m = re.search(r"\b(left|right)\b", t)
    if not m:
        return None
    return t[:m.start()] + ("right" if m.group(1) == "left" else "left") + t[m.end():]


def negation_flip(t: str):
    cues = sorted(NEGATION_CUES, key=len, reverse=True)
    m = re.search(r"(?:;\s*|\.\s*|^)(" + "|".join(map(re.escape, cues)) + r")\s+", t, re.I)
    if m and m.group(1).lower() in {"no", "denies", "without", "negative for"}:
        repl = "reports " if m.group(1).lower() == "denies" else "with "
        return t[:m.start(1)] + repl + t[m.end():]
    m = re.search(r"([,;]\s*)(no|denies)\s+", t, re.I)
    if m:
        return t[:m.start(2)] + ("reports " if m.group(2).lower() == "denies" else "with ") + t[m.end():]
    return None


def allergy_drop(t: str):
    m = re.search(r"(?:Allergies:[^.]*\.|Allergic to[^.]*\.)\s*", t, re.I)
    if not m:
        return None
    return t[:m.start()] + t[m.end():]


def med_invent(t: str):
    return t.rstrip() + " Started warfarin 5 mg daily."


PERTURBATIONS: dict[str, tuple[Callable[[str], str | None], str]] = {
    "dose_change": (dose_change, "medication"),
    "frequency_change": (frequency_change, "medication"),
    "laterality_flip": (laterality_flip, "laterality"),
    "negation_flip": (negation_flip, "condition"),
    "allergy_drop": (allergy_drop, "allergy"),
    "med_invent": (med_invent, "medication"),
}
