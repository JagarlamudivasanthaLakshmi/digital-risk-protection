from rest_framework import serializers

from brands.models import Brand
from .models import MonitoredItem


class MonitoredItemSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = MonitoredItem
        fields = (
            "id", "brand", "brand_name", "source", "external_id", "name",
            "url", "publisher", "content", "metadata", "last_seen_at", "created_at",
        )
        read_only_fields = ("id", "last_seen_at", "created_at")

    def validate_brand(self, brand):
        if brand.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("You can only monitor brands you own.")
        return brand


class MonitoringScanSerializer(serializers.Serializer):
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.none())
    source = serializers.ChoiceField(choices=("social", "app_store", "google_play"))
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["brand"].queryset = Brand.objects.filter(owner=request.user)
