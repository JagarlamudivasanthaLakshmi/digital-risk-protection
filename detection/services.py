from alerts.services import get_or_create_alert_for_finding
from brands.services import normalize_domains
from monitoring.collectors.providers import official_url_matches
from services.ai_analyzer import analyze_threat
from services.groq_service import GroqServiceError, is_groq_configured

from .models import RiskFinding
from .risk_scoring import score_item


def _ai_analysis(item, score):
    if score["explanation"].startswith(("Official ", "URL is allowlisted.")):
        return {
            "ai_status": RiskFinding.AIStatus.SKIPPED,
            "ai_summary": "",
            "ai_recommendation": "",
            "ai_error": "AI analysis skipped because this is an allowlisted brand asset.",
        }
    if not is_groq_configured():
        return {
            "ai_status": RiskFinding.AIStatus.NOT_CONFIGURED,
            "ai_summary": "",
            "ai_recommendation": "",
            "ai_error": "Configure GROQ_API_KEY to enable AI analysis.",
        }
    try:
        result = analyze_threat({
            "brand": item.brand.name,
            "official_domains": normalize_domains(item.brand.official_domains),
            "official_publishers": item.brand.official_publishers,
            "observed_item": {
                "name": item.name[:500],
                "source": item.source,
                "url": item.url[:1000],
                "publisher": item.publisher[:300],
                "content": item.content[:4000],
            },
            "deterministic_risk_score": score["risk_score"],
            "deterministic_severity": score["severity"],
            "detected_signals": score["signals"],
        })
    except GroqServiceError as exc:
        return {
            "ai_status": RiskFinding.AIStatus.FAILED,
            "ai_summary": "",
            "ai_recommendation": "",
            "ai_error": str(exc),
        }
    return {
        "ai_status": RiskFinding.AIStatus.COMPLETED,
        "ai_summary": result["summary"],
        "ai_recommendation": result["recommendation"],
        "ai_error": "",
    }


def record_finding(item, *, score=None, analyze_ai=True, existing=None):
    """Persist rule-based risk and optional AI explanation; create a threshold alert."""
    score = score or score_item(item, item.brand)
    ai_fields = _ai_analysis(item, score) if analyze_ai else {
        "ai_status": RiskFinding.AIStatus.NOT_CONFIGURED,
        "ai_summary": "",
        "ai_recommendation": "",
        "ai_error": "",
    }
    if existing is None:
        existing = RiskFinding.objects.filter(
            brand=item.brand, monitored_item=item
        ).order_by("-created_at").first()
    if existing:
        for field, value in {**score, **ai_fields}.items():
            setattr(existing, field, value)
        existing.save()
        finding = existing
    else:
        finding = RiskFinding.objects.create(
            brand=item.brand,
            monitored_item=item,
            **score,
            **ai_fields,
        )
    alert_created = False
    if finding.risk_score >= 30:
        _, alert_created = get_or_create_alert_for_finding(finding)
    return finding, alert_created
