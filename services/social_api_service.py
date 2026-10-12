def search_social_mentions(brand, limit=20, mastodon_instances=None):
    from monitoring.collectors.social_collector import collect_social_mentions

    return collect_social_mentions(
        brand, limit=limit, mastodon_instances=mastodon_instances
    )
