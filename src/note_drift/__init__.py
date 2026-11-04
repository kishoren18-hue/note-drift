"""note-drift: catch facts that change between a clinical note and its summary."""

from .compare import DriftReport, Finding, check, compare_facts
from .extract import Fact, extract

__version__ = "0.1.0"
__all__ = ["DriftReport", "Finding", "check", "compare_facts", "Fact", "extract"]
