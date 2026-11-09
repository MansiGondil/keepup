"""Step 7a: one small, swappable wrapper around a free LLM API.

The rest of Keepup only calls generate(prompt). Which provider answers is
chosen by LLM_PROVIDER in backend/.env:
  gemini  Google Gemini API free tier (needs GEMINI_API_KEY)
  groq    Groq API free tier (needs GROQ_API_KEY)
  fake    no network; returns a fixed reply, for tests and offline work
Adding another provider later = one more function + one line in PROVIDERS.

Run from the backend folder:
  python llm.py          # send one short test prompt
  python llm.py models   # list the models your key can use
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
# "-latest" is Google's alias for the current Flash-Lite model, so the
# default doesn't go stale. Set GEMINI_MODEL in .env to pin a version.
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"
GROQ_URL = "https://api.groq.com/openai/v1"
# Groq retires models often; check with: python llm.py models
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
TIMEOUT_SECONDS = 60


class LLMError(Exception):
    """The LLM call failed. rate_limited is True for HTTP 429 (quota used up)."""

    def __init__(self, message, rate_limited=False):
        super().__init__(message)
        self.rate_limited = rate_limited


def _api_key(variable):
    key = os.environ.get(variable)
    if not key:
        raise LLMError(f"{variable} is not set in backend/.env")
    return key


def _gemini_headers():
    # The key goes in a header, never in the URL, so it can't end up in
    # error messages or logs that print the URL.
    return {"x-goog-api-key": _api_key("GEMINI_API_KEY")}


def _groq_headers():
    return {"Authorization": f"Bearer {_api_key('GROQ_API_KEY')}"}


def _raise_for_status(name, response):
    """Turn an HTTP error into an LLMError with the provider's reason."""
    if response.status_code == 200:
        return
    try:
        reason = response.json()["error"]["message"]
    except Exception:
        reason = response.text[:200]
    raise LLMError(f"{name}: HTTP {response.status_code}: {reason}",
                   rate_limited=response.status_code == 429)


def _gemini_generate(prompt, max_output_tokens, temperature):
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_output_tokens,
                             "temperature": temperature},
    }
    try:
        response = httpx.post(f"{GEMINI_URL}/models/{model}:generateContent",
                              headers=_gemini_headers(), json=body,
                              timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise LLMError(f"gemini: network error: {type(error).__name__}") from None

    _raise_for_status("gemini", response)

    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        block = data.get("promptFeedback", {}).get("blockReason", "no answer")
        raise LLMError(f"gemini: empty response ({block})")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        reason = candidates[0].get("finishReason", "unknown")
        raise LLMError(f"gemini: no text in response (finishReason={reason})")
    return text


def _groq_generate(prompt, max_output_tokens, temperature):
    # Groq uses the same request format as OpenAI's chat completions.
    model = os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_output_tokens,
        "temperature": temperature,
    }
    if model.startswith("openai/gpt-oss"):
        # These models "think" before answering; keep that short so the
        # token budget goes to the answer.
        body["reasoning_effort"] = "low"
    try:
        response = httpx.post(f"{GROQ_URL}/chat/completions", headers=_groq_headers(),
                              json=body, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise LLMError(f"groq: network error: {type(error).__name__}") from None
    _raise_for_status("groq", response)

    choices = response.json().get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    if not text:
        reason = choices[0].get("finish_reason", "unknown") if choices else "no choices"
        raise LLMError(f"groq: no text in response (finish_reason={reason})")
    return text


def _fake_generate(prompt, max_output_tokens, temperature):
    return ("This is a fake summary from the offline test provider. "
            "It ignores the prompt and always returns the same text.")


PROVIDERS = {
    "gemini": _gemini_generate,
    "groq": _groq_generate,
    "fake": _fake_generate,
}


def provider_name():
    return os.environ.get("LLM_PROVIDER", "gemini").strip().lower()


def generate(prompt, max_output_tokens=400, temperature=0.2):
    """Send one prompt, return the reply text. Raises LLMError on failure."""
    name = provider_name()
    if name not in PROVIDERS:
        raise LLMError(f"unknown LLM_PROVIDER '{name}'; use one of: {', '.join(PROVIDERS)}")
    return PROVIDERS[name](prompt, max_output_tokens, temperature)


def list_models():
    """Names of the models the current provider's key can use."""
    name = provider_name()
    if name == "gemini":
        response = httpx.get(f"{GEMINI_URL}/models", headers=_gemini_headers(),
                             params={"pageSize": 1000}, timeout=TIMEOUT_SECONDS)
        _raise_for_status(name, response)
        return [m["name"].removeprefix("models/") for m in response.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]
    if name == "groq":
        response = httpx.get(f"{GROQ_URL}/models", headers=_groq_headers(),
                             timeout=TIMEOUT_SECONDS)
        _raise_for_status(name, response)
        return sorted(m["id"] for m in response.json().get("data", []) if m.get("active", True))
    raise LLMError(f"provider '{name}' has no model list")


def main():
    try:
        if sys.argv[1:] == ["models"]:
            for name in list_models():
                print(name)
            return
        print(f"provider: {provider_name()}")
        print(generate("In one short sentence, what is a news briefing?"))
    except (LLMError, httpx.HTTPError) as error:
        print(f"LLM call failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
