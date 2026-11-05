"""Backend tests. Run from web/:  python -m pytest api -q

External services (Supabase, Anthropic) are replaced with fakes, so the tests
run offline and never spend API credit.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("nd_api", Path(__file__).with_name("index.py"))
api = importlib.util.module_from_spec(spec)
sys.modules["nd_api"] = api
spec.loader.exec_module(api)
client = TestClient(api.app)

NOTE = (
    "Allergies: penicillin (hives)\nPlan: start cefdinir 300 mg twice daily for 10 days. "
    "Right tympanic membrane bulging. Denies chest pain."
)


def test_health_reports_configuration(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.get("/api/py/health")
    assert r.status_code == 200 and r.json()["ai"] is False and r.json()["model"] is None


def test_provider_prefers_gemini_unless_forced(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert client.get("/api/py/health").json()["provider"] == "gemini"
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    assert client.get("/api/py/health").json()["model"] == api.CLAUDE_MODEL


def test_check_finds_errors():
    bad = "Allergies: none known. Start cefdinir 300 mg once daily. Left tympanic membrane bulging. Has chest pain."
    r = client.post("/api/py/check", json={"note": NOTE, "summary": bad})
    assert r.status_code == 200
    body = r.json()
    assert body["worst"] == "high"
    details = " | ".join(f["detail"] for f in body["findings"])
    assert "frequency twice daily -> once daily" in details
    assert "right in note -> left" in details
    assert body["identifiers"] == []


def test_check_validates_input():
    assert client.post("/api/py/check", json={"note": "", "summary": "x"}).status_code == 422
    assert client.post("/api/py/check", json={"note": "x" * 20_001, "summary": "x"}).status_code == 422


@pytest.mark.parametrize("text,label", [
    ("Patient SSN 123-45-6789", "Social Security"),
    ("Call (470) 555-0199 with results", "phone"),
    ("MRN: 00482913", "medical record"),
    ("DOB: 04/12/1961", "date of birth"),
    ("lives at 42 Maple Street", "street address"),
])
def test_identifier_screen(text, label):
    assert any(label in x for x in api.find_identifiers(text))


def test_identifier_screen_ignores_clinical_numbers():
    assert api.find_identifiers("BP 158/94, HR 104, troponin 0.02, metformin 1000 mg twice daily") == []


def test_summarize_requires_sign_in(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    r = client.post("/api/py/summarize", json={"note": NOTE})
    assert r.status_code == 401


def test_summarize_blocks_identifiers_before_any_network_call(monkeypatch):
    called = []
    monkeypatch.setattr(api, "take_quota", lambda *a: called.append(1))
    r = client.post("/api/py/summarize", json={"note": NOTE + " MRN: 99887766"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 422 and "medical record number" in r.json()["detail"]
    assert not called


class FakeResp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p


def _fake_supabase(monkeypatch, status=200, payload=True):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers, json):
            assert url.endswith("/rest/v1/rpc/nd_take_quota")
            assert headers["Authorization"] == "Bearer good"
            return FakeResp(status, payload)

    monkeypatch.setattr(api.httpx, "AsyncClient", FakeClient)


def _fake_claude(monkeypatch, text):
    import anthropic

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    class Msgs:
        def create(self, **kw):
            assert kw["model"] == api.CLAUDE_MODEL
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(messages=Msgs()))


def test_summarize_faithful(monkeypatch):
    _fake_supabase(monkeypatch)
    _fake_claude(monkeypatch, "Child with right otitis media on cefdinir 300 mg twice daily. Allergic to penicillin.")
    r = client.post("/api/py/summarize", json={"note": NOTE}, headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    assert r.json()["summary"].startswith("Child with right otitis") and r.json()["injected"] == []


def test_summarize_challenge_parses_json(monkeypatch):
    _fake_supabase(monkeypatch)
    payload = {"summary": "On cefdinir 300 mg once daily.", "errors": ["frequency changed", "allergy dropped"]}
    _fake_claude(monkeypatch, "Here you go:\n" + json.dumps(payload))
    r = client.post("/api/py/summarize", json={"note": NOTE, "mode": "challenge"},
                    headers={"Authorization": "Bearer good"})
    assert r.status_code == 200 and r.json()["injected"] == payload["errors"]


def test_summarize_quota_exhausted(monkeypatch):
    _fake_supabase(monkeypatch, payload=False)
    _fake_claude(monkeypatch, "unused")
    r = client.post("/api/py/summarize", json={"note": NOTE}, headers={"Authorization": "Bearer good"})
    assert r.status_code == 429


def test_summarize_expired_session(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    _fake_supabase(monkeypatch, status=401, payload={"message": "JWT expired"})
    r = client.post("/api/py/summarize", json={"note": NOTE}, headers={"Authorization": "Bearer good"})
    assert r.status_code == 401


def _fake_gemini(monkeypatch, text, status=200):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    seen = {}

    def post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        parts = [{"text": "planning", "thought": True}, {"text": text}]
        return FakeResp(status, {"candidates": [{"content": {"parts": parts}}]})

    monkeypatch.setattr(api.httpx, "post", post)
    return seen


def test_summarize_with_gemini_challenge(monkeypatch):
    _fake_supabase(monkeypatch)
    payload = {"summary": "On cefdinir 300 mg once daily.", "errors": ["frequency changed", "allergy dropped"]}
    seen = _fake_gemini(monkeypatch, json.dumps(payload))
    r = client.post("/api/py/summarize", json={"note": NOTE, "mode": "challenge"},
                    headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    assert r.json()["injected"] == payload["errors"] and r.json()["model"] == api.GEMINI_MODEL
    assert seen["headers"]["x-goog-api-key"] == "g"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_gemini_rate_limit_is_friendly(monkeypatch):
    _fake_supabase(monkeypatch)
    _fake_gemini(monkeypatch, "", status=429)
    r = client.post("/api/py/summarize", json={"note": NOTE}, headers={"Authorization": "Bearer good"})
    assert r.status_code == 429 and "busy" in r.json()["detail"]
