def check_domain_reputation(client, domain):
    if not domain.strip():
        raise ValueError("A domain is required.")
    if not hasattr(client, "lookup_domain"):
        raise TypeError("The reputation client must expose lookup_domain(domain).")
    return client.lookup_domain(domain)
