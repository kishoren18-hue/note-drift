"""note-drift API (FastAPI, deployed as a Vercel Python function).

Routes
  GET  /api/py/health      liveness + which integrations are configured
  POST /api/py/check       compare a note with a summary (public, no data stored)
  POST /api/py/summarize   have Claude write a summary of a note (signed-in users, daily quota)

Nothing here stores note text. Saving a report is done by the browser straight
into Supabase, protected by row-level security.
"""

import json
import os
import re
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from note_drift import check as drift_check
from pydantic import BaseModel, Field

MAX_CHARS = 20_000
DAILY_AI_LIMIT = 20
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")

app = FastAPI(
    title="note-drift API",
    version="0.2.0",
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------- identifier screen ----------

PHI_PATTERNS = {
    "a Social Security number": r"\b\d{3}-\d{2}-\d{4}\b",
    "a phone number": r"(?<!\d)(?:\(\d{3}\)\s?|\d{3}[-.\s])\d{3}[-.\s]\d{4}(?!\d)",
    "an email address": r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    "a medical record number": r"\b(?:MRN|medical record(?: number| no\.?)?)\s*[:#]?\s*[A-Z0-9-]{4,}\b",
    "a date of birth": r"\b(?:DOB|date of birth|born)\s*[:]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "a street address": r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b",
}


def find_identifiers(*texts: str) -> list[str]:
    found = []
    for label, pattern in PHI_PATTERNS.items():
        if any(re.search(pattern, t, re.I if label != "a street address" else 0) for t in texts):
            found.append(label)
    return found


# ---------- models ----------


class CheckIn(BaseModel):
    note: str = Field(min_length=1, max_length=MAX_CHARS)
    summary: str = Field(min_length=1, max_length=MAX_CHARS)


class SummarizeIn(BaseModel):
    note: str = Field(min_length=20, max_length=MAX_CHARS)
    mode: Literal["faithful", "challenge"] = "faithful"


def _report_json(rep) -> dict:
    d = rep.as_dict()
    d["n_note_facts"] = len(rep.note_facts)
    d["n_summary_facts"] = len(rep.summary_facts)
    return d


# ---------- routes ----------


@app.get("/api/py/health")
def health():
    return {
        "ok": True,
        "ai": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "accounts": bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY")),
        "model": CLAUDE_MODEL,
    }


@app.post("/api/py/check")
def check(body: CheckIn):
    rep = drift_check(body.note, body.summary)
    out = _report_json(rep)
    out["identifiers"] = find_identifiers(body.note, body.summary)
    return out


async def take_quota(authorization: str | None) -> None:
    """Verify the Supabase session and count this request against the daily limit."""
    url, anon = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
    if not (url and anon):
        raise HTTPException(503, "Accounts aren't configured on this deployment.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to use AI summaries.")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{url}/rest/v1/rpc/nd_take_quota",
            headers={"apikey": anon, "Authorization": authorization, "Content-Type": "application/json"},
            json={},
        )
    if r.status_code in (401, 403):
        raise HTTPException(401, "Your session has expired. Sign in again.")
    if r.status_code != 200:
        raise HTTPException(502, "Couldn't check your usage limit. Try again shortly.")
    if r.json() is not True:
        raise HTTPException(429, f"Daily limit reached ({DAILY_AI_LIMIT} AI summaries per day). Try again tomorrow.")


FAITHFUL_PROMPT = """You are a careful clinical documentation assistant. Write a concise handoff summary (4-7 sentences) of the clinical note below for the next clinician. Keep every allergy, every active medication with dose and frequency, key vitals and labs, laterality, and the assessment and plan. Do not add anything that is not in the note.

Return only the summary text.

<note>
{note}
</note>"""

CHALLENGE_PROMPT = """This is a test of an automated error detector for clinical summaries. The note is synthetic.

Write a concise handoff summary (4-7 sentences) of the note below, but deliberately introduce exactly two subtle factual errors of different kinds chosen from: a changed medication dose, a changed medication frequency, a left/right swap, a negated finding stated as present (or the reverse), a dropped allergy, or a medication that is not in the note. The errors should read naturally, as if the summarizer made a mistake.

Respond with JSON only, in this exact shape:
{{"summary": "...", "errors": ["one short sentence describing error 1", "one short sentence describing error 2"]}}

<note>
{note}
</note>"""


def _claude(prompt: str, max_tokens: int = 700) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(503, "AI summaries aren't configured on this deployment yet.")
    import anthropic  # imported lazily so /check stays fast

    client = anthropic.Anthropic(api_key=key, timeout=45, max_retries=2)
    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=max_tokens, temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError:
        raise HTTPException(429, "The AI service is busy. Try again in a minute.") from None
    except anthropic.APIError as e:
        raise HTTPException(502, f"The AI service returned an error ({type(e).__name__}).") from None
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _parse_challenge(text: str) -> tuple[str, list[str]]:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0) if m else text)
        summary, errors = str(data["summary"]).strip(), [str(e) for e in data.get("errors", [])][:3]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(502, "The AI response wasn't in the expected format. Try again.") from None
    if not summary:
        raise HTTPException(502, "The AI returned an empty summary. Try again.")
    return summary, errors


@app.post("/api/py/summarize")
async def summarize(body: SummarizeIn, authorization: str | None = Header(default=None)):
    ids = find_identifiers(body.note)
    if ids:
        raise HTTPException(
            422,
            f"This note seems to contain {', '.join(ids)}. Only synthetic notes can be sent to the AI. "
            "Remove identifiers or use a sample note.",
        )
    await take_quota(authorization)
    if body.mode == "faithful":
        return {"summary": _claude(FAITHFUL_PROMPT.format(note=body.note)), "injected": [], "model": CLAUDE_MODEL}
    summary, errors = _parse_challenge(_claude(CHALLENGE_PROMPT.format(note=body.note)))
    return {"summary": summary, "injected": errors, "model": CLAUDE_MODEL}
