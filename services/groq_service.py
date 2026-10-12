import logging

import requests
from django.conf import settings


logger = logging.getLogger(__name__)
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqServiceError(Exception):
    """Raised when Groq cannot return a usable chat completion."""


def is_groq_configured():
    return bool(settings.GROQ_API_KEY)


def create_chat_completion(messages):
    """Call Groq and return the assistant message content."""
    if not is_groq_configured():
        raise RuntimeError("GROQ_API_KEY is not configured.")

    try:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": settings.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        logger.warning("Groq returned invalid JSON.")
        raise GroqServiceError("Groq returned an invalid response.") from exc
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning("Groq returned HTTP status %s during risk analysis.", status_code)
        raise GroqServiceError(f"Groq returned HTTP {status_code}.") from exc
    except requests.RequestException as exc:
        logger.warning("Groq request failed: %s", exc.__class__.__name__)
        raise GroqServiceError(
            "Could not connect to Groq. Check the network and try again."
        ) from exc
    except ValueError as exc:
        logger.warning("Groq returned a non-JSON response.")
        raise GroqServiceError("Groq returned an invalid response.") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Groq response did not include an assistant message.")
        raise GroqServiceError(
            "Groq returned a response in an unexpected format."
        ) from exc
    if not isinstance(content, str) or not content.strip():
        logger.warning("Groq response contained an empty assistant message.")
        raise GroqServiceError("Groq returned an empty analysis.")
    return content
