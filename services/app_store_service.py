def search_app_listings(brand, limit=25, country="us"):
    from monitoring.collectors.app_store_collector import collect_app_listings

    return collect_app_listings(brand, limit=limit, country=country)
