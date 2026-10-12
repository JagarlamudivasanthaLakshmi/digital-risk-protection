def demo_items(brand_name):
    """Return clearly synthetic records for local demonstrations."""
    return [
        {
            "source": "social",
            "name": f"{brand_name} Support (demo)",
            "url": "https://example.invalid/demo-account",
            "publisher": "Unverified demo publisher",
            "content": f"Synthetic monitoring example mentioning {brand_name}.",
        },
        {
            "source": "app_store",
            "name": f"{brand_name} Rewards (demo)",
            "url": "https://example.invalid/demo-app",
            "publisher": "Unverified demo publisher",
            "content": "Synthetic app listing. No real store data was queried.",
        },
    ]
