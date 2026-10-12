import logging
from urllib.parse import urlsplit


logger = logging.getLogger(__name__)


def normalize_domains(domains):
    """Normalize user-entered domains into hostnames suitable for comparisons."""
    normalized = set()
    for domain in domains or []:
        candidate = str(domain).strip().lower()
        if not candidate:
            continue
        try:
            parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
            hostname = (parsed.hostname or "").strip(".")
        except ValueError:
            logger.debug("Ignored a malformed official domain in a brand profile.")
            continue
        if hostname:
            normalized.add(hostname)
    return sorted(normalized)
