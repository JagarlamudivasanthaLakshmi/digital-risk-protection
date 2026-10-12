from rest_framework import serializers

from .models import RiskFinding


class RiskFindingSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    item_name = serializers.CharField(source="monitored_item.name", read_only=True)

    class Meta:
        model = RiskFinding
        fields = (
            "id", "brand", "brand_name", "monitored_item", "item_name", "risk_score",
            "severity", "signals", "explanation", "ai_status", "ai_summary",
            "ai_recommendation", "ai_error", "created_at",
        )
        read_only_fields = fields
