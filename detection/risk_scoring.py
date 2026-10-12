from .allowlist import is_allowlisted
from .logo_similarity import remote_app_logo_similarity
from .name_similarity import name_similarity
from .publisher_validator import validate_publisher
from .text_analyzer import analyze_text
from .url_analyzer import analyze_url
from monitoring.collectors.providers import official_app_matches, official_url_matches
from monitoring.models import SOCIAL_SOURCE_VALUES


def score_item(item, brand):
    if item.source in SOCIAL_SOURCE_VALUES and item.url and official_url_matches(
        item.url, brand.official_social_accounts
    ):
        return {
            "risk_score": 0,
            "severity": "low",
            "signals": [],
            "explanation": "Official social account is allowlisted.",
        }
    candidate = {
        "external_id": item.external_id,
        "url": item.url,
        "metadata": item.metadata,
    }
    if item.source in ("app_store", "google_play") and official_app_matches(
        candidate, brand.official_apps
    ):
        return {
            "risk_score": 0,
            "severity": "low",
            "signals": [],
            "explanation": "Official mobile application is allowlisted.",
        }
    if item.url and is_allowlisted(item.url, brand.official_domains):
        return {"risk_score": 0, "severity": "low", "signals": [], "explanation": "URL is allowlisted."}

    signals = analyze_text(
        f"{item.name} {item.content}",
        official_description=brand.description,
    )
    similarity = name_similarity(item.name, brand.name)
    if 0.70 <= similarity < 0.995:
        signals.append({"signal": "similar_brand_name", "similarity": round(similarity, 2), "weight": 25})
    signals.extend(analyze_url(item.url, brand.official_domains) if item.url else [])
    if item.source in ("app_store", "google_play"):
        signals.extend(validate_publisher(item.publisher, brand.official_publishers))
        if brand.logo and item.metadata.get("artwork"):
            similarity = remote_app_logo_similarity(
                item.metadata["artwork"], brand.logo
            )
            if similarity is not None and similarity >= 0.82:
                signals.append({
                    "signal": "similar_app_logo",
                    "similarity": round(similarity, 2),
                    "weight": 30,
                })
    score = min(100, sum(signal["weight"] for signal in signals))
    severity = "critical" if score >= 80 else "high" if score >= 55 else "medium" if score >= 30 else "low"
    explanation = (
        "Risk signals: " + ", ".join(signal["signal"].replace("_", " ") for signal in signals)
        if signals
        else "No configured risk signals were detected."
    )
    return {"risk_score": score, "severity": severity, "signals": signals, "explanation": explanation}
