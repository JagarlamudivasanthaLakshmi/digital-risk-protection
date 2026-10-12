import json
import logging

from .groq_service import GroqServiceError, create_chat_completion
from .prompt_templates import threat_analysis_messages


logger = logging.getLogger(__name__)


def analyze_threat(evidence):
    """Return a validated AI summary and recommendation for detected evidence."""
    content = create_chat_completion(threat_analysis_messages(evidence))
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("AI threat analysis returned invalid JSON.")
        raise GroqServiceError("AI analysis returned an invalid response.") from exc

    if not isinstance(result, dict):
        logger.warning("AI threat analysis response was not an object.")
        raise GroqServiceError("AI analysis returned an unexpected response.")

    summary = result.get("summary")
    recommendation = result.get("recommendation")
    if (
        not isinstance(summary, str)
        or not summary.strip()
        or not isinstance(recommendation, str)
        or not recommendation.strip()
    ):
        logger.warning("AI threat analysis response is missing required text.")
        raise GroqServiceError(
            "AI analysis did not include a valid summary and recommendation."
        )

    return {
        "summary": summary.strip()[:2000],
        "recommendation": recommendation.strip()[:1000],
    }
