import logging
import re
from urllib.parse import urlsplit

import requests


logger = logging.getLogger(__name__)
HTTP_TIMEOUT = (3.05, 8)


class CollectorError(Exception):
    """Raised when an external monitoring source cannot be queried."""


def get_json(url, *, params=None):
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": "DigitalRiskProtectionPrototype/1.0"},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        logger.warning("Monitoring provider returned invalid JSON.")
        raise CollectorError("The provider returned an invalid response.") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning("Monitoring provider returned HTTP status %s.", status)
        raise CollectorError(f"The provider returned HTTP {status}.") from exc
    except requests.RequestException as exc:
        logger.warning("Monitoring provider request failed: %s", exc.__class__.__name__)
        raise CollectorError("The provider could not be reached. Check connectivity and try again.") from exc
    except ValueError as exc:
        logger.warning("Monitoring provider returned a non-JSON response.")
        raise CollectorError("The provider returned an invalid response.") from exc
    if not isinstance(payload, dict):
        raise CollectorError("The provider response had an unexpected format.")
    return payload


def official_url_matches(candidate_url, official_urls):
    candidate = urlsplit(candidate_url or "")
    candidate_host = (candidate.hostname or "").casefold().removeprefix("www.")
    if not candidate_host:
        return False
    candidate_path = candidate.path.rstrip("/").casefold()
    for official_url in official_urls or []:
        parsed = urlsplit(
            official_url if "://" in official_url else f"https://{official_url}"
        )
        official_host = (parsed.hostname or "").casefold().removeprefix("www.")
        official_path = parsed.path.rstrip("/").casefold()
        if candidate_host == official_host and (
            not official_path or candidate_path == official_path
        ):
            return True
    return False


def official_app_matches(candidate, official_apps):
    candidate_ids = {
        str(candidate.get("external_id", "")).casefold(),
        str(candidate.get("metadata", {}).get("bundle_id", "")).casefold(),
        str(candidate.get("metadata", {}).get("store_id", "")).casefold(),
    }
    candidate_url = str(candidate.get("url", "")).rstrip("/").casefold()
    for official in official_apps or []:
        value = str(official).strip()
        if not value:
            continue
        folded = value.casefold().rstrip("/")
        if folded in candidate_ids or folded == candidate_url:
            return True
        try:
            urlsplit(value if "://" in value else f"https://{value}")
        except ValueError:
            logger.debug("Ignored a malformed official app asset in a brand profile.")
            continue
        app_ids = re.findall(r"id(\d+)", value, re.IGNORECASE)
        if any(app_id.casefold() in candidate_ids for app_id in app_ids):
            return True
    return False
