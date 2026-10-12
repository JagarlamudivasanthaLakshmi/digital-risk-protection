def build_threat_graph(findings):
    nodes = {}
    edges = []
    for finding in findings:
        brand_id = f"brand-{finding.brand_id}"
        nodes[brand_id] = {"id": brand_id, "label": finding.brand.name, "kind": "brand"}
        if finding.monitored_item_id:
            item_id = f"item-{finding.monitored_item_id}"
            nodes[item_id] = {
                "id": item_id,
                "label": finding.monitored_item.name,
                "kind": finding.monitored_item.source,
            }
            edges.append({"source": brand_id, "target": item_id, "finding": finding.pk})
    return {"nodes": list(nodes.values()), "edges": edges}
