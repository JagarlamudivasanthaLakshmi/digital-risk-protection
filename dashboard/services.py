from datetime import timedelta
from math import ceil

from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from alerts.models import Alert
from brands.models import Brand
from detection.models import RiskFinding
from monitoring.models import SOCIAL_SOURCE_VALUES, MonitoredItem


APP_SOURCE_VALUES = (MonitoredItem.Source.APP_STORE, MonitoredItem.Source.GOOGLE_PLAY)
SEVERITY_ORDER = ("critical", "high", "medium", "low")


def dashboard_stats(user):
    owned_brands = Brand.objects.filter(owner=user)
    findings = RiskFinding.objects.filter(brand__owner=user)
    social_findings = findings.filter(monitored_item__source__in=SOCIAL_SOURCE_VALUES)
    app_findings = findings.filter(monitored_item__source__in=APP_SOURCE_VALUES)
    total_findings = findings.count()

    colors = {"high": "#f43f46", "medium": "#ff8a00", "low": "#f5b900"}
    severity_data = []
    for severity, label in (("high", "High"), ("medium", "Medium"), ("low", "Low")):
        condition = Q(severity=severity)
        if severity == "high":
            condition |= Q(severity="critical")
        count = findings.filter(condition).count()
        severity_data.append({
            "name": label,
            "severity": severity,
            "count": count,
            "percentage": round(count * 100 / total_findings) if total_findings else 0,
            "color": colors[severity],
        })

    segments = []
    accumulated = 0
    for item in severity_data:
        end = accumulated + item["percentage"]
        if item["count"]:
            segments.append(f"{item['color']} {accumulated}% {end}%")
        accumulated = end
    pie_style = f"conic-gradient({', '.join(segments)})" if segments else "conic-gradient(#e8eef6 0% 100%)"

    today = timezone.localdate()
    first_day = today - timedelta(days=6)
    daily_counts = {
        row["day"]: row
        for row in findings.filter(created_at__date__gte=first_day)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            social=Count("id", filter=Q(monitored_item__source__in=SOCIAL_SOURCE_VALUES)),
            apps=Count("id", filter=Q(monitored_item__source__in=APP_SOURCE_VALUES)),
        )
    }
    trend = []
    for index in range(7):
        day = first_day + timedelta(days=index)
        counts = daily_counts.get(day, {})
        trend.append({
            "label": day.strftime("%b %d").replace(" 0", " "),
            "social": counts.get("social", 0),
            "apps": counts.get("apps", 0),
            "x": 35 + index * 88,
        })
    chart_max = max(10, ceil(max((max(p["social"], p["apps"]) for p in trend), default=0) / 10) * 10)
    for point in trend:
        point["social_y"] = round(130 - point["social"] / chart_max * 110, 1)
        point["apps_y"] = round(130 - point["apps"] / chart_max * 110, 1)

    alert_status = dict(
        Alert.objects.filter(finding__in=findings).values_list("finding_id", "status")
    )
    recent_findings = []
    for finding in findings.select_related("brand", "monitored_item").order_by("-created_at")[:5]:
        item = finding.monitored_item
        source = item.source if item else "web"
        recent_findings.append({
            "finding": finding,
            "source_label": "Social profile" if source in SOCIAL_SOURCE_VALUES else (
                "Mobile app" if source in APP_SOURCE_VALUES else "Web finding"
            ),
            "source_group": "social" if source in SOCIAL_SOURCE_VALUES else "apps",
            "status": alert_status.get(finding.pk, "monitored"),
            "url": f"/alerts/{finding.alert.pk}/" if finding.pk in alert_status else "/detection/analysis/",
        })

    threats = []
    for row in findings.values("brand_id", "brand__name").annotate(count=Count("id")).order_by("-count", "brand__name")[:5]:
        highest = next((severity for severity in SEVERITY_ORDER if findings.filter(
            brand_id=row["brand_id"], severity=severity
        ).exists()), "low")
        threats.append({
            "name": row["brand__name"],
            "count": row["count"],
            "severity": "high" if highest in ("critical", "high") else highest,
            "initial": (row["brand__name"] or "?")[0].upper(),
        })

    monitored = MonitoredItem.objects.filter(brand__in=owned_brands)
    return {
        "brand_count": owned_brands.count(),
        "monitored_count": monitored.count(),
        "alert_count": Alert.objects.filter(finding__brand__owner=user).count(),
        "social_detection_count": social_findings.count(),
        "app_detection_count": app_findings.count(),
        "detection_count": total_findings,
        "severity_data": severity_data,
        "pie_style": pie_style,
        "trend": trend,
        "trend_top_label": chart_max,
        "trend_mid_label": chart_max // 2,
        "trend_social_points": " ".join(f"{p['x']},{p['social_y']}" for p in trend),
        "trend_app_points": " ".join(f"{p['x']},{p['apps_y']}" for p in trend),
        "recent_findings": recent_findings,
        "top_threats": threats,
        "last_scan_at": monitored.aggregate(last=Max("last_seen_at"))["last"],
        "open_alert_count": Alert.objects.filter(
            finding__brand__owner=user, status=Alert.Status.OPEN
        ).count(),
        "investigation_count": Alert.objects.filter(
            finding__brand__owner=user, status=Alert.Status.INVESTIGATING
        ).count(),
        "resolved_count": Alert.objects.filter(
            finding__brand__owner=user, status=Alert.Status.RESOLVED
        ).count(),
        "high_risk_count": findings.filter(severity__in=("high", "critical")).count(),
    }
