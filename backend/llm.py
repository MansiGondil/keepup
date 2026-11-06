"""A small, provider-agnostic LLM client.

Works with any provider that offers an OpenAI-compatible API (Groq by
default). Settings come from backend/.env:
  LLM_API_KEY   your key (never printed)
  LLM_BASE_URL  the provider's API address (default: Groq)
  LLM_MODEL     the model id to use

Command line, from the backend folder:
  python llm.py --list-models     print the model ids the provider offers
  python llm.py "your text"       make one call, print the reply and token usage
"""

import argparse
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import openai

# Read the settings from backend/.env (next to this file).
load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3          # extra attempts after the first one
BASE_BACKOFF_SECONDS = 2  # wait 2 s, then 4 s, then 8 s (plus a little jitter)


def _api_key():
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        sys.exit("LLM_API_KEY is not set in backend/.env")
    return key


def _mask(text):
    """Replace the API key with *** anywhere it appears in a message."""
    key = os.environ.get("LLM_API_KEY", "").strip()
    text = str(text)
    return text.replace(key, "***") if key else text


def _client():
    """Create the client. max_retries=0: we do our own retries below."""
    return openai.OpenAI(
        api_key=_api_key(),
        base_url=os.environ.get("LLM_BASE_URL", "").strip() or DEFAULT_BASE_URL,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


def _wait_seconds(error, attempt):
    """How long to wait before retrying: the server's Retry-After if given,
    otherwise exponential backoff."""
    response = getattr(error, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        try:
            return min(float(retry_after), 60.0)  # never wait more than a minute
        except (TypeError, ValueError):
            pass
    return BASE_BACKOFF_SECONDS * 2 ** attempt + random.uniform(0, 0.5)


def _is_retryable(error):
    """Retry on rate limits (429), server errors (5xx), timeouts and dropped connections."""
    if isinstance(error, (openai.APITimeoutError, openai.APIConnectionError)):
        return True
    status = getattr(error, "status_code", None)
    return status == 429 or (status is not None and status >= 500)


def chat(messages, json_mode=False, max_tokens=300):
    """Send a list of chat messages and return (reply_text, usage).

    messages:   e.g. [{"role": "user", "content": "Hello"}]
    json_mode:  ask the model to reply with a JSON object only
    usage:      {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
    """
    model = os.environ.get("LLM_MODEL", "").strip()
    if not model:
        sys.exit("LLM_MODEL is not set in backend/.env (see: python llm.py --list-models)")

    client = _client()
    extra = {"response_format": {"type": "json_object"}} if json_mode else {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens, **extra
            )
            break
        except openai.APIError as error:
            if attempt == MAX_RETRIES or not _is_retryable(error):
                # Re-raise with the key masked, so it can't end up in a log.
                raise RuntimeError(_mask(error)) from None
            wait = _wait_seconds(error, attempt)
            print(f"LLM call failed ({type(error).__name__}), retrying in {wait:.1f}s...",
                  file=sys.stderr)
            time.sleep(wait)

    usage = response.usage
    return response.choices[0].message.content or "", {
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }


def list_models():
    """Return the sorted model ids the provider offers."""
    try:
        return sorted(model.id for model in _client().models.list())
    except openai.APIError as error:
        raise RuntimeError(_mask(error)) from None


def main():
    parser = argparse.ArgumentParser(description="Keepup LLM client")
    parser.add_argument("text", nargs="?", help="a message to send to the model")
    parser.add_argument("--list-models", action="store_true",
                        help="print the model ids the provider offers")
    args = parser.parse_args()

    if args.list_models:
        for model_id in list_models():
            print(model_id)
    elif args.text:
        reply, usage = chat([{"role": "user", "content": args.text}])
        print(reply)
        print(f"\ntokens: prompt={usage['prompt_tokens']}, "
              f"completion={usage['completion_tokens']}, total={usage['total_tokens']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
