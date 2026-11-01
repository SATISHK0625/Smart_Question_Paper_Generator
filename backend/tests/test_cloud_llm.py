import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.cloud_llm import (
    get_llm_config,
    get_llm_status,
    call_cloud_llm,
    ai_classify_document_header,
    ai_parse_ambiguous_questions
)

def test_llm_status_deterministic_when_no_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    status = get_llm_status()
    assert status["status"] == "deterministic_only"
    assert "No LLM_API_KEY configured" in status["message"]

def test_llm_status_ready_when_api_key_configured(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "dummy-secret-key-12345")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("LLM_ENABLED", "true")

    status = get_llm_status()
    assert status["status"] == "ready"
    assert status["provider"] == "gemini"
    assert status["model"] == "gemini-1.5-flash"

def test_gemini_call_success_mock(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
    monkeypatch.setenv("LLM_ENABLED", "true")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"institution_name": "Test Academy", "document_type": "worksheet"}'
                        }
                    ]
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        res = ai_classify_document_header(["Test Academy", "Class 5", "WORKSHEET"])
        assert res is not None
        assert res["institution_name"] == "Test Academy"
        assert res["document_type"] == "worksheet"

def test_llm_graceful_fallback_on_network_failure(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    with patch("requests.post", side_effect=Exception("Connection refused")):
        res = call_cloud_llm("Analyze this text")
        assert res is None, "Must gracefully return None without raising exception"

def test_ai_parse_ambiguous_questions_mock(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("LLM_ENABLED", "true")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"sections": [{"title": "SECTION 1", "questions": [{"number": "1", "text": "What is AI?", "marks": 5}]}]}'
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        parsed = ai_parse_ambiguous_questions("Irregular text: 1) What is AI? 5 marks")
        assert parsed is not None
        assert len(parsed["sections"]) == 1
        assert parsed["sections"][0]["questions"][0]["text"] == "What is AI?"
