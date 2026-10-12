from rest_framework import serializers


class DashboardStatsSerializer(serializers.Serializer):
    brand_count = serializers.IntegerField()
    monitored_count = serializers.IntegerField()
    open_alert_count = serializers.IntegerField()
    high_risk_count = serializers.IntegerField()
