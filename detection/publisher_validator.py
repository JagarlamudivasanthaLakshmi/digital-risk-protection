def validate_publisher(publisher, trusted_publishers):
    publisher = publisher.strip().casefold()
    trusted = {
        item.strip().casefold()
        for item in (trusted_publishers or [])
        if item.strip()
    }
    if publisher and trusted and publisher not in trusted:
        return [{"signal": "unverified_publisher", "publisher": publisher, "weight": 20}]
    return []
