from .models import Alert


def create_alert_for_finding(finding):
    alert, _ = get_or_create_alert_for_finding(finding)
    return alert


def get_or_create_alert_for_finding(finding):
    return Alert.objects.get_or_create(finding=finding)
