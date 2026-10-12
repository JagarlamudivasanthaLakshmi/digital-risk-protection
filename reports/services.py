from detection.models import RiskFinding

from .report_generator import findings_csv


def user_findings_csv(user):
    findings = RiskFinding.objects.filter(brand__owner=user).select_related(
        "brand", "monitored_item"
    )
    return findings_csv(findings)
