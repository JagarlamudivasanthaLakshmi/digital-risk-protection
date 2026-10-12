from detection.models import RiskFinding

from .graph_builder import build_threat_graph


def graph_for_user(user):
    findings = RiskFinding.objects.filter(brand__owner=user).select_related(
        "brand", "monitored_item"
    )
    return build_threat_graph(findings)
