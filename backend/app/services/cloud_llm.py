import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

try:
    import requests
except ImportError:
    requests = None

import urllib.request
import urllib.error

# Load environment variables from backend/.env if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger("cloud_llm")

# Provider configurations
DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022"
}

REQUEST_TIMEOUT_SECONDS = 15

def get_llm_config() -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    model = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS.get(provider, "gemini-1.5-flash")
    api_key = os.getenv("LLM_API_KEY", "").strip()
    enabled_str = os.getenv("LLM_ENABLED", "true").strip().lower()
    is_enabled = enabled_str in ("true", "1", "yes") and bool(api_key)

    return {
        "provider": provider,
        "model": model,
        "has_api_key": bool(api_key),
        "api_key": api_key,
        "is_enabled": is_enabled
    }

def get_llm_status() -> Dict[str, Any]:
    cfg = get_llm_config()
    if not cfg["has_api_key"]:
        return {
            "status": "deterministic_only",
            "provider": cfg["provider"],
            "model": cfg["model"],
            "message": "No LLM_API_KEY configured. Running in fully local deterministic mode (zero cloud cost, zero data leaves machine)."
        }
    if not cfg["is_enabled"]:
        return {
            "status": "disabled",
            "provider": cfg["provider"],
            "model": cfg["model"],
            "message": "LLM is disabled via LLM_ENABLED environment variable."
        }
    return {
        "status": "ready",
        "provider": cfg["provider"],
        "model": cfg["model"],
        "message": f"Cloud LLM ready ({cfg['provider'].capitalize()}: {cfg['model']}) for document understanding & ambiguous layout classification."
    }

def call_cloud_llm(prompt: str, system_instruction: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Executes a provider-agnostic request to the configured cloud LLM.
    Enforces:
    - Structured JSON response
    - 15s timeout
    - No raw binary data sent
    - Rate limit, network error, and schema error recovery
    - Zero API key logging
    """
    cfg = get_llm_config()
    if not cfg["is_enabled"] or not cfg["api_key"]:
        return None

    provider = cfg["provider"]
    model = cfg["model"]
    api_key = cfg["api_key"]

    try:
        if provider == "gemini":
            return _call_gemini(model, api_key, prompt, system_instruction)
        elif provider == "openai":
            return _call_openai(model, api_key, prompt, system_instruction)
        elif provider == "anthropic":
            return _call_anthropic(model, api_key, prompt, system_instruction)
        else:
            logger.warning(f"Unsupported LLM provider: {provider}")
            return None
    except Exception as e:
        logger.warning(f"Cloud LLM request to {provider} failed: {type(e).__name__} ({str(e)})")
        return None

def _http_post(url: str, json_data: Dict[str, Any], headers: Dict[str, str]) -> Tuple[int, Optional[Dict[str, Any]]]:
    """
    Executes HTTP POST using `requests` if available, falling back to standard library `urllib`.
    """
    if requests is not None:
        resp = requests.post(url, json=json_data, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, None
    else:
        req = urllib.request.Request(
            url,
            data=json.dumps(json_data).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body)
        except urllib.error.HTTPError as he:
            try:
                body = he.read().decode("utf-8")
                return he.code, json.loads(body)
            except Exception:
                return he.code, None

def _call_gemini(model: str, api_key: str, prompt: str, system_instruction: Optional[str]) -> Optional[Dict[str, Any]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    headers = {"Content-Type": "application/json"}
    status_code, data = _http_post(url, payload, headers)
    if status_code != 200 or not data:
        logger.warning(f"Gemini API returned status {status_code}")
        return None

    candidates = data.get("candidates", [])
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return None
    raw_text = parts[0].get("text", "").strip()
    return _parse_json_safely(raw_text)

def _call_openai(model: str, api_key: str, prompt: str, system_instruction: Optional[str]) -> Optional[Dict[str, Any]]:
    url = "https://api.openai.com/v1/chat/completions"
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    status_code, data = _http_post(url, payload, headers)
    if status_code != 200 or not data:
        logger.warning(f"OpenAI API returned status {status_code}")
        return None

    choices = data.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "").strip()
    return _parse_json_safely(content)

def _call_anthropic(model: str, api_key: str, prompt: str, system_instruction: Optional[str]) -> Optional[Dict[str, Any]]:
    url = "https://api.anthropic.com/v1/messages"
    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": 1500,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_instruction:
        payload["system"] = system_instruction

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    status_code, data = _http_post(url, payload, headers)
    if status_code != 200 or not data:
        logger.warning(f"Anthropic API returned status {status_code}")
        return None

    content_list = data.get("content", [])
    if not content_list:
        return None
    text = content_list[0].get("text", "").strip()
    return _parse_json_safely(text)

def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    # Strip markdown code blocks if wrapped
    cleaned = text
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to decode JSON from model response")
        return None

# --- AI-Assisted Specialized Tasks (Invoked only when needed) ---

def ai_classify_document_header(header_lines: List[str]) -> Optional[Dict[str, Any]]:
    """
    Uses Cloud AI to classify ambiguous header text into structured metadata:
    - institution_name
    - exam_name
    - subject_name
    - semester_class
    - document_type ("worksheet" or "exam_paper")
    """
    if not header_lines:
        return None

    prompt = (
        "Extract structured examination metadata from the following detected document header lines.\n"
        "Return a JSON object with keys:\n"
        "  'institution_name': string or null,\n"
        "  'exam_name': string or null,\n"
        "  'subject_name': string or null,\n"
        "  'semester_class': string or null,\n"
        "  'document_type': 'worksheet' or 'exam_paper'\n\n"
        "Header lines:\n" + "\n".join(f"- {line}" for line in header_lines[:8])
    )
    system = "You are an expert document layout and academic paper analysis engine. Respond strictly with JSON."
    return call_cloud_llm(prompt, system)

def ai_parse_ambiguous_questions(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Uses Cloud AI when deterministic regex encounters high uncertainty or irregular question formatting.
    Returns structured sections, questions, and options.
    """
    if not raw_text.strip():
        return None

    # Limit text to 4000 chars to avoid large prompts
    truncated_text = raw_text[:4000]

    prompt = (
        "Parse the following academic question paper text into structured sections and questions.\n"
        "Return a JSON object with a 'sections' array where each item has:\n"
        "  'title': string (e.g. 'A. MULTIPLE CHOICE QUESTIONS'),\n"
        "  'instructions': string or null,\n"
        "  'questions': array of objects with keys:\n"
        "     'number': string,\n"
        "     'text': string,\n"
        "     'marks': number or null,\n"
        "     'options': array of strings (for MCQs, e.g. ['a) Rock', 'b) Soil'])\n\n"
        "Text to parse:\n" + truncated_text
    )
    system = "You are a test paper structuring assistant. Respond strictly with JSON."
    return call_cloud_llm(prompt, system)

def ai_map_replacement_sections(
    reference_sections: List[str],
    replacement_sections: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Uses Cloud AI to map replacement sections to existing reference template sections.
    """
    if not reference_sections or not replacement_sections:
        return None

    prompt = (
        "Map the following new replacement question paper sections to the best matching reference template sections.\n"
        "Return a JSON object with a 'mapping' dictionary where keys are new section titles and values are corresponding reference section titles or null.\n\n"
        "Reference Sections:\n" + "\n".join(f"- {s}" for s in reference_sections) + "\n\n"
        "New Sections:\n" + "\n".join(f"- {s}" for s in replacement_sections)
    )
    system = "You are an academic layout structuring assistant. Respond strictly with JSON."
    return call_cloud_llm(prompt, system)

def ai_interpret_ambiguous_ocr(detected_text_fragments: List[str]) -> Optional[Dict[str, Any]]:
    """
    Interprets fragmented or ambiguous OCR results from scanned documents.
    """
    if not detected_text_fragments:
        return None

    prompt = (
        "Clean and reconstruct structured question paper text from the following ambiguous or noisy OCR fragments.\n"
        "Return a JSON object with keys:\n"
        "  'cleaned_heading': string,\n"
        "  'extracted_questions': array of strings,\n"
        "  'notes': string\n\n"
        "OCR Fragments:\n" + "\n".join(f"- {f}" for f in detected_text_fragments[:20])
    )
    system = "You are an OCR layout restoration expert. Respond strictly with JSON."
    return call_cloud_llm(prompt, system)

