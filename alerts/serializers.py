from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="finding.brand.name", read_only=True)
    severity = serializers.CharField(source="finding.severity", read_only=True)

    class Meta:
        model = Alert
        fields = ("id", "finding", "brand_name", "severity", "status", "assigned_to", "notes", "created_at", "updated_at")
        read_only_fields = ("id", "finding", "brand_name", "severity", "created_at", "updated_at")

    def validate_assigned_to(self, user):
        if user and self.instance and user.pk != self.instance.finding.brand.owner_id:
            raise serializers.ValidationError("You can only assign alerts to the brand owner.")
        return user
