from urllib.parse import urlsplit

from brands.services import normalize_domains


def analyze_url(url, official_domains):
    parsed = urlsplit(url if "://" in url else f"//{url}")
    hostname = (parsed.hostname or "").lower().strip(".")
    official = normalize_domains(official_domains)
    if not hostname or not official:
        return []
    if any(hostname == domain or hostname.endswith(f".{domain}") for domain in official):
        return []
    return [{"signal": "unofficial_domain", "hostname": hostname, "weight": 35}]
