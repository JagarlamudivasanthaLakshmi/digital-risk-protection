from .models import Alert


def filter_alerts(queryset, params):
    status = params.get("status")
    severity = params.get("severity")
    if status in Alert.Status.values:
        queryset = queryset.filter(status=status)
    if severity in ("low", "medium", "high", "critical"):
        queryset = queryset.filter(finding__severity=severity)
    return queryset
