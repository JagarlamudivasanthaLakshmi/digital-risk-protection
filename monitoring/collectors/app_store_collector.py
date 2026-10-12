from .providers import CollectorError, get_json, official_app_matches


APPLE_SEARCH_URL = "https://itunes.apple.com/search"


def collect_app_listings(brand, limit=25, country="us"):
    """Search Apple's public App Store search API for applications matching a brand."""
    if not brand.name.strip():
        raise ValueError("A non-empty brand name is required.")
    limit = max(1, min(int(limit), 50))
    payload = get_json(
        APPLE_SEARCH_URL,
        params={
            "term": brand.name,
            "entity": "software",
            "country": country,
            "limit": limit,
        },
    )
    results = []
    for app in payload.get("results", []):
        track_id = app.get("trackId")
        track_name = app.get("trackName")
        if not track_id or not track_name:
            continue
        bundle_id = app.get("bundleId", "")
        item = {
            "source": "app_store",
            "external_id": f"apple:{track_id}",
            "name": track_name,
            "url": app.get("trackViewUrl", ""),
            "publisher": app.get("sellerName", ""),
            "content": app.get("description", "")[:4000],
            "metadata": {
                "provider": "apple_app_store",
                "store_id": str(track_id),
                "bundle_id": bundle_id,
                "version": app.get("version", ""),
                "price": app.get("formattedPrice", ""),
                "artwork": app.get("artworkUrl100", ""),
                "genres": app.get("genres", []),
                "average_rating": app.get("averageUserRating"),
                "rating_count": app.get("userRatingCount"),
            },
        }
        if not official_app_matches(item, brand.official_apps):
            results.append(item)
    return results, []
