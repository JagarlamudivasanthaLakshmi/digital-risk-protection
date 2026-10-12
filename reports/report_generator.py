import csv
from io import StringIO


def findings_csv(findings):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(("brand", "item", "score", "severity", "created_at", "explanation"))
    for finding in findings:
        writer.writerow(
            (
                finding.brand.name,
                finding.monitored_item.name if finding.monitored_item else "",
                finding.risk_score,
                finding.severity,
                finding.created_at.isoformat(),
                finding.explanation,
            )
        )
    return output.getvalue()
