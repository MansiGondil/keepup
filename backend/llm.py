"""Step 7a: one small, swappable wrapper around a free LLM API.

The rest of Keepup only calls generate(prompt). Which provider answers is
chosen by LLM_PROVIDER in backend/.env:
  gemini  Google Gemini API free tier (needs GEMINI_API_KEY)
  fake    no network; returns a fixed reply, for tests and offline work
Adding another provider later = one more function + one line in PROVIDERS.

Run from the backend folder:
  python llm.py          # send one short test prompt
  python llm.py models   # list Gemini models your key can use
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
TIMEOUT_SECONDS = 60


class LLMError(Exception):
    """The LLM call failed. rate_limited is True for HTTP 429 (quota used up)."""

    def __init__(self, message, rate_limited=False):
        super().__init__(message)
        self.rate_limited = rate_limited


def _gemini_headers():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set in backend/.env")
    # The key goes in a header, never in the URL, so it can't end up in
    # error messages or logs that print the URL.
    return {"x-goog-api-key": key}


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

    if response.status_code != 200:
        # Google puts a readable reason in error.message.
        try:
            reason = response.json()["error"]["message"]
        except Exception:
            reason = response.text[:200]
        raise LLMError(f"gemini: HTTP {response.status_code}: {reason}",
                       rate_limited=response.status_code == 429)

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


def _fake_generate(prompt, max_output_tokens, temperature):
    return ("This is a fake summary from the offline test provider. "
            "It ignores the prompt and always returns the same text.")


PROVIDERS = {
    "gemini": _gemini_generate,
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


def list_gemini_models():
    """Names of the Gemini models this key can call with generateContent."""
    response = httpx.get(f"{GEMINI_URL}/models", headers=_gemini_headers(),
                         params={"pageSize": 1000}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return [m["name"].removeprefix("models/") for m in response.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])]


def main():
    try:
        if sys.argv[1:] == ["models"]:
            for name in list_gemini_models():
                print(name)
            return
        print(f"provider: {provider_name()}")
        print(generate("In one short sentence, what is a news briefing?"))
    except (LLMError, httpx.HTTPError) as error:
        print(f"LLM call failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
