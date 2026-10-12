def is_allowlisted(url, allowlist):
    """Match exact hostnames or their subdomains against a list of allowed domains."""
    from urllib.parse import urlsplit

    parsed = urlsplit(url if "://" in url else f"//{url}")
    hostname = (parsed.hostname or "").lower().strip(".")
    return any(
        hostname == domain.lower().strip(".")
        or hostname.endswith(f".{domain.lower().strip('.')}")
        for domain in allowlist
        if domain.strip()
    )
