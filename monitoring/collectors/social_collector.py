from urllib.parse import quote
from urllib.parse import urlsplit

from django.conf import settings

from .providers import CollectorError, get_json, official_url_matches


BLUESKY_SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"


def collect_social_mentions(brand, limit=20, mastodon_instances=None):
    """Search Bluesky and configured public Mastodon servers for brand profiles."""
    if not brand.name.strip():
        raise ValueError("A non-empty search query is required.")
    limit = max(1, min(int(limit), 50))
    results = []
    errors = []
    try:
        payload = get_json(
            BLUESKY_SEARCH_URL,
            params={"q": brand.name, "limit": limit},
        )
        for actor in payload.get("actors", []):
            handle = actor.get("handle", "")
            did = actor.get("did", "")
            if not handle or not did:
                continue
            item = {
                "source": "social",
                "external_id": f"bluesky:{did}",
                "name": actor.get("displayName") or handle,
                "url": f"https://bsky.app/profile/{quote(handle, safe='.')}",
                "publisher": "Bluesky",
                "content": actor.get("description", "")[:4000],
                "metadata": {
                    "provider": "bluesky",
                    "handle": handle,
                    "avatar": actor.get("avatar", ""),
                    "followers": actor.get("followersCount"),
                },
            }
            if not official_url_matches(item["url"], brand.official_social_accounts):
                results.append(item)
    except CollectorError as exc:
        errors.append(f"Bluesky: {exc}")

    instances = mastodon_instances or getattr(settings, "MASTODON_INSTANCES", [])
    for instance in instances:
        parsed_instance = str(instance).strip().rstrip("/")
        if not parsed_instance:
            continue
        if "://" not in parsed_instance:
            parsed_instance = f"https://{parsed_instance}"
        instance_url = urlsplit(parsed_instance)
        if instance_url.scheme != "https" or not instance_url.hostname:
            errors.append("Mastodon: configured instances must use HTTPS.")
            continue
        try:
            payload = get_json(
                f"{parsed_instance}/api/v2/search",
                params={"q": brand.name, "type": "accounts", "limit": min(limit, 40)},
            )
            for account in payload.get("accounts", []):
                account_url = account.get("url", "")
                account_id = account.get("id", "")
                if not account_url or not account_id:
                    continue
                item = {
                    "source": "social",
                    "external_id": f"mastodon:{urlsplit_host(parsed_instance)}:{account_id}",
                    "name": account.get("display_name") or account.get("acct", ""),
                    "url": account_url,
                    "publisher": "Mastodon",
                    "content": account.get("note", "")[:4000],
                    "metadata": {
                        "provider": "mastodon",
                        "instance": urlsplit_host(parsed_instance),
                        "acct": account.get("acct", ""),
                        "followers": account.get("followers_count"),
                    },
                }
                if not official_url_matches(item["url"], brand.official_social_accounts):
                    results.append(item)
        except CollectorError as exc:
            errors.append(f"{parsed_instance}: {exc}")

    if not results and errors:
        raise CollectorError(" ".join(errors))
    return results[:limit], errors


def urlsplit_host(url):
    from urllib.parse import urlsplit

    return urlsplit(url).hostname or ""
