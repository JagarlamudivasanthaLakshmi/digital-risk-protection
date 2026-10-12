import importlib
import json
import logging
import ssl
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .providers import CollectorError, official_app_matches


logger = logging.getLogger(__name__)
GOOGLE_PLAY_HOST = "play.google.com"
HTTP_TIMEOUT = 8
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_SCRAPER_LOCK = threading.RLock()
_search_module = None


def _load_search_module():
    global _search_module
    if _search_module is None:
        default_context_factory = ssl._create_default_https_context
        try:
            _search_module = importlib.import_module(
                "google_play_scraper.features.search"
            )
        finally:
            ssl._create_default_https_context = default_context_factory
    return _search_module


def _fetch_search_page(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != GOOGLE_PLAY_HOST:
        raise CollectorError("Google Play returned an unexpected search URL.")
    request = Request(
        url,
        headers={"User-Agent": "DigitalRiskProtectionPrototype/1.0"},
    )
    try:
        with urlopen(
            request,
            timeout=HTTP_TIMEOUT,
            context=ssl.create_default_context(),
        ) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        logger.warning("Google Play search returned HTTP status %s.", exc.code)
        raise CollectorError(
            f"Google Play search returned HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("Google Play search request failed: %s", exc.__class__.__name__)
        raise CollectorError(
            "Google Play could not be reached. Check connectivity and try again."
        ) from exc
    if len(content) > MAX_RESPONSE_BYTES:
        raise CollectorError("Google Play returned a response that was too large.")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CollectorError("Google Play returned an invalid response.") from exc


def _search_google_play(query, *, limit, country, lang):
    with _SCRAPER_LOCK:
        try:
            module = _load_search_module()
        except ModuleNotFoundError as exc:
            logger.error("Google Play scraper dependency is unavailable.")
            raise CollectorError(
                "Google Play search is unavailable. Install the project requirements and retry."
            ) from exc
        original_get = module.get
        module.get = _fetch_search_page
        try:
            return module.search(
                query,
                n_hits=limit,
                country=country,
                lang=lang,
            )
        except CollectorError:
            raise
        except (
            AttributeError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning(
                "Google Play search response could not be parsed: %s",
                exc.__class__.__name__,
            )
            raise CollectorError(
                "Google Play returned an unexpected search response."
            ) from exc
        finally:
            module.get = original_get


def collect_google_play_listings(brand, limit=25, country="us", lang="en"):
    """Search Google Play using bounded, certificate-verified public requests."""
    if not brand.name.strip():
        raise ValueError("A non-empty brand name is required.")
    limit = max(1, min(int(limit), 50))
    country = (country or "us").strip().lower()
    lang = (lang or "en").strip().lower()
    search_results = _search_google_play(
        brand.name,
        limit=limit,
        country=country,
        lang=lang,
    )
    if not isinstance(search_results, list):
        raise CollectorError("Google Play returned an unexpected search response.")

    candidates = []
    for app in search_results:
        if not isinstance(app, dict):
            logger.warning("Skipped a malformed Google Play search result.")
            continue
        package_name = app.get("appId")
        title = app.get("title")
        if not package_name or not title:
            continue
        item = {
            "source": "google_play",
            "external_id": f"google_play:{package_name}",
            "name": str(title),
            "url": (
                "https://play.google.com/store/apps/details?id="
                f"{quote(str(package_name), safe='')}&hl={quote(lang)}&gl={quote(country)}"
            ),
            "publisher": str(app.get("developer") or ""),
            "content": str(app.get("description") or "")[:4000],
            "metadata": {
                "provider": "google_play",
                "store_id": str(package_name),
                "bundle_id": str(package_name),
                "artwork": str(app.get("icon") or ""),
                "genre": str(app.get("genre") or ""),
                "score": app.get("score"),
                "installs": str(app.get("installs") or ""),
                "price": app.get("price"),
            },
        }
        if not official_app_matches(item, brand.official_apps):
            candidates.append(item)
    return candidates, []
