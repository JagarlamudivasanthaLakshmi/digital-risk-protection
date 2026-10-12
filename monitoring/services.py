import logging

from django.conf import settings

from detection.models import RiskFinding
from detection.risk_scoring import score_item
from detection.services import record_finding

from .collectors.app_store_collector import collect_app_listings
from .collectors.google_play_collector import collect_google_play_listings
from .collectors.providers import (
    CollectorError,
    official_app_matches,
    official_url_matches,
)
from .collectors.social_collector import collect_social_mentions
from .models import SOCIAL_SOURCE_VALUES, MonitoredItem


logger = logging.getLogger(__name__)
AI_ANALYSIS_LIMIT = 3


def _persist_candidate(brand, candidate):
    defaults = {
        "name": candidate["name"][:255],
        "url": candidate.get("url", "")[:1000],
        "publisher": candidate.get("publisher", "")[:255],
        "content": candidate.get("content", "")[:12000],
        "metadata": candidate.get("metadata", {}),
    }
    item, created = MonitoredItem.objects.update_or_create(
        brand=brand,
        source=candidate["source"],
        external_id=candidate["external_id"][:255],
        defaults=defaults,
    )
    return item, created


def scan_brand(brand, source, limit=20):
    """Collect, deduplicate, score, and alert on candidates for one owned brand."""
    if source == MonitoredItem.Source.SOCIAL:
        if not brand.social_search_enabled:
            raise CollectorError("Social monitoring is disabled for this brand profile.")
        candidates, warnings = collect_social_mentions(
            brand,
            limit=limit,
            mastodon_instances=settings.MASTODON_INSTANCES,
        )
    elif source == MonitoredItem.Source.APP_STORE:
        if not brand.app_store_search_enabled:
            raise CollectorError("App Store monitoring is disabled for this brand profile.")
        candidates, warnings = collect_app_listings(
            brand,
            limit=limit,
            country=settings.APPLE_APP_STORE_COUNTRY,
        )
    elif source == MonitoredItem.Source.GOOGLE_PLAY:
        if not brand.google_play_search_enabled:
            raise CollectorError("Google Play monitoring is disabled for this brand profile.")
        candidates, warnings = collect_google_play_listings(
            brand,
            limit=limit,
            country=settings.GOOGLE_PLAY_COUNTRY,
            lang=settings.GOOGLE_PLAY_LANGUAGE,
        )
    else:
        raise ValueError("Unsupported monitoring source.")

    persisted = []
    new_count = 0
    for candidate in candidates:
        if (
            candidate["source"] in (
                MonitoredItem.Source.APP_STORE,
                MonitoredItem.Source.GOOGLE_PLAY,
            )
            and official_app_matches(candidate, brand.official_apps)
        ) or (
            candidate["source"] in SOCIAL_SOURCE_VALUES
            and official_url_matches(
                candidate.get("url", ""), brand.official_social_accounts
            )
        ):
            continue
        item, created = _persist_candidate(brand, candidate)
        new_count += int(created)
        persisted.append((item, created))

    scored = []
    alert_count = 0
    for item, created in persisted:
        score = score_item(item, brand)
        scored.append((item, score, created))

    ai_candidates = [
        item
        for item, score, _ in sorted(
            scored, key=lambda entry: entry[1]["risk_score"], reverse=True
        )
        if score["risk_score"] >= 30
    ][:AI_ANALYSIS_LIMIT]
    ai_candidates = {item.pk for item in ai_candidates}

    for item, score, _ in scored:
        finding = RiskFinding.objects.filter(
            brand=brand, monitored_item=item
        ).order_by("-created_at").first()
        finding, created_alert = record_finding(
            item,
            score=score,
            analyze_ai=item.pk in ai_candidates,
            existing=finding,
        )
        alert_count += int(created_alert)

    return {
        "found": len(candidates),
        "new": new_count,
        "updated": len(persisted) - new_count,
        "scored": len(scored),
        "alerts": alert_count,
        "warnings": warnings,
        "items": [item for item, _, _ in scored],
    }
